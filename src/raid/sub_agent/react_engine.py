"""ReAct Engine for Sub-Agents - Focused on tool-based task execution"""

import json
import asyncio
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from pydantic import BaseModel
from datetime import datetime

if TYPE_CHECKING:
    from ..llm_backend.interface import LLMBackend
    from ..tools.base import ToolRegistry

from ..llm_backend.interface import LLMMessage
from ..message_queue.models import TaskMessage, ResultMessage


class SubAgentReActStep(BaseModel):
    """A single step in the Sub-Agent ReAct cycle"""
    step_number: int
    thought: str
    action: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    timestamp: datetime
    
    @classmethod
    def create_thought(cls, step_number: int, thought: str) -> "SubAgentReActStep":
        """Create a thought step"""
        return cls(
            step_number=step_number,
            thought=thought,
            timestamp=datetime.utcnow()
        )
    
    def add_action(self, action: Dict[str, Any]) -> None:
        """Add action to this step"""
        self.action = action
    
    def add_observation(self, observation: str) -> None:
        """Add observation to this step"""
        self.observation = observation


class SubAgentTaskContext(BaseModel):
    """Context for the current task being processed by Sub-Agent"""
    task_id: str
    task_prompt: str
    steps: List[SubAgentReActStep]
    status: str  # "in_progress", "completed", "failed"
    final_result: Optional[str] = None
    created_at: datetime
    
    @classmethod
    def create(cls, task_id: str, task_prompt: str) -> "SubAgentTaskContext":
        """Create a new task context"""
        return cls(
            task_id=task_id,
            task_prompt=task_prompt,
            steps=[],
            status="in_progress",
            created_at=datetime.utcnow()
        )
    
    def add_step(self, step: SubAgentReActStep) -> None:
        """Add a step to the context"""
        self.steps.append(step)
    
    def get_current_step_number(self) -> int:
        """Get the next step number"""
        return len(self.steps) + 1
    
    def complete_success(self, result: str) -> None:
        """Mark task as completed successfully"""
        self.status = "completed"
        self.final_result = result
    
    def complete_failure(self, reason: str) -> None:
        """Mark task as failed"""
        self.status = "failed"
        self.final_result = reason


class SubAgentReActEngine:
    """ReAct Engine for Sub-Agents implementing Thought-Action-Observation cycles"""
    
    def __init__(
        self, 
        llm_backend: "LLMBackend", 
        tool_registry: "ToolRegistry",
        agent_name: str,
        system_prompt: str,
        max_steps: int = 20,
        collaboration_context_provider=None,  # Function to get collaboration context
        calculation_result_sharer=None  # ADDED: Function to share calculation results
    ):
        self.llm_backend = llm_backend
        self.tool_registry = tool_registry
        self.agent_name = agent_name
        self.base_system_prompt = system_prompt
        self.max_steps = max_steps
        self.get_collaboration_context = collaboration_context_provider
        self.share_calculation_result = calculation_result_sharer  # ADDED
    
    def _create_react_system_prompt(self) -> str:
        """Create ReAct-enhanced system prompt for the Sub-Agent"""
        # Get available tools
        tool_descriptions = []
        for tool in self.tool_registry.get_all_tools().values():
            params_desc = ", ".join([
                f"{p.name} ({p.type}): {p.description}"
                for p in tool.parameters
            ])
            tool_descriptions.append(
                f"- {tool.name}: {tool.description}\n  Parameters: {params_desc}"
            )
        
        tools_section = "\n".join(tool_descriptions) if tool_descriptions else "No tools available."
        
        # Add collaboration context if available
        collaboration_context = ""
        if self.get_collaboration_context:
            try:
                collaboration_context = self.get_collaboration_context()
                if collaboration_context:
                    collaboration_context = f"\n\n{collaboration_context}"
            except Exception as e:
                print(f"Warning: Failed to get collaboration context: {e}")
                collaboration_context = ""
        
        return f"""{self.base_system_prompt}

Available Tools:
{tools_section}

ReAct Process for Task Execution:
You must use a Thought-Action-Observation cycle to complete tasks:

1. **Thought**: Analyze the current situation and plan your next action
2. **Action**: Either use a tool or provide your final answer
3. **Observation**: Analyze the tool result and determine if more actions are needed

To use a tool, respond with a JSON object in this format:
{{
    "thought": "Your reasoning about what to do next",
    "action": {{
        "tool": "tool_name",
        "parameters": {{"param1": "value1", "param2": "value2"}}
    }}
}}

To provide your final answer (when task is complete), respond with:
{{
    "thought": "I have completed the task successfully",
    "final_answer": "Your comprehensive final answer here"
}}

Guidelines:
- Always think step-by-step before taking action
- Use tools when you need to perform calculations, search, or process data
- Be precise and methodical in your approach
- Provide clear, complete final answers
- If you encounter errors, think about alternative approaches{collaboration_context}"""
    
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """Process a task using ReAct cycles"""
        context = SubAgentTaskContext.create(task.task_id, task.prompt)
        
        print("\n" + "="*50)
        print(f"🤖 Sub-Agent '{self.agent_name}' starting task...")
        print(f"🎯 Goal: {task.prompt}")
        print("="*50 + "\n")
        
        try:
            for step_num in range(1, self.max_steps + 1):
                print(f"🔄 ReAct Step {step_num}")
                
                # Generate thought and action
                step = await self._generate_thought_and_action(context, step_num)
                context.add_step(step)

                # Log the thought process immediately
                print(f"   🤔 Thought: {step.thought}")
                
                # Check if this is a final answer
                if self._is_final_answer(step):
                    final_answer = self._extract_final_answer(step)
                    context.complete_success(final_answer)
                    print(f"   ✅ Final Answer: {final_answer}")
                    print("\n" + "="*50)
                    print("✅ Task Completed Successfully!")
                    print("="*50 + "\n")
                    break
                
                if not step.action:
                    print("   ❌ Error: No action generated.")
                    context.complete_failure("Failed to generate valid action")
                    break
                
                # Execute action (tool)
                print(f"   🎬 Action: {step.action.get('tool')} with params {step.action.get('parameters', {})}")
                observation = await self._execute_tool_action(step.action)

                # Truncate long observations to prevent context overflow
                max_obs_length = 15000
                if len(observation) > max_obs_length:
                    half_len = max_obs_length // 2
                    truncated_observation = (
                        f"{observation[:half_len]}\n\n"
                        "... [OUTPUT TRUNCATED] ...\n\n"
                        f"{observation[-half_len:]}"
                    )
                    step.add_observation(truncated_observation)
                    print(f"   👀 Observation (truncated): {truncated_observation}")
                else:
                    step.add_observation(observation)
                    print(f"   👀 Observation: {observation}")
                
                # Check for tool errors that might require stopping
                if "Error:" in observation:
                    # Allow the LLM to process the error in the next thought step
                    pass
                
                print("-" * 40)

            if context.status == "in_progress":
                context.complete_failure("Reached max steps without completing the task")
                print("\n" + "="*50)
                print(f"❌ Task Failed: Reached max steps ({self.max_steps})")
                print("="*50 + "\n")

        except Exception as e:
            print(f"❌ An unexpected error occurred: {e}")
            import traceback
            traceback.print_exc()
            context.complete_failure(str(e))
        
        if context.status == "completed":
            return ResultMessage.success(
                task_id=context.task_id,
                correlation_id=task.correlation_id,
                result=context.final_result or "Completed"
            )
        else:
            return ResultMessage.create_error(
                task_id=context.task_id,
                correlation_id=task.correlation_id,
                error=context.final_result or "Unknown error"
            )
    
    async def _generate_thought_and_action(self, context: SubAgentTaskContext, step_num: int) -> SubAgentReActStep:
        """Generate thought and action using LLM"""
        # Build conversation history for LLM
        messages: List[LLMMessage] = [
            LLMMessage(role="system", content=self._create_react_system_prompt())
        ]
        
        # Add original task prompt
        messages.append(LLMMessage(role="user", content=context.task_prompt))
        
        # Add previous steps to conversation history
        for step in context.steps:
            if step.thought:
                # Reconstruct the LLM's last JSON response
                llm_response = {"thought": step.thought}
                if step.action:
                    llm_response["action"] = step.action
                elif self._is_final_answer(step):
                     llm_response["final_answer"] = self._extract_final_answer(step)
                
                messages.append(LLMMessage(role="assistant", content=json.dumps(llm_response)))

            if step.observation:
                # Observation from tool execution
                messages.append(LLMMessage(
                    role="user", 
                    content=f"Observation: {step.observation}"
                ))

        response = await self.llm_backend.generate(messages)
        response_content = response.content
        
        try:
            parsed_response = self._parse_react_response(response_content)
            
            thought = parsed_response.get("thought", "No thought provided.")
            step = SubAgentReActStep.create_thought(step_num, thought)
            
            if "action" in parsed_response:
                step.add_action(parsed_response["action"])
            elif "final_answer" in parsed_response:
                # This is a final answer, encapsulate it in an "action" for consistency
                step.add_action({"tool": "final_answer", "parameters": {"answer": parsed_response["final_answer"]}})
            
            return step

        except json.JSONDecodeError:
            return SubAgentReActStep.create_thought(step_num, f"Received invalid, non-JSON response from LLM: {response_content}")
        except Exception as e:
            return SubAgentReActStep.create_thought(step_num, f"Error parsing LLM response: {e}")

    def _parse_react_response(self, response_content: str) -> Dict[str, Any]:
        """Parse the JSON response from the LLM"""
        try:
            # The response might be wrapped in ```json ... ```
            if response_content.strip().startswith("```json"):
                json_part = response_content.strip().split("```json")[1].split("```")[0]
            else:
                json_part = response_content
            
            return json.loads(json_part)
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Error decoding JSON from LLM response: {e}\nRaw response: {response_content}")
            raise
    
    async def _execute_tool_action(self, action: Dict[str, Any]) -> str:
        """Execute a tool action and return the observation"""
        tool_name = action.get("tool")
        tool_params = action.get("parameters", {})
        
        if tool_name == "final_answer":
            return f"Task marked as complete with final answer: {tool_params.get('answer')}"

        if not tool_name:
            return "Error: No tool name provided in action"
        
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            return f"Error: Tool '{tool_name}' not found"
        
        try:
            result = await tool.execute(**tool_params)
            
            # If it's the calculator tool, share the result via collaboration
            if tool_name == "calculator" and self.share_calculation_result:
                try:
                    await self.share_calculation_result(str(result))
                except Exception as e:
                    print(f"Warning: Failed to share calculation result via collaboration: {e}")
            
            return str(result)
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"

    def _is_final_answer(self, step: SubAgentReActStep) -> bool:
        """Check if the action is a final answer"""
        return step.action and step.action.get("tool") == "final_answer"
    
    def _extract_final_answer(self, step: SubAgentReActStep) -> str:
        """Extract the final answer from the action"""
        if self._is_final_answer(step):
            return step.action.get("parameters", {}).get("answer", "No answer provided.")
        return "" 
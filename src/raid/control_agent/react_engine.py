"""ReAct Engine for Control Agent - Thought, Action, Observation loop"""

import json
import asyncio
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from pydantic import BaseModel
from datetime import datetime

if TYPE_CHECKING:
    from ..llm_backend.interface import LLMBackend
    from .meta_tools import MetaToolRegistry

from ..llm_backend.interface import LLMMessage


class ReActStep(BaseModel):
    """A single step in the ReAct cycle"""
    step_number: int
    thought: str
    action: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    timestamp: datetime
    
    @classmethod
    def create_thought(cls, step_number: int, thought: str) -> "ReActStep":
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


class TaskContext(BaseModel):
    """Context for the current task being processed"""
    task_id: str
    user_goal: str
    steps: List[ReActStep]
    status: str  # "in_progress", "completed", "failed"
    final_result: Optional[str] = None
    created_at: datetime
    
    @classmethod
    def create(cls, task_id: str, user_goal: str) -> "TaskContext":
        """Create a new task context"""
        return cls(
            task_id=task_id,
            user_goal=user_goal,
            steps=[],
            status="in_progress",
            created_at=datetime.utcnow()
        )
    
    def add_step(self, step: ReActStep) -> None:
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


class ReActEngine:
    """ReAct Engine implementing Thought-Action-Observation cycles"""
    
    def __init__(
        self, 
        llm_backend: "LLMBackend", 
        meta_tool_registry: "MetaToolRegistry",
        max_steps: int = 10
    ):
        self.llm_backend = llm_backend
        self.meta_tool_registry = meta_tool_registry
        self.max_steps = max_steps
        
        # Create system prompt for Control Agent
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self) -> str:
        """Create system prompt for the Control Agent"""
        tool_descriptions = []
        for tool in self.meta_tool_registry.get_all_tools().values():
            params_desc = ", ".join([
                f"{p.name} ({p.type}): {p.description}"
                for p in tool.parameters
            ])
            tool_descriptions.append(
                f"- {tool.name}: {tool.description}\\n  Parameters: {params_desc}"
            )
        
        tools_section = "\\n".join(tool_descriptions)
        
        return f"""You are RaidControl, a master AI orchestrator managing specialized Sub-Agents to accomplish user goals.

Your Role:
- Operate using Thought-Action-Observation cycles to achieve user requests
- Intelligently delegate tasks to specialized Sub-Agents when needed
- Think step-by-step and reason about the best approach
- Use your meta-tools to discover, orchestrate, and coordinate Sub-Agents

Available Meta-Tools:
{tools_section}

ReAct Process:
1. **Thought**: Analyze the user's goal, consider available Sub-Agents, and plan your next action
2. **Action**: Choose and execute a meta-tool (or conclude the task)
3. **Observation**: Analyze the result and determine next steps

To use a meta-tool, respond with a JSON object in this format:
{{
    "thought": "Your reasoning about what to do next",
    "action": {{
        "tool": "meta_tool_name",
        "parameters": {{"param1": "value1", "param2": "value2"}}
    }}
}}

To conclude successfully:
{{
    "thought": "Task is complete, summarizing results",
    "action": {{
        "tool": "conclude_task_success",
        "parameters": {{"final_summary": "What was accomplished"}}
    }}
}}

To conclude with failure:
{{
    "thought": "Cannot complete the task because...",
    "action": {{
        "tool": "conclude_task_failure", 
        "parameters": {{"reason": "Why the task failed"}}
    }}
}}

Guidelines:
- Always start by understanding what Sub-Agents are available
- Break complex tasks into Sub-Agent-appropriate subtasks  
- Be specific and clear in your Sub-Agent task prompts
- Monitor and validate Sub-Agent results
- Provide comprehensive final summaries"""
    
    async def process_goal(self, user_goal: str, task_id: Optional[str] = None) -> TaskContext:
        """Process a user goal using ReAct cycles"""
        if not task_id:
            import uuid
            task_id = str(uuid.uuid4())
        
        context = TaskContext.create(task_id, user_goal)
        
        print(f"🎯 Starting ReAct processing for goal: {user_goal}")
        print(f"📋 Task ID: {task_id}")
        
        for step_num in range(1, self.max_steps + 1):
            print(f"\\n🔄 ReAct Step {step_num}")
            
            # Generate thought and action
            step = await self._generate_thought_and_action(context, step_num)
            context.add_step(step)
            
            if not step.action:
                print(f"❌ No action generated in step {step_num}")
                context.complete_failure("Failed to generate valid action")
                break
            
            # Execute action
            observation = await self._execute_action(step.action)
            step.add_observation(observation)
            
            print(f"💭 Thought: {step.thought}")
            print(f"🎬 Action: {step.action['tool']} with {step.action.get('parameters', {})}")
            print(f"👀 Observation: {observation}")
            
            # Check if task is concluded
            if self._is_task_concluded(observation):
                if "TASK_COMPLETED_SUCCESSFULLY" in observation:
                    result = observation.replace("TASK_COMPLETED_SUCCESSFULLY: ", "")
                    context.complete_success(result)
                    print(f"✅ Task completed successfully!")
                elif "TASK_FAILED" in observation:
                    reason = observation.replace("TASK_FAILED: ", "")
                    context.complete_failure(reason)
                    print(f"❌ Task failed: {reason}")
                break
        
        if context.status == "in_progress":
            context.complete_failure(f"Maximum steps ({self.max_steps}) reached without completion")
            print(f"⚠️ Task reached maximum steps without completion")
        
        return context
    
    async def _generate_thought_and_action(self, context: TaskContext, step_num: int) -> ReActStep:
        """Generate thought and action for the current step"""
        
        # Create conversation history
        messages = [LLMMessage(role="system", content=self.system_prompt)]
        
        # Add user goal
        messages.append(LLMMessage(
            role="user", 
            content=f"Goal: {context.user_goal}\\n\\nPlease think about this goal and decide on your first action."
        ))
        
        # Add previous steps as conversation history
        for prev_step in context.steps:
            if prev_step.action and prev_step.observation:
                # Add assistant's thought+action
                assistant_content = json.dumps({
                    "thought": prev_step.thought,
                    "action": prev_step.action
                }, indent=2)
                messages.append(LLMMessage(role="assistant", content=assistant_content))
                
                # Add observation as user message
                messages.append(LLMMessage(role="user", content=f"Observation: {prev_step.observation}"))
        
        if step_num > 1:
            messages.append(LLMMessage(
                role="user", 
                content="Based on the previous observations, what is your next thought and action?"
            ))
        
        # Get LLM response
        try:
            response = await self.llm_backend.generate(messages)
            parsed_response = self._parse_react_response(response.content)
            
            step = ReActStep.create_thought(step_num, parsed_response.get("thought", ""))
            if "action" in parsed_response:
                step.add_action(parsed_response["action"])
            
            return step
            
        except Exception as e:
            print(f"Error generating thought/action: {e}")
            step = ReActStep.create_thought(step_num, f"Error in reasoning: {str(e)}")
            step.add_action({
                "tool": "conclude_task_failure",
                "parameters": {"reason": f"Internal error: {str(e)}"}
            })
            return step
    
    def _parse_react_response(self, response_content: str) -> Dict[str, Any]:
        """Parse LLM response into thought and action"""
        try:
            # First try to parse as raw JSON
            content = response_content.strip()
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError:
            try:
                # Try to extract JSON from code blocks
                import re
                json_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1)
                    parsed = json.loads(json_content)
                    return parsed
                
                # Try to extract JSON without code blocks
                json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1)
                    parsed = json.loads(json_content)
                    return parsed
                    
            except json.JSONDecodeError:
                pass
            
            # If all else fails, log and return error
            print(f"⚠️ Failed to parse JSON response: {response_content}")
            return {
                "thought": "Failed to parse response properly",
                "action": {
                    "tool": "conclude_task_failure",
                    "parameters": {"reason": "Invalid response format from Control Agent"}
                }
            }
    
    async def _execute_action(self, action: Dict[str, Any]) -> str:
        """Execute a meta-tool action"""
        try:
            tool_name = action.get("tool")
            parameters = action.get("parameters", {})
            
            if not tool_name:
                return "Error: No tool specified in action"
            
            meta_tool = self.meta_tool_registry.get_tool(tool_name)
            result = await meta_tool.execute(**parameters)
            return result
            
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error executing action: {str(e)}"
    
    def _is_task_concluded(self, observation: str) -> bool:
        """Check if the task has been concluded"""
        return ("TASK_COMPLETED_SUCCESSFULLY" in observation or 
                "TASK_FAILED" in observation)
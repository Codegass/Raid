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
                f"- {tool.name}: {tool.description}\n  Parameters: {params_desc}"
            )
        
        tools_section = "\n".join(tool_descriptions)
        
        return f"""🎯 YOU ARE RAIDCONTROL - SUPREME ORCHESTRATOR & STRATEGIC COMMANDER

## YOUR SUPREME AUTHORITY
You are the ultimate control and planning authority for the entire multi-agent system. You have complete oversight, strategic decision-making power, and coordination responsibility for accomplishing user goals through intelligent orchestration of specialized Sub-Agents.

## CORE RESPONSIBILITIES
1. **Strategic Planning**: Decompose complex goals into optimal sub-task sequences
2. **Resource Allocation**: Intelligently assign tasks to the most appropriate existing Sub-Agents
3. **Progress Coordination**: Monitor execution, adapt strategies, and ensure successful completion
4. **System Optimization**: Maximize efficiency by leveraging existing capabilities before creating new resources

## 🚨 CRITICAL DIRECTIVE: PREFER EXISTING STATIC PROFILES
**ALWAYS use existing static Sub-Agent profiles before considering dynamic creation. Dynamic agents should be your LAST RESORT.**

### 📋 STATIC SUB-AGENT PROFILES (YOUR PRIMARY RESOURCES)

#### 🛠️ **setup_agent** (PERSISTENT, MOST COMPREHENSIVE)
- **Capabilities**: Project environment setup, repository management, build systems, development infrastructure
- **Tools**: run_python_code, run_bash_command, websearch, network_request, create_file, read_file, list_files, delete_file, notification_user
- **Specializes in**: Git operations, dependency installation, build verification, CI/CD setup, environment configuration
- **Model**: o4-mini (advanced reasoning)
- **Lifecycle**: Persistent (never auto-cleaned), excluded from agent limits
- **Use for**: Any project setup, repository cloning, environment configuration, build tasks, infrastructure preparation

#### 🔧 **advanced_agent** (SYSTEM INTEGRATION SPECIALIST)
- **Capabilities**: Multi-domain coordination, system automation, complex workflows
- **Tools**: run_python_code, run_bash_command, websearch, network_request, create_file, read_file, list_files, delete_file
- **Specializes in**: System integration, workflow automation, multi-step processes, cross-domain tasks
- **Model**: gpt-4.1 (high capability)
- **Use for**: Complex automation, system integration, multi-step workflows, cross-domain coordination

#### 💻 **developer_agent** (SOFTWARE DEVELOPMENT)
- **Capabilities**: Software development, coding, technical implementation
- **Tools**: run_python_code, run_bash_command, create_file, read_file, list_files, delete_file
- **Specializes in**: Code writing, debugging, software architecture, technical problem solving
- **Model**: gpt-4.1 (high capability)
- **Use for**: Code development, debugging, software architecture, technical implementation

#### 🔍 **research_agent** (INFORMATION SPECIALIST)
- **Capabilities**: Information gathering, analysis, knowledge synthesis
- **Tools**: websearch, network_request, create_file, read_file
- **Specializes in**: Web research, data gathering, information analysis, knowledge compilation
- **Model**: gpt-4.1 (high capability)
- **Use for**: Web research, information gathering, data analysis, knowledge synthesis

#### 🧮 **calculator_agent** (MATHEMATICAL SPECIALIST)
- **Capabilities**: Mathematical computations, numerical analysis
- **Tools**: calculator, run_python_code
- **Specializes in**: Arithmetic, algebra, statistical calculations, mathematical modeling
- **Model**: gpt-4o-mini (optimized for calculations)
- **Use for**: Any mathematical operations, calculations, numerical analysis, statistical work

## ⚖️ PROFILE SELECTION DECISION MATRIX
**Follow this hierarchy strictly:**

1. **Mathematical/Numerical Tasks** → `calculator_agent`
2. **Project Setup/Environment Configuration** → `setup_agent` (PERSISTENT)
3. **Web Research/Information Gathering** → `research_agent`
4. **Software Development/Coding** → `developer_agent`
5. **Complex System Integration/Multi-domain** → `advanced_agent`
6. **Multi-Agent Collaboration Required** → `create_collaborative_sub_agent_group`
7. **No Static Profile Adequate** → `create_specialized_sub_agent` (LAST RESORT)

## ⚠️ DYNAMIC AGENT CREATION POLICY
**ONLY create dynamic agents when ALL of the following are true:**
1. **No existing static profile can handle the task** (you must explicitly justify this)
2. **Task requires highly specialized domain knowledge** not covered by static profiles
3. **Need very specific tool combinations** not available in any static profile
4. **Task requires unique system prompts** for niche use cases

**Before creating any dynamic agent, you MUST:**
- Explicitly state why each relevant static profile is insufficient
- Justify the specific need for dynamic creation
- Explain what unique capabilities the dynamic agent provides

## 🎯 STRATEGIC PLANNING METHODOLOGY

### Phase 1: Goal Analysis & Decomposition
1. **Understand the complete user goal**
2. **Identify all sub-tasks and dependencies**
3. **Assess complexity and resource requirements**
4. **Plan optimal execution sequence**

### Phase 2: Resource Mapping
1. **ALWAYS start with `discover_sub_agent_profiles`** to understand available resources
2. **Map each sub-task to most appropriate static profile**
3. **Identify any gaps that might require dynamic agents** (rare)
4. **Plan coordination and data flow between agents**

### Phase 3: Execution & Coordination
1. **Dispatch tasks in optimal sequence**
2. **Monitor progress and adapt strategy**
3. **Coordinate between multiple agents when needed**
4. **Validate results and ensure quality**

### Phase 4: Completion & Summary
1. **Synthesize all results**
2. **Verify goal achievement**
3. **Provide comprehensive final summary**

## 📡 AVAILABLE META-TOOLS
{tools_section}

## 🔄 REACT PROCESS FORMAT
Respond with JSON in this exact format:

```json
{{
    "thought": "Your strategic analysis and reasoning",
    "action": {{
        "tool": "meta_tool_name",
        "parameters": {{"param1": "value1", "param2": "value2"}}
    }}
}}
```

## 🎯 SUCCESS CRITERIA
- **Efficiency**: Maximize use of existing static profiles
- **Quality**: Ensure all sub-tasks are completed successfully
- **Coordination**: Seamlessly orchestrate multiple agents when needed
- **Adaptability**: Adjust strategy based on results and observations
- **Completeness**: Achieve user goals with comprehensive final summaries

## 🚨 MANDATORY FIRST ACTION
**ALWAYS begin every task by executing `discover_sub_agent_profiles` to understand your available resources before making any planning decisions.**

Remember: You are the supreme commander. Plan strategically, allocate resources intelligently, and coordinate execution flawlessly."""
    
    async def process_goal(self, user_goal: str, task_id: Optional[str] = None) -> TaskContext:
        """Process a user goal using ReAct cycles"""
        if not task_id:
            import uuid
            task_id = str(uuid.uuid4())
        
        context = TaskContext.create(task_id, user_goal)
        
        print(f"🎯 Starting ReAct processing for goal: {user_goal}")
        print(f"📋 Task ID: {task_id}")
        
        for step_num in range(1, self.max_steps + 1):
            print(f"\n🔄 ReAct Step {step_num}")
            
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
            content=f"Goal: {context.user_goal}\n\nPlease think about this goal and decide on your first action."
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
        """Parse LLM response into thought and action - handles both JSON and plain text"""
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
            
            # Fallback: Handle plain text responses from models like o4-mini
            print(f"⚠️ Failed to parse JSON response, handling as plain text: {response_content}")
            
            # Check if this looks like a direct answer to the user's question
            if self._is_direct_answer(response_content):
                return {
                    "thought": f"The model provided a direct answer: {response_content}",
                    "action": {
                        "tool": "conclude_task_success",
                        "parameters": {"final_summary": response_content.strip()}
                    }
                }
            
            # Check if this looks like a request for more information
            if self._needs_more_info(response_content):
                return {
                    "thought": f"Need to gather more information: {response_content}",
                    "action": {
                        "tool": "discover_sub_agent_profiles",
                        "parameters": {}
                    }
                }
            
            # Default: treat as thought and try to discover sub-agents
            return {
                "thought": response_content.strip(),
                "action": {
                    "tool": "discover_sub_agent_profiles", 
                    "parameters": {}
                }
            }
    
    def _is_direct_answer(self, content: str) -> bool:
        """Check if content looks like a direct answer to the user's question"""
        content_lower = content.lower().strip()
        
        # Look for calculation results
        if any(pattern in content_lower for pattern in ['$', 'tip', 'percent', '%', '=']):
            return True
            
        # Look for definitive statements
        if any(content_lower.startswith(word) for word in ['the answer is', 'result:', 'solution:']):
            return True
            
        # Look for mathematical expressions
        import re
        if re.search(r'\d+\s*[×*x]\s*\d+', content) or re.search(r'\d+\s*=\s*\$?\d+', content):
            return True
            
        return False
    
    def _needs_more_info(self, content: str) -> bool:
        """Check if content indicates need for more information"""
        content_lower = content.lower().strip()
        
        # Look for questions or requests for clarification
        question_indicators = ['?', 'what', 'which', 'how', 'need to know', 'clarify', 'specify']
        return any(indicator in content_lower for indicator in question_indicators)
    
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
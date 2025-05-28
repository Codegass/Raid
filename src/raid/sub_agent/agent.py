"""Sub-Agent implementation with LLM and tool integration"""

import json
import asyncio
import os
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..config.settings import RaidConfig
from ..llm_backend.interface import LLMBackend, LLMMessage
from ..llm_backend.factory import create_llm_backend
from ..tools.base import Tool, ToolRegistry
from ..tools.calculator import CalculatorTool
from ..message_queue.models import TaskMessage, ResultMessage
from ..message_queue.redis_mq import RedisMQ
from ..config.settings import LLMBackendConfig, MessageQueueConfig
from ..config.sub_agent_config import SubAgentProfile
from ..config.collaboration import CollaborationMessage, CollaborationMessageType, CollaborativeAgentGroup


class SubAgent:
    """LLM-based Sub-Agent that processes tasks using tools"""
    
    def __init__(self, profile: SubAgentProfile, mq_config: MessageQueueConfig, global_config: Optional["RaidConfig"] = None):
        self.profile = profile
        self.mq_config = mq_config
        
        # Initialize LLM backend - merge profile config with global config for credentials
        if global_config:
            # Use global config as base and override with profile specifics
            llm_config = LLMBackendConfig(
                provider=global_config.llm_backend.provider,
                api_key=global_config.llm_backend.api_key,
                base_url=global_config.llm_backend.base_url,
                model=profile.llm_config.get("model", global_config.llm_backend.model),
                max_tokens=profile.llm_config.get("max_tokens", global_config.llm_backend.max_tokens),
                temperature=profile.llm_config.get("temperature", global_config.llm_backend.temperature)
            )
        else:
            llm_config = LLMBackendConfig(**profile.llm_config)
        
        self.llm_backend = create_llm_backend(llm_config)
        
        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        self._register_tools()
        
        # Initialize message queue
        self.mq = RedisMQ(mq_config)
        
        # Collaboration support
        self.collaboration_enabled = os.getenv("RAID_COLLABORATION_ENABLED", "false").lower() == "true"
        self.collaboration_group_id = os.getenv("RAID_COLLABORATION_GROUP_ID")
        self.collaboration_channel = None
        self.collaboration_messages = []  # Store received collaboration messages
        self.collaboration_context = {}  # Store shared data from other agents
        
        if self.collaboration_enabled and self.collaboration_group_id:
            self.collaboration_channel = f"raid:collaboration:{self.collaboration_group_id}"
            print(f"Sub-Agent '{self.profile.name}' enabled for collaboration in group: {self.collaboration_group_id}")
        
        self.running = False
    
    def _register_tools(self) -> None:
        """Register tools based on profile configuration"""
        # Map tool names to tool classes
        tool_classes = {
            "calculator": CalculatorTool,
        }
        
        for tool_name in self.profile.tools:
            if tool_name in tool_classes:
                tool = tool_classes[tool_name]()
                self.tool_registry.register(tool)
            else:
                print(f"Warning: Unknown tool '{tool_name}' in profile")
    
    async def start(self) -> None:
        """Start the Sub-Agent to listen for tasks"""
        await self.mq.connect()
        self.running = True
        
        print(f"Sub-Agent '{self.profile.name}' started, listening for tasks...")
        
        # Start collaboration listener if enabled
        if self.collaboration_enabled and self.collaboration_channel:
            asyncio.create_task(self._start_collaboration_listener())
            print(f"Collaboration listener started for channel: {self.collaboration_channel}")
        
        task_queue = self.mq.get_task_queue_name(self.profile.name)
        result_queue = self.mq.get_result_queue_name(self.profile.name)
        
        while self.running:
            try:
                # Listen for tasks
                task = await self.mq.receive_task(task_queue, timeout=5)
                if task:
                    print(f"Received task: {task.task_id}")
                    try:
                        result = await self._process_task(task)
                        print(f"Task processed, status: {result.status}")
                        await self.mq.send_result(result_queue, result)
                        print(f"Result sent to queue: {result_queue}")
                        print(f"Completed task: {task.task_id}")
                    except Exception as task_error:
                        print(f"Error processing task {task.task_id}: {task_error}")
                        import traceback
                        traceback.print_exc()
                        # Send error result
                        error_result = ResultMessage.create_error(task.task_id, task.correlation_id, str(task_error))
                        await self.mq.send_result(result_queue, error_result)
                
            except Exception as e:
                print(f"Error in main loop: {e}")
                import traceback
                traceback.print_exc()
    
    async def stop(self) -> None:
        """Stop the Sub-Agent"""
        self.running = False
        await self.mq.disconnect()
        print(f"Sub-Agent '{self.profile.name}' stopped")
    
    async def _process_task(self, task: TaskMessage) -> ResultMessage:
        """Process a single task using LLM and tools"""
        try:
            # Create system message with profile prompt and tool information
            system_content = self._create_system_prompt()
            
            # Create user message with the task
            user_content = task.prompt
            
            messages = [
                LLMMessage(role="system", content=system_content),
                LLMMessage(role="user", content=user_content)
            ]
            
            # Process with LLM
            max_iterations = 5
            for iteration in range(max_iterations):
                # Get LLM response
                llm_response = await self.llm_backend.generate(
                    messages=messages,
                    max_tokens=task.llm_config.get("max_tokens"),
                    temperature=task.llm_config.get("temperature")
                )
                
                # Check if LLM wants to use a tool
                if self._is_tool_call(llm_response.content):
                    tool_call = self._parse_tool_call(llm_response.content)
                    if tool_call:
                        tool_result = await self._execute_tool(tool_call)
                        
                        # Add assistant message and tool result to conversation
                        messages.append(LLMMessage(role="assistant", content=llm_response.content))
                        messages.append(LLMMessage(role="user", content=f"Tool result: {tool_result}"))
                        continue
                
                # No tool call needed, return final response
                # Debug: check what's in llm_response
                print(f"LLM response content: {llm_response.content}")
                print(f"LLM response usage: {llm_response.usage}")
                print(f"LLM response usage type: {type(llm_response.usage)}")
                
                # Create result manually to avoid serialization issues
                from datetime import datetime
                return ResultMessage(
                    task_id=task.task_id,
                    correlation_id=task.correlation_id,
                    status="success",
                    result=llm_response.content,
                    usage=None,  # Temporarily disable usage to isolate the issue
                    timestamp=datetime.utcnow()
                )
            
            # Max iterations reached
            return ResultMessage.create_error(
                task_id=task.task_id,
                correlation_id=task.correlation_id,
                error="Maximum iterations reached without completion"
            )
            
        except Exception as e:
            return ResultMessage.create_error(
                task_id=task.task_id,
                correlation_id=task.correlation_id,
                error=str(e)
            )
    
    def _create_system_prompt(self) -> str:
        """Create system prompt with profile information and tool descriptions"""
        tool_descriptions = []
        for tool in self.tool_registry.get_all_tools().values():
            params_desc = ", ".join([
                f"{p.name} ({p.type}): {p.description}"
                for p in tool.parameters
            ])
            tool_descriptions.append(
                f"- {tool.name}: {tool.description}\\n  Parameters: {params_desc}"
            )
        
        tools_section = "\\n".join(tool_descriptions) if tool_descriptions else "No tools available."
        
        # Add collaboration context if available
        collaboration_context = self._get_collaboration_context_for_llm()
        collaboration_section = f"\n\n{collaboration_context}" if collaboration_context else ""
        
        collaboration_instructions = ""
        if self.collaboration_enabled:
            collaboration_instructions = """

Collaboration Instructions:
- You are part of a collaborative group of Sub-Agents
- You can share data and coordinate with other agents
- Consider using shared data from other agents when relevant
- Share your calculation results when they might benefit other agents"""
        
        return f"""{self.profile.system_prompt}

Available Tools:
{tools_section}

To use a tool, respond with a JSON object in this format:
{{
    "tool_call": {{
        "name": "tool_name",
        "parameters": {{"param1": "value1", "param2": "value2"}}
    }}
}}

After using a tool, you will receive the result and can either use another tool or provide your final response.{collaboration_instructions}{collaboration_section}"""
    
    def _is_tool_call(self, content: str) -> bool:
        """Check if LLM response contains a tool call"""
        content = content.strip()
        return content.startswith("{") and "tool_call" in content
    
    def _parse_tool_call(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse tool call from LLM response"""
        try:
            data = json.loads(content.strip())
            return data.get("tool_call")
        except json.JSONDecodeError:
            return None
    
    async def _execute_tool(self, tool_call: Dict[str, Any]) -> str:
        """Execute a tool call"""
        try:
            tool_name = tool_call.get("name")
            parameters = tool_call.get("parameters", {})
            
            if not tool_name:
                return "Error: No tool name provided"
            
            tool = self.tool_registry.get_tool(tool_name)
            result = await tool.execute(**parameters)
            
            # Share calculation results with collaborative agents if enabled
            if self.collaboration_enabled and tool_name == "calculator" and result:
                await self._share_calculation_result(result)
            
            return result
            
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error executing tool: {str(e)}"
    
    # Collaboration Methods
    
    async def _start_collaboration_listener(self) -> None:
        """Start listening for collaboration messages"""
        if not self.collaboration_channel:
            return
        
        async def collaboration_message_handler(channel: str, message_data: str):
            try:
                message_dict = eval(message_data)  # Safe in controlled environment
                message = CollaborationMessage(**message_dict)
                await self._handle_collaboration_message(message)
            except Exception as e:
                print(f"Error processing collaboration message: {e}")
        
        await self.mq.subscribe_to_channel(self.collaboration_channel, collaboration_message_handler)
    
    async def _handle_collaboration_message(self, message: CollaborationMessage) -> None:
        """Handle incoming collaboration messages"""
        # Don't process messages from self
        if message.sender_agent == self.profile.name:
            return
        
        # Check if message is for this agent (broadcast or targeted)
        if message.target_agent and message.target_agent != self.profile.name:
            return
        
        # Check if message is expired
        if message.is_expired():
            return
        
        print(f"Received collaboration message from {message.sender_agent}: {message.message_type}")
        
        # Store message for processing
        self.collaboration_messages.append(message)
        
        # Handle specific message types
        if message.message_type == CollaborationMessageType.DATA_SHARE:
            await self._handle_data_share(message)
        elif message.message_type == CollaborationMessageType.REQUEST_DATA:
            await self._handle_data_request(message)
        elif message.message_type == CollaborationMessageType.STATUS_UPDATE:
            await self._handle_status_update(message)
        elif message.message_type == CollaborationMessageType.VALIDATION:
            await self._handle_validation_request(message)
    
    async def _handle_data_share(self, message: CollaborationMessage) -> None:
        """Handle data sharing from another agent"""
        if message.data:
            # Store shared data in collaboration context
            for key, value in message.data.items():
                self.collaboration_context[f"{message.sender_agent}_{key}"] = value
            print(f"Stored shared data from {message.sender_agent}: {list(message.data.keys())}")
    
    async def _handle_data_request(self, message: CollaborationMessage) -> None:
        """Handle data request from another agent"""
        if message.request and message.sender_agent:
            # This is a simple implementation - in practice, agents could be smarter about what to share
            response_data = {}
            
            # Check if we have relevant data to share
            if "calculation" in message.request.lower() and "last_calculation" in self.collaboration_context:
                response_data["calculation_result"] = self.collaboration_context["last_calculation"]
            
            if response_data:
                # Send data back to requesting agent
                response_message = CollaborationMessage.create_data_share(
                    sender=self.profile.name,
                    group_id=self.collaboration_group_id,
                    data=response_data,
                    target_agent=message.sender_agent,
                    correlation_id=message.correlation_id
                )
                await self._send_collaboration_message(response_message)
    
    async def _handle_status_update(self, message: CollaborationMessage) -> None:
        """Handle status update from another agent"""
        if message.status:
            print(f"Status update from {message.sender_agent}: {message.status}")
            # Store status for potential use in decision making
            self.collaboration_context[f"{message.sender_agent}_status"] = message.status
    
    async def _handle_validation_request(self, message: CollaborationMessage) -> None:
        """Handle validation request from another agent"""
        # Simple validation response - in practice, this would involve actual validation logic
        validation_response = CollaborationMessage(
            message_type=CollaborationMessageType.DATA_SHARE,
            sender_agent=self.profile.name,
            target_agent=message.sender_agent,
            group_id=self.collaboration_group_id,
            data={"validation_status": "reviewed", "validation_agent": self.profile.name},
            correlation_id=message.correlation_id
        )
        await self._send_collaboration_message(validation_response)
    
    async def _send_collaboration_message(self, message: CollaborationMessage) -> bool:
        """Send a collaboration message to other agents"""
        if not self.collaboration_channel:
            return False
        
        try:
            await self.mq.publish_message(self.collaboration_channel, message.model_dump_json())
            print(f"Sent collaboration message: {message.message_type} to {message.target_agent or 'all'}")
            return True
        except Exception as e:
            print(f"Error sending collaboration message: {e}")
            return False
    
    def _get_collaboration_context_for_llm(self) -> str:
        """Get collaboration context to include in LLM prompts"""
        if not self.collaboration_enabled or not self.collaboration_context:
            return ""
        
        context_parts = []
        context_parts.append("Collaboration Context:")
        
        for key, value in self.collaboration_context.items():
            # Format the shared data for LLM understanding
            if isinstance(value, dict):
                context_parts.append(f"- {key}: {json.dumps(value)}")
            else:
                context_parts.append(f"- {key}: {value}")
        
        if self.collaboration_messages:
            recent_messages = self.collaboration_messages[-3:]  # Last 3 messages
            context_parts.append("Recent collaboration messages:")
            for msg in recent_messages:
                context_parts.append(f"- {msg.sender_agent} ({msg.message_type}): {msg.data or msg.status or msg.request}")
        
        return "\n".join(context_parts)
    
    async def _share_calculation_result(self, calculation_result: str) -> None:
        """Share a calculation result with collaborative agents"""
        if not self.collaboration_enabled:
            return
        
        # Store locally for future reference
        self.collaboration_context["last_calculation"] = calculation_result
        
        # Share with other agents
        message = CollaborationMessage.create_data_share(
            sender=self.profile.name,
            group_id=self.collaboration_group_id,
            data={"calculation_result": calculation_result, "calculated_by": self.profile.name}
        )
        await self._send_collaboration_message(message)
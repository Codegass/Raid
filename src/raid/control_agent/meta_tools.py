"""Meta-tools for Control Agent to orchestrate Sub-Agents"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from ..config.settings import RaidConfig
from ..config.sub_agent_config import SubAgentConfigurator, SubAgentProfile
from ..config.dynamic_subagent import DynamicSubAgentManager
from ..config.collaboration import CollaborationManager, CollaborationRestrictions, CollaborationMessageType
from ..docker_orchestrator.orchestrator import DockerOrchestrator
from ..message_queue.redis_mq import RedisMQ
from ..message_queue.models import TaskMessage


class MetaToolParameter(BaseModel):
    """Parameter definition for a meta-tool"""
    name: str
    type: str
    description: str
    required: bool = True


class MetaToolDefinition(BaseModel):
    """Meta-tool definition for LLM function calling"""
    name: str
    description: str
    parameters: List[MetaToolParameter]


class MetaTool(ABC):
    """Abstract base class for Control Agent meta-tools"""
    
    def __init__(self, config: RaidConfig):
        self.config = config
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Meta-tool name"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Meta-tool description"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[MetaToolParameter]:
        """Meta-tool parameters"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """Execute the meta-tool with given parameters"""
        pass
    
    def get_definition(self) -> MetaToolDefinition:
        """Get meta-tool definition for LLM function calling"""
        return MetaToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters
        )


class DiscoverSubAgentProfilesTool(MetaTool):
    """Meta-tool to discover available Sub-Agent profiles"""
    
    @property
    def name(self) -> str:
        return "discover_sub_agent_profiles"
    
    @property
    def description(self) -> str:
        return "Get list of available Sub-Agent profiles and their capabilities"
    
    @property
    def parameters(self) -> List[MetaToolParameter]:
        return []  # No parameters needed
    
    async def execute(self, **kwargs: Any) -> str:
        """Discover available Sub-Agent profiles"""
        try:
            configurator = SubAgentConfigurator()
            profiles = configurator.get_all_profiles()
            
            result = "Available Sub-Agent Profiles:\n"
            for name, profile in profiles.items():
                result += f"\n- **{name}** ({profile.version})\n"
                result += f"  Description: {profile.description}\n"
                result += f"  Tools: {', '.join(profile.tools)}\n"
                result += f"  LLM Model: {profile.llm_config.get('model', 'default')}\n"
            
            return result if profiles else "No Sub-Agent profiles available."
            
        except Exception as e:
            return f"Error discovering profiles: {str(e)}"


class DispatchToSubAgentTool(MetaTool):
    """Meta-tool to dispatch tasks to Sub-Agents"""
    
    def __init__(self, config: RaidConfig):
        super().__init__(config)
        self.orchestrator = DockerOrchestrator(config.docker_socket)
        self.mq = None  # Will be initialized when needed
    
    @property
    def name(self) -> str:
        return "dispatch_to_sub_agent"
    
    @property
    def description(self) -> str:
        return "Send a task to a specific Sub-Agent and wait for the result"
    
    @property
    def parameters(self) -> List[MetaToolParameter]:
        return [
            MetaToolParameter(
                name="sub_agent_profile",
                type="string",
                description="Name of the Sub-Agent profile to use (e.g., 'calculator_agent')",
                required=True
            ),
            MetaToolParameter(
                name="task_prompt",
                type="string",
                description="The task prompt to send to the Sub-Agent",
                required=True
            ),
            MetaToolParameter(
                name="timeout",
                type="integer",
                description="Timeout in seconds to wait for result (default: 30)",
                required=False
            )
        ]
    
    async def execute(self, **kwargs: Any) -> str:
        """Dispatch task to Sub-Agent and wait for result"""
        try:
            sub_agent_profile = kwargs.get("sub_agent_profile")
            task_prompt = kwargs.get("task_prompt")
            timeout = kwargs.get("timeout", 30)
            
            if not sub_agent_profile or not task_prompt:
                return "Error: sub_agent_profile and task_prompt are required"
            
            # Initialize MQ if needed
            if not self.mq:
                self.mq = RedisMQ(self.config.message_queue)
                await self.mq.connect()
            
            # Load Sub-Agent profile
            configurator = SubAgentConfigurator()
            try:
                profile = configurator.load_profile(sub_agent_profile)
            except FileNotFoundError:
                return f"Error: Sub-Agent profile '{sub_agent_profile}' not found"
            
            # Ensure Sub-Agent container is running
            try:
                container = self.orchestrator.ensure_sub_agent_running(
                    sub_agent_profile,
                    environment={
                        "RAID_LLM_PROVIDER": self.config.llm_backend.provider,
                        "OPENAI_API_KEY_N0MAIL": self.config.llm_backend.api_key or "",
                        "RAID_REDIS_HOST": "host.docker.internal",
                        "RAID_REDIS_PORT": str(self.config.message_queue.redis_port),
                    }
                )
                # Give container time to start
                await asyncio.sleep(2)
            except Exception as e:
                return f"Error starting Sub-Agent container: {str(e)}"
            
            # Create and send task
            task = TaskMessage.create(
                sub_agent_profile=sub_agent_profile,
                prompt=task_prompt,
                tools=profile.tools,
                llm_config=profile.llm_config
            )
            
            task_queue = self.mq.get_task_queue_name(sub_agent_profile)
            result_queue = self.mq.get_result_queue_name(sub_agent_profile)
            
            await self.mq.send_task(task_queue, task)
            
            # Wait for result
            result = await self.mq.wait_for_result(
                correlation_id=task.correlation_id,
                result_queue=result_queue,
                timeout=timeout
            )
            
            if result:
                if result.status == "success":
                    return f"Sub-Agent Result: {result.result}"
                else:
                    return f"Sub-Agent Error: {result.error}"
            else:
                return f"Timeout: No result received from {sub_agent_profile} within {timeout} seconds"
                
        except Exception as e:
            return f"Error dispatching to Sub-Agent: {str(e)}"


class ConcludeTaskSuccessTool(MetaTool):
    """Meta-tool to conclude a task successfully"""
    
    @property
    def name(self) -> str:
        return "conclude_task_success"
    
    @property
    def description(self) -> str:
        return "Mark the current task as completed successfully with a final summary"
    
    @property
    def parameters(self) -> List[MetaToolParameter]:
        return [
            MetaToolParameter(
                name="final_summary",
                type="string",
                description="A comprehensive summary of what was accomplished",
                required=True
            )
        ]
    
    async def execute(self, **kwargs: Any) -> str:
        """Conclude task with success"""
        final_summary = kwargs.get("final_summary", "Task completed successfully.")
        return f"TASK_COMPLETED_SUCCESSFULLY: {final_summary}"


class ConcludeTaskFailureTool(MetaTool):
    """Meta-tool to conclude a task with failure"""
    
    @property
    def name(self) -> str:
        return "conclude_task_failure"
    
    @property
    def description(self) -> str:
        return "Mark the current task as failed with an explanation"
    
    @property
    def parameters(self) -> List[MetaToolParameter]:
        return [
            MetaToolParameter(
                name="reason",
                type="string",
                description="Explanation of why the task failed",
                required=True
            )
        ]
    
    async def execute(self, **kwargs: Any) -> str:
        """Conclude task with failure"""
        reason = kwargs.get("reason", "Task failed for unknown reason.")
        return f"TASK_FAILED: {reason}"


class CreateSpecializedSubAgentTool(MetaTool):
    """Meta-tool to create dynamic specialized Sub-Agents for specific tasks"""
    
    def __init__(self, config: RaidConfig):
        super().__init__(config)
        self.dynamic_manager = DynamicSubAgentManager(config.max_dynamic_sub_agents)
        self.configurator = SubAgentConfigurator()
    
    @property
    def name(self) -> str:
        return "create_specialized_sub_agent"
    
    @property
    def description(self) -> str:
        return "Create a new specialized Sub-Agent with a specific role for a particular task"
    
    @property
    def parameters(self) -> List[MetaToolParameter]:
        return [
            MetaToolParameter(
                name="task_description",
                type="string",
                description="Detailed description of the task the Sub-Agent will handle",
                required=True
            ),
            MetaToolParameter(
                name="role",
                type="string",
                description="Role for the Sub-Agent: 'data_analyst', 'financial_analyst', 'research_analyst', 'problem_solver', or 'quality_analyst'. If not specified, role will be auto-suggested based on task.",
                required=False
            ),
            MetaToolParameter(
                name="specialization_notes",
                type="string",
                description="Additional notes about the specific specialization needed",
                required=False
            )
        ]
    
    async def execute(self, **kwargs: Any) -> str:
        """Create a specialized Sub-Agent"""
        try:
            task_description = kwargs.get("task_description")
            role = kwargs.get("role")
            specialization_notes = kwargs.get("specialization_notes", "")
            
            if not task_description:
                return "Error: task_description is required"
            
            # Check if we can create more agents
            if not self.dynamic_manager.can_create_agent():
                current_count = len(self.dynamic_manager.active_agents)
                return f"Error: Maximum number of dynamic Sub-Agents ({self.dynamic_manager.max_agents}) reached. Currently active: {current_count}"
            
            # Enhanced task description with specialization notes
            full_task_description = task_description
            if specialization_notes:
                full_task_description += f" Additional requirements: {specialization_notes}"
            
            # Create the dynamic Sub-Agent
            profile = self.dynamic_manager.create_dynamic_agent(
                task_description=full_task_description,
                role_name=role,
                llm_config={
                    "provider": self.config.llm_backend.provider,
                    "model": self.config.llm_backend.model or "gpt-3.5-turbo",
                    "max_tokens": 1000,
                    "temperature": 0.3
                }
            )
            
            # Save the profile temporarily (for dispatching)
            self.configurator.save_profile(profile)
            
            # Get role information
            agent_metadata = self.dynamic_manager.active_agents[profile.name]
            actual_role = agent_metadata["role"]
            
            result = f"✅ Created specialized Sub-Agent: '{profile.name}'\n"
            result += f"Role: {actual_role}\n"
            result += f"Specialization: {profile.description}\n"
            result += f"Available tools: {', '.join(profile.tools)}\n"
            result += f"Created for task: {task_description}\n"
            result += f"\nYou can now dispatch tasks to this Sub-Agent using the 'dispatch_to_sub_agent' tool with sub_agent_profile='{profile.name}'"
            
            # Show current usage
            active_count = len(self.dynamic_manager.active_agents)
            result += f"\n\nDynamic Sub-Agent usage: {active_count}/{self.dynamic_manager.max_agents}"
            
            return result
            
        except Exception as e:
            return f"Error creating specialized Sub-Agent: {str(e)}"


class CreateCollaborativeSubAgentGroupTool(MetaTool):
    """Meta-tool to create a group of Sub-Agents that can collaborate with restricted communication"""
    
    def __init__(self, config: RaidConfig):
        super().__init__(config)
        self.dynamic_manager = DynamicSubAgentManager(config.max_dynamic_sub_agents)
        self.collaboration_manager = CollaborationManager(config)
        self.configurator = SubAgentConfigurator()
        self.orchestrator = DockerOrchestrator(config.docker_socket)
        self.mq = None
    
    @property
    def name(self) -> str:
        return "create_collaborative_sub_agent_group"
    
    @property
    def description(self) -> str:
        return "Create a group of specialized Sub-Agents that can collaborate and share data directly with restricted communication"
    
    @property
    def parameters(self) -> List[MetaToolParameter]:
        return [
            MetaToolParameter(
                name="group_task_description",
                type="string",
                description="Description of the complex task that requires multiple Sub-Agents to collaborate",
                required=True
            ),
            MetaToolParameter(
                name="agent_roles",
                type="string",
                description="Comma-separated list of roles needed (e.g., 'financial_analyst,data_analyst,quality_analyst')",
                required=True
            ),
            MetaToolParameter(
                name="collaboration_type",
                type="string",
                description="Type of collaboration: 'data_sharing', 'validation_chain', 'parallel_analysis', or 'sequential_workflow'",
                required=True
            ),
            MetaToolParameter(
                name="shared_data_keys",
                type="string",
                description="Optional: Comma-separated list of allowed data keys for sharing (e.g., 'calculations,results,analysis')",
                required=False
            )
        ]
    
    async def execute(self, **kwargs: Any) -> str:
        """Create a collaborative Sub-Agent group"""
        try:
            group_task_description = kwargs.get("group_task_description")
            agent_roles_str = kwargs.get("agent_roles", "")
            collaboration_type = kwargs.get("collaboration_type", "data_sharing")
            shared_data_keys_str = kwargs.get("shared_data_keys", "")
            
            if not group_task_description or not agent_roles_str:
                return "Error: group_task_description and agent_roles are required"
            
            # Parse agent roles
            agent_roles = [role.strip() for role in agent_roles_str.split(",")]
            if len(agent_roles) < 2:
                return "Error: At least 2 agent roles required for collaboration"
            
            # Check if we can create the agents
            if len(agent_roles) > self.dynamic_manager.max_agents:
                return f"Error: Requested {len(agent_roles)} agents exceeds maximum ({self.dynamic_manager.max_agents})"
            
            available_slots = self.dynamic_manager.max_agents - len(self.dynamic_manager.active_agents)
            if len(agent_roles) > available_slots:
                return f"Error: Only {available_slots} agent slots available, requested {len(agent_roles)}"
            
            # Parse shared data keys
            shared_data_keys = None
            if shared_data_keys_str:
                shared_data_keys = set(key.strip() for key in shared_data_keys_str.split(","))
            
            # Set collaboration restrictions based on type
            restrictions = self._get_collaboration_restrictions(collaboration_type, shared_data_keys)
            
            # Create collaboration group
            group_name = f"collaborative_group_{collaboration_type}"
            collab_group = self.collaboration_manager.create_collaboration_group(
                group_name=group_name,
                restrictions=restrictions
            )
            
            # Create Sub-Agents for the group
            created_agents = []
            agent_profiles = []
            
            for i, role in enumerate(agent_roles):
                try:
                    # Create specialized agent with collaboration context
                    enhanced_task = f"{group_task_description}\n\nCollaboration Context: You are part of a {len(agent_roles)}-agent collaborative group with roles: {', '.join(agent_roles)}. Your role is '{role}'. You can share data and coordinate with other agents in your group."
                    
                    profile = self.dynamic_manager.create_dynamic_agent(
                        task_description=enhanced_task,
                        role_name=role,
                        llm_config={
                            "provider": self.config.llm_backend.provider,
                            "model": self.config.llm_backend.model or "gpt-3.5-turbo",
                            "max_tokens": 1000,
                            "temperature": 0.3
                        }
                    )
                    
                    # Save the profile
                    self.configurator.save_profile(profile)
                    
                    # Add agent to collaboration group
                    collab_group.add_agent(
                        agent_name=profile.name,
                        role=role,
                        profile_data={"profile": profile, "task": enhanced_task},
                        collaboration_permissions=restrictions.allowed_message_types
                    )
                    
                    created_agents.append(profile.name)
                    agent_profiles.append(profile)
                    
                except Exception as e:
                    # Cleanup on error
                    for cleanup_agent in created_agents:
                        self.dynamic_manager.remove_dynamic_agent(cleanup_agent)
                    return f"Error creating agent with role '{role}': {str(e)}"
            
            # Initialize messaging for the group
            await collab_group.initialize_messaging()
            
            # Start the Sub-Agent containers
            for profile in agent_profiles:
                try:
                    container = self.orchestrator.ensure_sub_agent_running(
                        profile.name,
                        environment={
                            "RAID_LLM_PROVIDER": self.config.llm_backend.provider,
                            "OPENAI_API_KEY_N0MAIL": self.config.llm_backend.api_key or "",
                            "RAID_REDIS_HOST": "host.docker.internal",
                            "RAID_REDIS_PORT": str(self.config.message_queue.redis_port),
                            "RAID_COLLABORATION_GROUP_ID": collab_group.group_id,
                            "RAID_COLLABORATION_ENABLED": "true"
                        }
                    )
                except Exception as e:
                    return f"Error starting container for {profile.name}: {str(e)}"
            
            # Prepare result
            result = f"✅ Created collaborative Sub-Agent group: '{collab_group.group_id}'\n"
            result += f"Group Name: {group_name}\n"
            result += f"Collaboration Type: {collaboration_type}\n"
            result += f"Task: {group_task_description}\n\n"
            
            result += "👥 Created Agents:\n"
            for i, agent_name in enumerate(created_agents):
                role = agent_roles[i]
                result += f"  - {agent_name} (Role: {role})\n"
            
            result += f"\n🔗 Collaboration Features:\n"
            result += f"  - Allowed message types: {', '.join(restrictions.allowed_message_types)}\n"
            result += f"  - Max messages/minute: {restrictions.max_messages_per_minute}\n"
            result += f"  - Message size limit: {restrictions.max_message_size_bytes} bytes\n"
            if shared_data_keys:
                result += f"  - Allowed data keys: {', '.join(shared_data_keys)}\n"
            
            result += f"\n📋 Usage:\n"
            result += f"  - Use 'dispatch_to_sub_agent' with any agent in the group\n"
            result += f"  - Agents will automatically collaborate through shared channels\n"
            result += f"  - Group ID: {collab_group.group_id}\n"
            
            # Show current usage
            active_count = len(self.dynamic_manager.active_agents)
            result += f"\nDynamic Sub-Agent usage: {active_count}/{self.dynamic_manager.max_agents}"
            
            return result
            
        except Exception as e:
            return f"Error creating collaborative Sub-Agent group: {str(e)}"
    
    def _get_collaboration_restrictions(
        self,
        collaboration_type: str,
        shared_data_keys: Optional[set] = None
    ) -> CollaborationRestrictions:
        """Get collaboration restrictions based on collaboration type"""
        
        if collaboration_type == "data_sharing":
            return CollaborationRestrictions(
                allowed_message_types={
                    CollaborationMessageType.DATA_SHARE,
                    CollaborationMessageType.REQUEST_DATA,
                    CollaborationMessageType.STATUS_UPDATE
                },
                max_messages_per_minute=20,
                allowed_data_keys=shared_data_keys,
                collaboration_timeout_minutes=45
            )
        
        elif collaboration_type == "validation_chain":
            return CollaborationRestrictions(
                allowed_message_types={
                    CollaborationMessageType.DATA_SHARE,
                    CollaborationMessageType.VALIDATION,
                    CollaborationMessageType.STATUS_UPDATE,
                    CollaborationMessageType.ERROR_REPORT
                },
                max_messages_per_minute=15,
                allowed_data_keys=shared_data_keys,
                collaboration_timeout_minutes=30
            )
        
        elif collaboration_type == "parallel_analysis":
            return CollaborationRestrictions(
                allowed_message_types={
                    CollaborationMessageType.DATA_SHARE,
                    CollaborationMessageType.STATUS_UPDATE,
                    CollaborationMessageType.COORDINATION
                },
                max_messages_per_minute=25,
                allowed_data_keys=shared_data_keys,
                collaboration_timeout_minutes=60
            )
        
        elif collaboration_type == "sequential_workflow":
            return CollaborationRestrictions(
                allowed_message_types={
                    CollaborationMessageType.DATA_SHARE,
                    CollaborationMessageType.STATUS_UPDATE,
                    CollaborationMessageType.COORDINATION,
                    CollaborationMessageType.REQUEST_DATA
                },
                max_messages_per_minute=10,
                allowed_data_keys=shared_data_keys,
                collaboration_timeout_minutes=90
            )
        
        else:
            # Default restrictions
            return CollaborationRestrictions(
                allowed_message_types={
                    CollaborationMessageType.DATA_SHARE,
                    CollaborationMessageType.STATUS_UPDATE
                },
                max_messages_per_minute=15,
                allowed_data_keys=shared_data_keys
            )


class MetaToolRegistry:
    """Registry for managing Control Agent meta-tools"""
    
    def __init__(self, config: RaidConfig):
        self.config = config
        self._tools: Dict[str, MetaTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register default meta-tools"""
        self.register(DiscoverSubAgentProfilesTool(self.config))
        self.register(DispatchToSubAgentTool(self.config))
        self.register(CreateSpecializedSubAgentTool(self.config))
        self.register(CreateCollaborativeSubAgentGroupTool(self.config))
        self.register(ConcludeTaskSuccessTool(self.config))
        self.register(ConcludeTaskFailureTool(self.config))
    
    def register(self, tool: MetaTool) -> None:
        """Register a meta-tool"""
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> MetaTool:
        """Get a meta-tool by name"""
        if name not in self._tools:
            raise ValueError(f"Meta-tool '{name}' not found")
        return self._tools[name]
    
    def get_all_tools(self) -> Dict[str, MetaTool]:
        """Get all registered meta-tools"""
        return self._tools.copy()
    
    def get_tool_definitions(self) -> List[MetaToolDefinition]:
        """Get definitions for all meta-tools"""
        return [tool.get_definition() for tool in self._tools.values()]
    
    def list_tool_names(self) -> List[str]:
        """List all meta-tool names"""
        return list(self._tools.keys())
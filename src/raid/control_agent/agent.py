"""Control Agent - The master orchestrator using ReAct cycles"""

import asyncio
from typing import Optional

from ..config.settings import RaidConfig
from ..llm_backend.factory import create_llm_backend
from .react_engine import ReActEngine, TaskContext
from .meta_tools import MetaToolRegistry


class ControlAgent:
    """LLM-based Control Agent that orchestrates Sub-Agents using ReAct cycles"""
    
    def __init__(self, config: RaidConfig):
        self.config = config
        
        # Initialize LLM backend for Control Agent
        self.llm_backend = create_llm_backend(config.llm_backend)
        
        # Initialize meta-tool registry
        self.meta_tool_registry = MetaToolRegistry(config)
        
        # Initialize ReAct engine
        self.react_engine = ReActEngine(
            llm_backend=self.llm_backend,
            meta_tool_registry=self.meta_tool_registry,
            max_steps=10
        )
        
        print("🤖 Control Agent initialized successfully")
        print(f"   LLM Backend: {config.llm_backend.provider} ({config.llm_backend.model})")
        print(f"   Meta-Tools: {len(self.meta_tool_registry.list_tool_names())} available")
    
    async def process_user_goal(self, user_goal: str, task_id: Optional[str] = None) -> TaskContext:
        """Process a user goal using ReAct cycles to orchestrate Sub-Agents"""
        
        print(f"\\n🎯 Control Agent received goal: {user_goal}")
        
        try:
            # Health check LLM backend
            if not await self.llm_backend.health_check():
                print("❌ LLM backend health check failed")
                context = TaskContext.create(task_id or "error", user_goal)
                context.complete_failure("LLM backend is not available")
                return context
            
            # Process the goal using ReAct engine
            context = await self.react_engine.process_goal(user_goal, task_id)
            
            print(f"\\n📊 Final Result:")
            print(f"   Status: {context.status}")
            print(f"   Steps taken: {len(context.steps)}")
            print(f"   Result: {context.final_result}")
            
            return context
            
        except Exception as e:
            print(f"❌ Error in Control Agent: {e}")
            context = TaskContext.create(task_id or "error", user_goal)
            context.complete_failure(f"Control Agent error: {str(e)}")
            return context
    
    async def get_available_sub_agents(self) -> str:
        """Get information about available Sub-Agents"""
        try:
            discover_tool = self.meta_tool_registry.get_tool("discover_sub_agent_profiles")
            return await discover_tool.execute()
        except Exception as e:
            return f"Error discovering Sub-Agents: {str(e)}"
    
    async def health_check(self) -> bool:
        """Check if Control Agent is healthy"""
        try:
            # Check LLM backend
            if not await self.llm_backend.health_check():
                return False
            
            # Check if meta-tools are available
            if len(self.meta_tool_registry.list_tool_names()) == 0:
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_meta_tool_info(self) -> str:
        """Get information about available meta-tools"""
        tools = self.meta_tool_registry.get_all_tools()
        
        info = "Control Agent Meta-Tools:\\n"
        for name, tool in tools.items():
            info += f"\\n- **{name}**: {tool.description}\\n"
            if tool.parameters:
                for param in tool.parameters:
                    required = " (required)" if param.required else " (optional)"
                    info += f"  • {param.name} ({param.type}){required}: {param.description}\\n"
        
        return info
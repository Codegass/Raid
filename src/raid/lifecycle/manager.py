"""Sub-Agent Lifecycle Manager - Automatic container lifecycle management"""

import asyncio
import time
from typing import Dict, Optional, Set, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..config.settings import RaidConfig
from ..config.sub_agent_config import SubAgentConfigurator
from ..docker_orchestrator.orchestrator import DockerOrchestrator


class AgentState(Enum):
    """Sub-Agent lifecycle states"""
    CREATING = "creating"
    STARTING = "starting"
    RUNNING = "running"
    WORKING = "working"
    IDLE = "idle"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class AgentInfo:
    """Information about a Sub-Agent"""
    name: str
    state: AgentState
    container_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_task_at: Optional[datetime] = None
    last_heartbeat_at: datetime = field(default_factory=datetime.utcnow)
    task_count: int = 0
    error_count: int = 0
    profile_name: str = ""
    is_persistent: bool = False
    exclude_from_count: bool = False
    
    def update_heartbeat(self):
        """Update the last heartbeat timestamp"""
        self.last_heartbeat_at = datetime.utcnow()
    
    def mark_task_started(self):
        """Mark that a task has started"""
        self.state = AgentState.WORKING
        self.last_task_at = datetime.utcnow()
        self.task_count += 1
        self.update_heartbeat()
    
    def mark_task_completed(self):
        """Mark that a task has completed"""
        self.state = AgentState.IDLE
        self.update_heartbeat()
    
    def mark_error(self):
        """Mark an error occurred"""
        self.error_count += 1
        self.state = AgentState.ERROR
        self.update_heartbeat()
    
    def is_idle_too_long(self, idle_timeout_minutes: int = 10) -> bool:
        """Check if agent has been idle too long"""
        if self.state != AgentState.IDLE:
            return False
        
        if not self.last_task_at:
            # Never processed a task, consider creation time
            return (datetime.utcnow() - self.created_at) > timedelta(minutes=idle_timeout_minutes)
        
        return (datetime.utcnow() - self.last_task_at) > timedelta(minutes=idle_timeout_minutes)
    
    def is_heartbeat_stale(self, heartbeat_timeout_minutes: int = 5) -> bool:
        """Check if heartbeat is stale (agent might be unresponsive)"""
        return (datetime.utcnow() - self.last_heartbeat_at) > timedelta(minutes=heartbeat_timeout_minutes)


class SubAgentLifecycleManager:
    """Independent Sub-Agent lifecycle manager with automatic cleanup"""
    
    def __init__(self, config: RaidConfig):
        self.config = config
        self.orchestrator = DockerOrchestrator(config.docker_socket)
        self.configurator = SubAgentConfigurator()
        
        # Agent tracking
        self.agents: Dict[str, AgentInfo] = {}
        self.max_agents = config.max_dynamic_sub_agents
        
        # Lifecycle configuration
        self.idle_timeout_minutes = 10  # Remove idle agents after 10 minutes
        self.heartbeat_timeout_minutes = 5  # Consider agents stale after 5 minutes
        self.cleanup_interval_seconds = 60  # Check for cleanup every minute
        self.force_cleanup_on_shutdown = True
        
        # State tracking
        self.running = False
        self.total_tasks_completed = 0
        self.cleanup_stats = {
            "idle_cleanups": 0,
            "stale_cleanups": 0,
            "capacity_cleanups": 0,
            "shutdown_cleanups": 0
        }
        
        # Callbacks for lifecycle events
        self.on_agent_created: Optional[Callable[[str, AgentInfo], None]] = None
        self.on_agent_removed: Optional[Callable[[str, AgentInfo], None]] = None
        self.on_capacity_reached: Optional[Callable[[int], None]] = None
        
        print(f"🔄 Lifecycle Manager initialized:")
        print(f"   Max agents: {self.max_agents}")
        print(f"   Idle timeout: {self.idle_timeout_minutes} minutes")
        print(f"   Cleanup interval: {self.cleanup_interval_seconds} seconds")
    
    async def start_monitoring(self):
        """Start the lifecycle monitoring loop"""
        if self.running:
            print("⚠️ Lifecycle manager already running")
            return
        
        self.running = True
        print("🔄 Starting Sub-Agent lifecycle monitoring...")
        
        # Start the monitoring loop
        asyncio.create_task(self._lifecycle_monitor_loop())
        print("✅ Lifecycle manager started")
    
    async def stop_monitoring(self):
        """Stop the lifecycle monitoring and cleanup all agents"""
        print("🔄 Stopping Sub-Agent lifecycle monitoring...")
        self.running = False
        
        if self.force_cleanup_on_shutdown:
            await self._cleanup_all_agents("System shutdown")
        
        # Also cleanup unused docker images
        self.orchestrator.cleanup_unused_images(max_images_to_keep=10)

        print("🔄 Lifecycle manager stopped")
    
    async def register_agent(self, agent_name: str, container_id: str, profile_name: str = "") -> bool:
        """Register a new Sub-Agent"""
        if agent_name in self.agents:
            print(f"⚠️ Agent '{agent_name}' already registered")
            return False
        
        # Load profile to check lifecycle configuration
        is_persistent = False
        exclude_from_count = False
        try:
            if profile_name:
                profile = self.configurator.load_profile(profile_name)
                if profile.lifecycle_config:
                    is_persistent = profile.lifecycle_config.persistent
                    exclude_from_count = profile.lifecycle_config.exclude_from_count
        except Exception as e:
            print(f"⚠️ Warning: Could not load profile '{profile_name}': {e}")
        
        # Check capacity (exclude persistent agents from count)
        current_count = len([a for a in self.agents.values() if not a.exclude_from_count])
        if not exclude_from_count and current_count >= self.max_agents:
            # Try to cleanup idle agents first
            await self._cleanup_idle_agents()
            
            current_count = len([a for a in self.agents.values() if not a.exclude_from_count])
            if current_count >= self.max_agents:
                print(f"❌ Cannot register agent '{agent_name}': capacity limit ({self.max_agents}) reached")
                if self.on_capacity_reached:
                    self.on_capacity_reached(current_count)
                return False
        
        # Register the agent
        agent_info = AgentInfo(
            name=agent_name,
            state=AgentState.RUNNING,
            container_id=container_id,
            profile_name=profile_name,
            is_persistent=is_persistent,
            exclude_from_count=exclude_from_count
        )
        
        self.agents[agent_name] = agent_info
        
        status_msg = f"✅ Registered agent '{agent_name}' (container: {container_id[:12]})"
        if is_persistent:
            status_msg += " [PERSISTENT]"
        if exclude_from_count:
            status_msg += " [EXCLUDED FROM COUNT]"
        print(status_msg)
        
        if self.on_agent_created:
            self.on_agent_created(agent_name, agent_info)
        
        return True
    
    async def unregister_agent(self, agent_name: str, reason: str = "Manual removal") -> bool:
        """Unregister and cleanup a Sub-Agent"""
        if agent_name not in self.agents:
            print(f"⚠️ Agent '{agent_name}' not found for unregistration")
            return False
        
        agent_info = self.agents[agent_name]
        
        # Stop the container
        await self._stop_agent_container(agent_info, reason)
        
        # Remove from tracking
        del self.agents[agent_name]
        print(f"✅ Unregistered agent '{agent_name}': {reason}")
        
        if self.on_agent_removed:
            self.on_agent_removed(agent_name, agent_info)
        
        return True
    
    def update_agent_heartbeat(self, agent_name: str):
        """Update agent heartbeat (called when agent is active)"""
        if agent_name in self.agents:
            self.agents[agent_name].update_heartbeat()
    
    def mark_agent_task_started(self, agent_name: str):
        """Mark that an agent started processing a task"""
        if agent_name in self.agents:
            self.agents[agent_name].mark_task_started()
            print(f"📋 Agent '{agent_name}' started task #{self.agents[agent_name].task_count}")
    
    def mark_agent_task_completed(self, agent_name: str):
        """Mark that an agent completed a task"""
        if agent_name in self.agents:
            self.agents[agent_name].mark_task_completed()
            self.total_tasks_completed += 1
            print(f"✅ Agent '{agent_name}' completed task (total: {self.total_tasks_completed})")
    
    def mark_agent_error(self, agent_name: str):
        """Mark that an agent encountered an error"""
        if agent_name in self.agents:
            self.agents[agent_name].mark_error()
            print(f"❌ Agent '{agent_name}' error #{self.agents[agent_name].error_count}")
    
    def get_agent_stats(self) -> Dict:
        """Get comprehensive statistics about managed agents"""
        state_counts = {}
        for state in AgentState:
            state_counts[state.value] = sum(1 for agent in self.agents.values() if agent.state == state)
        
        # Count agents by type
        regular_agents = [a for a in self.agents.values() if not a.exclude_from_count]
        persistent_agents = [a for a in self.agents.values() if a.is_persistent]
        
        return {
            "total_agents": len(self.agents),
            "regular_agents": len(regular_agents),
            "persistent_agents": len(persistent_agents),
            "max_capacity": self.max_agents,
            "capacity_used_pct": (len(regular_agents) / self.max_agents * 100) if self.max_agents > 0 else 0,
            "states": state_counts,
            "total_tasks_completed": self.total_tasks_completed,
            "cleanup_stats": self.cleanup_stats.copy(),
            "agents": {name: {
                "state": agent.state.value,
                "task_count": agent.task_count,
                "error_count": agent.error_count,
                "created_at": agent.created_at.isoformat(),
                "last_task_at": agent.last_task_at.isoformat() if agent.last_task_at else None,
                "profile": agent.profile_name,
                "is_persistent": agent.is_persistent,
                "exclude_from_count": agent.exclude_from_count
            } for name, agent in self.agents.items()}
        }
    
    async def _lifecycle_monitor_loop(self):
        """Main lifecycle monitoring loop"""
        while self.running:
            try:
                await self._perform_lifecycle_checks()
                await asyncio.sleep(self.cleanup_interval_seconds)
            except Exception as e:
                print(f"❌ Error in lifecycle monitor: {e}")
                await asyncio.sleep(self.cleanup_interval_seconds)
    
    async def _perform_lifecycle_checks(self):
        """Perform all lifecycle checks"""
        if not self.agents:
            return
        
        # Check for stale agents (unresponsive)
        await self._cleanup_stale_agents()
        
        # Check for idle agents (if over capacity or idle too long)
        await self._cleanup_idle_agents()
        
        # Update heartbeats for running containers
        await self._update_container_states()
    
    async def _cleanup_stale_agents(self):
        """Remove agents that haven't sent heartbeats (except persistent agents)"""
        stale_agents = []
        
        for name, agent in self.agents.items():
            if not agent.is_persistent and agent.is_heartbeat_stale(self.heartbeat_timeout_minutes):
                stale_agents.append(name)
        
        for agent_name in stale_agents:
            await self.unregister_agent(agent_name, "Stale heartbeat (unresponsive)")
            self.cleanup_stats["stale_cleanups"] += 1
    
    async def _cleanup_idle_agents(self):
        """Remove agents that have been idle too long or when over capacity (except persistent agents)"""
        idle_agents = []
        
        # Find idle agents (exclude persistent agents)
        for name, agent in self.agents.items():
            if (not agent.is_persistent and 
                agent.state == AgentState.IDLE and 
                agent.is_idle_too_long(self.idle_timeout_minutes)):
                idle_agents.append((name, agent))
        
        # Check capacity based on non-excluded agents only
        non_excluded_agents = [a for a in self.agents.values() if not a.exclude_from_count]
        if len(non_excluded_agents) >= self.max_agents:
            # Sort non-persistent idle agents by last activity (oldest first)
            idle_by_activity = sorted(
                [(name, agent) for name, agent in self.agents.items() 
                 if (agent.state == AgentState.IDLE and 
                     not agent.is_persistent and 
                     not agent.exclude_from_count)],
                key=lambda x: x[1].last_task_at or x[1].created_at
            )
            
            # Remove older idle agents to make room
            agents_to_remove = len(non_excluded_agents) - self.max_agents + 1
            for name, agent in idle_by_activity[:agents_to_remove]:
                if (name, agent) not in idle_agents:
                    idle_agents.append((name, agent))
        
        # Remove idle agents
        for agent_name, agent in idle_agents:
            non_excluded_count = len([a for a in self.agents.values() if not a.exclude_from_count])
            reason = "Capacity management" if non_excluded_count >= self.max_agents else "Idle timeout"
            await self.unregister_agent(agent_name, reason)
            
            if reason == "Capacity management":
                self.cleanup_stats["capacity_cleanups"] += 1
            else:
                self.cleanup_stats["idle_cleanups"] += 1
    
    async def _cleanup_all_agents(self, reason: str = "System cleanup"):
        """Stop and unregister all managed agents."""
        print(f"🧹 Cleaning up all agents due to: {reason}...")
        # Create a copy of agent names to avoid issues with modifying dict during iteration
        agent_names = list(self.agents.keys())
        for agent_name in agent_names:
            agent_info = self.agents.get(agent_name)
            if agent_info and not agent_info.is_persistent:
                await self._stop_agent_container(agent_info, reason)
        
        # Unregister non-persistent agents
        self.agents = {name: agent for name, agent in self.agents.items() if agent.is_persistent}
    
    async def _stop_agent_container(self, agent_info: AgentInfo, reason: str):
        """Stop and remove an agent's container"""
        if not agent_info.container_id:
            return
        
        try:
            agent_info.state = AgentState.STOPPING
            
            # Stop the container
            await asyncio.get_event_loop().run_in_executor(
                None, 
                self.orchestrator.stop_container, 
                agent_info.container_id
            )
            
            # Remove the container
            await asyncio.get_event_loop().run_in_executor(
                None, 
                self.orchestrator.remove_container, 
                agent_info.container_id
            )
            
            agent_info.state = AgentState.STOPPED
            print(f"🗑️ Stopped container {agent_info.container_id[:12]} for agent '{agent_info.name}': {reason}")
            
        except Exception as e:
            print(f"❌ Error stopping container for agent '{agent_info.name}': {e}")
            agent_info.state = AgentState.ERROR
    
    async def _update_container_states(self):
        """Update the state of containers based on Docker status"""
        for agent_name, agent_info in self.agents.items():
            if not agent_info.container_id:
                continue
            
            try:
                # Check if container is still running
                is_running = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.orchestrator.is_container_running,
                    agent_info.container_id
                )
                
                if not is_running and agent_info.state in [AgentState.RUNNING, AgentState.WORKING, AgentState.IDLE]:
                    print(f"⚠️ Container for agent '{agent_name}' is no longer running")
                    agent_info.mark_error()
                
            except Exception as e:
                print(f"❌ Error checking container status for agent '{agent_name}': {e}")
                agent_info.mark_error() 
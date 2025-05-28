"""Collaborative Sub-Agent Groups and Communication Management"""

import uuid
import asyncio
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
from .dynamic_subagent import DynamicSubAgentManager, SubAgentRole
from .settings import RaidConfig
from ..message_queue.redis_mq import RedisMQ


class CollaborationMessageType(str, Enum):
    """Types of messages allowed between collaborating Sub-Agents"""
    DATA_SHARE = "data_share"           # Share computed data/results
    REQUEST_DATA = "request_data"       # Request specific data from another agent
    STATUS_UPDATE = "status_update"     # Update on task progress
    COORDINATION = "coordination"       # Coordinate next steps
    VALIDATION = "validation"          # Request validation of results
    ERROR_REPORT = "error_report"      # Report errors or issues


class CollaborationMessage(BaseModel):
    """Structured message format for Sub-Agent collaboration"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: CollaborationMessageType
    sender_agent: str
    target_agent: Optional[str] = None  # None means broadcast to all in group
    group_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Restricted payload - only specific data types allowed
    data: Optional[Dict[str, Any]] = None
    request: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None
    
    # Metadata for tracking
    correlation_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """Check if message has expired"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    @classmethod
    def create_data_share(
        cls, 
        sender: str, 
        group_id: str, 
        data: Dict[str, Any],
        target_agent: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> "CollaborationMessage":
        """Create a data sharing message"""
        return cls(
            message_type=CollaborationMessageType.DATA_SHARE,
            sender_agent=sender,
            target_agent=target_agent,
            group_id=group_id,
            data=data,
            correlation_id=correlation_id,
            expires_at=datetime.utcnow() + timedelta(minutes=30)
        )
    
    @classmethod
    def create_request(
        cls,
        sender: str,
        target_agent: str,
        group_id: str,
        request: str,
        correlation_id: Optional[str] = None
    ) -> "CollaborationMessage":
        """Create a data request message"""
        return cls(
            message_type=CollaborationMessageType.REQUEST_DATA,
            sender_agent=sender,
            target_agent=target_agent,
            group_id=group_id,
            request=request,
            correlation_id=correlation_id,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
    
    @classmethod
    def create_status_update(
        cls,
        sender: str,
        group_id: str,
        status: str,
        correlation_id: Optional[str] = None
    ) -> "CollaborationMessage":
        """Create a status update message"""
        return cls(
            message_type=CollaborationMessageType.STATUS_UPDATE,
            sender_agent=sender,
            group_id=group_id,
            status=status,
            correlation_id=correlation_id,
            expires_at=datetime.utcnow() + timedelta(minutes=15)
        )


class CollaborationRestrictions(BaseModel):
    """Restrictions and rules for Sub-Agent collaboration"""
    allowed_message_types: Set[CollaborationMessageType] = Field(
        default_factory=lambda: {
            CollaborationMessageType.DATA_SHARE,
            CollaborationMessageType.REQUEST_DATA,
            CollaborationMessageType.STATUS_UPDATE
        }
    )
    max_message_size_bytes: int = 10000  # 10KB max message size
    max_messages_per_minute: int = 30
    allowed_data_keys: Optional[Set[str]] = None  # Restrict data keys if specified
    collaboration_timeout_minutes: int = 60
    auto_cleanup_expired: bool = True


class CollaborativeAgentGroup:
    """Manages a group of Sub-Agents that can collaborate with restricted communication"""
    
    def __init__(
        self,
        group_id: str,
        group_name: str,
        config: RaidConfig,
        restrictions: Optional[CollaborationRestrictions] = None
    ):
        self.group_id = group_id
        self.group_name = group_name
        self.config = config
        self.restrictions = restrictions or CollaborationRestrictions()
        
        self.agents: Dict[str, Dict[str, Any]] = {}  # agent_name -> metadata
        self.created_at = datetime.utcnow()
        self.collaboration_channel = f"raid:collaboration:{self.group_id}"
        self.message_history: List[CollaborationMessage] = []
        self.message_rate_tracking: Dict[str, List[datetime]] = {}
        
        self.mq: Optional[RedisMQ] = None
    
    async def initialize_messaging(self) -> None:
        """Initialize Redis messaging for collaboration"""
        if not self.mq:
            self.mq = RedisMQ(self.config.message_queue)
            await self.mq.connect()
    
    def add_agent(
        self,
        agent_name: str,
        role: str,
        profile_data: Dict[str, Any],
        collaboration_permissions: Optional[Set[CollaborationMessageType]] = None
    ) -> None:
        """Add a Sub-Agent to the collaboration group"""
        self.agents[agent_name] = {
            "role": role,
            "profile_data": profile_data,
            "joined_at": datetime.utcnow(),
            "permissions": collaboration_permissions or self.restrictions.allowed_message_types,
            "message_count": 0,
            "last_activity": datetime.utcnow()
        }
    
    def remove_agent(self, agent_name: str) -> None:
        """Remove a Sub-Agent from the collaboration group"""
        if agent_name in self.agents:
            del self.agents[agent_name]
            if agent_name in self.message_rate_tracking:
                del self.message_rate_tracking[agent_name]
    
    def get_agent_list(self) -> List[str]:
        """Get list of all agents in the group"""
        return list(self.agents.keys())
    
    def validate_message(self, message: CollaborationMessage, sender: str) -> bool:
        """Validate if a message is allowed according to restrictions"""
        # Check if sender is in group
        if sender not in self.agents:
            return False
        
        # Check message type permissions
        agent_permissions = self.agents[sender]["permissions"]
        if message.message_type not in agent_permissions:
            return False
        
        # Check rate limiting
        if not self._check_rate_limit(sender):
            return False
        
        # Check message size (approximation)
        message_json = message.model_dump_json()
        if len(message_json.encode()) > self.restrictions.max_message_size_bytes:
            return False
        
        # Check data keys if restricted
        if (message.data and 
            self.restrictions.allowed_data_keys and 
            not set(message.data.keys()).issubset(self.restrictions.allowed_data_keys)):
            return False
        
        # Check target agent exists (if specified)
        if message.target_agent and message.target_agent not in self.agents:
            return False
        
        return True
    
    def _check_rate_limit(self, sender: str) -> bool:
        """Check if sender is within rate limits"""
        now = datetime.utcnow()
        if sender not in self.message_rate_tracking:
            self.message_rate_tracking[sender] = []
        
        # Clean old messages (outside 1-minute window)
        cutoff_time = now - timedelta(minutes=1)
        self.message_rate_tracking[sender] = [
            msg_time for msg_time in self.message_rate_tracking[sender]
            if msg_time > cutoff_time
        ]
        
        # Check if under limit
        return len(self.message_rate_tracking[sender]) < self.restrictions.max_messages_per_minute
    
    async def send_collaboration_message(self, message: CollaborationMessage) -> bool:
        """Send a collaboration message with validation"""
        if not self.mq:
            await self.initialize_messaging()
        
        # Validate message
        if not self.validate_message(message, message.sender_agent):
            return False
        
        # Track rate limiting
        if message.sender_agent not in self.message_rate_tracking:
            self.message_rate_tracking[message.sender_agent] = []
        self.message_rate_tracking[message.sender_agent].append(datetime.utcnow())
        
        # Store in history
        self.message_history.append(message)
        self.agents[message.sender_agent]["message_count"] += 1
        self.agents[message.sender_agent]["last_activity"] = datetime.utcnow()
        
        # Send to Redis channel
        await self.mq.publish_message(self.collaboration_channel, message.model_dump_json())
        return True
    
    async def listen_for_messages(self, agent_name: str, callback: callable) -> None:
        """Listen for collaboration messages for a specific agent"""
        if not self.mq:
            await self.initialize_messaging()
        
        # Subscribe to collaboration channel
        async def message_handler(channel: str, message_data: str):
            try:
                message_dict = eval(message_data)  # Safe in controlled environment
                message = CollaborationMessage(**message_dict)
                
                # Check if message is for this agent
                if (message.target_agent is None or  # Broadcast
                    message.target_agent == agent_name):
                    
                    # Don't send back to sender
                    if message.sender_agent != agent_name:
                        # Check expiration
                        if not message.is_expired():
                            await callback(message)
            except Exception as e:
                print(f"Error processing collaboration message: {e}")
        
        await self.mq.subscribe_to_channel(self.collaboration_channel, message_handler)
    
    def get_group_status(self) -> Dict[str, Any]:
        """Get status of the collaboration group"""
        return {
            "group_id": self.group_id,
            "group_name": self.group_name,
            "agents": list(self.agents.keys()),
            "agent_count": len(self.agents),
            "created_at": self.created_at,
            "total_messages": len(self.message_history),
            "active_agents": [
                name for name, data in self.agents.items()
                if (datetime.utcnow() - data["last_activity"]).total_seconds() < 300  # 5 min
            ],
            "restrictions": self.restrictions.model_dump()
        }
    
    def cleanup_expired_messages(self) -> int:
        """Remove expired messages from history"""
        if not self.restrictions.auto_cleanup_expired:
            return 0
        
        initial_count = len(self.message_history)
        self.message_history = [
            msg for msg in self.message_history
            if not msg.is_expired()
        ]
        return initial_count - len(self.message_history)
    
    async def shutdown(self) -> None:
        """Shutdown the collaboration group"""
        if self.mq:
            await self.mq.unsubscribe_from_channel(self.collaboration_channel)
            await self.mq.disconnect()


class CollaborationManager:
    """Global manager for all collaborative Sub-Agent groups"""
    
    def __init__(self, config: RaidConfig):
        self.config = config
        self.active_groups: Dict[str, CollaborativeAgentGroup] = {}
        self.group_counter = 0
    
    def create_collaboration_group(
        self,
        group_name: str,
        restrictions: Optional[CollaborationRestrictions] = None
    ) -> CollaborativeAgentGroup:
        """Create a new collaboration group"""
        self.group_counter += 1
        group_id = f"collab_{self.group_counter}_{uuid.uuid4().hex[:8]}"
        
        group = CollaborativeAgentGroup(
            group_id=group_id,
            group_name=group_name,
            config=self.config,
            restrictions=restrictions
        )
        
        self.active_groups[group_id] = group
        return group
    
    def get_group(self, group_id: str) -> Optional[CollaborativeAgentGroup]:
        """Get a collaboration group by ID"""
        return self.active_groups.get(group_id)
    
    def list_groups(self) -> List[Dict[str, Any]]:
        """List all active collaboration groups"""
        return [group.get_group_status() for group in self.active_groups.values()]
    
    async def cleanup_inactive_groups(self, max_age_hours: int = 24) -> List[str]:
        """Remove groups that have been inactive"""
        now = datetime.utcnow()
        to_remove = []
        
        for group_id, group in self.active_groups.items():
            age = now - group.created_at
            if age.total_seconds() > (max_age_hours * 3600):
                # Check if any agent had recent activity
                recent_activity = any(
                    (now - agent_data["last_activity"]).total_seconds() < 3600
                    for agent_data in group.agents.values()
                )
                
                if not recent_activity:
                    to_remove.append(group_id)
                    await group.shutdown()
        
        for group_id in to_remove:
            del self.active_groups[group_id]
        
        return to_remove
    
    async def shutdown_all_groups(self) -> None:
        """Shutdown all collaboration groups"""
        for group in self.active_groups.values():
            await group.shutdown()
        self.active_groups.clear()
"""Message models for queue communication"""

from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
from datetime import datetime


class TaskMessage(BaseModel):
    """Message format for task requests"""
    task_id: str
    sub_agent_profile: str
    prompt: str
    tools: list[str]
    llm_config: Dict[str, Any]
    correlation_id: Optional[str] = None
    timestamp: datetime
    
    @classmethod
    def create(
        cls,
        sub_agent_profile: str,
        prompt: str,
        tools: list[str],
        llm_config: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> "TaskMessage":
        """Create a new task message"""
        return cls(
            task_id=str(uuid.uuid4()),
            sub_agent_profile=sub_agent_profile,
            prompt=prompt,
            tools=tools,
            llm_config=llm_config,
            correlation_id=correlation_id or str(uuid.uuid4()),
            timestamp=datetime.utcnow()
        )


class ResultMessage(BaseModel):
    """Message format for task results"""
    task_id: str
    correlation_id: str
    status: str  # "success", "error", "timeout"
    result: Optional[str] = None
    error: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    timestamp: datetime
    
    @classmethod
    def success(
        cls,
        task_id: str,
        correlation_id: str,
        result: str,
        usage: Optional[Dict[str, int]] = None
    ) -> "ResultMessage":
        """Create a success result message"""
        return cls(
            task_id=task_id,
            correlation_id=correlation_id,
            status="success",
            result=result,
            usage=usage,
            timestamp=datetime.utcnow()
        )
    
    @classmethod
    def create_error(
        cls,
        task_id: str,
        correlation_id: str,
        error: str
    ) -> "ResultMessage":
        """Create an error result message"""
        return cls(
            task_id=task_id,
            correlation_id=correlation_id,
            status="error",
            error=error,
            timestamp=datetime.utcnow()
        )
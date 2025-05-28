"""Abstract interface for LLM backends"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Response from LLM backend"""
    content: str
    finish_reason: str
    usage: Optional[Dict[str, int]] = None
    model: str


class LLMMessage(BaseModel):
    """Message format for LLM communication"""
    role: str  # "system", "user", "assistant"
    content: str


class LLMBackend(ABC):
    """Abstract base class for LLM backends"""
    
    def __init__(self, model: str, **kwargs: Any):
        self.model = model
        self.config = kwargs
    
    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """Generate response from LLM"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM backend is available"""
        pass
"""OpenAI backend implementation"""

from typing import List, Optional, Any
import openai
from .interface import LLMBackend, LLMResponse, LLMMessage


class OpenAIBackend(LLMBackend):
    """OpenAI LLM backend implementation"""
    
    def __init__(self, model: str, api_key: str, **kwargs: Any):
        super().__init__(model, **kwargs)
        self.client = openai.AsyncOpenAI(api_key=api_key)
    
    async def generate(
        self,
        messages: List[LLMMessage],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """Generate response using OpenAI API"""
        try:
            # Convert messages to OpenAI format
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            # Prepare request parameters
            request_params = {
                "model": self.model,
                "messages": openai_messages,
            }
            
            # Special handling for o4-mini model
            if self.model == "o4-mini":
                request_params["response_format"] = {"type": "text"}
                request_params["reasoning_effort"] = kwargs.get("reasoning_effort", "medium")
                # o4-mini uses max_completion_tokens instead of max_tokens
                if max_tokens is not None:
                    request_params["max_completion_tokens"] = max_tokens
                # o4-mini doesn't support custom temperature, only default (1)
                # So we skip temperature parameter for o4-mini
            else:
                # Standard models support temperature and max_tokens
                if temperature is not None:
                    request_params["temperature"] = temperature
                if max_tokens is not None:
                    request_params["max_tokens"] = max_tokens
            
            # Add other kwargs (excluding our special handled ones)
            for key, value in kwargs.items():
                if key not in ["reasoning_effort"]:  # Skip our custom params
                    request_params[key] = value
            
            # Make API call
            response = await self.client.chat.completions.create(**request_params)
            
            return LLMResponse(
                content=response.choices[0].message.content or "",
                finish_reason=response.choices[0].finish_reason or "unknown",
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                } if response.usage else None,
                model=response.model
            )
            
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check OpenAI API availability"""
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
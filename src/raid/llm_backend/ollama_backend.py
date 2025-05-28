"""Ollama backend implementation"""

from typing import List, Optional, Any
import aiohttp
import json
from .interface import LLMBackend, LLMResponse, LLMMessage


class OllamaBackend(LLMBackend):
    """Ollama LLM backend implementation"""
    
    def __init__(self, model: str, base_url: str = "http://localhost:11434", **kwargs: Any):
        super().__init__(model, **kwargs)
        self.base_url = base_url.rstrip("/")
    
    async def generate(
        self,
        messages: List[LLMMessage],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """Generate response using Ollama API"""
        try:
            # Convert messages to Ollama format
            ollama_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            # Prepare request payload
            payload = {
                "model": self.model,
                "messages": ollama_messages,
                "stream": False,
                **kwargs
            }
            
            # Add optional parameters
            options = {}
            if max_tokens is not None:
                options["num_predict"] = max_tokens
            if temperature is not None:
                options["temperature"] = temperature
            
            if options:
                payload["options"] = options
            
            # Make API call
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"Ollama API error: {error_text}")
                    
                    result = await response.json()
                    
                    return LLMResponse(
                        content=result.get("message", {}).get("content", ""),
                        finish_reason=result.get("done_reason", "stop"),
                        usage={
                            "prompt_tokens": result.get("prompt_eval_count", 0),
                            "completion_tokens": result.get("eval_count", 0),
                            "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
                        },
                        model=self.model
                    )
                    
        except Exception as e:
            raise RuntimeError(f"Ollama API error: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check Ollama API availability"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/version") as response:
                    return response.status == 200
        except Exception:
            return False
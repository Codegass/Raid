"""Factory for creating LLM backend instances"""

from typing import Any
from ..config.settings import LLMBackendConfig
from .interface import LLMBackend
from .openai_backend import OpenAIBackend
from .ollama_backend import OllamaBackend


def create_llm_backend(config: LLMBackendConfig) -> LLMBackend:
    """Create LLM backend instance based on configuration"""
    
    if config.provider == "openai":
        if not config.api_key:
            raise ValueError("OpenAI API key is required")
        return OpenAIBackend(
            model=config.model,
            api_key=config.api_key
        )
    
    elif config.provider == "ollama":
        if not config.base_url:
            raise ValueError("Ollama base URL is required")
        return OllamaBackend(
            model=config.model,
            base_url=config.base_url
        )
    
    else:
        raise ValueError(f"Unsupported LLM provider: {config.provider}")
"""LLM Backend Interface for OpenAI and Ollama integration"""

from .interface import LLMBackend, LLMResponse
from .openai_backend import OpenAIBackend
from .ollama_backend import OllamaBackend

__all__ = ["LLMBackend", "LLMResponse", "OpenAIBackend", "OllamaBackend"]
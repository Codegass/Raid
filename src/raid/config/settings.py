"""Global settings for the Raid system"""

from pydantic import BaseModel
from typing import Optional
import os


class LLMBackendConfig(BaseModel):
    """Configuration for LLM backends"""
    provider: str  # "openai" or "ollama"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str
    max_tokens: int = 1000
    temperature: float = 0.5


class MessageQueueConfig(BaseModel):
    """Configuration for message queue system"""
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None


class RaidConfig(BaseModel):
    """Main configuration for Raid system"""
    llm_backend: LLMBackendConfig
    message_queue: MessageQueueConfig
    docker_socket: str = "unix://var/run/docker.sock"
    max_dynamic_sub_agents: int = 5  # Maximum number of dynamically created Sub-Agents
    
    @classmethod
    def from_env(cls) -> "RaidConfig":
        """Create configuration from environment variables"""
        llm_provider = os.getenv("RAID_LLM_PROVIDER", "openai")
        print(f"DEBUG: Detected LLM Provider: '{llm_provider}' (Type: {type(llm_provider)})")
        
        if llm_provider == "openai":
            llm_config = LLMBackendConfig(
                provider="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model=os.getenv("RAID_OPENAI_MODEL", "gpt-4o")
            )
        elif llm_provider == "ollama":
            llm_config = LLMBackendConfig(
                provider="ollama",
                base_url=os.getenv("RAID_OLLAMA_URL", "http://localhost:11434"),
                model=os.getenv("RAID_OLLAMA_MODEL", "qwen3:30b")
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
        
        mq_config = MessageQueueConfig(
            redis_host=os.getenv("RAID_REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("RAID_REDIS_PORT", "6379")),
            redis_db=int(os.getenv("RAID_REDIS_DB", "0")),
            redis_password=os.getenv("RAID_REDIS_PASSWORD")
        )
        
        return cls(
            llm_backend=llm_config,
            message_queue=mq_config,
            docker_socket=os.getenv("RAID_DOCKER_SOCKET", "unix://var/run/docker.sock"),
            max_dynamic_sub_agents=int(os.getenv("RAID_MAX_DYNAMIC_SUB_AGENTS", "5"))
        )
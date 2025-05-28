"""Sub-Agent Auto-Configurator for YAML profile management"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import yaml
import os
from pathlib import Path


class DockerConfig(BaseModel):
    """Docker configuration for Sub-Agent"""
    base_image: str
    working_dir: str = "/app"
    expose_port: Optional[int] = None


class SubAgentProfile(BaseModel):
    """Sub-Agent profile configuration"""
    name: str
    description: str
    version: str
    llm_config: Dict[str, Any]
    tools: List[str]
    system_prompt: str
    docker_config: DockerConfig
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> "SubAgentProfile":
        """Load profile from YAML file"""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(**data)
    
    def to_yaml(self, yaml_path: str) -> None:
        """Save profile to YAML file"""
        with open(yaml_path, 'w') as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)


class SubAgentConfigurator:
    """Auto-configurator for Sub-Agent profiles"""
    
    def __init__(self, profiles_dir: str = "profiles"):
        self.profiles_dir = Path(profiles_dir)
        # Handle Docker container environment
        if not self.profiles_dir.exists():
            # Try current directory (for Docker containers)
            container_profile = Path("profile.yaml")
            if container_profile.exists():
                self.profiles_dir = Path(".")
            else:
                self.profiles_dir.mkdir(exist_ok=True)
    
    def load_profile(self, profile_name: str) -> SubAgentProfile:
        """Load a Sub-Agent profile by name"""
        # First try the standard path
        yaml_path = self.profiles_dir / f"{profile_name}.yaml"
        
        # If in Docker container, try "profile.yaml" 
        if not yaml_path.exists():
            container_profile = self.profiles_dir / "profile.yaml"
            if container_profile.exists():
                yaml_path = container_profile
        
        if not yaml_path.exists():
            raise FileNotFoundError(f"Profile '{profile_name}' not found at {yaml_path}")
        
        return SubAgentProfile.from_yaml(str(yaml_path))
    
    def save_profile(self, profile: SubAgentProfile) -> None:
        """Save a Sub-Agent profile"""
        yaml_path = self.profiles_dir / f"{profile.name}.yaml"
        profile.to_yaml(str(yaml_path))
    
    def list_profiles(self) -> List[str]:
        """List available profile names"""
        return [
            f.stem for f in self.profiles_dir.glob("*.yaml")
        ]
    
    def get_all_profiles(self) -> Dict[str, SubAgentProfile]:
        """Get all available profiles"""
        profiles = {}
        for profile_name in self.list_profiles():
            try:
                profiles[profile_name] = self.load_profile(profile_name)
            except Exception as e:
                print(f"Warning: Failed to load profile '{profile_name}': {e}")
        return profiles
    
    def generate_dockerfile(self, profile: SubAgentProfile) -> str:
        """Generate Dockerfile content for a Sub-Agent profile"""
        dockerfile_content = f"""# Dockerfile for {profile.name}
FROM {profile.docker_config.base_image}

WORKDIR {profile.docker_config.working_dir}

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Sub-Agent code
COPY src/ ./src/

# Copy profile configuration
COPY profiles/{profile.name}.yaml ./profile.yaml

# Set environment variables
ENV RAID_SUB_AGENT_PROFILE={profile.name}
ENV PYTHONPATH=/app/src

# Run the Sub-Agent
CMD ["python", "-m", "raid.sub_agent.main"]
"""
        
        if profile.docker_config.expose_port:
            dockerfile_content += f"\nEXPOSE {profile.docker_config.expose_port}\n"
        
        return dockerfile_content
    
    def generate_requirements_txt(self) -> str:
        """Generate requirements.txt for Sub-Agent Docker image"""
        return """pydantic>=2.0.0
pyyaml>=6.0
redis>=4.5.0
openai>=1.0.0
requests>=2.28.0
asyncio-mqtt>=0.13.0
aiohttp>=3.8.0
"""
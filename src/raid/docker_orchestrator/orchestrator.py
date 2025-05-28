"""Docker Orchestrator implementation for managing Sub-Agent containers"""

import os
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path
import docker
from docker.models.containers import Container
from docker.models.images import Image
from ..config.sub_agent_config import SubAgentProfile, SubAgentConfigurator


class DockerOrchestrator:
    """Manages Docker containers for Sub-Agents"""
    
    def __init__(self, docker_socket: str = "unix://var/run/docker.sock"):
        self.docker_client = docker.DockerClient(base_url=docker_socket)
        self.configurator = SubAgentConfigurator()
        self.running_containers: Dict[str, Container] = {}
    
    def build_sub_agent_image(self, profile: SubAgentProfile) -> Image:
        """Build Docker image for a Sub-Agent profile"""
        image_name = f"raid-subagent-{profile.name}:{profile.version}"
        
        # Check if image already exists
        try:
            existing_image = self.docker_client.images.get(image_name)
            print(f"Image {image_name} already exists, using existing image")
            return existing_image
        except docker.errors.ImageNotFound:
            pass
        
        # Create temporary build context
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Generate Dockerfile
            dockerfile_content = self.configurator.generate_dockerfile(profile)
            (temp_path / "Dockerfile").write_text(dockerfile_content)
            
            # Generate requirements.txt
            requirements_content = self.configurator.generate_requirements_txt()
            (temp_path / "requirements.txt").write_text(requirements_content)
            
            # Copy source code
            src_dir = temp_path / "src"
            src_dir.mkdir()
            self._copy_source_code(src_dir)
            
            # Copy profiles
            profiles_dir = temp_path / "profiles"
            profiles_dir.mkdir()
            profile.to_yaml(str(profiles_dir / f"{profile.name}.yaml"))
            
            # Build image
            print(f"Building Docker image: {image_name}")
            image, build_logs = self.docker_client.images.build(
                path=str(temp_path),
                tag=image_name,
                rm=True
            )
            
            print(f"Successfully built image: {image_name}")
            return image
    
    def start_sub_agent(
        self, 
        profile_name: str, 
        environment: Optional[Dict[str, str]] = None
    ) -> Container:
        """Start a Sub-Agent container"""
        container_name = f"raid-subagent-{profile_name}"
        
        # Check if container already exists (even if not in our tracking)
        try:
            existing_container = self.docker_client.containers.get(container_name)
            existing_container.reload()
            
            if existing_container.status == "running":
                print(f"Sub-Agent '{profile_name}' container already running, reusing it")
                self.running_containers[profile_name] = existing_container
                return existing_container
            else:
                print(f"Sub-Agent '{profile_name}' container exists but stopped, removing it")
                existing_container.remove(force=True)
        except docker.errors.NotFound:
            # Container doesn't exist, which is fine
            pass
        
        # Remove from our tracking if it was there
        if profile_name in self.running_containers:
            del self.running_containers[profile_name]
        
        # Load profile
        profile = self.configurator.load_profile(profile_name)
        
        # Build image if needed
        image = self.build_sub_agent_image(profile)
        
        # Prepare environment variables
        env_vars = {
            "RAID_SUB_AGENT_PROFILE": profile_name,
            **(environment or {})
        }
        
        # Start container (container_name already defined above)
        
        print(f"Starting Sub-Agent container: {container_name}")
        container = self.docker_client.containers.run(
            image=image.id,
            name=container_name,
            environment=env_vars,
            detach=True,
            remove=False,
            restart_policy={"Name": "unless-stopped"}
        )
        
        self.running_containers[profile_name] = container
        print(f"Sub-Agent '{profile_name}' started successfully")
        return container
    
    def stop_sub_agent(self, profile_name: str) -> None:
        """Stop a Sub-Agent container"""
        container_name = f"raid-subagent-{profile_name}"
        
        # Remove from tracking first
        if profile_name in self.running_containers:
            del self.running_containers[profile_name]
        
        try:
            container = self.docker_client.containers.get(container_name)
            print(f"Stopping Sub-Agent '{profile_name}'...")
            
            try:
                container.stop(timeout=10)
            except Exception as e:
                print(f"Error stopping container (will force remove): {e}")
            
            container.remove(force=True)
            print(f"Sub-Agent '{profile_name}' stopped and removed successfully")
            
        except docker.errors.NotFound:
            print(f"Sub-Agent '{profile_name}' container not found (already removed)")
        except Exception as e:
            print(f"Error stopping Sub-Agent '{profile_name}': {e}")
    
    def get_sub_agent_status(self, profile_name: str) -> Dict[str, Any]:
        """Get status of a Sub-Agent container"""
        if profile_name not in self.running_containers:
            return {"status": "not_running"}
        
        container = self.running_containers[profile_name]
        container.reload()  # Refresh container info
        
        return {
            "status": container.status,
            "id": container.id,
            "name": container.name,
            "created": container.attrs["Created"],
            "image": container.image.tags[0] if container.image.tags else "unknown"
        }
    
    def list_running_sub_agents(self) -> List[Dict[str, Any]]:
        """List all running Sub-Agent containers"""
        running_agents = []
        
        for profile_name, container in self.running_containers.items():
            status = self.get_sub_agent_status(profile_name)
            status["profile_name"] = profile_name
            running_agents.append(status)
        
        return running_agents
    
    def ensure_sub_agent_running(
        self, 
        profile_name: str, 
        environment: Optional[Dict[str, str]] = None
    ) -> Container:
        """Ensure a Sub-Agent is running, start if not"""
        container_name = f"raid-subagent-{profile_name}"
        
        # Check if container exists
        try:
            existing_container = self.docker_client.containers.get(container_name)
            existing_container.reload()
            
            if existing_container.status == "running":
                print(f"Sub-Agent '{profile_name}' container already running, reusing")
                self.running_containers[profile_name] = existing_container
                return existing_container
            else:
                print(f"Sub-Agent '{profile_name}' container exists but not running ({existing_container.status}), removing...")
                existing_container.remove(force=True)
                
        except docker.errors.NotFound:
            # Container doesn't exist, which is fine
            pass
        except Exception as e:
            print(f"Error checking existing container: {e}")
            # Try to remove it anyway
            try:
                existing_container = self.docker_client.containers.get(container_name)
                existing_container.remove(force=True)
            except:
                pass
        
        # Start fresh container
        return self.start_sub_agent(profile_name, environment)
    
    def cleanup_all(self) -> None:
        """Stop and cleanup all Sub-Agent containers"""
        profile_names = list(self.running_containers.keys())
        
        for profile_name in profile_names:
            try:
                self.stop_sub_agent(profile_name)
            except Exception as e:
                print(f"Error stopping {profile_name}: {e}")
        
        # Also clean up any orphaned raid containers
        try:
            containers = self.docker_client.containers.list(all=True, filters={"name": "raid-subagent"})
            for container in containers:
                try:
                    print(f"Cleaning up orphaned container: {container.name}")
                    container.remove(force=True)
                except Exception as e:
                    print(f"Error removing orphaned container {container.name}: {e}")
        except Exception as e:
            print(f"Error during orphaned container cleanup: {e}")
    
    def _copy_source_code(self, dest_dir: Path) -> None:
        """Copy source code to build context"""
        import shutil
        
        # Find the src directory
        current_file = Path(__file__)
        src_root = current_file.parent.parent.parent  # Go up to find src/
        
        if (src_root / "raid").exists():
            shutil.copytree(
                src_root / "raid",
                dest_dir / "raid",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
            )
        else:
            raise FileNotFoundError(f"Source code not found at {src_root}")
    
    def get_container_logs(self, profile_name: str, tail: int = 100) -> str:
        """Get logs from a Sub-Agent container"""
        if profile_name not in self.running_containers:
            return f"Sub-Agent '{profile_name}' is not running"
        
        container = self.running_containers[profile_name]
        logs = container.logs(tail=tail, timestamps=True)
        return logs.decode('utf-8')
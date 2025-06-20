"""Docker Orchestrator implementation for managing Sub-Agent containers"""

import os
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path
import docker
from docker.models.containers import Container
from docker.models.images import Image
import platform
import subprocess
from ..config.sub_agent_config import SubAgentProfile, SubAgentConfigurator


class DockerOrchestrator:
    """Manages Docker containers for Sub-Agents"""
    
    def __init__(self, docker_socket: str = "unix://var/run/docker.sock"):
        self.docker_client = docker.DockerClient(base_url=docker_socket)
        self.configurator = SubAgentConfigurator()
        self.running_containers: Dict[str, Container] = {}
    
    def _open_iterm_for_logs(self, container_name: str):
        """Opens a new iTerm2 tab/window to stream logs for a container on macOS."""
        print(f"🍏 macOS detected. Attempting to open logs for '{container_name}' in a new iTerm2 window.")

        # Using single quotes for the shell command to avoid escaping issues with AppleScript's double quotes.
        # The command is broken into two parts for clarity.
        prompt_command = f"echo '>>> Streaming logs for {container_name}...';"
        log_command = f"docker logs -f {container_name}"
        full_command = f"{prompt_command} {log_command}"

        # We need to escape double quotes inside the AppleScript string for the 'write text' command.
        # Since full_command has no double quotes, we are safe.
        script = f'''
        tell application "iTerm2"
            if current window is not null then
                tell current window
                    create tab with default profile
                end tell
            else
                create window with default profile
            end if
            
            tell current session of current window
                set name to "{container_name} logs"
                write text "{full_command}"
            end tell
        end tell
        '''
        
        try:
            subprocess.run(
                ["osascript", "-e", script], 
                check=True,
                capture_output=True,
                text=True
            )
            print(f"🚀 Successfully opened a new iTerm2 tab for '{container_name}'.")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  AppleScript for iTerm2 failed. Is iTerm2 running?")
            print(f"   STDERR: {e.stderr}")
            # I will also print the script for debugging
            print(f"   Failed script content:\n{script}")
        except FileNotFoundError:
            print("⚠️ `osascript` command not found. This feature is only available on macOS.")

    def build_sub_agent_image(self, profile: SubAgentProfile) -> Image:
        """Build Docker image for a Sub-Agent profile"""
        image_name = f"raid-subagent-{profile.name}:{profile.version}"
        
        # # --- FORCE REBUILD ---
        # # For development, we always want to rebuild the image to get the latest code.
        # # First, try to remove the existing image if it exists.
        # try:
        #     existing_image = self.docker_client.images.get(image_name)
        #     print(f"Removing existing image '{image_name}' to force rebuild...")
        #     self.docker_client.images.remove(image=image_name, force=True)
        #     print(f"Image '{image_name}' removed.")
        # except docker.errors.ImageNotFound:
        #     # This is expected if the image hasn't been built before.
        #     pass
        # except Exception as e:
        #     # Catch other potential errors, e.g., image is in use by a stopped container.
        #     print(f"⚠️  Could not remove existing image '{image_name}': {e}. Continuing with build...")
        
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
                rm=True,
                labels={"org.raid.agent": "true"}
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
            "PYTHONUNBUFFERED": "1",
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

        if platform.system() == "Darwin":
            try:
                self._open_iterm_for_logs(container_name)
            except Exception as e:
                print(f"⚠️  Could not open iTerm2 window for logs: {e}")

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
    
    # Methods for Lifecycle Manager
    
    def stop_container(self, container_id: str) -> None:
        """Stop a container by ID"""
        try:
            container = self.docker_client.containers.get(container_id)
            container.stop(timeout=10)
            print(f"Stopped container {container_id[:12]}")
        except docker.errors.NotFound:
            print(f"Container {container_id[:12]} not found (already removed)")
        except Exception as e:
            print(f"Error stopping container {container_id[:12]}: {e}")
    
    def remove_container(self, container_id: str) -> None:
        """Remove a container by ID"""
        try:
            container = self.docker_client.containers.get(container_id)
            container.remove(force=True)
            print(f"Removed container {container_id[:12]}")
        except docker.errors.NotFound:
            print(f"Container {container_id[:12]} not found (already removed)")
        except Exception as e:
            print(f"Error removing container {container_id[:12]}: {e}")
    
    def is_container_running(self, container_id: str) -> bool:
        """Check if a specific container is running by its ID."""
        try:
            container = self.docker_client.containers.get(container_id)
            return container.status == 'running'
        except docker.errors.NotFound:
            return False
        except Exception as e:
            print(f"Error checking container status for {container_id}: {e}")
            return False

    def cleanup_unused_images(self, max_images_to_keep: int = 10) -> None:
        """
        Cleans up unused raid-subagent images, keeping a specified number of the most recent ones.
        """
        print(f"\n🧹 Starting unused Docker image cleanup (keeping max {max_images_to_keep})...")
        try:
            # Prune dangling images (the <none>:<none> ones)
            pruned_images = self.docker_client.images.prune(filters={'dangling': True})
            if "ImagesDeleted" in pruned_images and pruned_images["ImagesDeleted"]:
                space_reclaimed = pruned_images.get('SpaceReclaimed', 0)
                print(f"🧹 Pruned {len(pruned_images['ImagesDeleted'])} dangling images, reclaimed {space_reclaimed // 1024 // 1024} MB.")

            # 1. Get all raid-subagent images, sorted by creation time (newest first)
            all_raid_images = self.docker_client.images.list(
                filters={"label": "org.raid.agent=true"}
            )
            all_raid_images.sort(key=lambda img: img.attrs['Created'], reverse=True)

            # 2. Find out which images are currently used by running containers
            running_containers = self.docker_client.containers.list(
                filters={"label": "org.raid.agent=true"}
            )
            used_image_ids = {container.image.id for container in running_containers}
            print(f"🕵️ Found {len(all_raid_images)} total Raid images and {len(used_image_ids)} images in use.")

            # 3. Determine which images are unused
            unused_images = []
            for img in all_raid_images:
                if img.id not in used_image_ids:
                    unused_images.append(img)
            
            print(f"👉 Found {len(unused_images)} unused images.")

            # 4. If unused images exceed the limit, remove the oldest ones
            if len(unused_images) > max_images_to_keep:
                images_to_remove = unused_images[max_images_to_keep:]
                print(f"🗑️  Will remove {len(images_to_remove)} oldest images to meet the limit.")
                for img_to_remove in images_to_remove:
                    try:
                        # Use the first tag for a more user-friendly name in logs
                        image_name = img_to_remove.tags[0] if img_to_remove.tags else img_to_remove.id
                        print(f"   - Removing {image_name}...")
                        self.docker_client.images.remove(image=img_to_remove.id, force=True)
                    except docker.errors.APIError as e:
                        print(f"   - ⚠️  Could not remove image {image_name}: {e}")
            else:
                print("✅ Image count is within the limit. No images to remove.")

        except Exception as e:
            print(f"❌ An error occurred during image cleanup: {e}")
        
        print("🧹 Image cleanup finished.")
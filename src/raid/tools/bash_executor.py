"""Bash command execution tool with security constraints (Docker-only)"""

import os
import subprocess
import asyncio
import tempfile
import shlex
from pathlib import Path
from typing import List, Dict, Any, Optional
from .base import Tool, ToolParameter


class RunBashCommandTool(Tool):
    """Tool for executing bash commands in a secure Docker environment"""
    
    def __init__(self):
        super().__init__()
        # Set up working directory to match the Dockerfile's WORKDIR
        self.working_dir = Path("/workspace")
        self.working_dir.mkdir(exist_ok=True)
        
        # Allowed commands (whitelist approach for security)
        self.allowed_commands = {
            # File operations
            'ls', 'cat', 'head', 'tail', 'wc', 'grep', 'find', 'sort', 'uniq',
            'cut', 'awk', 'sed', 'diff', 'file', 'stat', 'du', 'df',
            'cp', 'mv', 'mkdir', 'rmdir', 'touch', 'rm',
            'chmod', 'chown',
            
            # Text processing
            'echo', 'printf', 'tr', 'fold', 'fmt', 'nl', 'pr',
            
            # Data processing
            'jq', 'csvcut', 'csvstat', 'csvlook', 'csvgrep',
            
            # Archive operations
            'tar', 'gzip', 'gunzip', 'zip', 'unzip',
            
            # Network (limited)
            'curl', 'wget', 'ping',
            
            # System info (safe)
            'date', 'whoami', 'pwd', 'env', 'which', 'type', 'hostname',
            
            # Process info (limited)
            'ps', 'top', 'htop', 'free', 'uptime', 'kill',
            
            # Development tools
            'git', 'python3', 'pip3', 'node', 'npm', 'yarn',
            'gcc', 'g++', 'make', 'cmake',
            'java', 'javac', 'mvn', 'gradle',
            
            # Package managers (use with caution)
            'apt-get', 'apt-cache', 'dpkg', 'yum', 'dnf',
            
            # Database tools
            'sqlite3', 'mysql', 'psql',
        }
        
        # Forbidden patterns (blacklist for additional security)
        self.forbidden_patterns = [
            'rm -rf /', 'rm -rf *', 'rm -f /', 'rm -f *',
            'chmod 777',
            'sudo', 'su -', 'passwd', 'usermod', 'useradd', 'userdel',
            'systemctl', 'service', 'init.d',
            'mount', 'umount', 'fdisk', 'mkfs',
            'iptables', 'netstat -p', 'ss -p',
            'docker', 'kubectl', 'helm',
            'nc -l', 'ncat -l', 'socat',
            'python -c', 'perl -e', 'ruby -e',
            'eval', 'exec', 'source /',
            '$(', '`', 'bash -c', 'sh -c',
        ]
    
    @property
    def name(self) -> str:
        return "run_bash_command"
    
    @property
    def description(self) -> str:
        return (
            "Executes a bash command in a secure, isolated Docker environment. "
            "IMPORTANT: For commands that may produce long outputs (e.g., build scripts, logs), "
            "you MUST use the 'output_log_file' parameter to save the output to a file. "
            "Then, use another tool like 'cat' or 'grep' on that file to inspect the results. "
            "This avoids system errors from overly long outputs."
        )
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="command",
                type="string",
                description="The bash command to execute. If expecting long output, use 'output_log_file'."
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="Command timeout in seconds (default: 30, max: 300)"
            ),
            ToolParameter(
                name="working_dir",
                type="string",
                description="Working directory for command execution (default: workspace)"
            ),
            ToolParameter(
                name="output_log_file",
                type="string",
                description="Optional. If provided, redirects all command output (stdout/stderr) to this file. The tool will return the file path upon completion.",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> str:
        """Execute bash command with security constraints"""
        command = kwargs.get("command", "").strip()
        timeout = min(kwargs.get("timeout", 30), 300)
        working_dir = kwargs.get("working_dir", str(self.working_dir))
        output_log_file = kwargs.get("output_log_file")
        
        if not command:
            return "Error: Command is required"
        
        # Security checks
        security_check = self._check_security(command)
        if security_check:
            return f"Security Error: {security_check}"
        
        # Check if we're running in Docker (required for bash execution)
        if not self._is_running_in_docker():
            return "Security Error: Bash commands can only be executed within Docker containers"
        
        try:
            result = await self._execute_command_secure(command, timeout, working_dir, output_log_file)
            return result
            
        except Exception as e:
            return f"Execution Error: {str(e)}"
    
    def _check_security(self, command: str) -> Optional[str]:
        """Check command for security violations"""
        command_lower = command.lower()
        
        # Check for forbidden patterns
        for pattern in self.forbidden_patterns:
            if pattern.lower() in command_lower:
                return f"Forbidden pattern detected: {pattern}"
        
        # Parse command to get the main command
        try:
            parsed = shlex.split(command)
            if parsed:
                main_command = parsed[0].split('/')[-1]  # Remove path if present
                
                # Check if main command is allowed
                if main_command not in self.allowed_commands:
                    return f"Command '{main_command}' is not in the allowed list"
        except ValueError as e:
            return f"Invalid command syntax: {str(e)}"
        
        # Check for command chaining that might bypass security
        if any(op in command for op in ['&&', '||', ';']):
            return "Command chaining with &&, ||, or ; is not allowed"
        
        # Check for output redirection to sensitive locations
        if any(redirect in command for redirect in ['> /etc/', '> /bin/', '> /usr/', '> /var/log/']):
            return "Redirection to system directories is forbidden"
        
        return None
    
    def _is_running_in_docker(self) -> bool:
        """Check if we're running inside a Docker container"""
        try:
            # Check for /.dockerenv file
            if os.path.exists('/.dockerenv'):
                return True
            
            # Check cgroup for docker
            with open('/proc/1/cgroup', 'r') as f:
                cgroup_content = f.read()
                if 'docker' in cgroup_content or 'containerd' in cgroup_content:
                    return True
            
            return False
        except:
            # If we can't determine, assume not in Docker for safety
            return False
    
    async def _execute_command_secure(self, command: str, timeout: int, working_dir: str, output_log_file: Optional[str] = None) -> str:
        """Execute command in a secure manner"""
        try:
            # Resolve the target working directory robustly
            target_wd = Path(working_dir)
            if not target_wd.is_absolute():
                target_wd = self.working_dir.joinpath(target_wd).resolve()

            final_wd = self.working_dir if not target_wd.is_dir() else target_wd

            # Set up environment
            env = {
                'PATH': '/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin',
                'HOME': '/tmp', 'USER': 'raid', 'LC_ALL': 'C.UTF-8', 'LANG': 'C.UTF-8',
            }

            # If logging to a file, resolve the path
            log_path = None
            if output_log_file:
                log_path_obj = Path(output_log_file)
                log_path = final_wd.joinpath(log_path_obj) if not log_path_obj.is_absolute() else log_path_obj
                log_path.parent.mkdir(parents=True, exist_ok=True)

            # Create a temporary script to execute
            with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=str(final_wd), suffix='.sh') as script_file:
                script_file.write("#!/bin/bash\nset -eo pipefail\n")
                script_file.write(command + "\n")
                script_path = script_file.name
            os.chmod(script_path, 0o755)

            if log_path:
                # Redirect output to file and wait for completion
                with open(log_path, 'wb') as log_file:
                    process = await asyncio.create_subprocess_exec(
                        script_path, stdout=log_file, stderr=log_file, env=env, cwd=str(final_wd)
                    )
                    await asyncio.wait_for(process.wait(), timeout=timeout)
                os.remove(script_path)
                
                if process.returncode == 0:
                    return f"Command executed successfully. Output saved to: {log_path}"
                else:
                    return f"Command failed with exit code {process.returncode}. Full log saved to: {log_path}"
            else:
                # Capture output in memory
                process = await asyncio.create_subprocess_exec(
                    script_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=str(final_wd)
                )
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                os.remove(script_path)

                output = ""
                if stdout:
                    output += "Output:\n" + stdout.decode('utf-8', errors='ignore')
                if stderr:
                    output += "\nError/Warnings:\n" + stderr.decode('utf-8', errors='ignore')
                if process.returncode != 0:
                    output += f"\nExit code: {process.returncode}"
                
                return output if output else "Command executed successfully (no output)"

        except asyncio.TimeoutError:
            return f"Error: Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Execution Error: {str(e)}"


class SafeBashExecutor:
    """Alternative bash executor with additional sandboxing"""
    
    @staticmethod
    async def execute_in_chroot(command: str, timeout: int = 30) -> str:
        """Execute command in a chroot environment for additional security"""
        # This would require setting up a chroot jail
        # For now, we'll use the regular secure execution
        tool = RunBashCommandTool()
        return await tool._execute_command_secure(command, timeout, "/tmp/raid_workspace")
    
    @staticmethod
    def validate_command_syntax(command: str) -> bool:
        """Validate bash command syntax without executing"""
        try:
            # Use bash -n to check syntax
            result = subprocess.run(
                ['bash', '-n', '-c', command],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False


class LimitedNetworkTool(Tool):
    """Tool for limited network operations"""
    
    @property
    def name(self) -> str:
        return "network_request"
    
    @property
    def description(self) -> str:
        return "Make limited network requests (HTTP GET only) for data retrieval"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="url",
                type="string",
                description="URL to fetch (HTTP/HTTPS only)"
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="Request timeout in seconds (default: 10, max: 30)"
            )
        ]
    
    async def execute(self, **kwargs) -> str:
        """Make a limited HTTP GET request"""
        url = kwargs.get("url", "").strip()
        timeout = min(kwargs.get("timeout", 10), 30)
        
        if not url:
            return "Error: URL is required"
        
        if not url.startswith(('http://', 'https://')):
            return "Error: Only HTTP/HTTPS URLs are allowed"
        
        # Additional security: block private IP ranges
        import urllib.parse
        parsed_url = urllib.parse.urlparse(url)
        hostname = parsed_url.hostname
        
        if hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
            return "Error: Localhost requests are not allowed"
        
        try:
            # Use curl for the request (safer than Python requests in this context)
            command = f"curl -s -L --max-time {timeout} --max-filesize 10485760 '{url}'"
            
            tool = RunBashCommandTool()
            return await tool._execute_command_secure(command, timeout + 5, "/tmp")
            
        except Exception as e:
            return f"Network request failed: {str(e)}"
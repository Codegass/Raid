"""User notification tool for cross-platform system notifications"""

import asyncio
import platform
import subprocess
from typing import List, Any
from .base import Tool, ToolParameter


class NotificationUserTool(Tool):
    """Cross-platform notification tool for alerting users"""
    
    @property
    def name(self) -> str:
        return "notification_user"
    
    @property
    def description(self) -> str:
        return "Send a system notification to the user across Windows, Linux, and macOS platforms"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="title",
                type="string",
                description="Title of the notification",
                required=True
            ),
            ToolParameter(
                name="message",
                type="string",
                description="Main message content of the notification",
                required=True
            ),
            ToolParameter(
                name="urgency",
                type="string",
                description="Urgency level: 'low', 'normal', or 'critical' (default: 'normal')",
                required=False
            )
        ]
    
    async def execute(self, **kwargs: Any) -> str:
        """Send system notification without blocking"""
        title = kwargs.get("title", "Raid Agent Notification")
        message = kwargs.get("message", "")
        urgency = kwargs.get("urgency", "normal").lower()
        
        if not message:
            return "Error: message is required for notification"
        
        if urgency not in ["low", "normal", "critical"]:
            urgency = "normal"
        
        try:
            # Run notification in background to avoid blocking
            await self._send_notification_async(title, message, urgency)
            return f"✅ Notification sent successfully: '{title}'"
            
        except Exception as e:
            return f"❌ Failed to send notification: {str(e)}"
    
    async def _send_notification_async(self, title: str, message: str, urgency: str) -> None:
        """Send notification asynchronously based on platform"""
        system = platform.system().lower()
        
        try:
            if system == "windows":
                await self._notify_windows(title, message)
            elif system == "darwin":  # macOS
                await self._notify_macos(title, message)
            elif system == "linux":
                await self._notify_linux(title, message, urgency)
            else:
                # Fallback for unknown systems
                print(f"📢 NOTIFICATION: {title}\n{message}")
                
        except Exception as e:
            # Fallback to console output if system notification fails
            print(f"📢 NOTIFICATION (fallback): {title}\n{message}")
            print(f"(Notification system error: {e})")
    
    async def _notify_windows(self, title: str, message: str) -> None:
        """Send notification on Windows using PowerShell"""
        # Use PowerShell to show toast notification
        powershell_script = f'''
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        
        $notification = New-Object System.Windows.Forms.NotifyIcon
        $notification.Icon = [System.Drawing.SystemIcons]::Information
        $notification.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
        $notification.BalloonTipText = "{message}"
        $notification.BalloonTipTitle = "{title}"
        $notification.Visible = $true
        $notification.ShowBalloonTip(5000)
        
        Start-Sleep -Seconds 6
        $notification.Dispose()
        '''
        
        await self._run_command_async([
            "powershell", "-Command", powershell_script
        ])
    
    async def _notify_macos(self, title: str, message: str) -> None:
        """Send notification on macOS using osascript"""
        applescript = f'display notification "{message}" with title "{title}"'
        
        await self._run_command_async([
            "osascript", "-e", applescript
        ])
    
    async def _notify_linux(self, title: str, message: str, urgency: str) -> None:
        """Send notification on Linux using notify-send"""
        urgency_map = {
            "low": "low",
            "normal": "normal", 
            "critical": "critical"
        }
        
        urgency_level = urgency_map.get(urgency, "normal")
        
        # Try notify-send first (most common)
        try:
            await self._run_command_async([
                "notify-send", 
                f"--urgency={urgency_level}",
                "--expire-time=5000",
                title, 
                message
            ])
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        # Fallback to zenity
        try:
            await self._run_command_async([
                "zenity", "--info", 
                f"--title={title}",
                f"--text={message}",
                "--timeout=5"
            ])
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        # Fallback to kdialog (KDE)
        try:
            await self._run_command_async([
                "kdialog", "--passivepopup", 
                f"{title}\n{message}",
                "5"
            ])
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        # Final fallback to console
        print(f"📢 NOTIFICATION: {title}\n{message}")
    
    async def _run_command_async(self, command: List[str]) -> None:
        """Run command asynchronously without blocking"""
        try:
            # Create subprocess without waiting for completion
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Don't wait for completion to avoid blocking
            # The notification will run in background
            asyncio.create_task(self._cleanup_process(process))
            
        except Exception as e:
            # If subprocess creation fails, raise to trigger fallback
            raise RuntimeError(f"Failed to create notification process: {e}")
    
    async def _cleanup_process(self, process: asyncio.subprocess.Process) -> None:
        """Wait for process completion and cleanup (runs in background)"""
        try:
            await asyncio.wait_for(process.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            # Kill process if it takes too long
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except:
                # Force kill if needed
                try:
                    process.kill()
                except:
                    pass
        except Exception:
            # Ignore cleanup errors
            pass 
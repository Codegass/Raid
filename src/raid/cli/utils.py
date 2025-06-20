"""Shared utilities for Raid CLI"""

import asyncio
import functools
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

import click
from dotenv import load_dotenv
from ..config.settings import RaidConfig
from ..control_agent.agent import ControlAgent


def async_command(f):
    """Decorator to run async functions in Click commands"""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


def load_raid_config() -> RaidConfig:
    """Load Raid configuration from environment"""
    try:
        # Try to load .env file from current directory or project root
        env_paths = [
            ".env",  # Current directory
            os.path.join(os.getcwd(), ".env"),  # Explicit current directory
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),  # Project root
        ]
        
        env_loaded = False
        for env_path in env_paths:
            if os.path.exists(env_path):
                load_dotenv(env_path)
                env_loaded = True
                if os.getenv('RAID_CLI_DEBUG'):
                    click.echo(f"Loaded environment from: {env_path}")
                break
        
        if not env_loaded and os.getenv('RAID_CLI_DEBUG'):
            click.echo("No .env file found, using system environment variables")
        
        return RaidConfig.from_env()
    except Exception as e:
        click.echo(f"❌ Failed to load configuration: {e}", err=True)
        if os.getenv('RAID_CLI_DEBUG'):
            import traceback
            click.echo(f"Debug traceback: {traceback.format_exc()}")
        raise click.Abort()


async def get_control_agent() -> ControlAgent:
    """Get initialized Control Agent instance"""
    config = load_raid_config()
    agent = ControlAgent(config)
    await agent.start()
    return agent


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def format_timestamp(timestamp: datetime) -> str:
    """Format timestamp in human-readable format"""
    now = datetime.utcnow()
    diff = now - timestamp
    
    if diff.total_seconds() < 60:
        return "just now"
    elif diff.total_seconds() < 3600:
        return f"{int(diff.total_seconds()/60)}m ago"
    elif diff.total_seconds() < 86400:
        return f"{int(diff.total_seconds()/3600)}h ago"
    else:
        return f"{int(diff.total_seconds()/86400)}d ago"


def format_agent_state(state: str) -> str:
    """Format agent state with color coding"""
    state_colors = {
        "running": "green",
        "working": "blue",
        "idle": "yellow", 
        "stopping": "red",
        "stopped": "red",
        "error": "red",
        "creating": "cyan",
        "starting": "cyan"
    }
    
    state_icons = {
        "running": "🟢",
        "working": "🔵", 
        "idle": "🟡",
        "stopping": "🔴",
        "stopped": "⚫",
        "error": "❌",
        "creating": "🔵",
        "starting": "🔵"
    }
    
    color = state_colors.get(state.lower(), "white")
    icon = state_icons.get(state.lower(), "⚪")
    
    return click.style(f"{icon} {state.upper()}", fg=color)


def validate_agent_name(ctx, param, value):
    """Validate agent name parameter"""
    if value and not value.replace('_', '').replace('-', '').isalnum():
        raise click.BadParameter('Agent name must contain only letters, numbers, hyphens, and underscores.')
    return value


def safe_json_loads(data: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON data"""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None


class CliContext:
    """CLI context object to share state between commands"""
    
    def __init__(self):
        self.config: Optional[RaidConfig] = None
        self.control_agent: Optional[ControlAgent] = None
        self.verbose: bool = False
        self.format: str = "table"
    
    async def get_control_agent(self) -> ControlAgent:
        """Get or create control agent instance"""
        if not self.control_agent:
            if not self.config:
                self.config = load_raid_config()
            
            self.control_agent = ControlAgent(self.config)
            await self.control_agent.start()
        
        return self.control_agent
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.control_agent:
            await self.control_agent.stop()
            self.control_agent = None


pass_cli_context = click.make_pass_decorator(CliContext)
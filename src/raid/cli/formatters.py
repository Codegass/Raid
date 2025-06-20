"""Output formatters for Raid CLI"""

import json
import yaml
from datetime import datetime
from typing import Any, Dict, List, Optional

import click
from tabulate import tabulate


class OutputFormatter:
    """Base class for output formatters"""
    
    @staticmethod
    def format_agents_list(agents_data: Dict[str, Any], format_type: str = "table") -> str:
        """Format agents list data"""
        if format_type == "json":
            return json.dumps(agents_data, indent=2, default=str)
        elif format_type == "yaml":
            return yaml.dump(agents_data, default_flow_style=False)
        else:
            return OutputFormatter._format_agents_table(agents_data)
    
    @staticmethod
    def _format_agents_table(agents_data: Dict[str, Any]) -> str:
        """Format agents data as a table"""
        if not agents_data.get("agents"):
            return "No agents currently running."
        
        headers = ["Name", "State", "Profile", "Tasks", "Errors", "Created", "Last Activity"]
        rows = []
        
        for name, agent in agents_data["agents"].items():
            state = agent["state"]
            profile = agent.get("profile", "unknown")
            tasks = agent.get("task_count", 0)
            errors = agent.get("error_count", 0)
            created = OutputFormatter._format_time(agent.get("created_at"))
            last_activity = OutputFormatter._format_time(agent.get("last_task_at")) or "never"
            
            # Color code the state
            if state == "running":
                state_display = click.style("🟢 RUNNING", fg="green")
            elif state == "working":
                state_display = click.style("🔵 WORKING", fg="blue")
            elif state == "idle":
                state_display = click.style("🟡 IDLE", fg="yellow")
            elif state == "error":
                state_display = click.style("❌ ERROR", fg="red")
            else:
                state_display = f"⚪ {state.upper()}"
            
            rows.append([name, state_display, profile, tasks, errors, created, last_activity])
        
        table = tabulate(rows, headers=headers, tablefmt="grid")
        
        # Add summary
        summary = [
            f"Total Agents: {agents_data.get('total_agents', 0)}",
            f"Regular Agents: {agents_data.get('regular_agents', 0)}",
            f"Persistent Agents: {agents_data.get('persistent_agents', 0)}",
            f"Capacity: {agents_data.get('regular_agents', 0)}/{agents_data.get('max_capacity', 0)} ({agents_data.get('capacity_used_pct', 0):.1f}%)",
            f"Total Tasks Completed: {agents_data.get('total_tasks_completed', 0)}"
        ]
        
        return f"{table}\n\n📊 Summary:\n" + "\n".join(f"  {s}" for s in summary)
    
    @staticmethod
    def format_system_stats(stats_data: Dict[str, Any], format_type: str = "table") -> str:
        """Format system statistics"""
        if format_type == "json":
            return json.dumps(stats_data, indent=2, default=str)
        elif format_type == "yaml":
            return yaml.dump(stats_data, default_flow_style=False)
        else:
            return OutputFormatter._format_system_stats_table(stats_data)
    
    @staticmethod
    def _format_system_stats_table(stats_data: Dict[str, Any]) -> str:
        """Format system stats as readable text"""
        output = []
        
        # System Overview
        output.append("🤖 Raid System Status")
        output.append("=" * 50)
        
        # Agent Statistics
        agent_stats = stats_data.get("agent_stats", {})
        output.append(f"📊 Agent Statistics:")
        output.append(f"  Total Agents: {agent_stats.get('total_agents', 0)}")
        output.append(f"  Regular Agents: {agent_stats.get('regular_agents', 0)}")
        output.append(f"  Persistent Agents: {agent_stats.get('persistent_agents', 0)}")
        output.append(f"  Capacity Usage: {agent_stats.get('capacity_used_pct', 0):.1f}%")
        
        # State Distribution
        states = agent_stats.get("states", {})
        if states:
            output.append(f"\n📈 Agent States:")
            for state, count in states.items():
                if count > 0:
                    icon = {"running": "🟢", "working": "🔵", "idle": "🟡", "error": "❌"}.get(state, "⚪")
                    output.append(f"  {icon} {state.title()}: {count}")
        
        # Task Statistics
        output.append(f"\n📋 Task Statistics:")
        output.append(f"  Total Completed: {agent_stats.get('total_tasks_completed', 0)}")
        
        # Cleanup Statistics
        cleanup_stats = agent_stats.get("cleanup_stats", {})
        if any(cleanup_stats.values()):
            output.append(f"\n🗑️  Cleanup Statistics:")
            for cleanup_type, count in cleanup_stats.items():
                if count > 0:
                    output.append(f"  {cleanup_type.replace('_', ' ').title()}: {count}")
        
        # Configuration
        config = stats_data.get("config", {})
        if config:
            output.append(f"\n⚙️  Configuration:")
            output.append(f"  LLM Provider: {config.get('llm_provider', 'unknown')}")
            output.append(f"  Model: {config.get('llm_model', 'unknown')}")
            output.append(f"  Max Dynamic Agents: {config.get('max_dynamic_agents', 'unknown')}")
        
        return "\n".join(output)
    
    @staticmethod
    def format_profiles_list(profiles: List[Dict[str, Any]], format_type: str = "table") -> str:
        """Format profiles list"""
        if format_type == "json":
            return json.dumps(profiles, indent=2, default=str)
        elif format_type == "yaml":
            return yaml.dump(profiles, default_flow_style=False)
        else:
            return OutputFormatter._format_profiles_table(profiles)
    
    @staticmethod
    def _format_profiles_table(profiles: List[Dict[str, Any]]) -> str:
        """Format profiles as a table"""
        if not profiles:
            return "No agent profiles found."
        
        headers = ["Name", "Description", "Tools", "Model", "Persistent"]
        rows = []
        
        for profile in profiles:
            name = profile.get("name", "unknown")
            description = profile.get("description", "")[:50] + "..." if len(profile.get("description", "")) > 50 else profile.get("description", "")
            tools_count = len(profile.get("tools", []))
            model = profile.get("llm_config", {}).get("model", "unknown")
            is_persistent = "Yes" if profile.get("lifecycle_config", {}).get("persistent", False) else "No"
            
            rows.append([name, description, f"{tools_count} tools", model, is_persistent])
        
        return tabulate(rows, headers=headers, tablefmt="grid")
    
    @staticmethod
    def format_task_status(task_data: Dict[str, Any], format_type: str = "table") -> str:
        """Format task status information"""
        if format_type == "json":
            return json.dumps(task_data, indent=2, default=str)
        elif format_type == "yaml":
            return yaml.dump(task_data, default_flow_style=False)
        else:
            return OutputFormatter._format_task_status_text(task_data)
    
    @staticmethod
    def _format_task_status_text(task_data: Dict[str, Any]) -> str:
        """Format task status as readable text"""
        output = []
        
        output.append(f"📋 Task: {task_data.get('task_id', 'unknown')}")
        output.append(f"Status: {task_data.get('status', 'unknown')}")
        output.append(f"Agent: {task_data.get('agent_name', 'unknown')}")
        output.append(f"Created: {OutputFormatter._format_time(task_data.get('created_at'))}")
        
        if task_data.get("started_at"):
            output.append(f"Started: {OutputFormatter._format_time(task_data.get('started_at'))}")
        
        if task_data.get("completed_at"):
            output.append(f"Completed: {OutputFormatter._format_time(task_data.get('completed_at'))}")
        
        if task_data.get("error"):
            output.append(f"Error: {task_data.get('error')}")
        
        if task_data.get("result"):
            output.append(f"\nResult:\n{task_data.get('result')}")
        
        return "\n".join(output)
    
    @staticmethod
    def _format_time(timestamp_str: Optional[str]) -> str:
        """Format timestamp string"""
        if not timestamp_str:
            return "unknown"
        
        try:
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = timestamp_str
            
            now = datetime.utcnow().replace(tzinfo=timestamp.tzinfo)
            diff = now - timestamp
            
            if diff.total_seconds() < 60:
                return "just now"
            elif diff.total_seconds() < 3600:
                return f"{int(diff.total_seconds()/60)}m ago"
            elif diff.total_seconds() < 86400:
                return f"{int(diff.total_seconds()/3600)}h ago"
            else:
                return f"{int(diff.total_seconds()/86400)}d ago"
        except Exception:
            return str(timestamp_str)[:19]  # Fallback to raw string
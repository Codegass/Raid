"""Agent management commands for Raid CLI"""

import asyncio
from typing import Optional

import click
from .utils import async_command, pass_cli_context, validate_agent_name, CliContext
from .formatters import OutputFormatter


@click.group(name='agents')
def agents_group():
    """Manage Raid Sub-Agents"""
    pass


@agents_group.command()
@click.option('--profile', '-p', help='Filter by agent profile')
@click.option('--state', '-s', help='Filter by agent state')
@pass_cli_context
@async_command
async def list(cli_ctx: CliContext, profile: Optional[str], state: Optional[str]):
    """List all active agents with their status"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        # Get agent statistics from lifecycle manager
        stats = control_agent.lifecycle_manager.get_agent_stats()
        
        # Apply filters if specified
        if profile or state:
            filtered_agents = {}
            for name, agent_data in stats["agents"].items():
                if profile and agent_data.get("profile", "").lower() != profile.lower():
                    continue
                if state and agent_data.get("state", "").lower() != state.lower():
                    continue
                filtered_agents[name] = agent_data
            stats["agents"] = filtered_agents
            stats["total_agents"] = len(filtered_agents)
        
        # Format and display output
        output = OutputFormatter.format_agents_list(stats, cli_ctx.format)
        click.echo(output)
        
    except Exception as e:
        click.echo(f"❌ Failed to list agents: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@agents_group.command()
@pass_cli_context
@async_command
async def stats(cli_ctx: CliContext):
    """Show detailed agent statistics and relationships"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        # Get comprehensive statistics
        agent_stats = control_agent.lifecycle_manager.get_agent_stats()
        
        # Get collaboration information if available
        collab_info = {}
        try:
            # Try to get collaboration manager info
            if hasattr(control_agent.meta_tool_registry, 'collaboration_manager'):
                collab_manager = control_agent.meta_tool_registry.collaboration_manager
                collab_info = {
                    "collaboration_groups": collab_manager.list_groups(),
                    "total_groups": len(collab_manager.active_groups)
                }
        except Exception:
            # Collaboration might not be initialized
            pass
        
        # Combine all statistics
        full_stats = {
            "agent_stats": agent_stats,
            "collaboration_info": collab_info,
            "config": {
                "llm_provider": control_agent.config.llm_backend.provider,
                "llm_model": control_agent.config.llm_backend.model,
                "max_dynamic_agents": control_agent.config.max_dynamic_sub_agents,
                "docker_socket": control_agent.config.docker_socket
            }
        }
        
        # Format and display output
        output = OutputFormatter.format_system_stats(full_stats, cli_ctx.format)
        click.echo(output)
        
    except Exception as e:
        click.echo(f"❌ Failed to get agent statistics: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@agents_group.command()
@click.argument('profile_name')
@click.option('--task-description', '-t', help='Task description for dynamic agents')
@pass_cli_context
@async_command
async def create(cli_ctx: CliContext, profile_name: str, task_description: Optional[str]):
    """Create a new agent from the specified profile"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        click.echo(f"🔄 Creating agent with profile '{profile_name}'...")
        
        # Check if this is a dynamic agent creation
        if profile_name.startswith('dynamic_') or task_description:
            if not task_description:
                task_description = click.prompt("Enter task description for dynamic agent")
            
            # Use meta-tool to create specialized agent
            result = await control_agent.meta_tool_registry.execute_meta_tool(
                "create_specialized_sub_agent",
                {
                    "task_description": task_description,
                    "role_name": profile_name.replace('dynamic_', '') if profile_name.startswith('dynamic_') else None
                }
            )
            
            if "successfully" in result.lower():
                click.echo(f"✅ {result}")
            else:
                click.echo(f"❌ {result}")
        else:
            # Regular profile-based agent creation
            # This would use the dispatch_to_sub_agent meta-tool 
            # with a simple initialization task
            result = await control_agent.meta_tool_registry.execute_meta_tool(
                "dispatch_to_sub_agent",
                {
                    "sub_agent_profile": profile_name,
                    "task_prompt": "Initialize and report status"
                }
            )
            
            click.echo(f"✅ Agent created with profile '{profile_name}'")
            if cli_ctx.verbose:
                click.echo(f"Details: {result}")
                
    except Exception as e:
        click.echo(f"❌ Failed to create agent: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@agents_group.command()
@click.argument('agent_name', callback=validate_agent_name)
@click.option('--force', '-f', is_flag=True, help='Force stop without confirmation')
@pass_cli_context
@async_command
async def stop(cli_ctx: CliContext, agent_name: str, force: bool):
    """Stop and remove a specific agent"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        # Check if agent exists
        stats = control_agent.lifecycle_manager.get_agent_stats()
        if agent_name not in stats["agents"]:
            click.echo(f"❌ Agent '{agent_name}' not found")
            return
        
        agent_info = stats["agents"][agent_name]
        
        if not force:
            click.echo(f"Agent: {agent_name}")
            click.echo(f"State: {agent_info['state']}")
            click.echo(f"Tasks completed: {agent_info['task_count']}")
            
            if not click.confirm(f"Are you sure you want to stop '{agent_name}'?"):
                click.echo("Operation cancelled.")
                return
        
        click.echo(f"🔄 Stopping agent '{agent_name}'...")
        
        # Use lifecycle manager to unregister agent
        success = await control_agent.lifecycle_manager.unregister_agent(
            agent_name, "Manual stop via CLI"
        )
        
        if success:
            click.echo(f"✅ Agent '{agent_name}' stopped successfully")
        else:
            click.echo(f"❌ Failed to stop agent '{agent_name}'")
            
    except Exception as e:
        click.echo(f"❌ Failed to stop agent: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@agents_group.command()
@click.option('--dry-run', is_flag=True, help='Show what would be cleaned up without doing it')
@click.option('--force', '-f', is_flag=True, help='Force cleanup without confirmation')
@pass_cli_context
@async_command
async def cleanup(cli_ctx: CliContext, dry_run: bool, force: bool):
    """Remove idle and stale agents"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        # Get current agent statistics
        stats = control_agent.lifecycle_manager.get_agent_stats()
        idle_agents = []
        stale_agents = []
        
        # Find agents that could be cleaned up
        for name, agent_data in stats["agents"].items():
            if agent_data["state"] == "idle":
                idle_agents.append(name)
            elif agent_data["state"] == "error":
                stale_agents.append(name)
        
        total_cleanup = len(idle_agents) + len(stale_agents)
        
        if total_cleanup == 0:
            click.echo("✅ No agents need cleanup")
            return
        
        click.echo(f"🗑️  Found {total_cleanup} agents for cleanup:")
        if idle_agents:
            click.echo(f"  Idle agents ({len(idle_agents)}): {', '.join(idle_agents)}")
        if stale_agents:
            click.echo(f"  Error agents ({len(stale_agents)}): {', '.join(stale_agents)}")
        
        if dry_run:
            click.echo("🔍 Dry run - no agents were actually removed")
            return
        
        if not force and not click.confirm(f"Proceed with cleanup of {total_cleanup} agents?"):
            click.echo("Operation cancelled.")
            return
        
        # Perform manual cleanup by triggering lifecycle checks
        click.echo("🔄 Performing cleanup...")
        await control_agent.lifecycle_manager._cleanup_idle_agents()
        await control_agent.lifecycle_manager._cleanup_stale_agents()
        
        click.echo("✅ Cleanup completed")
        
    except Exception as e:
        click.echo(f"❌ Failed to cleanup agents: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@agents_group.command()
@click.argument('agent_name', callback=validate_agent_name)
@click.option('--lines', '-n', default=50, help='Number of log lines to show')
@click.option('--follow', '-f', is_flag=True, help='Follow log output (not implemented)')
@pass_cli_context
@async_command
async def logs(cli_ctx: CliContext, agent_name: str, lines: int, follow: bool):
    """View logs for a specific agent container"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        # Get agent information
        stats = control_agent.lifecycle_manager.get_agent_stats()
        if agent_name not in stats["agents"]:
            click.echo(f"❌ Agent '{agent_name}' not found")
            return
        
        # Get container ID from lifecycle manager
        agent_info = None
        for name, info in control_agent.lifecycle_manager.agents.items():
            if name == agent_name:
                agent_info = info
                break
        
        if not agent_info or not agent_info.container_id:
            click.echo(f"❌ No container found for agent '{agent_name}'")
            return
        
        if follow:
            click.echo("❌ Log following is not yet implemented")
            return
        
        click.echo(f"📋 Showing last {lines} lines for agent '{agent_name}':")
        click.echo("=" * 60)
        
        # Get logs from Docker orchestrator
        try:
            logs = control_agent.lifecycle_manager.orchestrator.get_container_logs(
                agent_info.container_id, tail=lines
            )
            
            if logs:
                click.echo(logs)
            else:
                click.echo("No logs available")
                
        except Exception as log_error:
            click.echo(f"❌ Failed to retrieve logs: {log_error}")
            
    except Exception as e:
        click.echo(f"❌ Failed to get agent logs: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@agents_group.command()
@pass_cli_context
@async_command
async def health(cli_ctx: CliContext):
    """Check health status of all agents"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        click.echo("🔍 Checking agent health...")
        
        # Get agent statistics
        stats = control_agent.lifecycle_manager.get_agent_stats()
        
        healthy_count = 0
        unhealthy_count = 0
        
        for name, agent_data in stats["agents"].items():
            state = agent_data["state"]
            if state in ["running", "working", "idle"]:
                status = click.style("✅ HEALTHY", fg="green")
                healthy_count += 1
            else:
                status = click.style("❌ UNHEALTHY", fg="red")
                unhealthy_count += 1
            
            click.echo(f"  {name}: {status} ({state})")
        
        click.echo(f"\n📊 Health Summary:")
        click.echo(f"  Healthy: {healthy_count}")
        click.echo(f"  Unhealthy: {unhealthy_count}")
        click.echo(f"  Total: {stats['total_agents']}")
        
        # Overall system health
        if unhealthy_count == 0:
            click.echo(click.style("🟢 System Status: HEALTHY", fg="green"))
        elif unhealthy_count < healthy_count:
            click.echo(click.style("🟡 System Status: DEGRADED", fg="yellow"))
        else:
            click.echo(click.style("🔴 System Status: UNHEALTHY", fg="red"))
            
    except Exception as e:
        click.echo(f"❌ Failed to check agent health: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()
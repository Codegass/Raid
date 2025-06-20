"""Collaboration management commands for Raid CLI"""

import uuid
from typing import Optional, List

import click
from .utils import async_command, pass_cli_context, CliContext
from .formatters import OutputFormatter


@click.group(name='collab')
def collab_group():
    """Manage agent collaboration groups"""
    pass


@collab_group.command()
@pass_cli_context
@async_command
async def groups(cli_ctx: CliContext):
    """List all collaboration groups"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        # Try to get collaboration manager
        try:
            if hasattr(control_agent.meta_tool_registry, 'collaboration_manager'):
                collab_manager = control_agent.meta_tool_registry.collaboration_manager
                groups = collab_manager.list_groups()
                
                if not groups:
                    click.echo("No collaboration groups found.")
                    return
                
                if cli_ctx.format == "json":
                    import json
                    click.echo(json.dumps(groups, indent=2, default=str))
                elif cli_ctx.format == "yaml":
                    import yaml
                    click.echo(yaml.dump(groups, default_flow_style=False))
                else:
                    click.echo("🤝 Collaboration Groups")
                    click.echo("=" * 50)
                    
                    for group in groups:
                        click.echo(f"\n📋 Group: {group['group_name']} ({group['group_id']})")
                        click.echo(f"   Agents: {group['agent_count']}")
                        click.echo(f"   Messages: {group['total_messages']}")
                        click.echo(f"   Active: {len(group['active_agents'])}")
                        if group['agents']:
                            click.echo(f"   Members: {', '.join(group['agents'])}")
                        
                click.echo(f"\n📊 Total Groups: {len(groups)}")
                
            else:
                click.echo("❌ Collaboration manager not available")
                click.echo("💡 Collaboration features may not be initialized")
                
        except Exception as e:
            click.echo(f"❌ Failed to access collaboration manager: {e}")
            if cli_ctx.verbose:
                click.echo(f"Details: {str(e)}")
        
    except Exception as e:
        click.echo(f"❌ Failed to list collaboration groups: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@collab_group.command()
@click.argument('group_name')
@click.option('--max-messages', default=30, help='Max messages per minute per agent')
@click.option('--max-size', default=10000, help='Max message size in bytes')
@pass_cli_context
@async_command
async def create(cli_ctx: CliContext, group_name: str, max_messages: int, max_size: int):
    """Create a new collaboration group"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        click.echo(f"🤝 Creating collaboration group '{group_name}'...")
        
        # Use meta-tool to create collaboration group
        try:
            result = await control_agent.meta_tool_registry.execute_meta_tool(
                "create_collaborative_sub_agent_group",
                {
                    "group_name": group_name,
                    "max_messages_per_minute": max_messages,
                    "max_message_size_bytes": max_size
                }
            )
            
            if "successfully" in result.lower():
                click.echo(f"✅ {result}")
            else:
                click.echo(f"❌ {result}")
                
        except Exception as meta_error:
            click.echo(f"❌ Collaboration features not available: {meta_error}")
            click.echo("💡 This feature requires the collaboration system to be initialized")
            if cli_ctx.verbose:
                click.echo(f"Error details: {str(meta_error)}")
        
    except Exception as e:
        click.echo(f"❌ Failed to create collaboration group: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@collab_group.command()
@click.argument('group_id')
@click.argument('agent_name')
@click.argument('role')
@pass_cli_context
@async_command
async def add(cli_ctx: CliContext, group_id: str, agent_name: str, role: str):
    """Add an agent to a collaboration group"""
    try:
        click.echo(f"👥 Adding agent '{agent_name}' to group '{group_id}' with role '{role}'")
        
        # Note: This functionality would require additional implementation
        # in the collaboration system to add existing agents to groups
        click.echo("❌ Adding existing agents to groups is not yet implemented")
        click.echo("💡 Use 'raid task collaborative' to create collaborative tasks")
        
    except Exception as e:
        click.echo(f"❌ Failed to add agent to group: {e}", err=True)
        raise click.Abort()


@collab_group.command()
@click.argument('group_id')
@pass_cli_context
@async_command
async def status(cli_ctx: CliContext, group_id: str):
    """Show detailed status of a collaboration group"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        click.echo(f"🔍 Checking status of collaboration group '{group_id}'...")
        
        # Try to get group information
        try:
            if hasattr(control_agent.meta_tool_registry, 'collaboration_manager'):
                collab_manager = control_agent.meta_tool_registry.collaboration_manager
                group = collab_manager.get_group(group_id)
                
                if not group:
                    click.echo(f"❌ Group '{group_id}' not found")
                    return
                
                status = group.get_group_status()
                
                if cli_ctx.format == "json":
                    import json
                    click.echo(json.dumps(status, indent=2, default=str))
                elif cli_ctx.format == "yaml":
                    import yaml
                    click.echo(yaml.dump(status, default_flow_style=False))
                else:
                    click.echo(f"📋 Group Status: {status['group_name']}")
                    click.echo("=" * 50)
                    click.echo(f"ID: {status['group_id']}")
                    click.echo(f"Created: {status['created_at']}")
                    click.echo(f"Total Agents: {status['agent_count']}")
                    click.echo(f"Active Agents: {len(status['active_agents'])}")
                    click.echo(f"Total Messages: {status['total_messages']}")
                    
                    if status['agents']:
                        click.echo(f"\n👥 Agents:")
                        for agent in status['agents']:
                            click.echo(f"  - {agent}")
                    
                    if status['active_agents']:
                        click.echo(f"\n🟢 Active Agents:")
                        for agent in status['active_agents']:
                            click.echo(f"  - {agent}")
            else:
                click.echo("❌ Collaboration manager not available")
                
        except Exception as e:
            click.echo(f"❌ Failed to get group status: {e}")
            if cli_ctx.verbose:
                click.echo(f"Details: {str(e)}")
        
    except Exception as e:
        click.echo(f"❌ Failed to check group status: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@collab_group.command()
@click.argument('group_id')
@click.option('--force', '-f', is_flag=True, help='Force shutdown without confirmation')
@pass_cli_context
@async_command
async def shutdown(cli_ctx: CliContext, group_id: str, force: bool):
    """Shutdown a collaboration group"""
    try:
        if not force:
            if not click.confirm(f"Are you sure you want to shutdown group '{group_id}'?"):
                click.echo("Operation cancelled.")
                return
        
        click.echo(f"🛑 Shutting down collaboration group '{group_id}'...")
        
        # Note: This would require implementation in the collaboration manager
        click.echo("❌ Group shutdown is not yet fully implemented")
        click.echo("💡 Groups will automatically cleanup after inactivity")
        
    except Exception as e:
        click.echo(f"❌ Failed to shutdown group: {e}", err=True)
        raise click.Abort()


@collab_group.command()
@click.argument('group_id')
@click.option('--lines', '-n', default=20, help='Number of recent messages to show')
@pass_cli_context
@async_command
async def messages(cli_ctx: CliContext, group_id: str, lines: int):
    """Show recent messages in a collaboration group"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        click.echo(f"💬 Recent messages in group '{group_id}' (last {lines}):")
        click.echo("=" * 60)
        
        # Note: This would require message history access in the collaboration system
        click.echo("❌ Message history viewing is not yet implemented")
        click.echo("💡 Message history is stored but access interface is not available")
        
    except Exception as e:
        click.echo(f"❌ Failed to get group messages: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@collab_group.command()
@pass_cli_context
@async_command
async def cleanup(cli_ctx: CliContext):
    """Clean up inactive collaboration groups"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        click.echo("🗑️ Cleaning up inactive collaboration groups...")
        
        try:
            if hasattr(control_agent.meta_tool_registry, 'collaboration_manager'):
                collab_manager = control_agent.meta_tool_registry.collaboration_manager
                removed_groups = await collab_manager.cleanup_inactive_groups(max_age_hours=24)
                
                if removed_groups:
                    click.echo(f"✅ Removed {len(removed_groups)} inactive groups:")
                    for group_id in removed_groups:
                        click.echo(f"  - {group_id}")
                else:
                    click.echo("✅ No inactive groups found")
            else:
                click.echo("❌ Collaboration manager not available")
                
        except Exception as e:
            click.echo(f"❌ Failed to cleanup groups: {e}")
            if cli_ctx.verbose:
                click.echo(f"Details: {str(e)}")
        
    except Exception as e:
        click.echo(f"❌ Failed to cleanup collaboration groups: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()
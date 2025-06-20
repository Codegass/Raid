"""System monitoring commands for Raid CLI"""

import click
from .utils import async_command, pass_cli_context, CliContext
from .formatters import OutputFormatter


@click.group(name='system')
def system_group():
    """System monitoring and management"""
    pass


@system_group.command()
@pass_cli_context
@async_command
async def status(cli_ctx: CliContext):
    """Show overall system status"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        click.echo("🤖 Raid System Status")
        click.echo("=" * 50)
        
        # Get agent statistics
        agent_stats = control_agent.lifecycle_manager.get_agent_stats()
        
        # System health indicators
        total_agents = agent_stats.get("total_agents", 0)
        running_agents = agent_stats.get("states", {}).get("running", 0)
        working_agents = agent_stats.get("states", {}).get("working", 0)
        error_agents = agent_stats.get("states", {}).get("error", 0)
        
        # Overall health
        healthy_agents = running_agents + working_agents
        if error_agents == 0 and total_agents > 0:
            health_status = click.style("🟢 HEALTHY", fg="green")
        elif error_agents < healthy_agents:
            health_status = click.style("🟡 DEGRADED", fg="yellow")
        elif total_agents == 0:
            health_status = click.style("⚪ NO AGENTS", fg="white")
        else:
            health_status = click.style("🔴 UNHEALTHY", fg="red")
        
        click.echo(f"Status: {health_status}")
        click.echo(f"Agents: {total_agents} total, {healthy_agents} healthy, {error_agents} errors")
        click.echo(f"Capacity: {agent_stats.get('capacity_used_pct', 0):.1f}% ({agent_stats.get('regular_agents', 0)}/{agent_stats.get('max_capacity', 0)})")
        click.echo(f"Tasks Completed: {agent_stats.get('total_tasks_completed', 0)}")
        
        # Configuration info
        click.echo(f"\n⚙️ Configuration:")
        click.echo(f"LLM Provider: {control_agent.config.llm_backend.provider}")
        click.echo(f"Model: {control_agent.config.llm_backend.model}")
        click.echo(f"Docker Socket: {control_agent.config.docker_socket}")
        
        # Recent activity
        if agent_stats.get("agents"):
            active_agents = [name for name, data in agent_stats["agents"].items() 
                           if data["state"] in ["running", "working"]]
            if active_agents:
                click.echo(f"\n🔄 Active Agents: {', '.join(active_agents[:5])}")
                if len(active_agents) > 5:
                    click.echo(f"   ... and {len(active_agents) - 5} more")
        
    except Exception as e:
        click.echo(f"❌ Failed to get system status: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@system_group.command()
@pass_cli_context
@async_command
async def stats(cli_ctx: CliContext):
    """Show comprehensive system statistics"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        # Get all available statistics
        agent_stats = control_agent.lifecycle_manager.get_agent_stats()
        
        # Get collaboration info if available
        collab_info = {}
        try:
            if hasattr(control_agent.meta_tool_registry, 'collaboration_manager'):
                collab_manager = control_agent.meta_tool_registry.collaboration_manager
                collab_info = {
                    "collaboration_groups": collab_manager.list_groups(),
                    "total_groups": len(collab_manager.active_groups)
                }
        except Exception:
            pass
        
        # System configuration
        config_info = {
            "llm_provider": control_agent.config.llm_backend.provider,
            "llm_model": control_agent.config.llm_backend.model,
            "max_dynamic_agents": control_agent.config.max_dynamic_sub_agents,
            "docker_socket": control_agent.config.docker_socket,
            "redis_host": control_agent.config.message_queue.host,
            "redis_port": control_agent.config.message_queue.port
        }
        
        # Combine all statistics
        full_stats = {
            "agent_stats": agent_stats,
            "collaboration_info": collab_info,
            "config": config_info
        }
        
        # Format and display
        output = OutputFormatter.format_system_stats(full_stats, cli_ctx.format)
        click.echo(output)
        
    except Exception as e:
        click.echo(f"❌ Failed to get system statistics: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@system_group.command()
@click.option('--lines', '-n', default=50, help='Number of log lines to show')
@pass_cli_context
@async_command
async def logs(cli_ctx: CliContext, lines: int):
    """Show Control Agent logs"""
    try:
        click.echo(f"📋 Control Agent Logs (last {lines} lines)")
        click.echo("=" * 60)
        
        # Note: This is a placeholder since centralized logging 
        # is not fully implemented in the current codebase
        click.echo("❌ Centralized logging is not yet fully implemented")
        click.echo("💡 Use 'raid agents logs <agent-name>' for individual agent logs")
        click.echo("💡 Check Docker logs with: docker logs <container-id>")
        
    except Exception as e:
        click.echo(f"❌ Failed to get system logs: {e}", err=True)
        raise click.Abort()


@system_group.command()
@pass_cli_context
@async_command
async def config(cli_ctx: CliContext):
    """Show current system configuration"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        config_data = {
            "LLM Backend": {
                "Provider": control_agent.config.llm_backend.provider,
                "Model": control_agent.config.llm_backend.model,
                "Max Tokens": getattr(control_agent.config.llm_backend, 'max_tokens', 'default'),
                "Temperature": getattr(control_agent.config.llm_backend, 'temperature', 'default')
            },
            "System Limits": {
                "Max Dynamic Agents": control_agent.config.max_dynamic_sub_agents,
                "Docker Socket": control_agent.config.docker_socket
            },
            "Message Queue": {
                "Host": control_agent.config.message_queue.host,
                "Port": control_agent.config.message_queue.port,
                "DB": control_agent.config.message_queue.db
            }
        }
        
        if cli_ctx.format == "json":
            import json
            click.echo(json.dumps(config_data, indent=2))
        elif cli_ctx.format == "yaml":
            import yaml
            click.echo(yaml.dump(config_data, default_flow_style=False))
        else:
            click.echo("⚙️ System Configuration")
            click.echo("=" * 50)
            
            for section, settings in config_data.items():
                click.echo(f"\n📋 {section}:")
                for key, value in settings.items():
                    click.echo(f"  {key}: {value}")
        
    except Exception as e:
        click.echo(f"❌ Failed to get system configuration: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@system_group.command()
@click.option('--force', '-f', is_flag=True, help='Force restart without confirmation')
@pass_cli_context
@async_command
async def restart(cli_ctx: CliContext, force: bool):
    """Restart the Control Agent and all Sub-Agents"""
    try:
        if not force:
            click.echo("⚠️  This will stop all running agents and restart the system")
            if not click.confirm("Are you sure you want to restart?"):
                click.echo("Operation cancelled.")
                return
        
        click.echo("🔄 Restarting Raid system...")
        
        control_agent = await cli_ctx.get_control_agent()
        
        # Stop all agents
        click.echo("🛑 Stopping all agents...")
        await control_agent.lifecycle_manager.stop_monitoring()
        
        # Start system again
        click.echo("🚀 Starting system...")
        await control_agent.lifecycle_manager.start_monitoring()
        
        click.echo("✅ System restarted successfully")
        
    except Exception as e:
        click.echo(f"❌ Failed to restart system: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@system_group.command()
@click.option('--timeout', '-t', default=30, help='Health check timeout in seconds')
@pass_cli_context
@async_command
async def health(cli_ctx: CliContext, timeout: int):
    """Perform comprehensive system health check"""
    try:
        click.echo("🔍 Performing system health check...")
        
        health_results = {
            "control_agent": False,
            "lifecycle_manager": False,
            "message_queue": False,
            "docker": False,
            "agents": 0
        }
        
        # Check Control Agent
        try:
            control_agent = await cli_ctx.get_control_agent()
            health_results["control_agent"] = True
            click.echo("✅ Control Agent: Healthy")
        except Exception as e:
            click.echo(f"❌ Control Agent: {e}")
        
        # Check Lifecycle Manager
        if health_results["control_agent"]:
            try:
                stats = control_agent.lifecycle_manager.get_agent_stats()
                health_results["lifecycle_manager"] = True
                health_results["agents"] = stats.get("total_agents", 0)
                click.echo("✅ Lifecycle Manager: Healthy")
                click.echo(f"📊 Active Agents: {health_results['agents']}")
            except Exception as e:
                click.echo(f"❌ Lifecycle Manager: {e}")
        
        # Check Message Queue (Redis)
        if health_results["control_agent"]:
            try:
                # Try to connect to Redis
                from ..message_queue.redis_mq import RedisMQ
                mq = RedisMQ(control_agent.config.message_queue)
                await mq.connect()
                await mq.disconnect()
                health_results["message_queue"] = True
                click.echo("✅ Message Queue (Redis): Healthy")
            except Exception as e:
                click.echo(f"❌ Message Queue (Redis): {e}")
        
        # Check Docker
        if health_results["control_agent"]:
            try:
                orchestrator = control_agent.lifecycle_manager.orchestrator
                # Try to get Docker info
                info = orchestrator.docker_client.info()
                health_results["docker"] = True
                click.echo("✅ Docker: Healthy")
                if cli_ctx.verbose:
                    click.echo(f"   Docker Version: {info.get('ServerVersion', 'unknown')}")
            except Exception as e:
                click.echo(f"❌ Docker: {e}")
        
        # Overall health assessment
        click.echo("\n🏥 Health Summary:")
        healthy_components = sum([
            health_results["control_agent"],
            health_results["lifecycle_manager"], 
            health_results["message_queue"],
            health_results["docker"]
        ])
        
        if healthy_components == 4:
            click.echo(click.style("🟢 System Status: HEALTHY", fg="green"))
        elif healthy_components >= 2:
            click.echo(click.style("🟡 System Status: DEGRADED", fg="yellow"))
        else:
            click.echo(click.style("🔴 System Status: CRITICAL", fg="red"))
        
        click.echo(f"Healthy Components: {healthy_components}/4")
        
    except Exception as e:
        click.echo(f"❌ Health check failed: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@system_group.command()
@pass_cli_context
@async_command
async def metrics(cli_ctx: CliContext):
    """Show detailed system metrics"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        # Get comprehensive metrics
        agent_stats = control_agent.lifecycle_manager.get_agent_stats()
        cleanup_stats = agent_stats.get("cleanup_stats", {})
        
        click.echo("📊 System Metrics")
        click.echo("=" * 50)
        
        # Agent metrics
        click.echo("🤖 Agent Metrics:")
        click.echo(f"  Total Agents: {agent_stats.get('total_agents', 0)}")
        click.echo(f"  Regular Agents: {agent_stats.get('regular_agents', 0)}")
        click.echo(f"  Persistent Agents: {agent_stats.get('persistent_agents', 0)}")
        click.echo(f"  Capacity Utilization: {agent_stats.get('capacity_used_pct', 0):.1f}%")
        
        # Performance metrics
        click.echo(f"\n📈 Performance Metrics:")
        click.echo(f"  Total Tasks Completed: {agent_stats.get('total_tasks_completed', 0)}")
        
        # State distribution
        states = agent_stats.get("states", {})
        if states:
            click.echo(f"\n📋 Agent State Distribution:")
            for state, count in states.items():
                if count > 0:
                    percentage = (count / agent_stats.get('total_agents', 1)) * 100
                    click.echo(f"  {state.title()}: {count} ({percentage:.1f}%)")
        
        # Cleanup metrics
        if any(cleanup_stats.values()):
            click.echo(f"\n🗑️ Cleanup Metrics:")
            total_cleanups = sum(cleanup_stats.values())
            for cleanup_type, count in cleanup_stats.items():
                if count > 0:
                    click.echo(f"  {cleanup_type.replace('_', ' ').title()}: {count}")
            click.echo(f"  Total Cleanups: {total_cleanups}")
        
        # Resource metrics (if available)
        try:
            import psutil
            click.echo(f"\n💾 System Resources:")
            click.echo(f"  CPU Usage: {psutil.cpu_percent()}%")
            click.echo(f"  Memory Usage: {psutil.virtual_memory().percent}%")
            click.echo(f"  Disk Usage: {psutil.disk_usage('/').percent}%")
        except ImportError:
            click.echo(f"\n💾 System Resources: Not available (install psutil for resource monitoring)")
        
    except Exception as e:
        click.echo(f"❌ Failed to get system metrics: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()
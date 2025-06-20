"""Main CLI entry point for Raid project"""

import click
from .utils import CliContext
from .agents import agents_group
from .tasks import tasks_group
from .system import system_group
from .profiles import profiles_group
from .collab import collab_group
from .control import control_group


@click.group(invoke_without_command=True)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'yaml']), 
              default='table', help='Output format')
@click.version_option(version='0.2.0', prog_name='raid')
@click.pass_context
def cli(ctx, verbose, format):
    """
    🤖 Raid - LLM-based Multi-Agent Orchestration System CLI
    
    The Raid CLI provides two main approaches for task execution:
    
    1. CONTROL AGENT (Recommended): Natural language goals with intelligent orchestration
       • raid control process "Calculate ROI for $50k investment at 8% over 5 years"
       • Uses ReAct reasoning to analyze, plan, and coordinate sub-agents
       
    2. DIRECT SUB-AGENT: Direct task dispatch to specific agent profiles  
       • raid task run calculator_agent "Calculate 15% tip on $85"
       • Direct routing without Control Agent orchestration
    
    Other commands: agent management, system monitoring, profiles, collaboration
    """
    # Ensure that ctx.obj exists and is a CliContext
    ctx.ensure_object(CliContext)
    ctx.obj.verbose = verbose
    ctx.obj.format = format
    
    if ctx.invoked_subcommand is None:
        # Show help if no subcommand is provided
        click.echo(ctx.get_help())


# Add command groups
cli.add_command(control_group)  # Control Agent is the main orchestrator
cli.add_command(agents_group)
cli.add_command(tasks_group)
cli.add_command(system_group)
cli.add_command(profiles_group)
cli.add_command(collab_group)


@cli.command()
@click.pass_context
def status(ctx):
    """Quick system status overview"""
    # This is a convenience command that calls system status
    from .system import status as system_status
    ctx.invoke(system_status)


@cli.command()
@click.pass_context  
def version(ctx):
    """Show Raid version information"""
    click.echo("🤖 Raid Multi-Agent Orchestration System")
    click.echo("Version: 0.2.0")
    click.echo("Architecture: Control Agent + Sub-Agents with Docker orchestration")
    click.echo("Features: Dynamic agents, collaboration, lifecycle management")


@cli.command()
@click.pass_context
def debug_env(ctx):
    """Debug environment configuration and .env file loading"""
    import os
    from dotenv import load_dotenv
    
    click.echo("🔍 Environment Configuration Debug")
    click.echo("=" * 50)
    
    # Check for .env files
    env_paths = [
        ".env",
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),
    ]
    
    click.echo("📁 Checking for .env files:")
    for i, env_path in enumerate(env_paths, 1):
        abs_path = os.path.abspath(env_path)
        exists = os.path.exists(env_path)
        status = "✅ EXISTS" if exists else "❌ NOT FOUND"
        click.echo(f"  {i}. {abs_path} - {status}")
        
        if exists:
            click.echo(f"     Loading from: {env_path}")
            load_dotenv(env_path)
            break
    
    # Check key environment variables
    click.echo(f"\n🔑 Environment Variables:")
    env_vars = [
        "RAID_LLM_PROVIDER",
        "OPENAI_API_KEY", 
        "RAID_OPENAI_MODEL",
        "RAID_OLLAMA_URL",
        "RAID_OLLAMA_MODEL",
        "RAID_REDIS_HOST",
        "RAID_REDIS_PORT",
        "RAID_DOCKER_SOCKET",
        "RAID_MAX_DYNAMIC_SUB_AGENTS"
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if var == "OPENAI_API_KEY" and value:
            # Mask API key for security
            masked_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***masked***"
            click.echo(f"  {var}: {masked_value}")
        elif value:
            click.echo(f"  {var}: {value}")
        else:
            click.echo(f"  {var}: ❌ NOT SET")
    
    # Try to load RaidConfig
    click.echo(f"\n⚙️ Configuration Loading:")
    try:
        from ..config.settings import RaidConfig
        config = RaidConfig.from_env()
        click.echo("  ✅ RaidConfig loaded successfully")
        click.echo(f"  LLM Provider: {config.llm_backend.provider}")
        click.echo(f"  LLM Model: {config.llm_backend.model}")
        click.echo(f"  Redis Host: {config.message_queue.host}")
        click.echo(f"  Docker Socket: {config.docker_socket}")
    except Exception as e:
        click.echo(f"  ❌ Failed to load RaidConfig: {e}")
    
    click.echo(f"\n💡 Current working directory: {os.getcwd()}")
    click.echo(f"💡 Python path: {os.path.dirname(__file__)}")


if __name__ == '__main__':
    cli()
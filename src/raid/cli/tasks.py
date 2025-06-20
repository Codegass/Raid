"""Task management commands for Raid CLI"""

import uuid
from datetime import datetime
from typing import Optional

import click
from .utils import async_command, pass_cli_context, CliContext
from .formatters import OutputFormatter


@click.group(name='task')
def tasks_group():
    """Manage and dispatch tasks to agents"""
    pass


@tasks_group.command()
@click.argument('profile_name')
@click.argument('task_prompt')
@click.option('--timeout', '-t', default=300, help='Task timeout in seconds')
@click.option('--wait', '-w', is_flag=True, help='Wait for task completion')
@click.option('--agent-name', help='Specific agent name to use (if available)')
@pass_cli_context
@async_command
async def run(cli_ctx: CliContext, profile_name: str, task_prompt: str, 
              timeout: int, wait: bool, agent_name: Optional[str]):
    """Dispatch a task to a specific agent profile"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        task_id = str(uuid.uuid4())[:8]
        
        click.echo(f"🚀 Dispatching task {task_id} to profile '{profile_name}'")
        if cli_ctx.verbose:
            click.echo(f"Task: {task_prompt}")
            click.echo(f"Timeout: {timeout}s")
        
        # Use the dispatch_to_sub_agent meta-tool
        meta_tool_params = {
            "sub_agent_profile": profile_name,
            "task_prompt": task_prompt,
            "timeout": timeout
        }
        
        if agent_name:
            # If specific agent name is provided, we'd need to check if it exists
            # For now, we'll include it in the task prompt
            meta_tool_params["task_prompt"] = f"[Agent: {agent_name}] {task_prompt}"
        
        if wait:
            click.echo("⏳ Waiting for task completion...")
            
            result = await control_agent.meta_tool_registry.execute_meta_tool(
                "dispatch_to_sub_agent",
                meta_tool_params
            )
            
            click.echo(f"✅ Task {task_id} completed")
            click.echo("📋 Result:")
            click.echo(result)
        else:
            # Start task asynchronously
            click.echo(f"📤 Task {task_id} dispatched (async)")
            click.echo(f"Use 'raid task status {task_id}' to check progress")
            
            # For async tasks, we'd typically store the task info
            # For now, just dispatch and show the immediate response
            result = await control_agent.meta_tool_registry.execute_meta_tool(
                "dispatch_to_sub_agent",
                meta_tool_params
            )
            
            if cli_ctx.verbose:
                click.echo(f"Initial response: {result}")
                
    except Exception as e:
        click.echo(f"❌ Failed to dispatch task: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@tasks_group.command()
@click.argument('task_id')
@pass_cli_context
@async_command
async def status(cli_ctx: CliContext, task_id: str):
    """Check the status of a specific task"""
    try:
        # Note: This is a placeholder implementation since task tracking
        # is not fully implemented in the current codebase
        click.echo(f"🔍 Checking status for task {task_id}")
        click.echo("❌ Task status tracking is not yet fully implemented")
        click.echo("💡 Suggestion: Use 'raid agents list' to see current agent activity")
        
    except Exception as e:
        click.echo(f"❌ Failed to get task status: {e}", err=True)
        raise click.Abort()


@tasks_group.command()
@click.option('--limit', '-l', default=10, help='Number of recent tasks to show')
@pass_cli_context
@async_command
async def history(cli_ctx: CliContext, limit: int):
    """Show recent task history"""
    try:
        # Note: This is a placeholder implementation since task history
        # is not fully implemented in the current codebase
        click.echo(f"📋 Recent tasks (last {limit}):")
        click.echo("❌ Task history tracking is not yet fully implemented")
        click.echo("💡 Suggestion: Check agent statistics with 'raid agents stats'")
        
    except Exception as e:
        click.echo(f"❌ Failed to get task history: {e}", err=True)
        raise click.Abort()


@tasks_group.command()
@click.argument('task_id')
@click.option('--force', '-f', is_flag=True, help='Force cancellation without confirmation')
@pass_cli_context
@async_command
async def cancel(cli_ctx: CliContext, task_id: str, force: bool):
    """Cancel a running task"""
    try:
        if not force:
            if not click.confirm(f"Are you sure you want to cancel task {task_id}?"):
                click.echo("Operation cancelled.")
                return
        
        click.echo(f"🚫 Cancelling task {task_id}")
        click.echo("❌ Task cancellation is not yet fully implemented")
        click.echo("💡 Suggestion: Stop the agent running the task with 'raid agents stop <agent-name>'")
        
    except Exception as e:
        click.echo(f"❌ Failed to cancel task: {e}", err=True)
        raise click.Abort()


@tasks_group.command()
@pass_cli_context
@async_command
async def templates(cli_ctx: CliContext):
    """Show available task templates and examples"""
    templates = {
        "Data Analysis": {
            "profile": "dynamic_data_analyst",
            "example": "Analyze the sales data and identify trends over the last quarter"
        },
        "Financial Calculation": {
            "profile": "dynamic_financial_analyst", 
            "example": "Calculate the ROI for a $50,000 investment with 8% annual return over 5 years"
        },
        "Research Task": {
            "profile": "dynamic_research_analyst",
            "example": "Research the latest developments in renewable energy technology"
        },
        "Problem Solving": {
            "profile": "dynamic_problem_solver",
            "example": "Help me optimize the resource allocation for our project team"
        },
        "Code Development": {
            "profile": "developer_agent",
            "example": "Write a Python function to parse CSV files and extract specific columns"
        },
        "System Setup": {
            "profile": "setup_agent",
            "example": "Setup development environment for https://github.com/user/project"
        }
    }
    
    click.echo("📚 Task Templates & Examples")
    click.echo("=" * 50)
    
    for category, info in templates.items():
        click.echo(f"\n🔹 {category}")
        click.echo(f"   Profile: {info['profile']}")
        click.echo(f"   Example: {info['example']}")
        click.echo(f"   Command: raid task run {info['profile']} \"{info['example']}\"")


@tasks_group.command()
@click.option('--profile', help='Agent profile to use')
@pass_cli_context
@async_command
async def interactive(cli_ctx: CliContext, profile: Optional[str]):
    """Interactive task creation wizard"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        click.echo("🧙 Interactive Task Creation Wizard")
        click.echo("=" * 40)
        
        # Get available profiles if not specified
        if not profile:
            click.echo("\n📋 Available profiles:")
            try:
                # Get available profiles from meta-tools
                profiles_result = await control_agent.meta_tool_registry.execute_meta_tool(
                    "discover_sub_agent_profiles", {}
                )
                
                if cli_ctx.verbose:
                    click.echo(f"Profiles: {profiles_result}")
                
                # For now, show common profiles
                common_profiles = [
                    "calculator_agent", "developer_agent", "advanced_agent",
                    "research_agent", "setup_agent"
                ]
                
                for i, p in enumerate(common_profiles, 1):
                    click.echo(f"  {i}. {p}")
                
                choice = click.prompt("Select profile number", type=int)
                if 1 <= choice <= len(common_profiles):
                    profile = common_profiles[choice - 1]
                else:
                    profile = click.prompt("Or enter custom profile name")
                    
            except Exception:
                profile = click.prompt("Enter agent profile name")
        
        # Get task description
        task_prompt = click.prompt("\n📝 Enter your task description")
        
        # Get optional parameters
        timeout = click.prompt("⏱️  Task timeout (seconds)", default=300, type=int)
        wait_for_completion = click.confirm("⏳ Wait for task completion?", default=True)
        
        # Confirm and execute
        click.echo(f"\n📋 Task Summary:")
        click.echo(f"   Profile: {profile}")
        click.echo(f"   Task: {task_prompt}")
        click.echo(f"   Timeout: {timeout}s")
        click.echo(f"   Wait: {wait_for_completion}")
        
        if click.confirm("\n🚀 Execute this task?"):
            # Use the run command implementation
            await run.callback(cli_ctx, profile, task_prompt, timeout, wait_for_completion, None)
        else:
            click.echo("Task cancelled.")
            
    except Exception as e:
        click.echo(f"❌ Failed to create interactive task: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@tasks_group.command()
@click.argument('profile_name')
@click.argument('task_description')
@click.option('--count', '-c', default=1, help='Number of agents to create')
@click.option('--group-name', help='Collaboration group name')
@pass_cli_context
@async_command
async def collaborative(cli_ctx: CliContext, profile_name: str, task_description: str, 
                       count: int, group_name: Optional[str]):
    """Create a collaborative task with multiple agents"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        if not group_name:
            group_name = f"collab_{str(uuid.uuid4())[:8]}"
        
        click.echo(f"🤝 Creating collaborative task with {count} agents")
        click.echo(f"Group: {group_name}")
        click.echo(f"Profile: {profile_name}")
        
        # Try to use the collaborative meta-tool
        try:
            result = await control_agent.meta_tool_registry.execute_meta_tool(
                "create_collaborative_sub_agent_group",
                {
                    "group_name": group_name,
                    "agent_profiles": [profile_name] * count,
                    "task_description": task_description
                }
            )
            
            click.echo(f"✅ Collaborative task created: {result}")
            
        except Exception as meta_error:
            click.echo(f"❌ Collaborative features not available: {meta_error}")
            click.echo("💡 Try using individual agents instead")
            
    except Exception as e:
        click.echo(f"❌ Failed to create collaborative task: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()
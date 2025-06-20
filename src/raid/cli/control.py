"""Control Agent task processing commands for Raid CLI"""

import uuid
from datetime import datetime
from typing import Optional

import click
from .utils import async_command, pass_cli_context, CliContext
from .formatters import OutputFormatter


@click.group(name='control')
def control_group():
    """Control Agent task processing with ReAct cycles"""
    pass


@control_group.command()
@click.argument('user_goal')
@click.option('--task-id', help='Custom task ID (auto-generated if not provided)')
@click.option('--max-steps', default=20, help='Maximum ReAct steps')
@click.option('--show-thinking', is_flag=True, help='Show Control Agent thinking process')
@pass_cli_context
@async_command
async def process(cli_ctx: CliContext, user_goal: str, task_id: Optional[str], 
                  max_steps: int, show_thinking: bool):
    """Process a user goal using Control Agent ReAct cycles
    
    This is the main way to start tasks with the Control Agent, which will:
    1. Analyze your goal using ReAct reasoning
    2. Discover available sub-agents
    3. Create specialized agents if needed
    4. Coordinate multiple agents for complex tasks
    5. Provide a comprehensive result
    """
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        if not task_id:
            task_id = str(uuid.uuid4())[:8]
        
        click.echo(f"🤖 Control Agent Processing Task: {task_id}")
        click.echo(f"🎯 Goal: {user_goal}")
        click.echo("=" * 60)
        
        if show_thinking:
            click.echo("🧠 Control Agent Thinking Process:")
            click.echo("-" * 40)
        
        # Set max steps if different from default
        if max_steps != 20:
            control_agent.react_engine.max_steps = max_steps
        
        start_time = datetime.utcnow()
        
        # Process the user goal using ReAct cycles
        task_context = await control_agent.process_user_goal(
            user_goal=user_goal,
            task_id=task_id
        )
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Display results
        click.echo("\n" + "=" * 60)
        click.echo("📋 Task Execution Summary")
        click.echo("=" * 60)
        
        # Task metadata
        click.echo(f"Task ID: {task_context.task_id}")
        click.echo(f"Status: {_format_task_status(task_context.status)}")
        click.echo(f"Duration: {duration:.2f} seconds")
        click.echo(f"ReAct Steps: {len(task_context.steps)}")
        
        # Show thinking process if requested
        if show_thinking and task_context.steps:
            click.echo(f"\n🧠 ReAct Thinking Process ({len(task_context.steps)} steps):")
            click.echo("-" * 50)
            
            for i, step in enumerate(task_context.steps, 1):
                # Handle ReActStep objects properly
                if hasattr(step, 'thought'):
                    click.echo(f"\n💭 Step {i}: {step.thought}")
                elif isinstance(step, dict):
                    click.echo(f"\n💭 Step {i}: {step.get('thought', 'No thought recorded')}")
                else:
                    click.echo(f"\n💭 Step {i}: {str(step)}")
                
                # Handle action
                action = None
                if hasattr(step, 'action'):
                    action = step.action
                elif isinstance(step, dict):
                    action = step.get('action')
                
                if action:
                    if isinstance(action, dict):
                        click.echo(f"🔧 Action: {action.get('name', 'unknown')}")
                        if cli_ctx.verbose and action.get('parameters'):
                            click.echo(f"   Parameters: {action['parameters']}")
                    else:
                        click.echo(f"🔧 Action: {str(action)}")
                
                # Handle observation  
                observation = None
                if hasattr(step, 'observation'):
                    observation = step.observation
                elif isinstance(step, dict):
                    observation = step.get('observation')
                
                if observation:
                    obs = observation[:200] + "..." if len(str(observation)) > 200 else str(observation)
                    click.echo(f"👁️  Observation: {obs}")
        
        # Sub-agents used
        if hasattr(task_context, 'sub_agents_used') and task_context.sub_agents_used:
            click.echo(f"\n🤝 Sub-Agents Used:")
            for agent in task_context.sub_agents_used:
                click.echo(f"  - {agent}")
        
        # Error information
        if task_context.status == "failed" and hasattr(task_context, 'error'):
            click.echo(f"\n❌ Error Details:")
            click.echo(f"   {task_context.error}")
        
        # Final result
        click.echo(f"\n📊 Final Result:")
        click.echo("-" * 30)
        if task_context.final_result:
            click.echo(task_context.final_result)
        else:
            click.echo("No result available")
        
        # Agent statistics after task
        if cli_ctx.verbose:
            stats = control_agent.lifecycle_manager.get_agent_stats()
            click.echo(f"\n📈 Post-Task Agent Statistics:")
            click.echo(f"   Active Agents: {stats.get('total_agents', 0)}")
            click.echo(f"   Total Tasks Completed: {stats.get('total_tasks_completed', 0)}")
            click.echo(f"   Capacity Usage: {stats.get('capacity_used_pct', 0):.1f}%")
        
    except Exception as e:
        click.echo(f"❌ Failed to process task: {e}", err=True)
        if cli_ctx.verbose:
            import traceback
            click.echo(f"Full error: {traceback.format_exc()}")
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@control_group.command()
@pass_cli_context
@async_command
async def interactive(cli_ctx: CliContext):
    """Interactive Control Agent task creation wizard"""
    try:
        click.echo("🧙 Control Agent Interactive Task Wizard")
        click.echo("=" * 50)
        
        # Get user goal
        user_goal = click.prompt("\n🎯 Describe your goal in natural language")
        
        # Get optional parameters
        show_thinking = click.confirm("🧠 Show Control Agent thinking process?", default=False)
        max_steps = click.prompt("⏱️  Maximum ReAct steps", default=20, type=int)
        
        if max_steps > 50:
            click.echo("⚠️  Warning: High step count may take a long time")
            if not click.confirm("Continue?"):
                click.echo("Operation cancelled.")
                return
        
        # Confirm execution
        click.echo(f"\n📋 Task Summary:")
        click.echo(f"   Goal: {user_goal}")
        click.echo(f"   Max Steps: {max_steps}")
        click.echo(f"   Show Thinking: {show_thinking}")
        
        if click.confirm("\n🚀 Execute this task with Control Agent?"):
            # Use the process command
            await process.callback(cli_ctx, user_goal, None, max_steps, show_thinking)
        else:
            click.echo("Task cancelled.")
            
    except Exception as e:
        click.echo(f"❌ Failed to create interactive task: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@control_group.command()
@pass_cli_context
@async_command
async def health(cli_ctx: CliContext):
    """Check Control Agent health and capabilities"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        click.echo("🔍 Control Agent Health Check")
        click.echo("=" * 40)
        
        health_status = {
            "control_agent": False,
            "llm_backend": False,
            "react_engine": False,
            "meta_tools": 0,
            "lifecycle_manager": False
        }
        
        # Check Control Agent
        try:
            if control_agent:
                health_status["control_agent"] = True
                click.echo("✅ Control Agent: Initialized")
            else:
                click.echo("❌ Control Agent: Not available")
        except Exception as e:
            click.echo(f"❌ Control Agent: {e}")
        
        # Check LLM Backend
        try:
            if control_agent.llm_backend:
                # Try a simple health check
                response = await control_agent.llm_backend.generate_response(
                    "Respond with 'OK' if you can process this message.",
                    max_tokens=10
                )
                if response and "ok" in response.lower():
                    health_status["llm_backend"] = True
                    click.echo("✅ LLM Backend: Healthy")
                else:
                    click.echo("⚠️ LLM Backend: Response unclear")
            else:
                click.echo("❌ LLM Backend: Not initialized")
        except Exception as e:
            click.echo(f"❌ LLM Backend: {e}")
        
        # Check ReAct Engine
        try:
            if control_agent.react_engine:
                health_status["react_engine"] = True
                click.echo("✅ ReAct Engine: Available")
                click.echo(f"   Max Steps: {control_agent.react_engine.max_steps}")
            else:
                click.echo("❌ ReAct Engine: Not initialized")
        except Exception as e:
            click.echo(f"❌ ReAct Engine: {e}")
        
        # Check Meta-Tools
        try:
            if control_agent.meta_tool_registry:
                meta_tools = control_agent.meta_tool_registry.list_tool_names()
                health_status["meta_tools"] = len(meta_tools)
                click.echo(f"✅ Meta-Tools: {len(meta_tools)} available")
                if cli_ctx.verbose:
                    for tool in meta_tools:
                        click.echo(f"   - {tool}")
            else:
                click.echo("❌ Meta-Tool Registry: Not initialized")
        except Exception as e:
            click.echo(f"❌ Meta-Tool Registry: {e}")
        
        # Check Lifecycle Manager
        try:
            if control_agent.lifecycle_manager:
                health_status["lifecycle_manager"] = True
                click.echo("✅ Lifecycle Manager: Available")
            else:
                click.echo("❌ Lifecycle Manager: Not initialized")
        except Exception as e:
            click.echo(f"❌ Lifecycle Manager: {e}")
        
        # Overall health assessment
        click.echo(f"\n🏥 Health Summary:")
        healthy_components = sum([
            health_status["control_agent"],
            health_status["llm_backend"],
            health_status["react_engine"],
            health_status["meta_tools"] > 0,
            health_status["lifecycle_manager"]
        ])
        
        if healthy_components == 5:
            click.echo(click.style("🟢 Control Agent Status: FULLY OPERATIONAL", fg="green"))
        elif healthy_components >= 3:
            click.echo(click.style("🟡 Control Agent Status: PARTIALLY OPERATIONAL", fg="yellow"))
        else:
            click.echo(click.style("🔴 Control Agent Status: DEGRADED", fg="red"))
        
        click.echo(f"Healthy Components: {healthy_components}/5")
        
    except Exception as e:
        click.echo(f"❌ Health check failed: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@control_group.command()
@pass_cli_context
@async_command
async def capabilities(cli_ctx: CliContext):
    """Show Control Agent capabilities and available meta-tools"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        click.echo("🛠️ Control Agent Capabilities")
        click.echo("=" * 50)
        
        # LLM Configuration
        llm_config = control_agent.config.llm_backend
        click.echo(f"🧠 LLM Configuration:")
        click.echo(f"   Provider: {llm_config.provider}")
        click.echo(f"   Model: {llm_config.model}")
        if hasattr(llm_config, 'max_tokens'):
            click.echo(f"   Max Tokens: {llm_config.max_tokens}")
        
        # ReAct Engine
        click.echo(f"\n🔄 ReAct Engine:")
        click.echo(f"   Max Steps: {control_agent.react_engine.max_steps}")
        click.echo(f"   Response Format: JSON-based thought-action-observation")
        
        # Meta-Tools
        meta_tools = control_agent.meta_tool_registry.list_tool_names()
        click.echo(f"\n🔧 Available Meta-Tools ({len(meta_tools)}):")
        
        for tool_name in meta_tools:
            try:
                tool_info = control_agent.meta_tool_registry.get_tool_info(tool_name)
                click.echo(f"\n  📋 {tool_name}")
                click.echo(f"     {tool_info.get('description', 'No description available')}")
                
                if cli_ctx.verbose and tool_info.get('parameters'):
                    click.echo(f"     Parameters:")
                    for param in tool_info['parameters']:
                        required = " (required)" if param.get('required') else " (optional)"
                        click.echo(f"       - {param['name']}: {param['type']}{required}")
                        click.echo(f"         {param.get('description', '')}")
                        
            except Exception as e:
                click.echo(f"  ❌ {tool_name}: Error getting info - {e}")
        
        # Workflow capabilities
        click.echo(f"\n🚀 Task Processing Capabilities:")
        click.echo("   ✅ Natural language goal processing")
        click.echo("   ✅ Automatic sub-agent discovery and selection")
        click.echo("   ✅ Dynamic specialized sub-agent creation")
        click.echo("   ✅ Multi-agent coordination and collaboration")
        click.echo("   ✅ Complex task breakdown and orchestration")
        click.echo("   ✅ Real-time agent lifecycle management")
        
        # Example goals
        click.echo(f"\n💡 Example Goals You Can Give to Control Agent:")
        examples = [
            "Calculate the compound interest on a $10,000 investment at 5% for 10 years",
            "Analyze sales data trends and create a summary report",
            "Set up a development environment for a Python web application",
            "Research the latest trends in renewable energy technology",
            "Create a financial model for a startup business plan",
            "Coordinate a data analysis pipeline with multiple data sources"
        ]
        
        for example in examples:
            click.echo(f"   • {example}")
        
        click.echo(f"\n🎯 Usage: raid control process \"<your goal in natural language>\"")
        
    except Exception as e:
        click.echo(f"❌ Failed to get capabilities: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


def _format_task_status(status: str) -> str:
    """Format task status with color coding"""
    status_colors = {
        "completed": "green",
        "failed": "red",
        "running": "blue",
        "pending": "yellow"
    }
    
    status_icons = {
        "completed": "✅",
        "failed": "❌",
        "running": "🔵",
        "pending": "🟡"
    }
    
    color = status_colors.get(status.lower(), "white")
    icon = status_icons.get(status.lower(), "⚪")
    
    return click.style(f"{icon} {status.upper()}", fg=color)
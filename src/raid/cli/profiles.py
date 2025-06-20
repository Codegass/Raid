"""Profile management commands for Raid CLI"""

import os
from typing import List, Dict, Any

import click
import yaml
from .utils import async_command, pass_cli_context, CliContext
from .formatters import OutputFormatter


@click.group(name='profiles')
def profiles_group():
    """Manage agent profiles"""
    pass


@profiles_group.command()
@pass_cli_context
@async_command
async def list(cli_ctx: CliContext):
    """List all available agent profiles"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        
        # Get profiles using the configurator
        configurator = control_agent.meta_tool_registry.configurator
        
        profiles_data = []
        
        # Get static profiles from the profiles directory
        profiles_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "..", "profiles")
        
        if os.path.exists(profiles_dir):
            for filename in os.listdir(profiles_dir):
                if filename.endswith('.yaml') or filename.endswith('.yml'):
                    profile_name = filename.replace('.yaml', '').replace('.yml', '')
                    try:
                        profile = configurator.load_profile(profile_name)
                        profiles_data.append({
                            "name": profile.name,
                            "description": profile.description,
                            "tools": profile.tools,
                            "llm_config": profile.llm_config.__dict__ if profile.llm_config else {},
                            "lifecycle_config": profile.lifecycle_config.__dict__ if profile.lifecycle_config else {},
                            "type": "static"
                        })
                    except Exception as e:
                        if cli_ctx.verbose:
                            click.echo(f"Warning: Could not load profile {profile_name}: {e}")
        
        # Get dynamic profile templates
        try:
            # Try to get dynamic agent manager info
            dynamic_roles = [
                {
                    "name": "dynamic_data_analyst",
                    "description": "Dynamic data analysis agent with statistical capabilities",
                    "tools": ["calculator", "run_python_code", "create_file", "read_file"],
                    "llm_config": {"model": "auto", "provider": "auto"},
                    "type": "dynamic"
                },
                {
                    "name": "dynamic_financial_analyst", 
                    "description": "Dynamic financial analysis agent for monetary calculations",
                    "tools": ["calculator", "run_python_code", "websearch"],
                    "llm_config": {"model": "auto", "provider": "auto"},
                    "type": "dynamic"
                },
                {
                    "name": "dynamic_research_analyst",
                    "description": "Dynamic research agent for information analysis",
                    "tools": ["websearch", "run_python_code", "create_file"],
                    "llm_config": {"model": "auto", "provider": "auto"},
                    "type": "dynamic"
                },
                {
                    "name": "dynamic_problem_solver",
                    "description": "Dynamic general problem-solving agent",
                    "tools": ["calculator", "run_python_code", "websearch", "run_bash_command"],
                    "llm_config": {"model": "auto", "provider": "auto"},
                    "type": "dynamic"
                }
            ]
            profiles_data.extend(dynamic_roles)
            
        except Exception as e:
            if cli_ctx.verbose:
                click.echo(f"Warning: Could not get dynamic profiles: {e}")
        
        # Format and display
        output = OutputFormatter.format_profiles_list(profiles_data, cli_ctx.format)
        click.echo(output)
        
        # Show summary
        static_count = len([p for p in profiles_data if p.get("type") == "static"])
        dynamic_count = len([p for p in profiles_data if p.get("type") == "dynamic"])
        
        click.echo(f"\n📊 Summary: {len(profiles_data)} profiles ({static_count} static, {dynamic_count} dynamic)")
        
    except Exception as e:
        click.echo(f"❌ Failed to list profiles: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@profiles_group.command()
@click.argument('profile_name')
@pass_cli_context
@async_command
async def show(cli_ctx: CliContext, profile_name: str):
    """Show detailed information about a specific profile"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        configurator = control_agent.meta_tool_registry.configurator
        
        # Try to load the profile
        try:
            profile = configurator.load_profile(profile_name)
            
            profile_data = {
                "name": profile.name,
                "description": profile.description,
                "version": profile.version,
                "tools": profile.tools,
                "llm_config": profile.llm_config.__dict__ if profile.llm_config else {},
                "docker_config": profile.docker_config.__dict__ if profile.docker_config else {},
                "lifecycle_config": profile.lifecycle_config.__dict__ if profile.lifecycle_config else {},
                "system_prompt": profile.system_prompt[:200] + "..." if len(profile.system_prompt) > 200 else profile.system_prompt
            }
            
            if cli_ctx.format == "json":
                import json
                click.echo(json.dumps(profile_data, indent=2))
            elif cli_ctx.format == "yaml":
                click.echo(yaml.dump(profile_data, default_flow_style=False))
            else:
                click.echo(f"📋 Profile: {profile.name}")
                click.echo("=" * 50)
                click.echo(f"Description: {profile.description}")
                click.echo(f"Version: {profile.version}")
                
                click.echo(f"\n🛠️ Tools ({len(profile.tools)}):")
                for tool in profile.tools:
                    click.echo(f"  - {tool}")
                
                if profile.llm_config:
                    click.echo(f"\n🧠 LLM Configuration:")
                    click.echo(f"  Provider: {profile.llm_config.provider}")
                    click.echo(f"  Model: {profile.llm_config.model}")
                    if hasattr(profile.llm_config, 'max_tokens'):
                        click.echo(f"  Max Tokens: {profile.llm_config.max_tokens}")
                
                if profile.docker_config:
                    click.echo(f"\n🐳 Docker Configuration:")
                    click.echo(f"  Base Image: {profile.docker_config.base_image}")
                    click.echo(f"  Working Dir: {profile.docker_config.working_dir}")
                    if profile.docker_config.additional_packages:
                        click.echo(f"  Packages: {len(profile.docker_config.additional_packages)} additional")
                
                if profile.lifecycle_config:
                    click.echo(f"\n⚙️ Lifecycle Configuration:")
                    click.echo(f"  Persistent: {profile.lifecycle_config.persistent}")
                    click.echo(f"  Auto Cleanup: {profile.lifecycle_config.auto_cleanup}")
                    click.echo(f"  Exclude from Count: {profile.lifecycle_config.exclude_from_count}")
                
                click.echo(f"\n📝 System Prompt Preview:")
                click.echo(f"  {profile.system_prompt[:200]}...")
                
        except FileNotFoundError:
            # Check if it's a dynamic profile
            dynamic_profiles = {
                "dynamic_data_analyst": "Data analysis and statistical calculations",
                "dynamic_financial_analyst": "Financial modeling and calculations", 
                "dynamic_research_analyst": "Research and information analysis",
                "dynamic_problem_solver": "General problem-solving tasks",
                "dynamic_quality_analyst": "Quality assurance and validation"
            }
            
            if profile_name in dynamic_profiles:
                click.echo(f"📋 Dynamic Profile: {profile_name}")
                click.echo("=" * 50)
                click.echo(f"Description: {dynamic_profiles[profile_name]}")
                click.echo("Type: Dynamic (created at runtime)")
                click.echo("Tools: Assigned based on role requirements")
                click.echo("LLM Config: Uses system defaults")
                click.echo("\n💡 Use 'raid task run {profile_name} \"<task>\"' to create an instance")
            else:
                click.echo(f"❌ Profile '{profile_name}' not found")
                click.echo("💡 Use 'raid profiles list' to see available profiles")
        
    except Exception as e:
        click.echo(f"❌ Failed to show profile: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@profiles_group.command()
@click.argument('profile_name')
@pass_cli_context
@async_command
async def validate(cli_ctx: CliContext, profile_name: str):
    """Validate a profile configuration"""
    try:
        control_agent = await cli_ctx.get_control_agent()
        configurator = control_agent.meta_tool_registry.configurator
        
        click.echo(f"🔍 Validating profile '{profile_name}'...")
        
        validation_results = {
            "profile_exists": False,
            "yaml_valid": False,
            "required_fields": False,
            "tools_available": False,
            "llm_config_valid": False,
            "docker_config_valid": False
        }
        
        try:
            # Try to load the profile
            profile = configurator.load_profile(profile_name)
            validation_results["profile_exists"] = True
            validation_results["yaml_valid"] = True
            click.echo("✅ Profile file exists and YAML is valid")
            
            # Check required fields
            required_fields = ["name", "description", "tools"]
            missing_fields = []
            
            for field in required_fields:
                if not hasattr(profile, field) or not getattr(profile, field):
                    missing_fields.append(field)
            
            if not missing_fields:
                validation_results["required_fields"] = True
                click.echo("✅ All required fields present")
            else:
                click.echo(f"❌ Missing required fields: {', '.join(missing_fields)}")
            
            # Check tools availability
            if profile.tools:
                # Get available tools from the system
                available_tools = [
                    "calculator", "run_python_code", "run_bash_command", 
                    "websearch", "create_file", "read_file", "list_files", 
                    "delete_file", "notification_user"
                ]
                
                invalid_tools = [tool for tool in profile.tools if tool not in available_tools]
                
                if not invalid_tools:
                    validation_results["tools_available"] = True
                    click.echo(f"✅ All {len(profile.tools)} tools are available")
                else:
                    click.echo(f"❌ Invalid tools: {', '.join(invalid_tools)}")
                    click.echo(f"Available tools: {', '.join(available_tools)}")
            
            # Check LLM configuration
            if profile.llm_config:
                if hasattr(profile.llm_config, 'provider') and hasattr(profile.llm_config, 'model'):
                    validation_results["llm_config_valid"] = True
                    click.echo("✅ LLM configuration is valid")
                else:
                    click.echo("❌ LLM configuration missing provider or model")
            else:
                click.echo("⚠️ No LLM configuration specified (will use defaults)")
                validation_results["llm_config_valid"] = True
            
            # Check Docker configuration
            if profile.docker_config:
                if hasattr(profile.docker_config, 'base_image'):
                    validation_results["docker_config_valid"] = True
                    click.echo("✅ Docker configuration is valid")
                else:
                    click.echo("❌ Docker configuration missing base_image")
            else:
                click.echo("⚠️ No Docker configuration specified (will use defaults)")
                validation_results["docker_config_valid"] = True
            
        except FileNotFoundError:
            click.echo(f"❌ Profile file '{profile_name}.yaml' not found")
        except yaml.YAMLError as e:
            click.echo(f"❌ YAML syntax error: {e}")
        except Exception as e:
            click.echo(f"❌ Validation error: {e}")
        
        # Summary
        passed_checks = sum(validation_results.values())
        total_checks = len(validation_results)
        
        click.echo(f"\n📊 Validation Summary:")
        click.echo(f"Checks passed: {passed_checks}/{total_checks}")
        
        if passed_checks == total_checks:
            click.echo(click.style("✅ Profile is valid and ready to use", fg="green"))
        elif passed_checks >= total_checks - 1:
            click.echo(click.style("⚠️ Profile has minor issues but should work", fg="yellow"))
        else:
            click.echo(click.style("❌ Profile has significant issues", fg="red"))
        
    except Exception as e:
        click.echo(f"❌ Failed to validate profile: {e}", err=True)
        raise click.Abort()
    finally:
        await cli_ctx.cleanup()


@profiles_group.command()
@click.argument('template_name')
@click.argument('profile_name')
@pass_cli_context
@async_command
async def create(cli_ctx: CliContext, template_name: str, profile_name: str):
    """Create a new profile from a template"""
    try:
        templates = {
            "basic": {
                "name": profile_name,
                "description": f"Basic agent profile: {profile_name}",
                "version": "1.0",
                "llm_config": {
                    "provider": "openai",
                    "model": "gpt-3.5-turbo",
                    "max_tokens": 1000,
                    "temperature": 0.3
                },
                "tools": ["calculator", "run_python_code"],
                "system_prompt": f"You are {profile_name}, a helpful AI assistant.",
                "docker_config": {
                    "base_image": "python:3.9-slim",
                    "working_dir": "/app"
                }
            },
            "developer": {
                "name": profile_name,
                "description": f"Developer-focused agent: {profile_name}",
                "version": "1.0", 
                "llm_config": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "max_tokens": 2000,
                    "temperature": 0.1
                },
                "tools": ["run_python_code", "run_bash_command", "create_file", "read_file", "list_files"],
                "system_prompt": f"You are {profile_name}, a software development assistant specialized in coding tasks.",
                "docker_config": {
                    "base_image": "python:3.9-slim",
                    "working_dir": "/workspace",
                    "additional_packages": ["git", "curl", "build-essential"]
                }
            },
            "analyst": {
                "name": profile_name,
                "description": f"Data analysis agent: {profile_name}",
                "version": "1.0",
                "llm_config": {
                    "provider": "openai", 
                    "model": "gpt-4",
                    "max_tokens": 2000,
                    "temperature": 0.2
                },
                "tools": ["calculator", "run_python_code", "websearch", "create_file", "read_file"],
                "system_prompt": f"You are {profile_name}, a data analysis specialist focused on statistical analysis and insights.",
                "docker_config": {
                    "base_image": "python:3.9-slim",
                    "working_dir": "/data"
                }
            }
        }
        
        if template_name not in templates:
            click.echo(f"❌ Template '{template_name}' not found")
            click.echo(f"Available templates: {', '.join(templates.keys())}")
            return
        
        # Create profile file
        profiles_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "..", "profiles")
        profile_file = os.path.join(profiles_dir, f"{profile_name}.yaml")
        
        if os.path.exists(profile_file):
            if not click.confirm(f"Profile '{profile_name}' already exists. Overwrite?"):
                click.echo("Operation cancelled.")
                return
        
        # Ensure profiles directory exists
        os.makedirs(profiles_dir, exist_ok=True)
        
        # Write profile file
        with open(profile_file, 'w') as f:
            yaml.dump(templates[template_name], f, default_flow_style=False, sort_keys=False)
        
        click.echo(f"✅ Profile '{profile_name}' created from template '{template_name}'")
        click.echo(f"📁 Location: {profile_file}")
        click.echo("💡 Edit the file to customize the profile configuration")
        
    except Exception as e:
        click.echo(f"❌ Failed to create profile: {e}", err=True)
        raise click.Abort()


@profiles_group.command()
@pass_cli_context
@async_command
async def templates(cli_ctx: CliContext):
    """List available profile templates"""
    templates = {
        "basic": "Simple agent with basic tools (calculator, Python)",
        "developer": "Development-focused agent with coding tools",
        "analyst": "Data analysis agent with statistical capabilities"
    }
    
    click.echo("📚 Available Profile Templates")
    click.echo("=" * 50)
    
    for template_name, description in templates.items():
        click.echo(f"\n🔹 {template_name}")
        click.echo(f"   {description}")
        click.echo(f"   Usage: raid profiles create {template_name} <profile-name>")
    
    click.echo(f"\n💡 Example: raid profiles create developer my_coding_agent")
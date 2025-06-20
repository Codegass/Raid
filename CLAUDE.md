# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Project Raid is an LLM-based multi-agent orchestration system featuring:
- **LLM Control Agent**: An LLM-powered orchestrator operating in ReAct mode (Thought-Action-Observation cycles)
- **LLM Sub-Agents**: Specialized agents running in Docker containers, each with specific tools and capabilities
- **Docker Orchestrator**: Manages Sub-Agent containers and their lifecycle
- **Message Queue Communication**: Agents communicate via MQ for task distribution and results

## Architecture

The system follows a phased development approach:
1. **Phase 1**: LLM Sub-Agent foundation with scripted triggers
2. **Phase 2**: LLM-based Control Agent with ReAct cycles and single Sub-Agent orchestration
3. **Phase 3**: Multi-profile Sub-Agents with expanded Control Agent meta-tools
4. **Phase 4**: Long-term memory (RAG) and external API proxy capabilities
5. **Phase 5**: Production hardening with observability and security

### Key Components
- **Control Agent Meta-Tools**: `dispatch_to_sub_agent()`, `plan_sub_task()`, `discover_sub_agent_profiles()`, etc.
- **Sub-Agent Auto-Configurator**: YAML-based definitions for Sub-Agent profiles with lifecycle configuration
- **LLM Backend Interface**: Abstraction for OpenAI/Ollama integration with o4-mini model support
- **Lifecycle Manager**: Automatic Sub-Agent container lifecycle management with persistent agent support
- **Dynamic Sub-Agent Creation**: Runtime generation of specialized agents based on task requirements and role templates
- **Collaboration System**: Structured inter-agent communication with security restrictions and message validation
- **Setup Agent**: Specialized persistent agent for project environment configuration and build verification
- **Tool System**: Comprehensive modular tools including calculator, file operations, Python execution, web search, bash execution, and cross-platform notifications

## Development Setup

The project currently requires:
- Docker (installed and running)
- UV package manager (based on README reference)
- Python 3.9+ (specified in pyproject.toml)
- Redis (for message queue communication)

### Development Tools
- **Linting**: `ruff` (configured in pyproject.toml)
- **Formatting**: `black` (line length: 88)
- **Type Checking**: `mypy` with strict untyped definitions
- **Testing**: `pytest` framework

Note: Current version is v0.2 with significant progress on core components and dynamic agent capabilities.

## Current Implementation Status (v0.2)

### Completed Components
- **Control Agent**: Fully implemented with ReAct engine and meta-tools
- **Sub-Agents**: Complete with Docker containerization and tool integration
- **Docker Orchestrator**: Container management and lifecycle operations
- **LLM Backends**: OpenAI and Ollama provider implementations with o4-mini support
- **Message Queue**: Redis-based communication system
- **Lifecycle Manager**: Automatic container cleanup and resource management with persistent agent support
- **Dynamic Agent Profiles**: Runtime generation of specialized agents (data analyst, financial analyst, etc.)
- **Tool System**: Calculator, file operations, Python execution, web search, bash execution, and cross-platform notifications
- **Setup Agent**: Specialized persistent agent for environment configuration and project setup
- **Collaboration System**: Multi-agent coordination with structured communication and security restrictions

### Recent Additions
- **Setup Agent**: Specialized agent for repository cloning, environment setup, and build verification
  - Uses o4-mini model with 20,000 token capacity
  - Persistent lifecycle (excludes from count, no auto-cleanup)
  - Cross-platform notification system (Windows, macOS, Linux)
  - Comprehensive development tool set
- **Enhanced Lifecycle Management**: 
  - Agent state tracking with heartbeat monitoring
  - Persistent vs regular agent distinction
  - Capacity management and idle timeout handling
  - Automatic container state synchronization
- **Dynamic Sub-Agent Creation**: 
  - Role-based templates (data_analyst, financial_analyst, research_analyst, problem_solver, quality_analyst)
  - Task-specific agent profiles with automatic role suggestion
  - Runtime agent generation with specialized tools and prompts
- **Collaboration Features**: 
  - Structured inter-agent communication with message types
  - Rate limiting and security restrictions
  - Group-based collaboration management
  - Message validation and expiration handling
- **Enhanced Tool Set**: 
  - Cross-platform notification tool with system integration
  - File operations suite (create, read, list, delete)
  - Bash executor for system-level commands
  - Enhanced web search with validation
- **ReAct Engine**: Available for both Control Agent and Sub-Agents

## Context Management

Critical design focus on context management for the Control Agent's LLM:
- **Scratchpad/Working Memory**: T-A-O cycle history for current tasks
- **Long-term Memory**: Archive/RAG system for past task retrieval
- **Token Limit Management**: Strategies for context window optimization

## Testing

The project includes comprehensive test scripts in the `scripts/` directory:
- `test_control_agent.py`: Control Agent functionality and ReAct cycles
- `test_sub_agent.py`: Sub-Agent operations and tool integration
- `test_advanced_tools.py`: Advanced tool functionality testing
- `test_collaborative_subagents.py`: Multi-agent collaboration scenarios
- `test_dynamic_subagent_creation.py`: Dynamic agent profile generation
- `test_setup_agent_full.py`: Setup Agent configuration and tool integration testing
- `setup_agent_demo.py`: Demonstration of Setup Agent environment configuration capabilities

## Agent Profiles

The project includes several specialized agent profiles:
- **setup_agent**: Persistent environment configuration agent with comprehensive toolset
- **advanced_agent**: Multi-purpose agent with full tool access
- **calculator_agent**: Basic calculation-focused agent
- **developer_agent**: Development-oriented agent with coding tools
- **research_agent**: Research and analysis focused agent

Dynamic agents are created at runtime based on role templates:
- **data_analyst**: Statistical analysis and data interpretation
- **financial_analyst**: Financial modeling and calculations
- **research_analyst**: Research methodology and information analysis
- **problem_solver**: General problem-solving with systematic approach
- **quality_analyst**: Quality assurance and validation processes

## Security Considerations

- Secure credential/endpoint injection for Sub-Agent LLM access
- Prompt injection protection for Control Agent
- Meta-tool permission controls
- Inter-agent communication restrictions and validation
- Rate limiting for collaboration messages
- Lifecycle management security (persistent agent controls)
- Cross-platform notification system sandboxing
- No secrets in code or commits

## Setup Agent Usage

The Setup Agent is a specialized persistent agent designed for project environment configuration:

### Key Features
- **Persistent Lifecycle**: Not subject to automatic cleanup, designed for long-running setup tasks
- **Comprehensive Toolset**: Includes repository cloning, environment analysis, dependency installation, and build verification
- **Cross-Platform Notifications**: Alerts users on Windows, macOS, and Linux when setup is complete
- **o4-mini Model**: Uses advanced reasoning with 20,000 token capacity for complex setup decisions

### Usage Example
```python
await dispatch_to_sub_agent(
    sub_agent_profile="setup_agent",
    task_prompt="""
    Setup development environment for: https://github.com/user/project-name
    Requirements:
    - Clone repository to /workspace
    - Install all dependencies
    - Run build verification
    - Execute test suite
    - Notify when complete
    """,
    timeout=1800  # 30 minutes for complex setups
)
```

For detailed Setup Agent usage, see `SETUP_AGENT_GUIDE.md`.

## Command Line Interface (CLI)

Raid includes a comprehensive CLI for system management and monitoring:

### Installation & Usage
```bash
# Install with CLI support
pip install -e .

# Use the CLI
raid --help
```

### Key CLI Commands

#### Control Agent Processing (RECOMMENDED)
- `raid control process "<goal>"` - Process natural language goals with ReAct reasoning
- `raid control process "<goal>" --show-thinking` - Show Control Agent thinking process
- `raid control interactive` - Interactive goal creation wizard
- `raid control health` - Check Control Agent health and capabilities
- `raid control capabilities` - Show available meta-tools and features

#### Agent Management
- `raid agents list` - List all active agents with status
- `raid agents stats` - Detailed statistics and relationships
- `raid agents create <profile>` - Create new agent from profile
- `raid agents stop <agent-name>` - Stop specific agent
- `raid agents cleanup` - Remove idle/stale agents
- `raid agents logs <agent-name>` - View agent container logs
- `raid agents health` - Check health status of all agents

#### Direct Sub-Agent Dispatch (Alternative)
- `raid task run <profile> "<prompt>"` - Dispatch task to specific agent profile
- `raid task interactive` - Interactive task creation wizard
- `raid task collaborative <profile> "<task>" --count N` - Multi-agent collaborative tasks
- `raid task templates` - Show available task templates

#### System Monitoring
- `raid status` - Quick system status overview
- `raid system stats` - Comprehensive system statistics
- `raid system health` - Perform system health check
- `raid system config` - Show current configuration
- `raid system metrics` - Detailed system metrics

#### Profile Management
- `raid profiles list` - List available agent profiles
- `raid profiles show <profile>` - Show profile details
- `raid profiles validate <profile>` - Validate profile configuration
- `raid profiles create <template> <name>` - Create new profile from template

#### Collaboration Management
- `raid collab groups` - List collaboration groups
- `raid collab create <group-name>` - Create collaboration group
- `raid collab status <group-id>` - Show group status

### Output Formats
- `--format table` (default) - Formatted tables with colors
- `--format json` - JSON output for programmatic use
- `--format yaml` - YAML output for configuration

### Key Features
- **Control Agent Processing** - Natural language goals with ReAct reasoning and intelligent orchestration
- **Real-time monitoring** with agent status and relationships  
- **Dual task dispatch modes** - Control Agent orchestration or direct sub-agent dispatch
- **Comprehensive statistics** including resource utilization
- **Health monitoring** with system-wide health checks
- **Profile management** with validation and templates
- **Collaboration support** for multi-agent coordination

### Usage Examples
```bash
# RECOMMENDED: Control Agent with intelligent orchestration
raid control process "Calculate ROI for $50k investment at 8% over 5 years"
raid control process "Setup React development environment" --show-thinking

# Alternative: Direct sub-agent dispatch  
raid task run calculator_agent "Calculate 15% tip on $85"
raid task run setup_agent "Clone and setup GitHub project"
```

For detailed CLI usage, see `CLI_USAGE.md` and `CONTROL_AGENT_USAGE.md`.
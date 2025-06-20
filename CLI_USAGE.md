# Raid CLI Usage Guide

The Raid CLI provides comprehensive management and monitoring capabilities for the Raid multi-agent orchestration system.

## Installation

After installing the Raid package, the CLI will be available as the `raid` command:

```bash
# Install in development mode
pip install -e .

# Or install from package
pip install raid
```

## Global Options

- `--verbose, -v`: Enable verbose output for debugging
- `--format, -f`: Output format (table, json, yaml) - default: table
- `--help`: Show help information

## Command Structure

```
raid [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGS]
```

## Quick Commands

```bash
# RECOMMENDED: Use Control Agent for intelligent orchestration
raid control process "Calculate the ROI for a $50,000 investment at 8% over 5 years"

# Show Control Agent thinking process
raid control process "Analyze sales trends" --show-thinking

# Alternative: Direct sub-agent dispatch
raid task run calculator_agent "Calculate 15% tip on $85"

# System monitoring
raid status
raid agents list
raid system stats
```

## Control Agent Processing (`raid control`) - **RECOMMENDED**

The Control Agent is the main orchestrator that uses ReAct reasoning to intelligently analyze your goals and coordinate sub-agents.

### Process User Goals
```bash
# Basic goal processing - Control Agent figures out everything
raid control process "Calculate compound interest on $10,000 at 5% for 10 years"

# Show the Control Agent's reasoning process  
raid control process "Setup Python development environment" --show-thinking

# Custom parameters
raid control process "Analyze market trends" --max-steps 25 --task-id analysis_001
```

### Interactive Mode
```bash
# Launch guided task creation wizard
raid control interactive

# Prompts for goal, thinking visibility, step limits
```

### Control Agent Health
```bash
# Check Control Agent health and capabilities
raid control health

# Show available meta-tools and capabilities
raid control capabilities
```

### Example Goals for Control Agent
```bash
# Financial analysis
raid control process "Calculate total cost of ownership for a $30k car over 5 years"

# Data analysis  
raid control process "Analyze customer purchase patterns and identify growth opportunities"

# Project setup
raid control process "Setup complete React TypeScript development environment"

# Research tasks
raid control process "Research renewable energy adoption trends with statistics"

# Multi-agent coordination
raid control process "Create financial model with market analysis and risk assessment"
```

## Agent Management (`raid agents`)

### List Agents
```bash
# List all active agents
raid agents list

# Filter by profile
raid agents list --profile calculator_agent

# Filter by state
raid agents list --state running

# Output as JSON
raid agents list --format json
```

### Agent Statistics
```bash
# Show detailed agent statistics
raid agents stats

# Include collaboration relationships
raid agents stats --format yaml
```

### Create Agents
```bash
# Create agent from existing profile
raid agents create calculator_agent

# Create dynamic agent with task description
raid agents create dynamic_data_analyst --task-description "Analyze sales data trends"

# Create specialized agent
raid agents create dynamic_financial_analyst -t "Calculate investment ROI"
```

### Stop Agents
```bash
# Stop specific agent (with confirmation)
raid agents stop my_agent

# Force stop without confirmation
raid agents stop my_agent --force
```

### Agent Maintenance
```bash
# Clean up idle and error agents
raid agents cleanup

# Dry run to see what would be cleaned
raid agents cleanup --dry-run

# Force cleanup without confirmation
raid agents cleanup --force
```

### Agent Logs
```bash
# View agent container logs
raid agents logs my_agent

# Show more lines
raid agents logs my_agent --lines 100
```

### Health Check
```bash
# Check health of all agents
raid agents health
```

## Task Management (`raid task`)

### Run Tasks
```bash
# Basic task execution
raid task run calculator_agent "Calculate compound interest"

# Wait for completion
raid task run developer_agent "Write a Python sorting function" --wait

# Set custom timeout
raid task run setup_agent "Setup Node.js project" --timeout 1800

# Use specific agent instance
raid task run calculator_agent "Calculate tax" --agent-name calc_001
```

### Task Templates
```bash
# Show available task templates
raid task templates

# Examples from templates:
raid task run dynamic_data_analyst "Analyze the sales data trends"
raid task run dynamic_financial_analyst "Calculate ROI for $50k investment at 8% over 5 years"
raid task run setup_agent "Setup development environment for https://github.com/user/project"
```

### Interactive Task Creation
```bash
# Launch interactive task wizard
raid task interactive

# With pre-selected profile
raid task interactive --profile developer_agent
```

### Collaborative Tasks
```bash
# Create collaborative task with multiple agents
raid task collaborative data_analyst "Market analysis project" --count 3

# Create with custom group name
raid task collaborative researcher "Research study" --count 2 --group-name market_research
```

### Task Status (Planned)
```bash
# Check task status (not fully implemented)
raid task status task_123

# View task history (not fully implemented)
raid task history --limit 20

# Cancel running task (not fully implemented)
raid task cancel task_123
```

## System Monitoring (`raid system`)

### System Status
```bash
# Quick system overview
raid status
# or
raid system status
```

### Comprehensive Statistics
```bash
# Detailed system stats
raid system stats

# Output as JSON for monitoring
raid system stats --format json
```

### Configuration
```bash
# Show current configuration
raid system config

# Configuration as YAML
raid system config --format yaml
```

### System Health
```bash
# Comprehensive health check
raid system health

# With custom timeout
raid system health --timeout 60
```

### System Metrics
```bash
# Show detailed metrics
raid system metrics
```

### System Management
```bash
# Restart the system
raid system restart

# Force restart without confirmation
raid system restart --force
```

## Profile Management (`raid profiles`)

### List Profiles
```bash
# List all available profiles
raid profiles list

# Output as JSON
raid profiles list --format json
```

### Profile Details
```bash
# Show profile configuration
raid profiles show calculator_agent

# Show dynamic profile info
raid profiles show dynamic_data_analyst
```

### Profile Validation
```bash
# Validate profile configuration
raid profiles validate my_custom_agent

# Will check:
# - Profile file exists and valid YAML
# - Required fields present
# - Tools are available
# - LLM and Docker config valid
```

### Create Profiles
```bash
# List available templates
raid profiles templates

# Create from template
raid profiles create basic my_simple_agent
raid profiles create developer my_coding_agent
raid profiles create analyst my_data_agent
```

## Collaboration Management (`raid collab`)

### List Groups
```bash
# List all collaboration groups
raid collab groups

# Output as JSON
raid collab groups --format json
```

### Create Groups
```bash
# Create collaboration group
raid collab create "data_analysis_team"

# With custom settings
raid collab create "research_group" --max-messages 50 --max-size 20000
```

### Group Management
```bash
# Show group status
raid collab status group_123

# View group messages (planned)
raid collab messages group_123 --lines 50

# Shutdown group
raid collab shutdown group_123

# Cleanup inactive groups
raid collab cleanup
```

## Output Formats

### Table Format (Default)
```bash
raid agents list
# Displays formatted table with colors and icons
```

### JSON Format
```bash
raid agents list --format json
# Outputs structured JSON for programmatic use
```

### YAML Format
```bash
raid system stats --format yaml
# Outputs YAML for configuration or documentation
```

## Environment Configuration

The CLI respects these environment variables:

```bash
# LLM Configuration
export RAID_LLM_PROVIDER=openai
export OPENAI_API_KEY=your_key
export RAID_OPENAI_MODEL=gpt-4

# Or for Ollama
export RAID_LLM_PROVIDER=ollama
export RAID_OLLAMA_URL=http://localhost:11434
export RAID_OLLAMA_MODEL=llama2

# System Configuration
export RAID_MAX_DYNAMIC_SUB_AGENTS=10
export RAID_DOCKER_SOCKET=unix:///var/run/docker.sock

# Redis Configuration
export RAID_REDIS_HOST=localhost
export RAID_REDIS_PORT=6379
export RAID_REDIS_DB=0
```

## Common Use Cases

### Development Workflow
```bash
# 1. Check system status
raid status

# 2. List available profiles
raid profiles list

# 3. Create a development agent
raid agents create developer_agent

# 4. Run a coding task
raid task run developer_agent "Create a REST API endpoint" --wait

# 5. Check agent health
raid agents health

# 6. Clean up when done
raid agents cleanup
```

### Data Analysis Pipeline
```bash
# 1. Create data analyst
raid task run dynamic_data_analyst "Load and analyze sales_data.csv"

# 2. Create financial analyst for ROI calculations
raid task run dynamic_financial_analyst "Calculate campaign ROI"

# 3. Generate collaborative report
raid task collaborative data_analyst "Quarterly business review" --count 2
```

### Project Setup
```bash
# Use setup agent for environment configuration
raid task run setup_agent "Setup development environment for https://github.com/myorg/project" --timeout 1800 --wait
```

### System Monitoring
```bash
# Monitor system health
raid system health

# Check detailed metrics
raid system metrics

# List active agents
raid agents list --state running

# Clean up idle agents
raid agents cleanup --dry-run
```

## Troubleshooting

### Common Issues

1. **CLI not found**: Ensure the package is installed correctly
   ```bash
   pip install -e .
   ```

2. **Connection errors**: Check Redis and Docker are running
   ```bash
   raid system health
   ```

3. **Agent creation fails**: Verify environment variables are set
   ```bash
   raid system config
   ```

4. **Task fails**: Check agent logs
   ```bash
   raid agents logs <agent-name>
   ```

### Verbose Mode
```bash
# Enable verbose output for debugging
raid --verbose agents list
raid -v task run calculator_agent "test" --wait
```

### Health Checks
```bash
# Comprehensive system health check
raid system health

# Check specific agent health
raid agents health
```

## Integration Examples

### Monitoring Script
```bash
#!/bin/bash
# Basic monitoring script
echo "=== Raid System Status ==="
raid status
echo "=== Active Agents ==="
raid agents list --state running
echo "=== System Health ==="
raid system health
```

### Automated Cleanup
```bash
#!/bin/bash
# Cleanup script for maintenance
echo "Cleaning up idle agents..."
raid agents cleanup --force
echo "Cleaning up collaboration groups..."
raid collab cleanup
```

This CLI provides comprehensive management capabilities for the Raid multi-agent system while being user-friendly and suitable for both interactive use and automation.
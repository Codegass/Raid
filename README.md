# Project Raid 🚀

A sophisticated multi-agent LLM orchestration system that enables intelligent task distribution and collaborative problem-solving through specialized AI agents with advanced tool capabilities.

## Overview

Project Raid implements a hierarchical multi-agent architecture where a **Control Agent** orchestrates multiple **Sub-Agents** to solve complex tasks through intelligent decomposition and delegation. The system supports both individual and collaborative agent execution with role-based specialization, secure inter-agent communication, and a comprehensive suite of tools for research, development, and analysis.

## Architecture

### Core Components

- **Control Agent**: Master orchestrator using ReAct (Reasoning-Action-Observation) cycles
- **Sub-Agents**: Specialized workers with domain-specific capabilities and advanced tools
- **Docker Orchestrator**: Container lifecycle management for Sub-Agents
- **Message Queue**: Redis-based communication system with pub/sub for collaboration
- **LLM Backend**: Abstracted interface supporting OpenAI and Ollama
- **Dynamic Agent Manager**: Runtime creation of specialized Sub-Agents
- **Collaboration System**: Secure direct communication between Sub-Agent groups
- **Advanced Tool System**: Comprehensive toolkit for web search, code execution, file operations, and more

### Key Features

- 🧠 **Intelligent Task Orchestration**: Control Agent uses ReAct cycles to plan and execute complex workflows
- 🔧 **Dynamic Specialization**: Create Sub-Agents with specific roles (financial analyst, data analyst, etc.)
- 🤝 **Collaborative Agent Groups**: Sub-Agents can work together with predefined, restricted communication
- 🌐 **Web Search Integration**: Real-time internet research capabilities with multiple search providers
- 🐍 **Code Execution**: Secure Python code execution with data analysis libraries
- 📁 **File Operations**: Complete file management within isolated workspaces
- 💻 **System Commands**: Safe bash command execution in Docker containers
- 🐳 **Containerized Execution**: Isolated Sub-Agent environments using Docker
- 🔄 **Async Message Queues**: Reliable Redis-based communication with pub/sub support
- 🎯 **Configurable Limits**: Control resource usage with agent and collaboration limits
- 🛠️ **Extensible Tools**: Plugin-based tool system for Sub-Agents
- ✨ **Enhanced Stability & Reliability**: Increased timeouts for long tasks and robust Docker orchestration ensure agents run dependably on the latest code.
- 🔒 **Security-First Design**: Strict collaboration restrictions and message validation

## Advanced Tool System

### Available Tools

#### **Research & Information**
- **`websearch`**: Internet search using DuckDuckGo and SerpAPI
  - Real-time information gathering
  - Multiple search provider fallback
  - Credible source prioritization

#### **Code Execution & Development**
- **`run_python_code`**: Secure Python code execution
  - Data analysis with pandas, numpy, matplotlib
  - Statistical computing and visualization
  - Sandboxed environment with security restrictions
- **`run_bash_command`**: Enhanced secure shell command execution (Docker only)
  - **NEW: `output_log_file` Parameter**: Redirects long outputs (build logs, etc.) to files, preventing context overflows
  - **Intelligence-First Design**: Agents automatically use log files + grep/tail for analyzing large command outputs
  - **Enhanced Security**: Whitelist of 50+ allowed commands, forbidden pattern detection, command chaining prevention
  - **Development Tools**: git, gcc, python, npm, maven, gradle, and package managers
  - **Working Directory Management**: Fixed path resolution for reliable command execution
  - **Timeout Management**: Configurable timeouts (30s-300s) with async execution

#### **File Management**
- **`create_file`**: Create files with content
- **`read_file`**: Read file contents with size limits  
- **`list_files`**: List workspace files
- **`delete_file`**: Remove files from workspace
- **Workspace isolation**: All file operations in `/tmp/raid_workspace`

#### **System Notifications**
- **`notification_user`**: Cross-platform system notifications
  - **Windows**: PowerShell toast notifications
  - **macOS**: osascript display notifications
  - **Linux**: notify-send, zenity, or kdialog fallbacks
  - **Urgency levels**: low, normal, critical
  - **Non-blocking**: Async execution without system delays

#### **Network Operations**
- **`network_request`**: Limited HTTP GET requests
- **`calculator`**: Mathematical calculations and computations

### Security Features

#### **Code Execution Security**
- ✅ Restricted imports (no os, sys, subprocess)
- ✅ Forbidden operations (no exec, eval, file system access)
- ✅ Execution timeout limits (30-120 seconds)
- ✅ Output size restrictions
- ✅ Sandboxed environment isolation

#### **File Operations Security**
- ✅ Workspace isolation (`/tmp/raid_workspace`)
- ✅ Allowed file extensions only
- ✅ Path traversal prevention
- ✅ File size limits (10MB max)
- ✅ No system directory access

#### **Command Execution Security**
- ✅ Docker environment requirement
- ✅ Command whitelist approach
- ✅ Dangerous pattern blacklist
- ✅ No system modification commands
- ✅ Safe development tools only

## Quick Start

### Prerequisites

- Python 3.9+
- Docker & Docker Compose  
- Redis server
- OpenAI API key OR Ollama installation
- (Optional) SerpAPI key for enhanced web search

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Raid
   ```

2. **Install dependencies with CLI support**
   ```bash
   pip install -e .
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start Redis**
   ```bash
   # Using Docker
   docker run -d -p 6379:6379 redis:alpine
   
   # Or using local Redis
   redis-server
   ```

### CLI Usage (Recommended)

**Raid includes a comprehensive CLI for intelligent task processing and system management:**

```bash
# Check CLI help
raid --help

# RECOMMENDED: Control Agent processing with intelligent orchestration
raid control process "Calculate ROI for $50k investment at 8% over 5 years"
raid control process "Setup React development environment" --show-thinking
raid control interactive  # Interactive wizard

# Agent management
raid agents list          # List active agents
raid agents stats         # Detailed statistics
raid agents health        # Health status

# System monitoring
raid status              # Quick system overview
raid system health       # Full health check

# Profile management
raid profiles list       # Available profiles
raid profiles show setup_agent  # Show profile details
```

### Test Scripts Usage

1. **Test Sub-Agent functionality**
   ```bash
   python scripts/test_sub_agent.py
   ```

2. **Test Control Agent orchestration**
   ```bash
   python scripts/test_control_agent.py
   ```

3. **Test dynamic Sub-Agent creation**
   ```bash
   python scripts/test_dynamic_subagent_creation.py
   ```

4. **Test collaborative Sub-Agent groups**
   ```bash
   python scripts/test_collaborative_subagents.py
   ```

5. **Test advanced tools functionality**
   ```bash
   python scripts/test_advanced_tools.py
   ```

6. **Test Setup Agent capabilities**
   ```bash
   python scripts/test_setup_agent_full.py
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RAID_LLM_PROVIDER` | LLM provider (openai/ollama) | openai |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `RAID_OPENAI_MODEL` | OpenAI model | gpt-4o |
| `RAID_OLLAMA_URL` | Ollama server URL | http://localhost:11434 |
| `RAID_OLLAMA_MODEL` | Ollama model | qwen3:30b |
| `RAID_REDIS_HOST` | Redis host | localhost |
| `RAID_REDIS_PORT` | Redis port | 6379 |
| `RAID_MAX_DYNAMIC_SUB_AGENTS` | Max dynamic agents | 5 |
| `SERP_API_KEY` | SerpAPI key for enhanced web search (optional) | - |

### Sub-Agent Profiles

Sub-Agents are configured using YAML profiles in the `profiles/` directory:

```yaml
name: advanced_agent
description: Advanced Sub-Agent with comprehensive tool capabilities
version: "1.0"
llm_config:
  provider: openai
  model: gpt-4o
  max_tokens: 2000
  temperature: 0.3
tools:
  - calculator
  - websearch
  - run_python_code
  - create_file
  - read_file
  - list_files
  - run_bash_command
system_prompt: |
  You are an advanced Sub-Agent with comprehensive capabilities...
docker_config:
  base_image: python:3.9-slim
  working_dir: /app
```

## Command Line Interface (CLI)

Raid includes a comprehensive CLI for system management and intelligent task processing:

### Installation & Basic Usage
```bash
# Install with CLI support
pip install -e .

# Use the CLI
raid --help
```

### Key CLI Commands

#### **Control Agent Processing (RECOMMENDED)**
- `raid control process "<goal>"` - Process natural language goals with ReAct reasoning
- `raid control process "<goal>" --show-thinking` - Show Control Agent thinking process
- `raid control interactive` - Interactive goal creation wizard
- `raid control health` - Check Control Agent health and capabilities
- `raid control capabilities` - Show available meta-tools and features

#### **Agent Management**
- `raid agents list` - List all active agents with status
- `raid agents stats` - Detailed statistics and relationships
- `raid agents create <profile>` - Create new agent from profile
- `raid agents stop <agent-name>` - Stop specific agent
- `raid agents cleanup` - Remove idle/stale agents
- `raid agents logs <agent-name>` - View agent container logs
- `raid agents health` - Check health status of all agents

#### **Direct Sub-Agent Dispatch (Alternative)**
- `raid task run <profile> "<prompt>"` - Dispatch task to specific agent profile
- `raid task interactive` - Interactive task creation wizard
- `raid task collaborative <profile> "<task>" --count N` - Multi-agent collaborative tasks
- `raid task templates` - Show available task templates

#### **System Monitoring**
- `raid status` - Quick system status overview
- `raid system stats` - Comprehensive system statistics
- `raid system health` - Perform system health check
- `raid system config` - Show current configuration
- `raid system metrics` - Detailed system metrics

#### **Profile Management**
- `raid profiles list` - List available agent profiles
- `raid profiles show <profile>` - Show profile details
- `raid profiles validate <profile>` - Validate profile configuration
- `raid profiles create <template> <name>` - Create new profile from template

#### **Collaboration Management**
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

## Setup Agent - Specialized Environment Configuration

**The Setup Agent is a persistent, specialized agent designed for project environment setup and development infrastructure configuration.**

### Key Features
- **Persistent Lifecycle**: Not subject to automatic cleanup, designed for long-running setup tasks
- **Advanced LLM Model**: Uses o4-mini with 20,000 token capacity for complex setup decisions
- **Comprehensive Toolset**: Includes repository cloning, environment analysis, dependency installation, and build verification
- **Cross-Platform Notifications**: Alerts users on Windows, macOS, and Linux when setup is complete
- **Enhanced Output Handling**: Automatically redirects large build outputs to log files for reliable analysis
- **Development Tools**: Pre-installed with git, build-essential, Python, Docker, and common development utilities

### Specialized Capabilities

#### **Environment Setup Workflow**
1. **Repository Analysis**: Clone and analyze project structure and technology stack
2. **Dependency Management**: Install system dependencies and configure package managers
3. **Build Environment**: Set up Python, Node.js, Java, Docker environments as needed
4. **Configuration**: Generate and validate configuration files
5. **Testing**: Run build verification and test suites
6. **Documentation**: Generate setup documentation and troubleshooting guides
7. **Notification**: Alert users when environment is ready

#### **Technology Stack Support**
- **Languages**: Python, Node.js, Java, Go, Rust, and more
- **Package Managers**: pip, npm, maven, gradle, cargo
- **Containerization**: Docker and Docker Compose setup
- **Databases**: Configuration for PostgreSQL, MySQL, Redis
- **CI/CD**: Pipeline configuration and validation

### Usage Examples

#### **CLI Usage**
```bash
# Setup a GitHub project
raid task run setup_agent "Setup development environment for: https://github.com/user/project-name"

# Using Control Agent (recommended)
raid control process "Clone and setup the React project at github.com/facebook/react for development"
```

#### **Programmatic Usage**
```python
await dispatch_to_sub_agent(
    sub_agent_profile="setup_agent",
    task_prompt=\"\"\"
    Setup development environment for: https://github.com/user/project-name
    Requirements:
    - Clone repository to /workspace
    - Install all dependencies
    - Run build verification
    - Execute test suite
    - Notify when complete
    \"\"\",
    timeout=1800  # 30 minutes for complex setups
)
```

### Enhanced Security & Reliability
- **Output Management**: Large build logs automatically saved to files and analyzed with grep/tail
- **Error Recovery**: Intelligent diagnosis and fixing of common setup issues
- **Resource Monitoring**: Tracks resource usage during complex builds
- **Cross-Platform**: Works consistently across Ubuntu, macOS, and Windows containers
- **Persistent Storage**: Maintains setup state across container restarts

## Advanced Features

### Dynamic Specialized Agents

The Control Agent can automatically create specialized Sub-Agents based on task requirements:

- **Financial Analyst**: Financial calculations, ROI analysis, market research
- **Data Analyst**: Statistical analysis, data visualization, trend identification  
- **Research Analyst**: Web research, information synthesis, evidence-based analysis
- **Problem Solver**: Systematic problem decomposition, multi-tool integration
- **Quality Analyst**: Validation, quality assurance, accuracy verification

**Enhanced Capabilities**: All dynamic roles now include advanced tools for comprehensive analysis.

**Example:**
```python
# Control Agent automatically creates a financial analyst with web search and Python
task = "Research current mortgage rates and calculate payments for $400,000 loan"
result = await control_agent.process_task(task)
```

### Collaborative Sub-Agent Groups

**Revolutionary Feature**: The Control Agent can create groups of Sub-Agents that collaborate directly with each other through secure, restricted communication channels.

#### How It Works

1. **Control Agent Assessment**: Determines if a task requires multiple agents
2. **Group Creation**: Creates a collaboration group with specific roles
3. **Secure Communication**: Agents communicate through validated message schemas
4. **Tool Coordination**: Agents share results from web searches, calculations, and analyses
5. **Result Aggregation**: Control Agent synthesizes collaborative results

#### Collaboration Types

**Data Sharing**
- Agents share calculation results, research findings, and intermediate data
- Use case: Complex financial analysis requiring web research and calculations
- Restrictions: 20 messages/minute, 45-minute timeout

**Validation Chain**
- Sequential validation of results by different specialist agents
- Use case: Multi-step verification of research and calculations
- Restrictions: 15 messages/minute, 30-minute timeout

**Parallel Analysis**
- Multiple agents analyze different aspects simultaneously
- Use case: Comprehensive research from multiple perspectives with tool integration
- Restrictions: 25 messages/minute, 60-minute timeout

**Sequential Workflow**
- Step-by-step processing where each agent builds on previous work
- Use case: Complex multi-stage problem solving with different tools
- Restrictions: 10 messages/minute, 90-minute timeout

#### Security & Restrictions

🔒 **Security-First Design**
- **Predefined Groups Only**: Collaboration only within Control Agent-created groups
- **Message Schema Validation**: Strict formats for all inter-agent communication
- **Rate Limiting**: Configurable maximum messages per minute per agent
- **Data Key Whitelisting**: Optional restriction of shareable data types
- **Message Expiration**: Automatic cleanup of expired messages
- **Isolated Channels**: Each group has its own Redis communication channel
- **No Cross-Group Communication**: Agents can't communicate outside their group

**Message Types** (Restricted Format):
- `DATA_SHARE`: Share computed results, research findings, file contents
- `REQUEST_DATA`: Request specific data from another agent
- `STATUS_UPDATE`: Progress updates and tool execution status
- `COORDINATION`: Coordinate next steps and tool usage
- `VALIDATION`: Request result validation and verification
- `ERROR_REPORT`: Report issues or tool execution errors

#### Collaboration Examples

**Example 1: Comprehensive Business Analysis**
```python
task = """
I need a comprehensive market analysis for launching a SaaS product:
- Research current SaaS market trends and pricing
- Calculate financial projections for different pricing models
- Analyze competitor pricing and features
- Create financial models with Python
- Validate calculations and provide recommendations

Use multiple agents to collaborate on research, analysis, and validation.
"""
result = await control_agent.process_task(task)
```

**Example 2: Data Science Project**
```python
task = """
Analyze customer churn data and create predictive model:
- Search for latest churn analysis techniques
- Process and analyze the dataset with Python
- Create visualizations and statistical models
- Validate model accuracy and interpret results
- Generate comprehensive report with findings

Collaborate between research, data analysis, and quality assurance agents.
"""
result = await control_agent.process_task(task)
```

**Example 3: Research Report Generation**
```python
task = """
Create comprehensive report on renewable energy investment opportunities:
- Research current renewable energy market trends
- Analyze investment data and calculate ROI scenarios
- Find latest policy changes and incentives
- Create financial projections and risk assessments
- Compile findings into structured report file

Use collaborative agents for research, analysis, and validation.
"""
result = await control_agent.process_task(task)
```

## Usage Examples

### Basic Task Execution

```python
import asyncio
from raid.config.settings import RaidConfig
from raid.control_agent.agent import ControlAgent

async def main():
    config = RaidConfig.from_env()
    control_agent = ControlAgent(config)
    
    result = await control_agent.process_task(
        "Research current AI development trends and create a summary with key statistics"
    )
    print(result)

asyncio.run(main())
```

### Advanced Multi-Tool Task

```python
async def advanced_analysis():
    config = RaidConfig.from_env()
    control_agent = ControlAgent(config)
    
    task = """
    I need comprehensive analysis for a tech startup investment decision:
    
    1. Research current AI/ML startup funding trends
    2. Calculate investment scenarios for $2M funding
    3. Analyze market size and growth projections
    4. Create financial models with Python
    5. Generate risk assessment report
    6. Save all analysis to structured files
    
    Use web search for current data, Python for calculations,
    and file operations for deliverables.
    """
    
    result = await control_agent.process_task(task)
    print(result)

asyncio.run(advanced_analysis())
```

### Collaborative Multi-Agent Task

```python
async def collaborative_research():
    config = RaidConfig.from_env()
    control_agent = ControlAgent(config)
    
    # Control Agent will automatically create collaborative group if needed
    task = """
    Comprehensive climate change investment analysis:
    
    Research Requirements:
    - Current climate tech investment trends
    - Carbon credit market analysis  
    - Renewable energy ROI calculations
    - Policy impact assessments
    
    Analysis Requirements:
    - Financial modeling with Python
    - Risk-return calculations
    - Market size estimations
    - Create investment recommendation report
    
    Please create a team of specialized agents to collaborate on
    research, financial analysis, and validation of findings.
    """
    
    result = await control_agent.process_task(task)
    print(result)

asyncio.run(collaborative_research())
```

### Meta-Tools Available to Control Agent

1. **`discover_sub_agent_profiles`** - List available Sub-Agent profiles
2. **`dispatch_to_sub_agent`** - Send tasks to specific Sub-Agents
3. **`create_specialized_sub_agent`** - Create dynamic specialized Sub-Agents
4. **`create_collaborative_sub_agent_group`** - Create groups of Sub-Agents that can collaborate directly
5. **`conclude_task_success`** - Mark tasks as completed successfully
6. **`conclude_task_failure`** - Mark tasks as failed

## Project Structure

```
Raid/
├── src/raid/
│   ├── config/              # Configuration management
│   │   ├── settings.py      # Global settings
│   │   ├── sub_agent_config.py  # Sub-Agent profiles
│   │   ├── dynamic_subagent.py  # Dynamic agent creation
│   │   └── collaboration.py # Collaboration framework
│   ├── control_agent/       # Control Agent implementation
│   │   ├── agent.py         # Main Control Agent class
│   │   ├── react_engine.py  # ReAct reasoning engine
│   │   └── meta_tools.py    # Meta-tools for orchestration
│   ├── sub_agent/          # Sub-Agent implementation
│   │   ├── agent.py        # Sub-Agent class with collaboration
│   │   └── main.py         # Sub-Agent entry point
│   ├── tools/              # Advanced tool implementations
│   │   ├── base.py         # Tool base classes
│   │   ├── calculator.py   # Mathematical calculations
│   │   ├── websearch.py    # Web search capabilities
│   │   ├── python_executor.py  # Python code execution
│   │   ├── file_operations.py  # File management
│   │   └── bash_executor.py    # Bash command execution
│   ├── docker_orchestrator/ # Container management
│   ├── message_queue/      # Redis-based messaging + pub/sub
│   └── llm_backend/        # LLM abstraction layer
├── profiles/               # Sub-Agent YAML profiles
│   ├── calculator_agent.yaml    # Basic calculator agent
│   ├── advanced_agent.yaml      # Full-featured agent
│   ├── research_agent.yaml      # Research-focused agent
│   └── developer_agent.yaml     # Development-focused agent
├── scripts/               # Test and utility scripts
│   ├── test_sub_agent.py
│   ├── test_control_agent.py
│   ├── test_dynamic_subagent_creation.py
│   ├── test_collaborative_subagents.py
│   └── test_advanced_tools.py
└── CLAUDE.md              # Claude Code instructions
```

## Development

### Adding New Tools

1. Create tool class inheriting from `BaseTool`
2. Implement required methods (`name`, `description`, `parameters`, `execute`)
3. Add security validations and restrictions
4. Register in Sub-Agent tool registry
5. Add to Sub-Agent profile configurations
6. Test with security constraints

### Creating Custom Sub-Agent Profiles

1. Create YAML file in `profiles/` directory
2. Define capabilities, tools, and system prompt
3. Configure Docker environment if needed
4. Specify tool combinations for specialization
5. Test with Sub-Agent scripts

### Extending Meta-Tools

1. Create class inheriting from `MetaTool`
2. Implement required methods and parameters
3. Register in `MetaToolRegistry`
4. Add to Control Agent capabilities

### Adding Collaboration Types

1. Define new collaboration restrictions in `collaboration.py`
2. Add message type validation
3. Update `CreateCollaborativeSubAgentGroupTool`
4. Test with new collaboration scenarios

## Performance & Scaling

- **Concurrent Processing**: Multiple Sub-Agents can process tasks simultaneously
- **Collaborative Efficiency**: Sub-Agents can share intermediate results to avoid duplicate work
- **Advanced Tool Integration**: Seamless coordination between web search, code execution, and file operations
- **Resource Limits**: Configurable limits prevent resource exhaustion
- **Container Reuse**: Intelligent container lifecycle management
- **Async Architecture**: Non-blocking operations throughout the system
- **Message Optimization**: Efficient Redis pub/sub for collaboration
- **Automatic Cleanup**: Expired messages and inactive groups are automatically removed
- **Tool Caching**: Intelligent caching of search results and computation outputs

## Security Considerations

### Advanced Tool Security
- **Sandboxed Execution**: All code execution in isolated environments
- **Input Validation**: Comprehensive validation of all tool inputs
- **Output Sanitization**: Safe handling of tool outputs and results
- **Resource Limits**: Memory, CPU, and execution time constraints
- **Network Restrictions**: Limited and controlled internet access

### Collaboration Security
- **No Unauthorized Communication**: Sub-Agents can only communicate within predefined groups
- **Message Validation**: All inter-agent messages must conform to strict schemas
- **Rate Limiting**: Prevents message flooding and resource abuse
- **Data Sanitization**: Optional whitelisting of shareable data keys
- **Isolation**: Each collaboration group operates in complete isolation
- **Audit Trail**: All collaboration messages are logged and tracked

### Container Security
- **Process Isolation**: Each Sub-Agent runs in its own Docker container
- **Network Isolation**: Containers have limited network access
- **Resource Limits**: CPU and memory constraints prevent resource exhaustion
- **File System Restrictions**: Limited access to host file system

## Use Cases

### Individual Sub-Agent Tasks
- **Research & Analysis**: Web research with data validation
- **Financial Modeling**: Complex calculations with market research
- **Data Science**: Statistical analysis with visualization
- **Software Development**: Code generation with testing and validation
- **Content Creation**: Research-backed content with fact-checking

### Collaborative Multi-Agent Tasks
- **Market Research**: Multiple agents handling different aspects (trends, competitors, financial analysis)
- **Investment Analysis**: Collaborative financial modeling with risk assessment and validation
- **Product Development**: Research, technical analysis, and market validation by specialized agents
- **Academic Research**: Literature review, data analysis, and peer validation
- **Business Intelligence**: Multi-source data gathering, analysis, and strategic recommendations

### Advanced Integration Scenarios
- **Automated Reporting**: Web research, data analysis, and document generation
- **Due Diligence**: Comprehensive company analysis with financial modeling
- **Scientific Analysis**: Literature research, data processing, and statistical validation
- **Competitive Intelligence**: Market research, competitor analysis, and strategic planning
- **Risk Assessment**: Multi-factor analysis with scenario modeling and validation

## Getting Started Examples

### 1. Simple Research Task
```bash
# Test basic web search and analysis
python -c "
import asyncio
from src.raid.config.settings import RaidConfig
from src.raid.control_agent.agent import ControlAgent

async def main():
    config = RaidConfig.from_env()
    agent = ControlAgent(config)
    result = await agent.process_task('Research the latest developments in quantum computing and summarize key breakthroughs')
    print(result)

asyncio.run(main())
"
```

### 2. Data Analysis Task
```bash
# Test Python code execution with file operations
python -c "
import asyncio
from src.raid.config.settings import RaidConfig
from src.raid.control_agent.agent import ControlAgent

async def main():
    config = RaidConfig.from_env()
    agent = ControlAgent(config)
    result = await agent.process_task('Create a Python script to analyze sales data, generate statistics, and save results to a CSV file')
    print(result)

asyncio.run(main())
"
```

### 3. Collaborative Analysis
```bash
# Test multi-agent collaboration
python -c "
import asyncio
from src.raid.config.settings import RaidConfig
from src.raid.control_agent.agent import ControlAgent

async def main():
    config = RaidConfig.from_env()
    agent = ControlAgent(config)
    result = await agent.process_task('Analyze the investment potential of renewable energy stocks: research market trends, calculate financial metrics, and validate findings with multiple specialized agents')
    print(result)

asyncio.run(main())
"
```

## License

[License information]

## Contributing

[Contributing guidelines]

---

**Project Raid** - Intelligent Multi-Agent Orchestration for Complex Problem Solving

*Featuring revolutionary collaborative agent capabilities with enterprise-grade security, advanced tool integration, and real-world problem-solving capabilities.*
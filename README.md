# Project Raid 🚀

A sophisticated multi-agent LLM orchestration system that enables intelligent task distribution and collaborative problem-solving through specialized AI agents.

## Overview

Project Raid implements a hierarchical multi-agent architecture where a **Control Agent** orchestrates multiple **Sub-Agents** to solve complex tasks through intelligent decomposition and delegation. The system supports both individual and collaborative agent execution with role-based specialization and secure inter-agent communication.

## Architecture

### Core Components

- **Control Agent**: Master orchestrator using ReAct (Reasoning-Action-Observation) cycles
- **Sub-Agents**: Specialized workers with domain-specific capabilities  
- **Docker Orchestrator**: Container lifecycle management for Sub-Agents
- **Message Queue**: Redis-based communication system with pub/sub for collaboration
- **LLM Backend**: Abstracted interface supporting OpenAI and Ollama
- **Dynamic Agent Manager**: Runtime creation of specialized Sub-Agents
- **Collaboration System**: Secure direct communication between Sub-Agent groups

### Key Features

- 🧠 **Intelligent Task Orchestration**: Control Agent uses ReAct cycles to plan and execute complex workflows
- 🔧 **Dynamic Specialization**: Create Sub-Agents with specific roles (financial analyst, data analyst, etc.)
- 🤝 **Collaborative Agent Groups**: Sub-Agents can work together with predefined, restricted communication
- 🐳 **Containerized Execution**: Isolated Sub-Agent environments using Docker
- 🔄 **Async Message Queues**: Reliable Redis-based communication with pub/sub support
- 🎯 **Configurable Limits**: Control resource usage with agent and collaboration limits
- 🛠️ **Extensible Tools**: Plugin-based tool system for Sub-Agents
- 🔒 **Security-First Design**: Strict collaboration restrictions and message validation

## Quick Start

### Prerequisites

- Python 3.9+
- Docker & Docker Compose
- Redis server
- OpenAI API key OR Ollama installation

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Raid
   ```

2. **Install dependencies**
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

### Basic Usage

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

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RAID_LLM_PROVIDER` | LLM provider (openai/ollama) | openai |
| `OPENAI_API_KEY_N0MAIL` | OpenAI API key | - |
| `RAID_OPENAI_MODEL` | OpenAI model | gpt-4o |
| `RAID_OLLAMA_URL` | Ollama server URL | http://localhost:11434 |
| `RAID_OLLAMA_MODEL` | Ollama model | qwen3:30b |
| `RAID_REDIS_HOST` | Redis host | localhost |
| `RAID_REDIS_PORT` | Redis port | 6379 |
| `RAID_MAX_DYNAMIC_SUB_AGENTS` | Max dynamic agents | 5 |

### Sub-Agent Profiles

Sub-Agents are configured using YAML profiles in the `profiles/` directory:

```yaml
name: calculator_agent
description: Sub-Agent specialized in mathematical calculations
version: "1.0"
llm_config:
  provider: openai
  model: gpt-4o
  max_tokens: 1000
  temperature: 0.3
tools:
  - calculator
system_prompt: |
  You are a calculator Sub-Agent specialized in mathematical operations...
docker_config:
  base_image: python:3.9-slim
  working_dir: /app
```

## Advanced Features

### Dynamic Specialized Agents

The Control Agent can automatically create specialized Sub-Agents based on task requirements:

- **Financial Analyst**: Financial calculations, ROI analysis, cost-benefit analysis
- **Data Analyst**: Statistical analysis, trend identification, data processing  
- **Research Analyst**: Information synthesis, evidence-based analysis
- **Problem Solver**: Systematic problem decomposition and solution generation
- **Quality Analyst**: Validation, quality assurance, accuracy verification

**Example:**
```python
# Control Agent automatically creates a financial analyst for this task
task = "Calculate ROI for $50,000 investment with $8,000 monthly revenue increase"
result = await control_agent.process_task(task)
```

### Collaborative Sub-Agent Groups

**Revolutionary Feature**: The Control Agent can create groups of Sub-Agents that collaborate directly with each other through secure, restricted communication channels.

#### How It Works

1. **Control Agent Assessment**: Determines if a task requires multiple agents
2. **Group Creation**: Creates a collaboration group with specific roles
3. **Secure Communication**: Agents communicate through validated message schemas
4. **Result Aggregation**: Control Agent synthesizes collaborative results

#### Collaboration Types

**Data Sharing**
- Agents share calculation results and intermediate data
- Use case: Complex financial analysis requiring multiple calculations
- Restrictions: 20 messages/minute, 45-minute timeout

**Validation Chain**
- Sequential validation of results by different specialist agents
- Use case: Multi-step verification of critical calculations
- Restrictions: 15 messages/minute, 30-minute timeout

**Parallel Analysis**
- Multiple agents analyze different aspects simultaneously
- Use case: Comprehensive data analysis from multiple perspectives
- Restrictions: 25 messages/minute, 60-minute timeout

**Sequential Workflow**
- Step-by-step processing where each agent builds on previous work
- Use case: Complex multi-stage problem solving
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
- `DATA_SHARE`: Share computed results
- `REQUEST_DATA`: Request specific data from another agent
- `STATUS_UPDATE`: Progress updates
- `COORDINATION`: Coordinate next steps
- `VALIDATION`: Request result validation
- `ERROR_REPORT`: Report issues or errors

#### Collaboration Examples

**Example 1: Financial Analysis Team**
```python
task = """
I need comprehensive financial analysis for a business expansion:
- Initial investment: $75,000
- Monthly revenue increase: $12,000  
- Monthly cost increase: $4,500
- Duration: 3 years

Please create a team of agents to:
1. Calculate financial metrics (ROI, payback period, NPV)
2. Validate all calculations  
3. Provide risk assessment
"""
result = await control_agent.process_task(task)
```

**Example 2: Data Validation Chain**
```python
task = """
Analyze quarterly sales data with validation:
Q1: [85k, 92k, 88k, 95k], Q2: [98k, 105k, 102k, 110k]

Create agents to:
1. Calculate statistical measures
2. Validate calculations 
3. Identify trends and provide insights
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
        "Calculate the compound interest on $10,000 at 5% annually for 10 years"
    )
    print(result)

asyncio.run(main())
```

### Collaborative Multi-Agent Task

```python
async def collaborative_analysis():
    config = RaidConfig.from_env()
    control_agent = ControlAgent(config)
    
    # Control Agent will automatically create collaborative group if needed
    task = """
    I need a comprehensive business analysis requiring multiple specialists:
    
    Revenue data: [120k, 135k, 150k, 165k] (quarterly)
    Costs: [80k, 85k, 90k, 95k] (quarterly)
    Investment options: Project A ($200k), Project B ($150k)
    
    Please analyze growth trends, calculate ROI for both projects, 
    and provide validated recommendations.
    """
    
    result = await control_agent.process_task(task)
    print(result)

asyncio.run(collaborative_analysis())
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
│   ├── docker_orchestrator/ # Container management
│   ├── message_queue/      # Redis-based messaging + pub/sub
│   ├── llm_backend/        # LLM abstraction layer
│   └── tools/              # Tool implementations
├── profiles/               # Sub-Agent YAML profiles
├── scripts/               # Test and utility scripts
│   ├── test_sub_agent.py
│   ├── test_control_agent.py
│   ├── test_dynamic_subagent_creation.py
│   └── test_collaborative_subagents.py
└── CLAUDE.md              # Claude Code instructions
```

## Development

### Adding New Tools

1. Create tool class inheriting from `BaseTool`
2. Implement required methods (`name`, `description`, `parameters`, `execute`)
3. Register in tool registry
4. Add to Sub-Agent profile configuration

### Creating Custom Sub-Agent Profiles

1. Create YAML file in `profiles/` directory
2. Define capabilities, tools, and system prompt
3. Configure Docker environment if needed
4. Test with Sub-Agent scripts

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
- **Resource Limits**: Configurable limits prevent resource exhaustion
- **Container Reuse**: Intelligent container lifecycle management
- **Async Architecture**: Non-blocking operations throughout the system
- **Message Optimization**: Efficient Redis pub/sub for collaboration
- **Automatic Cleanup**: Expired messages and inactive groups are automatically removed

## Security Considerations

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

## Use Cases

### Individual Sub-Agent Tasks
- Mathematical calculations
- Data analysis and statistics
- Financial modeling
- Quality validation
- Research and information synthesis

### Collaborative Multi-Agent Tasks
- **Complex Financial Analysis**: Multiple agents handle different aspects (calculations, validation, risk assessment)
- **Data Science Workflows**: Data processing, analysis, and validation by specialized agents
- **Multi-Step Problem Solving**: Sequential workflows where each agent builds on previous results
- **Quality Assurance**: Parallel validation of results by multiple specialist agents
- **Research Projects**: Collaborative information gathering, analysis, and synthesis

## License

[License information]

## Contributing

[Contributing guidelines]

---

**Project Raid** - Intelligent Multi-Agent Orchestration for Complex Problem Solving

*Featuring revolutionary collaborative agent capabilities with enterprise-grade security and control.*
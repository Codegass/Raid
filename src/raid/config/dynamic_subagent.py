"""Dynamic Sub-Agent creation and role-based templates"""

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from .sub_agent_config import SubAgentProfile, DockerConfig


class SubAgentRole:
    """Defines a role template for dynamic Sub-Agent creation"""
    
    def __init__(
        self,
        role_name: str,
        description: str,
        tools: List[str],
        system_prompt_template: str,
        specialization: str
    ):
        self.role_name = role_name
        self.description = description
        self.tools = tools
        self.system_prompt_template = system_prompt_template
        self.specialization = specialization
    
    def create_profile(
        self, 
        task_description: str,
        llm_config: Dict[str, Any],
        instance_id: Optional[str] = None
    ) -> SubAgentProfile:
        """Create a Sub-Agent profile for this role"""
        
        if not instance_id:
            instance_id = str(uuid.uuid4())[:8]
        
        profile_name = f"dynamic_{self.role_name}_{instance_id}"
        
        # Customize system prompt with task-specific information
        system_prompt = self.system_prompt_template.format(
            task_description=task_description,
            specialization=self.specialization
        )
        
        return SubAgentProfile(
            name=profile_name,
            description=f"{self.description} (Created for: {task_description})",
            version="dynamic-1.0",
            llm_config=llm_config,
            tools=self.tools,
            system_prompt=system_prompt,
            docker_config=DockerConfig(
                base_image="python:3.9-slim",
                working_dir="/app",
                expose_port=None
            )
        )


class RoleTemplateRegistry:
    """Registry of available role templates for dynamic Sub-Agent creation"""
    
    def __init__(self):
        self.roles: Dict[str, SubAgentRole] = {}
        self._register_default_roles()
    
    def _register_default_roles(self) -> None:
        """Register default role templates"""
        
        # Data Analyst Role
        self.register_role(SubAgentRole(
            role_name="data_analyst",
            description="Specialized Sub-Agent for data analysis and calculations",
            tools=["calculator"],
            system_prompt_template="""You are a specialized Data Analyst Sub-Agent focused on {specialization}.

Task Context: {task_description}

Your expertise includes:
- Statistical analysis and data interpretation
- Mathematical calculations and modeling
- Data validation and quality assessment
- Generating insights from numerical data

For the current task, apply your analytical skills to:
1. Understand the data requirements
2. Perform accurate calculations using the calculator tool
3. Validate results for correctness
4. Provide clear explanations of findings

Always use the calculator tool for any mathematical operations, even simple ones.
Provide detailed analysis and explain your reasoning.""",
            specialization="data analysis and statistical calculations"
        ))
        
        # Financial Analyst Role
        self.register_role(SubAgentRole(
            role_name="financial_analyst",
            description="Specialized Sub-Agent for financial calculations and analysis",
            tools=["calculator"],
            system_prompt_template="""You are a specialized Financial Analyst Sub-Agent focused on {specialization}.

Task Context: {task_description}

Your expertise includes:
- Financial modeling and calculations
- Cost-benefit analysis
- ROI and profitability assessments
- Budget analysis and forecasting
- Tax and discount calculations

For the current task, apply your financial expertise to:
1. Understand the financial context and requirements
2. Perform accurate financial calculations using the calculator tool
3. Consider relevant financial principles (time value of money, compound interest, etc.)
4. Provide business-relevant insights and recommendations

Always use the calculator tool for any mathematical operations.
Present results in clear financial terms with appropriate context.""",
            specialization="financial analysis and monetary calculations"
        ))
        
        # Research Analyst Role
        self.register_role(SubAgentRole(
            role_name="research_analyst",
            description="Specialized Sub-Agent for research and information analysis",
            tools=["calculator"],
            system_prompt_template="""You are a specialized Research Analyst Sub-Agent focused on {specialization}.

Task Context: {task_description}

Your expertise includes:
- Research methodology and analysis
- Data synthesis and interpretation
- Quantitative and qualitative analysis
- Trend identification and pattern recognition
- Evidence-based reasoning

For the current task, apply your research skills to:
1. Analyze the information requirements systematically
2. Use the calculator tool for any quantitative analysis needed
3. Synthesize findings into coherent insights
4. Provide evidence-based conclusions

Always use the calculator tool for numerical analysis.
Structure your findings clearly with supporting evidence.""",
            specialization="research and analytical investigations"
        ))
        
        # Problem Solver Role
        self.register_role(SubAgentRole(
            role_name="problem_solver",
            description="Specialized Sub-Agent for general problem-solving tasks",
            tools=["calculator"],
            system_prompt_template="""You are a specialized Problem Solver Sub-Agent focused on {specialization}.

Task Context: {task_description}

Your expertise includes:
- Systematic problem decomposition
- Logical reasoning and analysis
- Solution generation and evaluation
- Root cause analysis
- Step-by-step problem resolution

For the current task, apply your problem-solving methodology:
1. Break down the problem into manageable components
2. Use the calculator tool for any computational elements
3. Apply logical reasoning to find optimal solutions
4. Verify solutions for completeness and accuracy

Always use the calculator tool for mathematical operations.
Provide clear, step-by-step solutions with reasoning.""",
            specialization="systematic problem-solving and logical analysis"
        ))
        
        # Quality Analyst Role  
        self.register_role(SubAgentRole(
            role_name="quality_analyst",
            description="Specialized Sub-Agent for quality assurance and validation",
            tools=["calculator"],
            system_prompt_template="""You are a specialized Quality Analyst Sub-Agent focused on {specialization}.

Task Context: {task_description}

Your expertise includes:
- Quality control and assurance processes
- Validation and verification methods
- Error detection and correction
- Accuracy assessment and improvement
- Standard compliance checking

For the current task, apply your quality assurance skills to:
1. Validate the accuracy of all inputs and requirements
2. Use the calculator tool to verify any calculations
3. Check for errors, inconsistencies, or edge cases
4. Ensure outputs meet quality standards

Always use the calculator tool for verification calculations.
Provide thorough quality assessments with detailed validation.""",
            specialization="quality assurance and validation processes"
        ))
    
    def register_role(self, role: SubAgentRole) -> None:
        """Register a role template"""
        self.roles[role.role_name] = role
    
    def get_role(self, role_name: str) -> SubAgentRole:
        """Get a role template by name"""
        if role_name not in self.roles:
            raise ValueError(f"Role '{role_name}' not found")
        return self.roles[role_name]
    
    def get_available_roles(self) -> Dict[str, str]:
        """Get list of available roles with descriptions"""
        return {
            name: role.description 
            for name, role in self.roles.items()
        }
    
    def suggest_role_for_task(self, task_description: str) -> str:
        """Suggest the best role for a given task description"""
        task_lower = task_description.lower()
        
        # Simple keyword-based role suggestion
        if any(word in task_lower for word in ["financial", "money", "cost", "price", "budget", "profit", "discount"]):
            return "financial_analyst"
        elif any(word in task_lower for word in ["data", "statistics", "analysis", "trend", "pattern"]):
            return "data_analyst"
        elif any(word in task_lower for word in ["research", "investigate", "study", "explore"]):
            return "research_analyst"
        elif any(word in task_lower for word in ["quality", "verify", "validate", "check", "accurate"]):
            return "quality_analyst"
        else:
            return "problem_solver"  # Default role


class DynamicSubAgentManager:
    """Manages dynamic Sub-Agent creation and lifecycle"""
    
    def __init__(self, max_agents: int = 5):
        self.max_agents = max_agents
        self.active_agents: Dict[str, Dict[str, Any]] = {}  # profile_name -> metadata
        self.role_registry = RoleTemplateRegistry()
    
    def can_create_agent(self) -> bool:
        """Check if we can create a new dynamic agent"""
        return len(self.active_agents) < self.max_agents
    
    def create_dynamic_agent(
        self,
        task_description: str,
        role_name: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None
    ) -> SubAgentProfile:
        """Create a new dynamic Sub-Agent"""
        
        if not self.can_create_agent():
            raise RuntimeError(f"Maximum number of dynamic Sub-Agents ({self.max_agents}) reached")
        
        # Suggest role if not provided
        if not role_name:
            role_name = self.role_registry.suggest_role_for_task(task_description)
        
        # Get role template
        role = self.role_registry.get_role(role_name)
        
        # Use default LLM config if not provided
        if not llm_config:
            llm_config = {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "max_tokens": 1000,
                "temperature": 0.3
            }
        
        # Create profile
        profile = role.create_profile(task_description, llm_config)
        
        # Track the agent
        self.active_agents[profile.name] = {
            "role": role_name,
            "task_description": task_description,
            "created_at": datetime.utcnow(),
            "profile": profile
        }
        
        return profile
    
    def remove_dynamic_agent(self, profile_name: str) -> None:
        """Remove a dynamic Sub-Agent"""
        if profile_name in self.active_agents:
            del self.active_agents[profile_name]
    
    def list_active_agents(self) -> Dict[str, Dict[str, Any]]:
        """List all active dynamic agents"""
        return self.active_agents.copy()
    
    def cleanup_old_agents(self, max_age_hours: int = 24) -> List[str]:
        """Clean up agents older than specified hours"""
        now = datetime.utcnow()
        to_remove = []
        
        for profile_name, metadata in self.active_agents.items():
            age = now - metadata["created_at"]
            if age.total_seconds() > (max_age_hours * 3600):
                to_remove.append(profile_name)
        
        for profile_name in to_remove:
            self.remove_dynamic_agent(profile_name)
        
        return to_remove
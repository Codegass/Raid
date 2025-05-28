"""Base classes for Sub-Agent tools"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel


class ToolParameter(BaseModel):
    """Parameter definition for a tool"""
    name: str
    type: str
    description: str
    required: bool = True


class ToolDefinition(BaseModel):
    """Tool definition for LLM function calling"""
    name: str
    description: str
    parameters: List[ToolParameter]


class Tool(ABC):
    """Abstract base class for Sub-Agent tools"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """Tool parameters"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """Execute the tool with given parameters"""
        pass
    
    def get_definition(self) -> ToolDefinition:
        """Get tool definition for LLM function calling"""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters
        )


class ToolRegistry:
    """Registry for managing available tools"""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:
        """Register a tool"""
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Tool:
        """Get a tool by name"""
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found")
        return self._tools[name]
    
    def get_all_tools(self) -> Dict[str, Tool]:
        """Get all registered tools"""
        return self._tools.copy()
    
    def get_tool_definitions(self) -> List[ToolDefinition]:
        """Get definitions for all tools"""
        return [tool.get_definition() for tool in self._tools.values()]
    
    def list_tool_names(self) -> List[str]:
        """List all tool names"""
        return list(self._tools.keys())
"""Tools available to Sub-Agents"""

from .base import Tool, ToolRegistry

# Import all tool implementations
from .calculator import CalculatorTool
from .notification import NotificationUserTool
from .websearch import WebSearchTool
from .python_executor import RunPythonCodeTool
from .file_operations import CreateFileTool, ReadFileTool, ListFilesTool, DeleteFileTool
from .bash_executor import RunBashCommandTool, LimitedNetworkTool

# Auto-discovery tool mapping for dynamic registration
AVAILABLE_TOOLS = {
    "calculator": CalculatorTool,
    "notification_user": NotificationUserTool,
    "websearch": WebSearchTool,
    "run_python_code": RunPythonCodeTool,
    "create_file": CreateFileTool,
    "read_file": ReadFileTool,
    "list_files": ListFilesTool,
    "delete_file": DeleteFileTool,
    "run_bash_command": RunBashCommandTool,
    "network_request": LimitedNetworkTool,
}

def create_tool_registry(tool_names) -> ToolRegistry:
    """Create a tool registry with specified tools"""
    registry = ToolRegistry()
    
    for tool_name in tool_names:
        if tool_name in AVAILABLE_TOOLS:
            try:
                tool_instance = AVAILABLE_TOOLS[tool_name]()
                registry.register(tool_instance)
                print(f"✅ Registered tool: {tool_name}")
            except Exception as e:
                print(f"❌ Failed to register tool '{tool_name}': {e}")
        else:
            available = ", ".join(AVAILABLE_TOOLS.keys())
            print(f"⚠️ Unknown tool '{tool_name}'. Available: {available}")
    
    return registry

__all__ = [
    "Tool", 
    "ToolRegistry", 
    "AVAILABLE_TOOLS",
    "create_tool_registry",
    # Tool classes
    "CalculatorTool", 
    "NotificationUserTool", 
    "WebSearchTool",
    "RunPythonCodeTool",
    "CreateFileTool", 
    "ReadFileTool", 
    "ListFilesTool", 
    "DeleteFileTool",
    "RunBashCommandTool", 
    "LimitedNetworkTool"
]
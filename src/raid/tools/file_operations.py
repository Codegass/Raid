"""File operation tools for creating and reading files"""

import os
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from .base import Tool, ToolParameter


class CreateFileTool(Tool):
    """Tool for creating files with content"""
    
    def __init__(self):
        super().__init__()
        # Set up working directory for Sub-Agent files
        self.working_dir = Path("/tmp/raid_workspace")
        self.working_dir.mkdir(exist_ok=True)
    
    @property
    def name(self) -> str:
        return "create_file"
    
    @property
    def description(self) -> str:
        return "Create a new file with specified content. Files are created in the agent's workspace directory."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="filename",
                type="string",
                description="Name of the file to create (with extension)"
            ),
            ToolParameter(
                name="content",
                type="string",
                description="Content to write to the file"
            ),
            ToolParameter(
                name="encoding",
                type="string",
                description="File encoding (default: utf-8)"
            )
        ]
    
    async def execute(self, **kwargs) -> str:
        """Create a file with specified content"""
        filename = kwargs.get("filename", "").strip()
        content = kwargs.get("content", "")
        encoding = kwargs.get("encoding", "utf-8")
        
        if not filename:
            return "Error: Filename is required"
        
        # Security: Prevent path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            return "Error: Invalid filename. Only simple filenames are allowed (no paths)"
        
        # Security: Check file extension
        allowed_extensions = {
            '.txt', '.md', '.json', '.csv', '.py', '.js', '.html', '.css', 
            '.xml', '.yaml', '.yml', '.log', '.conf', '.ini'
        }
        
        file_ext = Path(filename).suffix.lower()
        if file_ext not in allowed_extensions:
            return f"Error: File extension '{file_ext}' not allowed. Allowed: {', '.join(allowed_extensions)}"
        
        try:
            file_path = self.working_dir / filename
            
            # Check if file already exists
            if file_path.exists():
                return f"Error: File '{filename}' already exists"
            
            # Write content to file
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            
            # Get file size
            file_size = file_path.stat().st_size
            
            return f"Successfully created file '{filename}' ({file_size} bytes) in workspace"
            
        except UnicodeEncodeError as e:
            return f"Encoding error: {str(e)}"
        except PermissionError:
            return f"Permission denied: Cannot create file '{filename}'"
        except Exception as e:
            return f"Error creating file: {str(e)}"


class ReadFileTool(Tool):
    """Tool for reading files"""
    
    def __init__(self):
        super().__init__()
        self.working_dir = Path("/tmp/raid_workspace")
        self.working_dir.mkdir(exist_ok=True)
    
    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return "Read content from a file in the agent's workspace directory."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="filename",
                type="string",
                description="Name of the file to read"
            ),
            ToolParameter(
                name="encoding",
                type="string", 
                description="File encoding (default: utf-8)"
            ),
            ToolParameter(
                name="max_lines",
                type="integer",
                description="Maximum number of lines to read (default: 1000)"
            )
        ]
    
    async def execute(self, **kwargs) -> str:
        """Read content from a file"""
        filename = kwargs.get("filename", "").strip()
        encoding = kwargs.get("encoding", "utf-8")
        max_lines = kwargs.get("max_lines", 1000)
        
        if not filename:
            return "Error: Filename is required"
        
        # Security: Prevent path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            return "Error: Invalid filename. Only simple filenames are allowed (no paths)"
        
        try:
            file_path = self.working_dir / filename
            
            # Check if file exists
            if not file_path.exists():
                return f"Error: File '{filename}' not found in workspace"
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                return f"Error: File '{filename}' is too large ({file_size} bytes). Maximum size: 10MB"
            
            # Read file content
            with open(file_path, 'r', encoding=encoding) as f:
                if max_lines:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            lines.append(f"... (truncated after {max_lines} lines)")
                            break
                        lines.append(line.rstrip('\n\r'))
                    content = '\n'.join(lines)
                else:
                    content = f.read()
            
            return f"Content of '{filename}' ({file_size} bytes):\n\n{content}"
            
        except UnicodeDecodeError as e:
            return f"Encoding error: {str(e)}. Try specifying a different encoding."
        except PermissionError:
            return f"Permission denied: Cannot read file '{filename}'"
        except Exception as e:
            return f"Error reading file: {str(e)}"


class ListFilesTool(Tool):
    """Tool for listing files in the workspace"""
    
    def __init__(self):
        super().__init__()
        self.working_dir = Path("/tmp/raid_workspace")
        self.working_dir.mkdir(exist_ok=True)
    
    @property
    def name(self) -> str:
        return "list_files"
    
    @property
    def description(self) -> str:
        return "List all files in the agent's workspace directory."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="pattern",
                type="string",
                description="Optional file pattern to filter by (e.g., '*.txt', '*.py')"
            )
        ]
    
    async def execute(self, **kwargs) -> str:
        """List files in the workspace"""
        pattern = kwargs.get("pattern", "*")
        
        try:
            if pattern == "*":
                files = list(self.working_dir.iterdir())
            else:
                files = list(self.working_dir.glob(pattern))
            
            # Filter only files (not directories)
            files = [f for f in files if f.is_file()]
            
            if not files:
                if pattern == "*":
                    return "No files found in workspace"
                else:
                    return f"No files matching pattern '{pattern}' found in workspace"
            
            # Sort files by name
            files.sort(key=lambda x: x.name)
            
            # Format file list
            file_list = []
            for file_path in files:
                stat = file_path.stat()
                size = stat.st_size
                modified = stat.st_mtime
                
                # Format size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                
                file_list.append(f"{file_path.name:<30} {size_str:>10}")
            
            header = f"Files in workspace ({len(files)} files):\n"
            header += f"{'Name':<30} {'Size':>10}\n"
            header += "-" * 42
            
            return header + "\n" + "\n".join(file_list)
            
        except Exception as e:
            return f"Error listing files: {str(e)}"


class DeleteFileTool(Tool):
    """Tool for deleting files from workspace"""
    
    def __init__(self):
        super().__init__()
        self.working_dir = Path("/tmp/raid_workspace")
        self.working_dir.mkdir(exist_ok=True)
    
    @property
    def name(self) -> str:
        return "delete_file"
    
    @property
    def description(self) -> str:
        return "Delete a file from the agent's workspace directory."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="filename",
                type="string",
                description="Name of the file to delete"
            )
        ]
    
    async def execute(self, **kwargs) -> str:
        """Delete a file from workspace"""
        filename = kwargs.get("filename", "").strip()
        
        if not filename:
            return "Error: Filename is required"
        
        # Security: Prevent path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            return "Error: Invalid filename. Only simple filenames are allowed (no paths)"
        
        try:
            file_path = self.working_dir / filename
            
            # Check if file exists
            if not file_path.exists():
                return f"Error: File '{filename}' not found in workspace"
            
            # Delete the file
            file_path.unlink()
            
            return f"Successfully deleted file '{filename}'"
            
        except PermissionError:
            return f"Permission denied: Cannot delete file '{filename}'"
        except Exception as e:
            return f"Error deleting file: {str(e)}"
"""Python code execution tool with security constraints"""

import sys
import io
import contextlib
import tempfile
import os
import subprocess
import json
import asyncio
from typing import List, Dict, Any, Optional
from .base import Tool, ToolParameter


class RunPythonCodeTool(Tool):
    """Tool for executing Python code in a controlled environment"""
    
    def __init__(self):
        super().__init__()
        # Restricted imports for security
        self.allowed_imports = {
            'math', 'random', 'datetime', 'time', 'json', 'csv', 'sqlite3',
            'statistics', 'collections', 'itertools', 'functools', 'operator',
            'decimal', 'fractions', 'uuid', 'hashlib', 'base64', 'urllib.parse',
            'pandas', 'numpy', 'matplotlib.pyplot', 'seaborn', 'plotly',
            'requests', 'beautifulsoup4', 'lxml', 'os', 'sys', 'subprocess', 'shutil'
        }
        
        # Forbidden patterns for security - much more relaxed inside a container
        self.forbidden_patterns = [
            '__import__',  # Still a good idea to restrict this
            # 'eval(', 'exec(', # Let's allow these for now, but be careful
        ]
    
    @property
    def name(self) -> str:
        return "run_python_code"
    
    @property
    def description(self) -> str:
        return "Execute Python code in a secure environment. Supports data analysis, calculations, and visualization. Some imports and operations are restricted for security."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="code",
                type="string",
                description="The Python code to execute"
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="Execution timeout in seconds (default: 30, max: 120)"
            )
        ]
    
    async def execute(self, **kwargs) -> str:
        """Execute Python code with security constraints"""
        code = kwargs.get("code", "").strip()
        timeout = min(kwargs.get("timeout", 30), 120)
        
        if not code:
            return "Error: Python code is required"
        
        # Security check
        security_check = self._check_security(code)
        if security_check:
            return f"Security Error: {security_check}"
        
        try:
            # For containerized agents, we can execute with less isolation
            # as the container itself is the sandbox.
            # Using subprocess to run the code in a separate process.
            result = await self._execute_in_subprocess(code, timeout)
            return result
            
        except Exception as e:
            return f"Execution Error: {str(e)}"
    
    def _check_security(self, code: str) -> Optional[str]:
        """
        Check code for security violations.
        Since this runs inside a container, we can be more permissive.
        """
        code_lower = code.lower()
        
        # We still might want to prevent some truly dangerous operations
        # For now, let's keep it simple.
        if '__import__' in code_lower:
            return "Forbidden operation detected: __import__"
        
        return None

    async def _execute_in_subprocess(self, code: str, timeout: int) -> str:
        """Execute Python code in a separate process for isolation."""
        # Create a temporary file to write the code to
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.py', delete=False) as tmp_file:
            tmp_file.write(code)
            script_path = tmp_file.name

        try:
            # Execute the script using the same python interpreter
            process = await asyncio.create_subprocess_exec(
                sys.executable, script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for the process to complete with a timeout
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

            # Format the output
            output = ""
            if stdout:
                output += f"Output:\n{stdout.decode('utf-8').strip()}\n"
            if stderr:
                output += f"Errors:\n{stderr.decode('utf-8').strip()}\n"

            return output.strip() if output else "Code executed successfully with no output."

        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return f"Execution Error: Code execution timed out after {timeout} seconds."
        except Exception as e:
            return f"Execution Error: {str(e)}"
        finally:
            # Clean up the temporary file
            if os.path.exists(script_path):
                os.remove(script_path)

    async def _execute_code_isolated(self, code: str, timeout: int) -> str:
        """Execute code in an isolated environment"""
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # Create a restricted global environment
        restricted_globals = {
            '__builtins__': {
                'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
                'chr': chr, 'dict': dict, 'enumerate': enumerate, 'filter': filter,
                'float': float, 'format': format, 'frozenset': frozenset,
                'hex': hex, 'int': int, 'isinstance': isinstance, 'len': len,
                'list': list, 'map': map, 'max': max, 'min': min, 'oct': oct,
                'ord': ord, 'pow': pow, 'print': print, 'range': range,
                'reversed': reversed, 'round': round, 'set': set, 'slice': slice,
                'sorted': sorted, 'str': str, 'sum': sum, 'tuple': tuple,
                'type': type, 'zip': zip
            }
        }
        
        # Add safe imports
        import_code = """
import math
import random
import datetime
import time
import json
import statistics
import collections
import itertools
import functools
import operator
import decimal
import fractions
import uuid
import hashlib
import base64
try:
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    plt.ioff()  # Turn off interactive mode
except ImportError:
    pass
"""
        
        full_code = import_code + "\n" + code
        
        try:
            # Redirect stdout and stderr
            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):
                
                # Execute the code
                exec(full_code, restricted_globals)
            
            # Get output
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()
            
            # Format result
            result_parts = []
            
            if stdout_output.strip():
                result_parts.append(f"Output:\n{stdout_output.strip()}")
            
            if stderr_output.strip():
                result_parts.append(f"Warnings/Errors:\n{stderr_output.strip()}")
            
            if not result_parts:
                result_parts.append("Code executed successfully (no output)")
            
            return "\n\n".join(result_parts)
            
        except SyntaxError as e:
            return f"Syntax Error: {str(e)}"
        except NameError as e:
            return f"Name Error: {str(e)} (Note: Some imports may be restricted)"
        except ImportError as e:
            return f"Import Error: {str(e)} (Note: Some imports are restricted for security)"
        except TimeoutError:
            return f"Execution timed out after {timeout} seconds"
        except Exception as e:
            return f"Runtime Error: {str(e)}"
        finally:
            stdout_capture.close()
            stderr_capture.close()


class SafePythonExecutor:
    """Alternative Python executor using subprocess for better isolation"""
    
    @staticmethod
    async def execute_in_subprocess(code: str, timeout: int = 30) -> str:
        """Execute Python code in a subprocess for better security"""
        try:
            # Create a temporary file with the code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                # Add safety imports and restrictions
                safe_code = f"""
import sys
import signal

# Set up timeout handler
def timeout_handler(signum, frame):
    raise TimeoutError("Code execution timed out")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm({timeout})

try:
    # Restrict imports
    import builtins
    original_import = builtins.__import__
    
    def restricted_import(name, *args, **kwargs):
        allowed = {{'math', 'random', 'datetime', 'time', 'json', 'statistics', 
                  'collections', 'itertools', 'functools', 'operator', 'decimal', 
                  'fractions', 'uuid', 'hashlib', 'base64', 'pandas', 'numpy', 
                  'matplotlib', 'seaborn', 'plotly'}}
        
        if name.split('.')[0] not in allowed:
            raise ImportError(f"Import of '{{name}}' is not allowed")
        
        return original_import(name, *args, **kwargs)
    
    builtins.__import__ = restricted_import
    
    # User code starts here
{code}

except Exception as e:
    print(f"Error: {{e}}")
finally:
    signal.alarm(0)  # Disable the alarm
"""
                f.write(safe_code)
                temp_file = f.name
            
            # Execute the file
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout + 5,  # Add buffer for setup
                cwd='/tmp'  # Run in temporary directory
            )
            
            # Clean up
            os.unlink(temp_file)
            
            # Format output
            output_parts = []
            if result.stdout.strip():
                output_parts.append(f"Output:\n{result.stdout.strip()}")
            
            if result.stderr.strip():
                output_parts.append(f"Errors:\n{result.stderr.strip()}")
            
            if result.returncode != 0:
                output_parts.append(f"Exit code: {result.returncode}")
            
            if not output_parts:
                output_parts.append("Code executed successfully (no output)")
            
            return "\n\n".join(output_parts)
            
        except subprocess.TimeoutExpired:
            return f"Code execution timed out after {timeout} seconds"
        except Exception as e:
            return f"Execution error: {str(e)}"
"""Calculator tool for mathematical operations"""

from typing import List, Any
from .base import Tool, ToolParameter
import ast
import operator


class CalculatorTool(Tool):
    """Simple calculator tool for basic mathematical operations"""
    
    # Safe operators for calculator
    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "Perform mathematical calculations with basic arithmetic operations (+, -, *, /, **)"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="expression",
                type="string",
                description="Mathematical expression to evaluate (e.g., '2 + 3 * 4')",
                required=True
            )
        ]
    
    def _safe_eval(self, node: ast.AST) -> float:
        """Safely evaluate an AST node"""
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Num):  # Python < 3.8
            return node.n
        elif isinstance(node, ast.BinOp):
            left = self._safe_eval(node.left)
            right = self._safe_eval(node.right)
            op = self._operators.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operation: {type(node.op)}")
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._safe_eval(node.operand)
            op = self._operators.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operation: {type(node.op)}")
            return op(operand)
        else:
            raise ValueError(f"Unsupported node type: {type(node)}")
    
    async def execute(self, **kwargs: Any) -> str:
        """Execute calculator operation"""
        expression = kwargs.get("expression")
        if not expression:
            return "Error: No expression provided"
        
        try:
            # Parse the expression into an AST
            tree = ast.parse(expression, mode='eval')
            
            # Evaluate the expression safely
            result = self._safe_eval(tree.body)
            
            return f"Result: {result}"
            
        except ZeroDivisionError:
            return "Error: Division by zero"
        except ValueError as e:
            return f"Error: {str(e)}"
        except SyntaxError:
            return "Error: Invalid mathematical expression"
        except Exception as e:
            return f"Error: Failed to evaluate expression - {str(e)}"
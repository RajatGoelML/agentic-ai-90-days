# ================================
# Tool Base Contracts
# ================================

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ToolResult:
    """
    Standard output wrapper for all tool executions.

    Makes success and failure explicit — callers check result.success
    rather than inspecting raw dicts or catching exceptions.
    """
    success: bool
    data: Any = None
    error: Optional[str] = None
    source: Optional[str] = None

    def __bool__(self):
        return self.success


class BaseTool(ABC):
    """
    Abstract base class all tools must extend.

    Enforces a consistent interface: every tool has a name,
    a description, and a single run(input_data) entry point
    that returns a ToolResult.

    Example:
        class MyTool(BaseTool):
            name = "my_tool"
            description = "Does X given Y."

            def run(self, input_data: dict) -> ToolResult:
                ...
                return ToolResult(success=True, data=result, source=self.name)
    """

    name: str = "base_tool"
    description: str = "No description provided."

    @abstractmethod
    def run(self, input_data: dict) -> ToolResult:
        """Execute the tool. Must return a ToolResult."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<Tool: {self.name}>"

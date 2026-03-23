"""
MCP工具基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """MCP工具基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具

        Returns:
            工具执行结果
        """
        pass

    def get_schema(self) -> Dict[str, Any]:
        """获取工具的JSON Schema"""
        return {
            "name": self.name,
            "description": self.description
        }

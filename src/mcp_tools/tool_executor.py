"""
MCP工具执行器

统一执行各种MCP工具
"""

from typing import Dict, Any, Callable, Optional
import asyncio

from .position_eval import PositionEvalTool


class ToolExecutor:
    """MCP工具执行器

    管理并执行各种MCP工具
    """

    _instance: Optional['ToolExecutor'] = None

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self._position_eval: Optional[PositionEvalTool] = None
        self._opening_book = OpeningBookTool()
        self._register_default_tools()

    @classmethod
    def get_instance(cls) -> 'ToolExecutor':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """重置单例（用于测试）"""
        cls._instance = None

    def _register_default_tools(self):
        """注册默认工具"""
        self.register("evaluate_position", self._wrap_async(self._do_evaluate_position))
        self.register("query_opening_book", self._wrap_async(self._do_query_opening_book))
        self.register("validate_and_explain", self._wrap_async(self._do_validate_and_explain))

    def _wrap_async(self, func):
        """将同步函数包装为异步函数"""
        async def wrapper(**kwargs):
            result = func(**kwargs)
            if asyncio.iscoroutine(result):
                return await result
            return result
        return wrapper

    def register(self, name: str, func: Callable):
        """注册工具"""
        self.tools[name] = func

    def set_position_eval(self, tool: PositionEvalTool):
        """设置局面评估工具"""
        self._position_eval = tool

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }

        try:
            func = self.tools[tool_name]
            if asyncio.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _do_evaluate_position(self, fen: str, depth: int = 15) -> Dict[str, Any]:
        """执行局面评估"""
        if self._position_eval is None:
            self._position_eval = PositionEvalTool()
        return await self._position_eval.execute(fen, depth)

    async def _do_query_opening_book(self, fen: str) -> Dict[str, Any]:
        """执行开局库查询"""
        return await self._opening_book.query(fen)

    async def _do_validate_and_explain(self, fen: str, move: str) -> Dict[str, Any]:
        """执行走步验证"""
        from ..core.referee_engine import RefereeEngine
        try:
            engine = RefereeEngine(fen)
            is_valid = engine.validate_move(move)
            legal_moves = engine.get_legal_moves()

            if is_valid:
                return {
                    "success": True,
                    "fen": fen,
                    "move": move,
                    "valid": True,
                    "explanation": f"走步 {move} 是合法的"
                }
            else:
                return {
                    "success": True,
                    "fen": fen,
                    "move": move,
                    "valid": False,
                    "explanation": f"走步 {move} 是非法的。合法走步示例: {legal_moves[:5]}"
                }
        except Exception as e:
            return {
                "success": False,
                "fen": fen,
                "move": move,
                "valid": None,
                "explanation": f"FEN解析错误: {str(e)}"
            }

    def set_tool(self, name: str, func: Callable):
        """设置/替换工具"""
        self.tools[name] = func

    def get_available_tools(self) -> list:
        """获取可用工具列表"""
        return list(self.tools.keys())


class OpeningBookTool:
    """开局库工具（简化实现）"""

    # 标准初始FEN
    INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR"

    async def query(self, fen: str) -> Dict[str, Any]:
        """查询开局库

        简化实现：只检查初始局面的几个常见开局
        """
        # 提取基本FEN（只取位置部分，去除走子方和后续信息）
        base_fen = fen.split()[0] if fen else ""

        # 检查是否是初始局面
        # 非初始局面，返回空（暂不支持）
        return {
            "success": True,
            "fen": fen,
            "moves": [],
            "evaluation": "开局库暂未实现完整开局"
        }

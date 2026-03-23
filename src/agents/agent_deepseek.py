"""
DeepSeek Agent

红方对战Agent，使用DeepSeek LLM
"""

from typing import Dict, Any, TYPE_CHECKING

from .base_agent import BaseAgent, AgentConfig, AgentResult, AgentStatus

if TYPE_CHECKING:
    from ..mcp_tools.tool_executor import ToolExecutor


class DeepSeekAgent(BaseAgent):
    """Agent1: DeepSeek红方Agent"""

    async def think(self, game_state: Dict[str, Any]) -> AgentResult:
        """思考走步

        Args:
            game_state: 当前游戏状态

        Returns:
            AgentResult: 决策结果
        """
        self.status = AgentStatus.THINKING

        try:
            # 构建Prompt，传入Agent的颜色
            messages = self.prompt_builder.build_game_prompt(
                game_state,
                player_color=self.config.color
            )

            # 发送请求
            response = await self.config.llm_adapter.chat(
                messages,
                tools=self.prompt_builder.get_tools() if self.config.use_tools else None,
                tool_choice="auto"
            )

            self.last_response = response

            # 如果有工具调用，执行工具循环
            if response.has_tool_calls():
                tool_executor = self._get_tool_executor()
                return await self.execute_tool_loop(response, tool_executor, game_state)
            else:
                move = self._extract_move(
                    response.content,
                    legal_moves=game_state.get('legal_moves', [])
                )
                return AgentResult(
                    success=True,
                    move=move,
                    thought=response.content[:500] if response.content else ""
                )

        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResult(success=False, error=str(e))

        finally:
            self.status = AgentStatus.IDLE

    def _get_tool_executor(self):
        """获取工具执行器（由外部注入）"""
        from ..mcp_tools.tool_executor import ToolExecutor
        return ToolExecutor.get_instance()

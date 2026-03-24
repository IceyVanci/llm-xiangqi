"""
Referee Agent

独立裁判Agent，用于验证走步合法性和游戏结束判定
"""

from typing import Dict, Any, Tuple, Optional, TYPE_CHECKING

from .base_agent import BaseAgent, AgentConfig, AgentResult, AgentStatus
from .prompt_builder import PromptBuilder

if TYPE_CHECKING:
    from ..core.referee_engine import RefereeEngine


class RefereeAgent:
    """独立裁判Agent（MiniMax-M2.7驱动）

    职责：
    1. 验证Agent走步的合法性
    2. 判断游戏是否结束（将军/绝杀/长将/和棋）
    3. 向双方同步棋盘状态
    4. 解释违规原因
    """

    def __init__(self, config: AgentConfig, referee_engine: "RefereeEngine"):
        self.config = config
        self.llm_adapter = config.llm_adapter
        self.referee_engine = referee_engine
        self.prompt_builder = PromptBuilder(config.system_prompt)

    async def validate_and_comment(
        self, agent_name: str, move: str, fen_after: str
    ) -> Tuple[bool, Optional[str], str]:
        """验证走步并生成评注

        注意：此方法在走步应用后调用，用于生成评注和LLM辅助分析。
        基本合法性校验已由 RefereeEngine.apply_move 完成。

        Args:
            agent_name: 执行走步的Agent名称
            move: ICCS格式走步
            fen_after: 走步后的FEN

        Returns:
            (is_valid, error_message, commentary)
        """
        game_state = {
            "turn": self.referee_engine.get_current_turn(),
            "fen": fen_after,
            "proposed_move": move,
            "action": "comment",
        }

        messages = self.prompt_builder.build_validation_prompt(game_state)

        commentary = ""
        try:
            response = await self.llm_adapter.chat(messages)
            commentary = response.content[:200] if response.content else ""
        except Exception as e:
            commentary = f"(LLM评注失败: {e})"

        return True, None, commentary

    async def check_game_end(self) -> Tuple[bool, Optional[str]]:
        """检查游戏是否结束

        Returns:
            (is_ended, reason)
        """
        return self.referee_engine.check_game_end()

    async def generate_state_broadcast(
        self, turn: str, fen: str, last_move: Optional[str], last_move_by: Optional[str]
    ) -> str:
        """生成向双方广播的状态消息

        Args:
            turn: 当前回合
            fen: 当前FEN
            last_move: 上一步走步
            last_move_by: 上一步执行者

        Returns:
            广播消息文本
        """
        ascii_board = self.referee_engine.render_ascii_board(fen)

        prompt = f"""生成状态广播消息。

当前回合: {turn}
最后走步: {last_move} by {last_move_by}
FEN: {fen}

ASCII棋盘:
{ascii_board}

请用中文生成简洁的广播消息，内容包括：
1. 宣布当前轮到哪方走棋
2. 报告上一步走棋（如果有）
3. 请当前玩家走棋

保持中立和简洁。
"""
        messages = [{"role": "user", "content": prompt}]

        response = await self.llm_adapter.chat(messages)
        return response.content

    async def explain_violation(
        self, agent_name: str, move: str, fen: str, reason: str
    ) -> str:
        """解释违规原因（用于调试和日志）

        Args:
            agent_name: 违规Agent名称
            move: 违规走步
            fen: 当前FEN
            reason: 违规原因

        Returns:
            解释文本
        """
        game_state = {
            "turn": self.referee_engine.get_current_turn(),
            "fen": fen,
            "violated_move": move,
            "violation_reason": reason,
            "action": "explain",
        }

        messages = self.prompt_builder.build_explanation_prompt(game_state)

        response = await self.llm_adapter.chat(messages)
        return response.content

    async def get_game_advice(self, fen: str) -> str:
        """获取游戏建议（用于调试模式）

        Args:
            fen: 当前FEN

        Returns:
            建议文本
        """
        ascii_board = self.referee_engine.render_ascii_board(fen)

        prompt = f"""分析当前局面，给出简要建议。

FEN: {fen}

ASCII棋盘:
{ascii_board}

请分析：
1. 当前局面态势
2. 哪方占优
3. 建议的策略方向

保持简洁，100字以内。
"""
        messages = [{"role": "user", "content": prompt}]

        response = await self.llm_adapter.chat(messages)
        return response.content

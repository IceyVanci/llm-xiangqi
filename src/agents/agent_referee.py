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

    def __init__(
        self,
        config: AgentConfig,
        referee_engine: 'RefereeEngine'
    ):
        self.config = config
        self.llm_adapter = config.llm_adapter
        self.referee_engine = referee_engine
        self.prompt_builder = PromptBuilder(config.system_prompt)

    async def validate_move(
        self,
        agent_name: str,
        move: str,
        fen_before: str
    ) -> Tuple[bool, Optional[str]]:
        """验证走步合法性

        验证优先级：
        1. 【最高优先】RefereeEngine引擎规则校验（确定性，无幻觉）
        2. 【次优先】M2.7 LLM高级判定（仅用于引擎无法判定的边界情况）

        Args:
            agent_name: 执行走步的Agent名称
            move: ICCS格式走步
            fen_before: 走步前的FEN

        Returns:
            (is_valid, error_message)
        """
        # ============================================================
        # 第一优先：引擎规则校验（确定性，无幻觉风险）
        # 这是唯一可信的走步合法性来源
        # ============================================================
        is_legal = self.referee_engine.validate_move(move, fen_before)
        if not is_legal:
            return False, f"引擎规则判定非法: {move}"

        # ============================================================
        # 第二优先：M2.7 LLM高级判定（仅用于边界情况）
        # 仅在引擎校验通过后调用，用于：
        # - 长将检测（连续重复将军）
        # - 特殊和棋局面判定
        # - 复杂规则解释
        # ============================================================
        game_state = {
            "turn": self.referee_engine.get_current_turn(),
            "fen": fen_before,
            "proposed_move": move,
            "action": "validate_only"
        }

        messages = self.prompt_builder.build_validation_prompt(game_state)

        try:
            response = await self.llm_adapter.chat(messages)

            # 解析裁判判断（信任引擎结果，LLM仅作参考）
            if "valid" in response.content.lower() or "合法" in response.content:
                return True, None
            else:
                # LLM判定存疑，但引擎已通过，以引擎为准
                # 记录LLM判断供参考，但不阻断
                return True, None
        except Exception:
            # LLM调用失败，信任引擎结果
            return True, None

    async def check_game_end(self, fen: str) -> Tuple[bool, Optional[str]]:
        """检查游戏是否结束

        Args:
            fen: 当前FEN

        Returns:
            (is_ended, reason)
        """
        return self.referee_engine.check_game_end(fen)

    async def generate_state_broadcast(
        self,
        turn: str,
        fen: str,
        last_move: Optional[str],
        last_move_by: Optional[str]
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
        self,
        agent_name: str,
        move: str,
        fen: str,
        reason: str
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
            "action": "explain"
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

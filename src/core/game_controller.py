"""
游戏控制器

协调Agent和RefereeEngine的交互，管理游戏流程
"""

from typing import Optional, Tuple, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass
import asyncio

from .referee_engine import RefereeEngine, INITIAL_FEN, Color
from .state_serializer import (
    GameState,
    GamePhase,
    GameResult,
    MoveResult,
    ValidationResult,
)

if TYPE_CHECKING:
    from ..agents.agent_referee import RefereeAgent
    from ..mcp_tools.position_eval import PikafishEngine


def _calculate_win_probability(score: int, current_turn: str) -> Tuple[float, float]:
    """根据引擎评分计算双方胜率

    Args:
        score: 引擎评分（从当前走子方视角，正分表示当前走子方优势）
        current_turn: 当前走子方 ("Red" 或 "Black")

    Returns:
        (red_win_prob, black_win_prob) 百分比
    """
    import math

    # 使用sigmoid函数将评分转换为当前走子方的胜率
    # 评分范围通常在 -3000 到 +3000 之间
    k = 0.002

    # 当前走子方的胜率
    current_turn_win_rate = 1 / (1 + math.exp(-k * score))

    # 根据当前走子方转换为红黑胜率
    if current_turn == "Red":
        red_win = current_turn_win_rate
        black_win = 1 - red_win
    else:
        black_win = current_turn_win_rate
        red_win = 1 - black_win

    # 考虑和棋概率（评分接近0时和棋概率较高）
    draw_prob = max(0, 0.3 - abs(score) * 0.0001)
    red_win = red_win * (1 - draw_prob)
    black_win = black_win * (1 - draw_prob)

    return round(red_win * 100, 1), round(black_win * 100, 1)


@dataclass
class GameController:
    """
    游戏控制器

    职责：
    1. 回合管理
    2. 胜负判定
    3. 走棋历史
    4. 超时控制（一期暂不启用）
    """

    def __init__(
        self, referee_engine: Optional[RefereeEngine] = None, max_turns: int = 200
    ):
        self.referee = referee_engine or RefereeEngine(INITIAL_FEN)
        self.max_turns = max_turns
        self.turn_count = 0
        self.phase = GamePhase.RED_TO_MOVE
        self.result = GameResult.IN_PROGRESS
        self.result_reason: Optional[str] = None

    def get_current_state(self) -> GameState:
        """获取当前游戏状态"""
        return GameState.from_engine(self.referee)

    def get_current_turn(self) -> str:
        """获取当前回合"""
        return self.referee.get_current_turn()

    def apply_move(self, agent_name: str, iccs_move: str) -> MoveResult:
        """应用走步

        Args:
            agent_name: 执行走步的Agent名称
            iccs_move: ICCS格式走步 (如 "h2e2")

        Returns:
            MoveResult: 走步结果
        """
        # 验证走步格式
        if not self._validate_iccs_format(iccs_move):
            return MoveResult(success=False, error=f"Invalid ICCS format: {iccs_move}")

        # 验证走步合法性
        if not self.referee.validate_move(iccs_move):
            # 调试日志
            from ..utils.logger import get_logger

            logger = get_logger("game", level="INFO")
            legal = self.referee.get_legal_moves()
            logger.error(
                f"DEBUG: agent_name={agent_name}, iccs_move={iccs_move}, current_turn={self.referee.get_current_turn()}, phase={self.phase}"
            )
            return MoveResult(
                success=False,
                error=f"Illegal move: {iccs_move}, current_turn={self.referee.get_current_turn()}, legal_moves={legal[:5]}...",
            )

        try:
            # 应用走步
            new_fen = self.referee.apply_move(iccs_move)

            # 更新游戏状态
            self.turn_count += 1

            # 更新GameState
            state = self.get_current_state()
            state.last_move = iccs_move
            state.last_move_by = agent_name

            # 检查游戏是否结束
            is_over, reason = self.referee.check_game_end()
            if is_over:
                self.phase = GamePhase.GAME_OVER
                self.result = (
                    GameResult.RED_WIN
                    if self.referee.board.current_color == Color.BLACK
                    else GameResult.BLACK_WIN
                )
                self.result_reason = reason
            else:
                # 切换回合
                if self.phase == GamePhase.RED_TO_MOVE:
                    self.phase = GamePhase.BLACK_TO_MOVE
                else:
                    self.phase = GamePhase.RED_TO_MOVE

            return MoveResult(success=True, move=iccs_move, new_fen=new_fen)

        except Exception as e:
            return MoveResult(success=False, error=str(e))

    def _validate_iccs_format(self, move: str) -> bool:
        """验证ICCS走步格式"""
        if len(move) != 4:
            return False
        if not (move[0].isalpha() and move[2].isalpha()):
            return False
        if not (move[1].isdigit() and move[3].isdigit()):
            return False
        col1, row1 = ord(move[0].lower()) - ord("a"), int(move[1])
        col2, row2 = ord(move[2].lower()) - ord("a"), int(move[3])
        return 0 <= col1 <= 8 and 0 <= col2 <= 8 and 0 <= row1 <= 9 and 0 <= row2 <= 9

    def is_game_over(self) -> Tuple[bool, GameResult, Optional[str]]:
        """检查游戏是否结束"""
        return (self.phase == GamePhase.GAME_OVER, self.result, self.result_reason)

    def reset(self, fen: str = INITIAL_FEN) -> None:
        """重置游戏"""
        self.referee.reset(fen)
        self.turn_count = 0
        self.phase = GamePhase.RED_TO_MOVE
        self.result = GameResult.IN_PROGRESS
        self.result_reason = None

    def get_game_info(self) -> Dict[str, Any]:
        """获取游戏信息"""
        return {
            "turn_count": self.turn_count,
            "max_turns": self.max_turns,
            "phase": self.phase.value,
            "result": self.result.value,
            "result_reason": self.result_reason,
            "current_turn": self.get_current_turn(),
            "move_history": self.referee.move_history.copy(),
        }


class LLMAgentGameController(GameController):
    """
    LLM Agent游戏控制器

    支持LLM Agent对战的完整流程管理
    """

    def __init__(
        self,
        red_agent=None,
        black_agent=None,
        referee_engine: Optional[RefereeEngine] = None,
        referee_agent: Optional["RefereeAgent"] = None,
        max_turns: int = 200,
    ):
        super().__init__(referee_engine, max_turns)
        self.red_agent = red_agent
        self.black_agent = black_agent
        self.current_agent = None
        self.referee_agent = referee_agent
        self._position_evaluator = None

    def _get_position_evaluator(self):
        """获取局面评估器（延迟初始化）"""
        if self._position_evaluator is None:
            from ..mcp_tools.position_eval import PikafishEngine

            try:
                self._position_evaluator = PikafishEngine.get_instance(depth=15)
            except Exception:
                self._position_evaluator = None
        return self._position_evaluator

    async def _evaluate_and_report(
        self, fen: str, move_by: str, move_color: str
    ) -> str:
        """评估局面并生成报告

        Args:
            fen: 当前FEN
            move_by: 走步方名称
            move_color: 走步方颜色

        Returns:
            评估报告字符串
        """
        evaluator = self._get_position_evaluator()

        if evaluator is None or not evaluator.is_available():
            return "（引擎不可用，无法评估胜率）"

        try:
            result = evaluator.evaluate(fen, depth=12)
            score = result.get("score", 0)
            evaluation = result.get("evaluation", "未知")
            best_move = result.get("bestmove")

            # 获取当前走子方
            current_turn = self.referee.get_current_turn()

            # 计算胜率
            red_win, black_win = _calculate_win_probability(score, current_turn)

            report = f"\n【局面评估】评分: {score} ({evaluation})"
            report += f"\n【胜率估算】红方: {red_win}% | 黑方: {black_win}%"
            if best_move:
                report += f"\n【引擎推荐】{best_move}"

            return report

        except Exception as e:
            return f"（评估失败: {e}）"

    async def _validate_with_referee(
        self, agent_name: str, move: Optional[str], fen_after: str
    ) -> Tuple[bool, Optional[str], str]:
        """使用RefereeAgent校验并评注

        Args:
            agent_name: 执行走步的Agent名称
            move: ICCS格式走步
            fen_after: 走步后的FEN

        Returns:
            (is_valid, error_message, commentary)
        """
        if self.referee_agent is None:
            return True, None, ""

        if move is None:
            return False, "Move is None", ""

        try:
            is_valid, error, commentary = await self.referee_agent.validate_and_comment(
                agent_name, move, fen_after
            )
            return is_valid, error, commentary
        except Exception as e:
            from ..utils.logger import get_logger

            logger = get_logger("game", level="WARNING")
            logger.warning(f"RefereeAgent validation failed: {e}")
            return True, None, ""

    async def play_turn(self) -> MoveResult:
        """执行当前回合

        Returns:
            MoveResult: 走步结果
        """
        if self.phase == GamePhase.GAME_OVER:
            return MoveResult(success=False, error="Game is over")

        # 获取当前Agent
        if self.phase == GamePhase.RED_TO_MOVE:
            self.current_agent = self.red_agent
        else:
            self.current_agent = self.black_agent

        if self.current_agent is None:
            return MoveResult(success=False, error="No agent for current turn")

        # 获取当前合法走步
        legal_moves = self.referee.get_legal_moves()
        last_error_msg = None

        # 最多重试3次（当LLM产生幻觉非法走步时）
        for attempt in range(3):
            # 获取当前状态
            state = self.get_current_state()

            # 如果是重试且上次有错误，添加纠正性反馈
            if attempt > 0 and last_error_msg:
                self.current_agent.add_correction_feedback(last_error_msg, legal_moves)

            # Agent思考
            result = await self.current_agent.think(state.to_dict())

            if not result.success:
                return MoveResult(success=False, error=result.error)

            # 后置校验：检查LLM返回的走步是否在合法列表中
            if result.move and result.move in legal_moves:
                # 走步合法，应用它
                move_result = self.apply_move(
                    self.current_agent.config.name, result.move
                )
                if move_result.success:
                    move_result.thought = result.thought
                return move_result
            else:
                # LLM幻觉了非法走步或解析失败，记录并重试
                from ..utils.logger import get_logger

                logger = get_logger("game", level="WARNING")
                if result.move is None:
                    last_error_msg = "输出格式错误：未能在响应中找到有效的ICCS走步。请严格按照JSON格式输出，包含move字段，值为4字符的ICCS坐标（如h2e2）。"
                    logger.warning(f"LLM返回None (解析失败), attempt {attempt + 1}/3")
                else:
                    last_error_msg = f"你的走步 '{result.move}' 不在合法列表中。合法走步共{len(legal_moves)}种，请务必从以下列表中选择一个：{legal_moves[:10]}..."
                    logger.warning(
                        f"LLM幻觉非法走步: {result.move}, attempt {attempt + 1}/3"
                    )

                # 清除agent历史，强制重新思考
                self.current_agent.reset()

        # 3次重试都失败
        return MoveResult(success=False, error=f"LLM连续3次产生非法走步，已放弃")

    async def run_game(self, verbose: bool = True) -> Dict[str, Any]:
        """运行完整游戏

        Args:
            verbose: 是否输出详细信息

        Returns:
            游戏结果信息
        """
        from ..utils.logger import get_logger

        logger = get_logger("game", level="INFO")

        if verbose:
            logger.info("=" * 60)
            logger.info("LLM Chinese Chess Game Started")
            logger.info("=" * 60)
            state = self.get_current_state()
            logger.info(f"\nInitial Board:\n{state.ascii_board}")
            red_model = (
                self.red_agent.config.llm_adapter.model if self.red_agent else "None"
            )
            black_model = (
                self.black_agent.config.llm_adapter.model
                if self.black_agent
                else "None"
            )
            logger.info(
                f"Red Agent: {self.red_agent.config.name if self.red_agent else 'None'}:{red_model}"
            )
            logger.info(
                f"Black Agent: {self.black_agent.config.name if self.black_agent else 'None'}:{black_model}"
            )
            if self.referee_agent:
                logger.info(f"Referee: {self.referee_agent.config.name}")

        # 游戏主循环
        while self.phase != GamePhase.GAME_OVER:
            if self.turn_count >= self.max_turns:
                self.phase = GamePhase.GAME_OVER
                self.result = GameResult.DRAW
                self.result_reason = "Maximum turns reached"
                break

            # 记录走步前的FEN
            fen_before = self.referee.current_fen

            # 执行回合
            move_result = await self.play_turn()

            if not move_result.success:
                logger.error(f"Move failed: {move_result.error}")
                break

            # 获取走步信息
            if self.phase == GamePhase.BLACK_TO_MOVE:
                move_by = self.red_agent.config.name if self.red_agent else "Red"
                move_model = (
                    self.red_agent.config.llm_adapter.model
                    if self.red_agent
                    else "Unknown"
                )
                move_color = "Red"
            else:
                move_by = self.black_agent.config.name if self.black_agent else "Black"
                move_model = (
                    self.black_agent.config.llm_adapter.model
                    if self.black_agent
                    else "Unknown"
                )
                move_color = "Black"

            if verbose:
                logger.info(
                    f"\n{move_by}:{move_model} ({move_color}) moved: {move_result.move}"
                )
                if move_result.thought:
                    logger.info(f"Thought: {move_result.thought.replace(chr(10), ' ')}")

            # RefereeAgent校验并评注
            state = self.get_current_state()
            if self.referee_agent and move_result.move:
                is_valid, error_msg, commentary = await self._validate_with_referee(
                    move_by, move_result.move, state.fen
                )
                if not is_valid:
                    logger.warning(f"[Referee] {error_msg}")
                elif verbose and commentary:
                    logger.info(f"[Referee] {commentary}")
                elif verbose:
                    logger.info(f"[Referee] 走步合法 ✓")

            # 输出胜率评估
            if verbose:
                eval_report = await self._evaluate_and_report(
                    state.fen, move_by, move_color
                )
                logger.info(eval_report)
                logger.info(f"Board:\n{state.ascii_board}")

            # 检查游戏是否结束
            is_over, result, reason = self.is_game_over()
            if is_over:
                if verbose:
                    logger.info(f"\nGame Over: {reason}")
                    logger.info(f"Result: {result}")
                break

        # 返回游戏结果
        return {
            "success": True,
            "turn_count": self.turn_count,
            "result": self.result.value,
            "result_reason": self.result_reason,
            "move_history": self.referee.move_history.copy(),
        }

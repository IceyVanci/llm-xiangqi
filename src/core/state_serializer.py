"""
状态序列化模块

将游戏状态转换为LLM友好的格式
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class GamePhase(Enum):
    """游戏阶段"""
    NOT_STARTED = "not_started"
    RED_TO_MOVE = "red_to_move"
    BLACK_TO_MOVE = "black_to_move"
    GAME_OVER = "game_over"


class GameResult(Enum):
    """游戏结果"""
    RED_WIN = "red_win"
    BLACK_WIN = "black_win"
    DRAW = "draw"
    IN_PROGRESS = "in_progress"


class GameEndReason(Enum):
    """游戏结束原因枚举
    
    用于标识游戏结束的具体原因，便于前端显示和日志记录
    """
    # 红方胜利
    RED_CHECKMATE = "red_checkmate"          # 红方将死黑方
    RED_STALEMATE = "red_stalemate"          # 黑方困毙（红方胜利）
    RED_KING_CAPTURED = "red_king_captured"  # 红方吃掉了黑将
    RED_RESIGNATION = "red_resignation"      # 黑方投降
    
    # 黑方胜利
    BLACK_CHECKMATE = "black_checkmate"       # 黑方将死红方
    BLACK_STALEMATE = "black_stalemate"       # 红方困毙（黑方胜利）
    BLACK_KING_CAPTURED = "black_king_captured"  # 黑方吃掉了红帅
    BLACK_RESIGNATION = "black_resignation"  # 红方投降
    
    # 和棋
    THREE_FOLD_REPETITION = "three_fold_repetition"  # 三次重复局面
    MAX_TURNS = "max_turns"                          # 达到最大回合数
    STALEMATE_DRAW = "stalemate_draw"               # 双方同意和棋/僵局
    
    # 违规
    RED_PERPETUAL_CHECK = "red_perpetual_check"       # 红方长将违规
    BLACK_PERPETUAL_CHECK = "black_perpetual_check"   # 黑方长将违规
    
    # 未开始/进行中
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    
    @classmethod
    def from_result_string(cls, reason: str) -> "GameEndReason":
        """从结果字符串推断 GameEndReason
        
        Args:
            reason: referee_engine.check_game_end() 返回的原因字符串
            
        Returns:
            对应的 GameEndReason 枚举值
        """
        if not reason:
            return cls.NOT_STARTED
            
        reason_lower = reason.lower()
        
        # 红方胜利相关
        if "红方被将死" in reason:
            return cls.RED_CHECKMATE
        if "红方被困" in reason:
            return cls.RED_STALEMATE
        if "红帅被吃" in reason or "红将被吃" in reason:
            return cls.BLACK_KING_CAPTURED
        if "red resigned" in reason_lower:
            return cls.RED_RESIGNATION
            
        # 黑方胜利相关
        if "黑方被将死" in reason:
            return cls.BLACK_CHECKMATE
        if "黑方被困" in reason:
            return cls.BLACK_STALEMATE
        if "黑将被吃" in reason or "黑帅被吃" in reason:
            return cls.RED_KING_CAPTURED
        if "black resigned" in reason_lower:
            return cls.BLACK_RESIGNATION
            
        # 和棋相关
        if "三次重复局面" in reason:
            return cls.THREE_FOLD_REPETITION
        if "maximum turns" in reason_lower:
            return cls.MAX_TURNS
        if "判和" in reason:
            return cls.STALEMATE_DRAW
            
        # 长将违规
        if "红方长将" in reason:
            return cls.RED_PERPETUAL_CHECK
        if "黑方长将" in reason:
            return cls.BLACK_PERPETUAL_CHECK
            
        return cls.STALEMATE_DRAW  # 默认判和（保守策略）
    
    def to_display_string(self) -> str:
        """转换为前端友好显示字符串
        
        Returns:
            中文显示字符串
        """
        display_map = {
            cls.RED_CHECKMATE: "红方胜利 - 将军！",
            cls.RED_STALEMATE: "红方胜利 - 黑方被困毙",
            cls.RED_KING_CAPTURED: "红方胜利 - 吃掉黑将",
            cls.RED_RESIGNATION: "红方胜利 - 黑方投降",
            cls.BLACK_CHECKMATE: "黑方胜利 - 将军！",
            cls.BLACK_STALEMATE: "黑方胜利 - 红方被困毙",
            cls.BLACK_KING_CAPTURED: "黑方胜利 - 吃掉红帅",
            cls.BLACK_RESIGNATION: "黑方胜利 - 红方投降",
            cls.THREE_FOLD_REPETITION: "和棋 - 三次重复局面",
            cls.MAX_TURNS: "和棋 - 达到最大回合数",
            cls.STALEMATE_DRAW: "和棋",
            cls.RED_PERPETUAL_CHECK: "红方胜利 - 黑方长将违规",
            cls.BLACK_PERPETUAL_CHECK: "黑方胜利 - 红方长将违规",
            cls.NOT_STARTED: "游戏未开始",
            cls.IN_PROGRESS: "游戏进行中",
        }
        return display_map.get(self, "未知结果")


@dataclass
class GameState:
    """游戏状态数据类

    用于在Agent、Controller和RefereeEngine之间传递状态
    """
    turn: str  # "Red" or "Black"
    fen: str
    ascii_board: str
    legal_moves: List[str]
    legal_moves_count: int
    game_history: List[str] = field(default_factory=list)
    annotated_moves: List[Dict[str, Any]] = field(default_factory=list)
    last_move: Optional[str] = None
    last_move_by: Optional[str] = None
    phase: GamePhase = GamePhase.NOT_STARTED
    result: GameResult = GameResult.IN_PROGRESS
    result_reason: Optional[str] = None
    end_reason: Optional[GameEndReason] = None  # 新增：游戏结束原因的枚举值

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "turn": self.turn,
            "fen": self.fen,
            "ascii_board": self.ascii_board,
            "legal_moves": self.legal_moves,
            "legal_moves_count": self.legal_moves_count,
            "game_history": self.game_history,
            "annotated_moves": self.annotated_moves,
            "last_move": self.last_move,
            "last_move_by": self.last_move_by,
            "phase": self.phase.value,
            "result": self.result.value,
            "result_reason": self.result_reason,
            "end_reason": self.end_reason.value if self.end_reason else None,
            "end_reason_display": self.end_reason.to_display_string() if self.end_reason else None,
        }

    @classmethod
    def from_engine(cls, engine) -> "GameState":
        """从RefereeEngine创建GameState"""
        annotated_moves = engine.get_annotated_moves()
        return cls(
            turn=engine.get_current_turn(),
            fen=engine.current_fen,
            ascii_board=engine.render_ascii_board(),
            legal_moves=[m["move"] for m in annotated_moves],
            legal_moves_count=len(annotated_moves),
            game_history=engine.move_history.copy(),
            annotated_moves=annotated_moves,
        )


@dataclass
class MoveResult:
    """走步结果"""
    success: bool
    move: Optional[str] = None
    thought: Optional[str] = None
    error: Optional[str] = None
    new_fen: Optional[str] = None


@dataclass
class ValidationResult:
    """走步验证结果"""
    is_valid: bool
    error_message: Optional[str] = None
    explanation: Optional[str] = None

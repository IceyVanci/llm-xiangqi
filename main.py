"""
LLM中国象棋对战程序 - zgxqaidz

入口文件
"""

import asyncio
import argparse
from pathlib import Path

from src.core.referee_engine import RefereeEngine, INITIAL_FEN
from src.core.game_controller import GameController
from src.core.state_serializer import GameState
from src.utils.logger import get_logger


logger = get_logger("main", level="INFO")


async def demo_mode():
    """演示模式：展示核心功能"""
    logger.info("=" * 60)
    logger.info("LLM Chinese Chess Arena - Demo Mode")
    logger.info("=" * 60)

    # 初始化引擎
    engine = RefereeEngine()
    controller = GameController(referee_engine=engine)

    # 展示初始状态
    state = controller.get_current_state()
    logger.info(f"\nCurrent Turn: {state.turn}")
    logger.info(f"FEN: {state.fen}")
    logger.info(f"\nChessboard:\n{state.ascii_board}")
    logger.info(f"\nLegal Moves: {state.legal_moves_count} moves available")
    logger.info(f"Sample moves: {state.legal_moves[:5]}")

    # 演示一个完整走步
    logger.info("\n" + "-" * 40)
    logger.info("演示：红方走炮二平五 (h2e2)")

    result = controller.apply_move("DemoAgent", "h2e2")
    if result.success:
        logger.info(f"Move applied successfully!")
        logger.info(f"New FEN: {result.new_fen}")
        state = controller.get_current_state()
        logger.info(f"\nChessboard after move:\n{state.ascii_board}")
        logger.info(f"Next turn: {state.turn}")
    else:
        logger.error(f"Move failed: {result.error}")

    # 演示走步验证
    logger.info("\n" + "-" * 40)
    logger.info("演示：黑方走炮8平2 (i7e7)")

    result = controller.apply_move("DemoAgent2", "i7e7")
    if result.success:
        logger.info(f"Move applied successfully!")
        state = controller.get_current_state()
        logger.info(f"\nChessboard after move:\n{state.ascii_board}")
        logger.info(f"Next turn: {state.turn}")
        logger.info(f"Move history: {state.game_history}")
    else:
        logger.error(f"Move failed: {result.error}")

    logger.info("\n" + "=" * 60)
    logger.info("Demo completed")
    logger.info("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="LLM Chinese Chess Arena")
    parser.add_argument(
        "--mode",
        choices=["demo", "game"],
        default="demo",
        help="运行模式"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径"
    )

    args = parser.parse_args()

    if args.mode == "demo":
        asyncio.run(demo_mode())
    elif args.mode == "game":
        logger.info("Game mode not implemented yet")


if __name__ == "__main__":
    main()

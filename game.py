"""
LLM中国象棋对战 - 完整对战模式

使用真实LLM Agent进行对战
"""

import asyncio
import argparse
from pathlib import Path

from src.core.referee_engine import RefereeEngine, INITIAL_FEN
from src.core.game_controller import LLMAgentGameController
from src.agents.agent_deepseek import DeepSeekAgent
from src.agents.agent_minimax import MiniMaxAgent
from src.agents.agent_glm import GLMAgent
from src.agents.agent_referee import RefereeAgent
from src.agents.base_agent import AgentConfig
from src.agents.prompt_builder import PromptBuilder
from src.llm_adapters.deepseek_adapter import DeepSeekAdapter
from src.llm_adapters.minimax_adapter import MiniMaxAdapter
from src.llm_adapters.glm_adapter import GLMAdapter
from src.llm_adapters.mimo_adapter import MiMoAdapter
from src.utils.config_loader import ConfigLoader
from src.utils.logger import get_logger


logger = get_logger("game", level="INFO")


def load_agents():
    """加载Agent配置"""
    logger.info("Loading agent configurations...")

    # 加载Agent1 (DeepSeek/Red)
    agent1_config = ConfigLoader.load_yaml(
        Path(__file__).parent / "config" / "agent1_config.yaml"
    )
    llm1_config = agent1_config['llm']
    agent1_data = agent1_config['agent']

    # 创建DeepSeek适配器
    deepseek_adapter = DeepSeekAdapter(
        api_key=llm1_config['api_key'],
        model=llm1_config['model'],
        base_url=llm1_config['base_url'],
        timeout=llm1_config.get('timeout', 30),
        max_retries=llm1_config.get('max_retries', 3),
        temperature=llm1_config.get('temperature', 0.7),
        max_tokens=llm1_config.get('max_tokens', 2048)
    )

    # 加载System Prompt
    prompt_path = Path(__file__).parent / agent1_data.get('system_prompt_file', 'prompts/agent_system.txt')
    agent1_prompt = PromptBuilder.from_file(str(prompt_path)).system_prompt if prompt_path.exists() else ""

    # 创建Agent1配置
    agent1_cfg = AgentConfig(
        name=agent1_data['name'],
        color=agent1_data['color'],
        description=agent1_data.get('description', ''),
        llm_adapter=deepseek_adapter,
        system_prompt=agent1_prompt,
        max_retries=agent1_data.get('max_retries', 3),
        use_tools=agent1_data.get('use_tools', False),  # 一期关闭工具
        use_reflection=agent1_data.get('use_reflection', False)
    )

    # 加载Agent2 (MiMo/Black)
    agent2_config = ConfigLoader.load_yaml(
        Path(__file__).parent / "config" / "agent2_config.yaml"
    )
    llm2_config = agent2_config['llm']
    agent2_data = agent2_config['agent']

    # 根据provider创建对应的适配器
    provider = llm2_config.get('provider', 'glm')
    if provider == 'mimo':
        llm2_adapter = MiMoAdapter(
            api_key=llm2_config['api_key'],
            model=llm2_config['model'],
            base_url=llm2_config['base_url'],
            timeout=llm2_config.get('timeout', 60),
            max_retries=llm2_config.get('max_retries', 3),
            temperature=llm2_config.get('temperature', 0.7),
            max_tokens=llm2_config.get('max_tokens', 2048)
        )
    elif provider == 'glm':
        llm2_adapter = GLMAdapter(
            api_key=llm2_config['api_key'],
            model=llm2_config['model'],
            base_url=llm2_config['base_url'],
            timeout=llm2_config.get('timeout', 60),
            max_retries=llm2_config.get('max_retries', 3),
            temperature=llm2_config.get('temperature', 0.7),
            max_tokens=llm2_config.get('max_tokens', 2048)
        )
    elif provider == 'minimax':
        llm2_adapter = MiniMaxAdapter(
            api_key=llm2_config['api_key'],
            model=llm2_config['model'],
            base_url=llm2_config['base_url'],
            timeout=llm2_config.get('timeout', 60),
            max_retries=llm2_config.get('max_retries', 3),
            temperature=llm2_config.get('temperature', 0.7),
            max_tokens=llm2_config.get('max_tokens', 2048)
        )
    else:
        raise ValueError(f"Unsupported provider for Agent2: {provider}")

    prompt_path = Path(__file__).parent / agent2_data.get('system_prompt_file', 'prompts/agent_system.txt')
    agent2_prompt = PromptBuilder.from_file(str(prompt_path)).system_prompt if prompt_path.exists() else ""

    agent2_cfg = AgentConfig(
        name=agent2_data['name'],
        color=agent2_data['color'],
        description=agent2_data.get('description', ''),
        llm_adapter=llm2_adapter,
        system_prompt=agent2_prompt,
        max_retries=agent2_data.get('max_retries', 3),
        use_tools=agent2_data.get('use_tools', False),
        use_reflection=agent2_data.get('use_reflection', False)
    )

    # 创建Agent实例（暂时使用GLMAgent作为基础，后续可扩展）
    agent1 = DeepSeekAgent(agent1_cfg)
    agent2 = GLMAgent(agent2_cfg)

    logger.info(f"Agent1 (Red): {agent1.config.name} - {agent1.config.description}")
    logger.info(f"Agent2 (Black): {agent2.config.name} - {agent2.config.description}")

    return agent1, agent2


async def run_battle(agent1, agent2, max_turns: int = 100):
    """运行完整对局"""
    logger.info("=" * 60)
    logger.info("LLM CHINESE CHESS BATTLE")
    logger.info("=" * 60)

    # 创建裁判引擎
    referee_engine = RefereeEngine()

    # 创建游戏控制器
    controller = LLMAgentGameController(
        red_agent=agent1,
        black_agent=agent2,
        referee_engine=referee_engine,
        max_turns=max_turns
    )

    # 显示初始局面
    state = controller.get_current_state()
    logger.info(f"\nInitial Position:")
    logger.info(f"\n{state.ascii_board}")
    logger.info(f"FEN: {state.fen}")
    logger.info(f"Legal moves: {state.legal_moves_count}")

    # 运行对局
    result = await controller.run_game(verbose=True)

    # 显示结果
    logger.info("\n" + "=" * 60)
    logger.info("GAME OVER")
    logger.info("=" * 60)
    logger.info(f"Result: {result['result']}")
    logger.info(f"Reason: {result['result_reason']}")
    logger.info(f"Total turns: {result['turn_count']}")
    logger.info(f"Move history: {' '.join(result['move_history'])}")

    return result


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="LLM Chinese Chess Battle")
    parser.add_argument(
        "--turns", type=int, default=100,
        help="最大回合数 (default: 100)"
    )
    args = parser.parse_args()

    try:
        # 加载Agent
        agent1, agent2 = load_agents()

        # 运行对局
        result = await run_battle(agent1, agent2, args.turns)

    except KeyboardInterrupt:
        logger.info("\nGame interrupted by user")
    except Exception as e:
        logger.error(f"Game error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

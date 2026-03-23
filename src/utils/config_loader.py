"""
配置加载模块

支持YAML配置文件和环境变量引用
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: str
    model: str
    api_key: str
    base_url: str
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30


@dataclass
class AgentConfig:
    """Agent配置"""
    name: str
    color: str
    description: str
    llm: LLMConfig
    system_prompt_file: str
    max_retries: int = 3
    retry_delay: int = 2
    use_tools: bool = True
    use_reflection: bool = False


@dataclass
class RefereeConfig:
    """裁判配置"""
    name: str
    role: str
    description: str
    llm: LLMConfig
    system_prompt_file: str
    validate_all_moves: bool = True
    explain_violations: bool = True


@dataclass
class PikafishConfig:
    """Pikafish引擎配置"""
    enabled: bool = True
    path: str = "engines/pikafish.exe"
    depth: int = 15
    threads: int = 4


@dataclass
class MCPToolsConfig:
    """MCP工具配置"""
    enabled: bool = True
    tools_dir: str = "data/opening_books"
    pikafish: PikafishConfig = field(default_factory=PikafishConfig)


@dataclass
class TimeControlConfig:
    """时限配置"""
    enabled: bool = False
    seconds_per_turn: int = 60


@dataclass
class GameConfig:
    """游戏全局配置"""
    initial_fen: str = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    time_control: TimeControlConfig = field(default_factory=TimeControlConfig)
    max_turns: int = 200


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    file: str = "logs/game.log"
    console: bool = True


@dataclass
class AppConfig:
    """应用完整配置"""
    game: GameConfig
    mcp_tools: MCPToolsConfig
    logging: LoggingConfig


class ConfigLoader:
    """配置加载器"""

    @staticmethod
    def _resolve_env_vars(value: Any) -> Any:
        """解析环境变量引用 ${VAR_NAME}"""
        if isinstance(value, str):
            if value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                return os.environ.get(env_var, "")
            # Handle ${VAR_NAME:default} format
            if value.startswith("${") and ":" in value:
                inner = value[2:-1]
                var_name, default = inner.split(":", 1)
                return os.environ.get(var_name, default)
        return value

    @staticmethod
    def _resolve_dict_env_vars(d: Dict[str, Any]) -> Dict[str, Any]:
        """递归解析字典中的环境变量"""
        result = {}
        for key, value in d.items():
            if isinstance(value, dict):
                result[key] = ConfigLoader._resolve_dict_env_vars(value)
            else:
                result[key] = ConfigLoader._resolve_env_vars(value)
        return result

    @classmethod
    def load_yaml(cls, path: str) -> Dict[str, Any]:
        """加载YAML配置文件"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return cls._resolve_dict_env_vars(config or {})

    @classmethod
    def load_agent_config(cls, path: str) -> AgentConfig:
        """加载Agent配置"""
        data = cls.load_yaml(path)
        llm_data = data.get('llm', {})
        agent_data = data.get('agent', {})

        llm = LLMConfig(
            provider=llm_data.get('provider', ''),
            model=llm_data.get('model', ''),
            api_key=llm_data.get('api_key', ''),
            base_url=llm_data.get('base_url', ''),
            temperature=llm_data.get('temperature', 0.7),
            max_tokens=llm_data.get('max_tokens', 2048),
            timeout=llm_data.get('timeout', 30)
        )

        return AgentConfig(
            name=agent_data.get('name', ''),
            color=agent_data.get('color', ''),
            description=agent_data.get('description', ''),
            llm=llm,
            system_prompt_file=agent_data.get('system_prompt_file', ''),
            max_retries=agent_data.get('max_retries', 3),
            retry_delay=agent_data.get('retry_delay', 2),
            use_tools=agent_data.get('use_tools', True),
            use_reflection=agent_data.get('use_reflection', False)
        )

    @classmethod
    def load_game_config(cls, path: str) -> GameConfig:
        """加载游戏配置"""
        data = cls.load_yaml(path)
        game_data = data.get('game', {})

        tc_data = game_data.get('time_control', {})
        time_control = TimeControlConfig(
            enabled=tc_data.get('enabled', False),
            seconds_per_turn=tc_data.get('seconds_per_turn', 60)
        )

        return GameConfig(
            initial_fen=game_data.get('initial_fen', ''),
            time_control=time_control,
            max_turns=game_data.get('max_turns', 200)
        )

    @classmethod
    def load_logging_config(cls, path: str) -> LoggingConfig:
        """加载日志配置"""
        data = cls.load_yaml(path)
        logging_data = data.get('logging', {})

        return LoggingConfig(
            level=logging_data.get('level', 'INFO'),
            file=logging_data.get('file', 'logs/game.log'),
            console=logging_data.get('console', True)
        )

## 项目结构

```
llm-xiangqi/
├── config/                 # 配置文件
│   ├── agent1_config.yaml  # Agent1 (红方) 配置
│   ├── agent2_config.yaml  # Agent2 (黑方) 配置
│   ├── referee_config.yaml # 裁判配置
│   └── game_config.yaml    # 游戏全局配置
├── prompts/                # System prompts
│   ├── agent_system.txt
│   └── referee_system.txt
├── src/
│   ├── agents/             # Agent 实现
│   ├── core/               # 核心引擎
│   ├── llm_adapters/       # LLM 适配器
│   ├── mcp_tools/          # MCP Tools
│   └── utils/              # 工具函数
├── tests/                  # 测试
├── main.py                 # 入口文件
└── game.py                 # 游戏对战入口
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Keys

编辑配置文件，填入你的 API Key:

- `config/agent1_config.yaml` - 红方 Agent
- `config/agent2_config.yaml` - 黑方 Agent
- `config/referee_config.yaml` - 裁判 Agent

### 3. 运行演示

```bash
python game.py
```

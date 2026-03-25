# LLM 中国象棋框架 (LLM-Xiangqi)

**LLM-Xiangqi** 是一个基于 LLM Agent 的中国象棋对战框架，支持多种 LLM 提供者（DeepSeek、GLM、MiniMax、MiMo）。框架内置完整的象棋规则引擎、3D 可视化界面以及灵活的多 Agent 对战架构，可用于 AI 对战、研究 LLM 推理能力、评估不同模型在棋类任务中的表现。

## 项目结构

```
llm-xiangqi/
├── config/                    # 配置文件
│   ├── agent1_config.yaml     # 红方 Agent 配置
│   ├── agent2_config.yaml     # 黑方 Agent 配置
│   └── game_config.yaml       # 游戏全局配置
├── prompts/                   # System prompts
│   └── agent_default.txt      # 默认提示词
├── src/
│   ├── agents/                # Agent 实现
│   │   ├── base_agent.py     # 基类
│   │   ├── agent_deepseek.py  # DeepSeek Agent
│   │   ├── agent_glm.py       # GLM Agent
│   │   ├── agent_minimax.py   # MiniMax Agent
│   │   └── prompt_builder.py  # Prompt 构建器
│   ├── core/                  # 核心引擎
│   │   ├── referee_engine.py  # 裁判引擎（走法验证）
│   │   ├── state_serializer.py # 状态序列化
│   │   └── game_controller.py # 游戏控制器
│   ├── gui/                   # 3D 界面
│   │   ├── chess_gui.py       # 主 GUI
│   │   ├── chess_board_renderer.py
│   │   ├── piece_renderer.py
│   │   └── camera_controller.py
│   ├── llm_adapters/          # LLM 适配器
│   │   ├── base_adapter.py    # 基类
│   │   ├── deepseek_adapter.py
│   │   ├── glm_adapter.py
│   │   ├── minimax_adapter.py
│   │   └── mimo_adapter.py
│   ├── mcp_tools/             # MCP Tools
│   │   ├── base_tool.py
│   │   └── tool_executor.py
│   └── utils/                 # 工具函数
│       ├── config_loader.py
│       └── logger.py
├── tests/                     # 测试
├── game.py                    # 游戏对战入口
├── main.py                    # 主入口
└── requirements.txt           # 依赖
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Keys

编辑配置文件填入 API Key：

- `config/agent1_config.yaml` - 红方 Agent（默认 DeepSeek）
- `config/agent2_config.yaml` - 黑方 Agent（默认 GLM，可配置为 minimax/mimo）

### 3. 运行对战

```bash
python game.py
```

可选参数：

- `--turns N` - 最大回合数（默认 100）

## 支持的 LLM 提供者

| 提供者 | 模型示例 | 配置 provider |
|--------|----------|---------------|
| DeepSeek | deepseek-chat | `deepseek` |
| GLM | glm-4 | `glm` |
| MiniMax | MiniMax-Text-01 | `minimax` |
| MiMo | MiMo-7B | `mimo` |

## 功能特性

### 核心框架
- **模块化 Agent 架构**：基于基类设计，方便扩展新的 LLM 提供者
- **完整的中国象棋规则引擎**：棋子移动验证、将军/应将检测、胜负判定（困毙）
- **多 Adapter 支持**：DeepSeek、GLM、MiniMax、MiMo 等主流 LLM 提供者
- **灵活的配置系统**：支持为红黑双方独立配置不同的模型和策略
- **MCP Tools 集成**：支持通过 MCP 协议扩展 Agent 工具能力

### 3D 可视化
- **实时 3D 渲染**：基于 pyglet/OpenGL 的 3D 棋盘与棋子展示
- **相机视角控制**：支持多角度观察棋盘
- **走法动画**：直观展示每一步棋的移动过程

### 对战与调试
- **实时对战展示**：支持红黑双方 AI 自动对弈
- **走法历史记录**：完整记录每一步棋及其时间戳
- **可配置回合上限**：防止无限对局

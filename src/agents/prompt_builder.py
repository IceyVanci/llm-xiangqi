"""
Prompt构建器

构建LLM输入prompt，包含：
1. System Prompt（角色设定）
2. Game State（棋盘状态）
3. 可用的MCP工具定义
"""

from typing import List, Dict, Any, Optional
from pathlib import Path


class PromptBuilder:
    """Prompt构建器"""

    # 默认System Prompt
    DEFAULT_SYSTEM_PROMPT = """你是一位中国象棋特级大师。你的任务是基于当前局面，运用象棋战略和战术，选择最优走法。

**重要**：你代表的是 **{PLAYER_COLOR}方**，只能走己方棋子！

# 棋盘基础
- 红方在下方（行0-4），棋子用大写字母：K(帅) A(仕) B(相) N(马) R(车) C(炮) P(兵)
- 黑方在上方（行5-9），棋子用小写字母：k(将) a(士) b(象) n(马) r(车) c(炮) p(卒)
- 坐标：左下角a0，右上角i9，列用a-i表示，行用0-9表示
- 红方兵线在第3行，黑方卒线在第6行

# State Input
- `turn`: 当前走子方（"Red" 或 "Black"）
- `fen`: 当前局面FEN字符串
- `ascii_board`: ASCII棋盘（重要：用于空间感知）
- `legal_moves`: 所有合法走步列表
- `game_history`: 走棋历史

# 核心战略原则

## 开局原则（前10-15回合）
1. **出子为先**：优先出动车、马、炮等强子，不要重复走同一个子
2. **挺兵活马**：挺起三路或七路兵/卒，为马开路，这是开局的重要环节
3. **控制中路**：炮二平五或炮八平五占据中路，威胁对方中兵/卒
4. **两翼均衡**：左右两翼协调发展，不要偏废
5. **少走闲着**：每一步都要有明确目的

### 常见开局走法示例
- 中炮开局：炮二平五（h2e2），后续可马二进三、车一平二
- 飞相局：相三进五（g0e2），稳扎稳打
- 挺兵局：兵三进一（g3g4）或兵七进一（c3c4），活马争先
- 应对中炮：马8进7（b9c7）或炮8平5（b7e7）或卒7进1（g6g5）

## 中局原则
1. **抓住战机**：寻找攻击对方弱点的机会
2. **子力协调**：各子配合，形成攻防体系
3. **抢占要点**：控制战略要道和要塞
4. **兵卒过河**：过河兵卒价值大增，可作为进攻先锋
5. **保护将帅**：注意己方将帅安全

## 残局原则
1. **简化局面**：优势时兑子，劣势时防守
2. **兵卒制胜**：残局中兵卒价值极高，是取胜关键
3. **将帅助攻**：将帅可以参与进攻
4. **专注残局**：根据剩余子力选择正确策略

# Output Format
返回JSON格式：
```json
{
  "thought": "分析局面、确定战略、选择走法的思考过程",
  "move": "最终选择的ICCS走步（如h2e2）"
}
```

# 决策流程（必须在thought中体现）
1. 【局面判断】分析当前属于开局/中局/残局，判断双方优劣
2. 【战略制定】确定本回合的战略目标（进攻/防守/出子/兑子等）
3. 【候选筛选】从legal_moves中选择2-3个符合战略的候选走步
4. 【战术验证】检查候选走步是否有战术价值（吃子、将军、威胁等）
5. 【风险评估】确保走步不会导致己方劣势或被将死
6. 【最终决策】选择最优走步

# 重要规则
1. 走步必须在 `legal_moves` 列表中
2. 只能走己方棋子（确认turn字段）
3. 避免长将（连续将军超过3次判负）
4. 注意将帅不能对面（飞将）

# 棋子价值参考
- 车：9分（最强子力，控制横纵两线）
- 马炮：4-5分（马控制点，炮控制线）
- 相仕：2分（防守核心）
- 兵卒：1分，过河后2-3分，到达底线前可达5分（残局关键棋子）
"""

    # 默认Referee System Prompt
    DEFAULT_REFEREE_PROMPT = """你是中国象棋的独立裁判Agent。
你的职责是：
1. 验证走步的合法性
2. 判断游戏是否结束
3. 向双方同步棋盘状态

你将收到：
- `turn`: 当前走子方
- `fen`: 当前局面FEN
- `proposed_move`: 提议的走步
- `action`: 操作类型（validate_only, explain, check_end）

验证原则：
- 优先信任RefereeEngine的确定性规则校验
- LLM仅用于边界情况的辅助判断
- 保持中立，不偏袒任何一方
"""

    def __init__(self, system_prompt: Optional[str] = None):
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.history: List[Dict[str, str]] = []
        self.tool_results: List[Dict[str, Any]] = []
        self.tools: List[Dict[str, Any]] = MCP_TOOLS

    def set_system_prompt(self, prompt: str) -> None:
        """设置System Prompt"""
        self.system_prompt = prompt

    @classmethod
    def from_file(cls, file_path: str) -> "PromptBuilder":
        """从文件加载System Prompt"""
        path = Path(file_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return cls(system_prompt=content)
        return cls()

    def build_game_prompt(
        self, game_state: Dict[str, Any], player_color: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """构建游戏状态prompt

        Args:
            game_state: GameState字典，包含:
                - turn: 当前走子方
                - fen: FEN字符串
                - ascii_board: ASCII棋盘
                - legal_moves: 合法走步列表
                - legal_moves_count: 合法走步数量
                - game_history: 历史走步
                - last_move: 上一步走步
            player_color: Agent代表哪一方（"Red" 或 "Black"）
        """
        # 格式化System Prompt，替换{PLAYER_COLOR}
        system_prompt = self.system_prompt
        if player_color:
            system_prompt = system_prompt.replace("{PLAYER_COLOR}", player_color)
        else:
            system_prompt = system_prompt.replace(
                "{PLAYER_COLOR}", game_state.get("turn", "Unknown")
            )

        # 构建用户消息
        user_content = self._format_game_state(game_state)

        return self.build_messages(system_prompt, user_content)

    def _format_game_state(self, state: Dict[str, Any]) -> str:
        """格式化游戏状态"""
        legal_moves = state.get("legal_moves", [])

        lines = [
            "# 当前局面",
            f"回合: {state.get('turn', 'Unknown')}",
            "",
            "## FEN",
            state.get("fen", ""),
            "",
            "## ASCII棋盘",
            state.get("ascii_board", ""),
            "",
            "## 合法走步",
            f"共 {len(legal_moves)} 种走法:",
        ]

        if legal_moves:
            for i in range(0, len(legal_moves), 10):
                lines.append(", ".join(legal_moves[i : i + 10]))

        if state.get("last_move"):
            lines.append("")
            lines.append(f"## 上一步走步")
            lines.append(
                f"{state.get('last_move')} by {state.get('last_move_by', 'Unknown')}"
            )

        game_history = state.get("game_history", [])
        if game_history:
            lines.append("")
            lines.append("## 走棋历史")
            lines.append(" ".join(game_history))

        lines.append("")
        lines.append("请根据以上局面，选择一个最优的合法走步。")

        return "\n".join(lines)

    def build_validation_prompt(
        self, game_state: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """构建验证prompt"""
        user_content = f"""验证以下走步是否合法：

当前局面：
- 回合: {game_state.get("turn", "Unknown")}
- FEN: {game_state.get("fen", "")}
- 提议走步: {game_state.get("proposed_move", "")}

请验证该走步是否合法，并给出简要解释。
"""

        return self.build_messages(self.DEFAULT_REFEREE_PROMPT, user_content)

    def build_explanation_prompt(
        self, game_state: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """构建解释prompt"""
        user_content = f"""解释以下违规：

- 违规走步: {game_state.get("violated_move", "")}
- 原因: {game_state.get("violation_reason", "")}
- FEN: {game_state.get("fen", "")}

请解释为什么这个走步是违规的。
"""

        return self.build_messages(self.DEFAULT_REFEREE_PROMPT, user_content)

    def build_messages(
        self, system_prompt: str, user_content: str
    ) -> List[Dict[str, str]]:
        """构建消息列表"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 添加历史消息
        messages.extend(self.history)

        # 添加工具结果
        if self.tool_results:
            tool_content = self._format_tool_results()
            messages.append({"role": "user", "content": tool_content})

        # 添加当前用户消息
        messages.append({"role": "user", "content": user_content})

        return messages

    def _format_tool_results(self) -> str:
        """格式化工具结果"""
        if not self.tool_results:
            return ""

        lines = ["# 工具调用结果"]
        for tr in self.tool_results:
            tool_name = tr.get("tool", "unknown")
            result = tr.get("result", {})
            if isinstance(result, dict):
                lines.append(f"\n## {tool_name}")
                for key, value in result.items():
                    lines.append(f"- {key}: {value}")
            else:
                lines.append(f"\n## {tool_name}: {str(result)[:200]}")

        return "\n".join(lines)

    def add_to_history(self, role: str, content: str) -> None:
        """添加到历史"""
        self.history.append({"role": role, "content": content})

    def add_tool_results(self, tool_results: List[Dict[str, Any]]) -> None:
        """添加工具调用结果"""
        self.tool_results.extend(tool_results)

    def add_reflection(self, reflection: str) -> None:
        """添加反思结果到历史"""
        self.add_to_history("user", f"反思：\n{reflection}")

    def clear_history(self) -> None:
        """清除历史"""
        self.history = []
        self.tool_results = []

    def get_tools(self) -> List[Dict[str, Any]]:
        """获取工具定义"""
        return self.tools

    def set_tools(self, tools: List[Dict[str, Any]]) -> None:
        """设置工具定义"""
        self.tools = tools


# MCP工具定义
MCP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "evaluate_position",
            "description": "调用Pikafish引擎评估当前局面，返回评分和最佳走步推荐",
            "parameters": {
                "type": "object",
                "properties": {
                    "fen": {"type": "string", "description": "当前局面FEN"},
                    "depth": {
                        "type": "integer",
                        "description": "搜索深度(1-20)，越深越准确但越慢",
                        "default": 15,
                    },
                },
                "required": ["fen"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_opening_book",
            "description": "查询开局库中当前局面的推荐走法",
            "parameters": {
                "type": "object",
                "properties": {"fen": {"type": "string", "description": "当前局面FEN"}},
                "required": ["fen"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_and_explain",
            "description": "验证走步并给出解释",
            "parameters": {
                "type": "object",
                "properties": {
                    "fen": {"type": "string", "description": "当前局面FEN"},
                    "move": {"type": "string", "description": "要验证的ICCS走步"},
                },
                "required": ["fen", "move"],
            },
        },
    },
]

# Implementation Plan

[Overview]
将 K:\llm-xiangqi-main（母项目）的功能更新同步到当前 electron 实现项目中。主要涉及后端 Python 文件（FEN验证、性能优化）和前端 JavaScript 文件（GameStateManager 增强）。

实施分为三个阶段：1) 后端基础文件同步，2) Electron GameStateManager 更新，3) 测试验证。

[Types]

### Python 后端类型定义
无新增类型，仅同步现有类型的实现细节。

### JavaScript 前端类型定义
```javascript
// 新增导出常量和接口
const GAME_STATUS = {
  WAITING: 'waiting',      // 新增
  PLAYING: 'playing',
  FINISHED: 'finished',
};

const PIECE_NAMES = {
  'K': '帅', 'A': '仕', 'B': '相', 'N': '傌', 'R': '俥', 'C': '炮', 'P': '兵',
  'k': '将', 'a': '士', 'b': '象', 'n': '马', 'r': '车', 'c': '砲', 'p': '卒',
};

const ICCS_COLS = 'abcdefghi';  // 新增
```

[Files]

### 新增文件
无

### 需修改文件

#### Python 后端 (src/)
1. **src/core/referee_engine.py**
   - 添加 `_validate_fen_format()` 方法（FEN格式验证）
   - 添加 `FEN_PATTERN` 正则表达式常量
   - 添加 `MAX_FEN_LENGTH` 长度限制常量
   - 添加 `_position_counter` 字典属性（性能优化）
   - 修改 `_parse_fen()` 方法调用验证
   - 修改 `_is_threefold_repetition()` 使用计数器
   - 修改 `reset()` 方法重置计数器
   - 修改 `apply_move()` 更新计数器

2. **src/core/game_controller.py**
   - 添加 `GameEndReasons` 常量类
   - 修改 `get_logger` 使用方式为模块级导入

3. **src/core/state_serializer.py**
   - 无需修改（已与母项目一致）

#### Electron 前端 (electron/src/renderer/js/)
4. **electron/src/renderer/js/GameStateManager.js** (完全重写)
   - 使用 ES6 模块导出替换全局导出
   - 添加 `ICCS_COLS` 常量
   - 添加 `iccsToIndex()` 静态方法
   - 添加 `indexToIccs()` 静态方法
   - 添加 `iccsToWorld()` 静态方法
   - 添加 `getPieceAtIccs()` 实例方法
   - 添加 `getPieceColor()` 静态方法
   - 添加 `getPieceName()` 静态方法
   - 添加 `board` 矩阵属性 (10x9)
   - 添加 `legalMoves` 属性
   - 添加 `resultReason` 属性
   - 添加 `_listeners` Set 结构替换数组
   - 修改 `addListener()` 返回取消订阅函数
   - 修改 `reset()` 初始化逻辑
   - 修改 `_parseFen()` 修复行列映射
   - 修改 `getBoardLayout()` 返回棋子颜色

[Functions]

### Python 函数

1. **新增: `_validate_fen_format(self, fen: str) -> None`**
   - 文件: src/core/referee_engine.py
   - 用途: 验证 FEN 字符串格式合法性
   - 验证: 类型、长度、正则匹配

2. **修改: `_parse_fen(self, fen: str) -> None`**
   - 文件: src/core/referee_engine.py
   - 变更: 开头调用 `_validate_fen_format()`

3. **修改: `_is_threefold_repetition(self) -> bool`**
   - 文件: src/core/referee_engine.py
   - 变更: 优先使用 `_position_counter` 字典

4. **修改: `apply_move(self, iccs_move: str) -> str`**
   - 文件: src/core/referee_engine.py
   - 变更: 更新 `_position_counter`

5. **修改: `reset(self, fen: str) -> None`**
   - 文件: src/core/referee_engine.py
   - 变更: 重置 `_position_counter` 字典

6. **新增: `class GameEndReasons`
   - 文件: src/core/game_controller.py
   - 用途: 游戏结束原因字符串常量

### JavaScript 函数

1. **新增: `static iccsToIndex(iccs) -> [row, col] | null`**
   - 文件: electron/src/renderer/js/GameStateManager.js
   - 用途: ICCS 坐标转棋盘索引

2. **新增: `static indexToIccs(row, col) -> string | null`**
   - 文件: electron/src/renderer/js/GameStateManager.js
   - 用途: 棋盘索引转 ICCS 坐标

3. **新增: `static iccsToWorld(iccs, cellSize) -> {x, y, z}`**
   - 文件: electron/src/renderer/js/GameStateManager.js
   - 用途: ICCS 转 3D 世界坐标

4. **新增: `getPieceAtIccs(iccs) -> string | null`**
   - 文件: electron/src/renderer/js/GameStateManager.js
   - 用途: 获取 ICCS 位置的棋子

5. **新增: `static getPieceColor(pieceChar) -> 'Red' | 'Black' | null`**
   - 文件: electron/src/renderer/js/GameStateManager.js
   - 用途: 获取棋子颜色

6. **新增: `static getPieceName(pieceChar) -> string`**
   - 文件: electron/src/renderer/js/GameStateManager.js
   - 用途: 获取棋子中文名称

7. **修改: `_parseFen() -> void`**
   - 文件: electron/src/renderer/js/GameStateManager.js
   - 变更: 使用 `this.board[9 - row][col]` 正确映射

8. **修改: `reset() -> void`**
   - 文件: electron/src/renderer/js/GameStateManager.js
   - 变更: 初始化 `board`、`legalMoves`、`resultReason`

[Classes]

### Python 类

1. **修改: `RefereeEngine`**
   - 文件: src/core/referee_engine.py
   - 新增属性:
     - `_position_counter: Dict[str, int]` - 位置计数器
   - 新增方法:
     - `_validate_fen_format(fen: str)`
   - 修改方法:
     - `_parse_fen()` - 添加验证
     - `_is_threefold_repetition()` - 优先用计数器
     - `apply_move()` - 更新计数器
     - `reset()` - 重置计数器

2. **新增: `GameEndReasons`**
   - 文件: src/core/game_controller.py
   - 类型: 类常量
   - 属性: RED_PERPETUAL_CHECK, BLACK_PERPETUAL_CHECK, RED_VICTORY, BLACK_VICTORY, DRAW, RESIGNATION_RED, RESIGNATION_BLACK, MAX_TURNS, STALEMATE

### JavaScript 类

1. **修改: `GameStateManager`**
   - 文件: electron/src/renderer/js/GameStateManager.js
   - 导出方式: ES6 export 替换 window 导出
   - 新增静态方法: iccsToIndex, indexToIccs, iccsToWorld, getPieceColor, getPieceName
   - 新增实例方法: getPieceAtIccs
   - 新增属性: board, legalMoves, resultReason, _listeners (Set)
   - 移除属性: listeners (数组)

[Dependencies]

### Python 依赖
无需新增依赖，保持 requirements.txt 不变。

### JavaScript 依赖
无需新增依赖，保持 package.json 不变。

[Testing]

### 测试策略

1. **Python 后端测试**
   - 修改现有测试文件以适应新 API
   - 添加 FEN 验证的边界测试用例

2. **JavaScript 前端测试**
   - 手动测试 GameStateManager 坐标转换
   - 测试 FEN 解析正确性
   - 测试 WebSocket 消息处理

3. **集成测试**
   - 启动 electron 应用验证整体功能
   - 测试 WebSocket 连接和数据同步

### 验证清单
- [ ] FEN 格式验证对非法输入抛出正确异常
- [ ] 三次重复检测性能提升验证
- [ ] GameStateManager ICCS 坐标转换正确
- [ ] FEN 解析后棋子位置正确对应
- [ ] Electron 应用启动无错误
- [ ] WebSocket 消息收发正常

[Implementation Order]

### 实施步骤

1. **Phase 1: 同步后端基础文件**
   - 1.1 更新 src/core/referee_engine.py (FEN验证+计数器)
   - 1.2 更新 src/core/game_controller.py (GameEndReasons)
   - 1.3 验证后端测试通过

2. **Phase 2: 更新 Electron GameStateManager**
   - 2.1 重写 electron/src/renderer/js/GameStateManager.js
   - 2.2 更新导出方式（ES6 module）
   - 2.3 测试坐标转换功能

3. **Phase 3: 集成验证**
   - 3.1 启动 Electron 应用
   - 3.2 验证 3D 棋盘渲染
   - 3.3 验证 WebSocket 数据同步
   - 3.4 测试走步动画

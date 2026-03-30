
# LLM-Xiangqi Electron 便携版
# 本程序是使用electron实现的原始程序的GUI单文件版本

使用了Minimax M2.7实现 

> 📚 基于 [原项目 llm-xiangqi](https://github.com/Laffinty/llm-xiangqi)  
> 📄 查看原项目说明: [README-original.md](./README-original.md)

中国象棋 AI 对战桌面应用 - 单文件 EXE，双击即用！

## 功能特性

- 🎮 **3D 棋盘界面** - Three.js 渲染，支持旋转/缩放视角
- 🤖 **AI 对战** - 支持 DeepSeek、MiMo、MiniMax 等 LLM API
- 📜 **AI 对话日志** - 实时显示 AI 的思考过程和回复
- 🔊 **音效系统** - 走棋、吃子、将军等音效反馈
- 📦 **便携版** - 单一 EXE 文件，无需安装
- 🔧 **零配置** - 输入 API Key 即可开始游戏

## 界面说明

- `/` 或 `/index.html` - 2D 界面 + ASCII 棋盘
- `/3d` - 3D 棋盘界面（推荐）

## 3D 界面功能

### 控制按钮
- 📷 **重置视角** - 恢复相机到默认位置
- 🔊 **音效** - 开启/关闭音效
- ❓ **帮助** - 显示控制说明

### 游戏控制
- 🚀 **启动游戏** - 开始 AI 对战
- ⏹ **停止** - 暂停游戏
- 🔄 **互换双方配置** - 交换红黑双方的 API 配置
- 🆕 **还原棋盘开始新的对局** - 重置棋盘并清空状态

### AI 对话日志
- 🔴 **红方日志** - 显示红方 AI 的系统提示和回复
- ⚫ **黑方日志** - 显示黑方 AI 的系统提示和回复
- 点击标题可展开/折叠日志面板

## 安装依赖

```bash
cd electron
npm install
```

## 开发模式

```bash
npm start
```

## 构建 EXE

```bash
npm run build
```

输出文件: `dist/LLM-Xiangqi.exe`

## 构建说明

1. 确保已安装 Node.js 18+
2. 运行 `npm install`
3. 运行 `npm run build`
4. 等待构建完成（约5-10分钟）
5. 在 `dist` 文件夹中找到 `LLM-Xiangqi.exe`

## 使用方法

1. 双击 `LLM-Xiangqi.exe`
2. 选择 LLM 提供商（DeepSeek/MiMo/MiniMax）或手动配置
3. 输入红方和黑方的 API Key
4. 点击「启动游戏」
5. 观看 AI 对战！

## 项目结构

```
electron/
├── main.js           # 主进程（HTTP 服务器、WebSocket、游戏逻辑）
├── preload.js        # 预加载脚本（安全桥接）
├── package.json      # 项目配置
└── src/
    └── renderer/
        ├── 3d.html       # 3D 界面
        ├── index.html    # 2D 界面
        ├── css/
        │   └── style.css # 样式表
        └── js/
            ├── SceneManager.js      # Three.js 场景管理
            ├── MoveAnimator.js      # 移动动画
            ├── ParticleSystem.js    # 粒子特效
            ├── SoundManager.js      # 音效管理
            ├── WebSocketClient.js   # WebSocket 客户端
            ├── GameStateManager.js  # 游戏状态管理
            └── CompatibilityChecker.js # 兼容性检查
```

## 技术栈

- **前端**: HTML5, CSS3, JavaScript, Three.js (WebGL)
- **后端**: Node.js, Electron
- **通信**: WebSocket
- **AI**: OpenAI 兼容 API (DeepSeek, MiMo, MiniMax 等)

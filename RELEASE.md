# LLM-Xiangqi v1.0.0 Release Notes

## 新增功能

### 🎮 Electron 桌面应用
- 完整的 Electron 桌面应用，支持 Windows 便携版
- 双击即可运行的单文件 EXE

### 🌐 3D 棋盘界面
- 基于 Three.js 的 3D 渲染
- 支持鼠标旋转/缩放视角
- 棋子移动动画
- 粒子特效（移动轨迹、吃子爆炸）
- 音效系统（走棋、吃子、将军）

### 📜 AI 对话日志
- 实时显示红方和黑方 AI 的思考过程
- 可折叠的日志面板
- 区分系统提示和 AI 回复

### 🔄 游戏控制
- 互换双方配置
- 还原棋盘开始新的对局
- 音效开关控制

## 文件变更

### 新增文件
- `electron/` - Electron 桌面应用目录
- `electron/main.js` - 主进程（HTTP/WebSocket/游戏逻辑）
- `electron/preload.js` - 预加载脚本
- `electron/package.json` - 项目配置
- `electron/src/renderer/` - 前端界面和资源
- `src/renderer/3d.html` - 3D 界面
- `src/renderer/css/style.css` - 样式表
- `src/renderer/js/SceneManager.js` - 3D 场景管理
- `src/renderer/js/MoveAnimator.js` - 移动动画
- `src/renderer/js/ParticleSystem.js` - 粒子系统
- `src/renderer/js/SoundManager.js` - 音效管理
- `src/renderer/js/WebSocketClient.js` - WebSocket 客户端
- `src/renderer/js/GameStateManager.js` - 游戏状态管理
- `src/renderer/js/CompatibilityChecker.js` - 兼容性检查
- `README-original.md` - 原项目说明

### 更新文件
- `README.md` - 更新项目文档
- `main.js` - 添加 AI 对话日志发送
- `3d.html` - 添加 AI 日志显示和重置游戏功能

## 技术栈
- **前端**: HTML5, CSS3, JavaScript, Three.js (WebGL)
- **后端**: Node.js, Electron
- **通信**: WebSocket
- **AI**: OpenAI 兼容 API (DeepSeek, MiMo, MiniMax)

## 使用方法
1. 运行 `LLM-Xiangqi.exe`
2. 配置红方和黑方的 API Key
3. 点击「启动游戏」
4. 观看 AI 对战！

## 开发者说明

### 构建 EXE
```bash
cd electron
npm install
npm run build
```

### 开发模式
```bash
cd electron
npm start
```

# LLM-Xiangqi Electron 便携版

中国象棋 AI 对战桌面应用 - 单文件 EXE，双击即用！

## 功能特性

- 🎮 **3D 棋盘界面** - Three.js 渲染，支持旋转/缩放视角
- 🤖 **AI 对战** - 支持 DeepSeek、MiMo、MiniMax 等 LLM API
- 📦 **便携版** - 单一 EXE 文件，无需安装
- 🔧 **零配置** - 输入 API Key 即可开始游戏

## 界面说明

- `/` 或 `/index.html` - 2D 界面 + ASCII 棋盘
- `/3d` - 3D 棋盘界面

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

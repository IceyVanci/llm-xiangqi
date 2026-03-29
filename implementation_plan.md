# Implementation Plan: Electron 便携版应用

## [Overview]

将 LLM-Xiangqi 项目改造为 Electron 单文件便携应用程序，实现一键启动、零配置运行。

**目标：** 创建单一 EXE 文件，用户双击即可运行完整的中国象棋 AI 对战程序，无需安装 Python、Node.js 或其他依赖。

**技术方案：**
- 使用 Electron 作为桌面应用框架
- 将 Python 后端逻辑转换为 Node.js 实现
- 使用 electron-builder 打包为便携式 EXE

## [Files]

### 新建文件
- `electron/package.json` - Electron 项目配置
- `electron/main.js` - Electron 主进程
- `electron/preload.js` - 预加载脚本
- `electron/src/renderer/` - 前端界面
- `electron/build/` - 构建配置

### 修改文件
- `config_gui.html` → 迁移到 `electron/src/renderer/`
- `server.py` → 逻辑迁移到 `electron/src/backend/`
- `web_3d_client/` → 集成到 Electron 应用

### 删除文件
- `server.py` (逻辑迁移)
- `launcher.html` (不再需要)
- `start.bat` / `start.sh` (不再需要)

## [Technical Architecture]

### Frontend (Electron Renderer)
- HTML/CSS/JavaScript
- 3D 渲染 (Three.js)
- WebSocket 客户端

### Backend (Electron Main Process)
- Node.js HTTP 服务器
- WebSocket 服务器
- LLM API 调用 (使用 fetch/axios)

### Data Flow
```
用户双击 EXE 
    → Electron 启动 
    → 内置 HTTP 服务器 (端口 8888)
    → 打开配置界面
    → 用户配置 API Key
    → 启动游戏
    → 3D 棋盘显示
```

## [Dependencies]

### 核心依赖
- `electron` - 桌面应用框架
- `electron-builder` - 打包工具
- `ws` - WebSocket 服务器
- `three` - 3D 渲染
- `axios` - HTTP 请求

### 开发依赖
- `electron-rebuild` - 原生模块编译

## [Build Configuration]

### electron-builder 配置
- Windows: NSIS 便携模式
- 输出: `LLM-Xiangqi.exe`
- 包含所有资源文件

## [Implementation Order]

1. 创建 Electron 项目结构
2. 实现主进程 (HTTP/WebSocket 服务器)
3. 实现预加载脚本
4. 迁移前端界面
5. 集成 3D 棋盘
6. 测试完整流程
7. 配置 electron-builder
8. 构建 EXE 文件

## [Key Decisions]

1. **是否保留 Python 后端？**
   - 方案A: 完全用 Node.js 重写
   - 方案B: 打包 Python 解释器

2. **是否需要内嵌 LLM API？**
   - 是，需要在 Electron 中直接调用 LLM

3. **3D 棋盘处理？**
   - 复用现有 Three.js 代码

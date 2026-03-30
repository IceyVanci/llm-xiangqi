# 修复计划 - Electron 3D 棋盘界面问题

## 概述

修复 Electron 3D 棋盘界面中存在的4个问题：光照显示、走步记录布局、还原棋盘功能和纵向显示。

## 问题分析

### 问题 1: 棋盘光照问题
**位置**: `electron/src/renderer/js/SceneManager.js` - `_initLighting()` 方法

**当前状态**:
- 环境光强度 0.5
- 半球光 0.4
- 主光源强度 1.2
- 补光强度 0.5

**问题**: 光照可能不够均匀，导致棋盘某些区域过暗或过亮

**修复方案**:
1. 增加环境光强度到 0.6
2. 调整主光源位置和角度
3. 添加柔和阴影配置
4. 使用 PCFSoftShadowMap 替代当前阴影类型

---

### 问题 2: 走步记录与 AI 日志叠加
**位置**: `electron/src/renderer/css/style.css`

**当前状态**:
- `#move-history` 使用 `max-height: 200px`
- `.ai-log-section` 没有设置最大高度

**问题**: 两个面板在垂直方向上重叠或显示混乱

**修复方案**:
1. 为 `.history-section` 设置固定的 `max-height` 和 `overflow-y: auto`
2. 为 `.ai-log-section` 设置合适的布局
3. 确保两个区域在侧边栏内正确分配空间

---

### 问题 3: 还原棋盘功能未实现
**位置**: `electron/main.js` 和 `electron/src/renderer/3d.html`

**当前状态**:
- 前端 `resetGame()` 函数存在
- 但服务器端没有处理 `reset_game` 消息类型

**问题**: 点击「还原棋盘」按钮时，前端重置了UI但游戏状态未真正重置

**修复方案**:
1. 在 `main.js` 中添加 `reset_game` 消息处理
2. 重置游戏状态、FEN 字符串、走步历史
3. 通知所有连接的客户端刷新状态

---

### 问题 4: 棋盘纵向显示问题
**位置**: `electron/src/renderer/css/style.css`

**当前状态**:
- `#canvas-container` 使用 `flex: 1`
- `#side-panel` 使用固定宽度 320px

**问题**: 当窗口纵向高度调整时，canvas-container 可能被压缩或溢出

**修复方案**:
1. 确保 `#app` 使用 `height: 100vh`
2. `#canvas-container` 使用 `flex: 1; min-height: 0;`
3. 添加 `overflow: hidden` 防止溢出
4. 确保 canvas 元素正确响应容器大小变化

---

## 文件修改清单

### 需要修改的文件:
1. `electron/src/renderer/js/SceneManager.js`
   - 修改 `_initLighting()` 方法改善光照

2. `electron/src/renderer/css/style.css`
   - 修复布局问题（走步记录、AI日志、纵向显示）

3. `electron/main.js`
   - 添加 `reset_game` WebSocket 消息处理

---

## 修复顺序

1. **先修复布局问题** (CSS) - 最直观
   - 修复纵向显示
   - 修复走步记录和AI日志布局

2. **修复光照问题** (SceneManager.js)

3. **修复还原棋盘功能** (main.js)

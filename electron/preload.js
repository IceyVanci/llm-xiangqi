/**
 * Electron 预加载脚本
 * 在渲染进程和主进程之间建立安全通信
 */

const { contextBridge, ipcRenderer } = require('electron');

// 暴露给渲染进程的 API
contextBridge.exposeInMainWorld('electronAPI', {
    // ========== 配置管理（加密存储） ==========
    
    // 获取保存的配置
    getConfig: () => ipcRenderer.invoke('get-config'),
    
    // 保存配置（API Key 会被加密存储）
    saveConfig: (config) => ipcRenderer.invoke('save-config', config),
    
    // 清除所有配置
    clearConfig: () => ipcRenderer.invoke('clear-config'),
    
    // ========== 原有功能 ==========
    
    // 发送消息到主进程
    send: (channel, data) => {
        ipcRenderer.send(channel, data);
    },
    
    // 接收来自主进程的消息
    on: (channel, callback) => {
        const subscription = (event, ...args) => callback(...args);
        ipcRenderer.on(channel, subscription);
        return () => ipcRenderer.removeListener(channel, subscription);
    },
    
    // 一次性接收消息
    once: (channel, callback) => {
        ipcRenderer.once(channel, (event, ...args) => callback(...args));
    },
    
    // 获取版本
    getVersion: () => ipcRenderer.invoke('get-version'),
});

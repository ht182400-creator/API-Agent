/**
 * Electron 预加载脚本
 * 暴露安全的 API 给渲染进程
 */

const { contextBridge, ipcRenderer } = require('electron');

/**
 * 暴露给渲染进程的 API
 */
contextBridge.exposeInMainWorld('apiPlatform', {
  // 获取应用版本
  getVersion: () => ipcRenderer.invoke('get-version'),
  
  // 获取 Docker 状态
  getDockerStatus: () => ipcRenderer.invoke('get-docker-status'),
  
  // 重启 Docker 服务
  restartDocker: () => ipcRenderer.send('restart-docker'),
  
  // 停止 Docker 服务
  stopDocker: () => ipcRenderer.send('stop-docker'),
  
  // 监听 Docker 状态变化
  onDockerStatus: (callback) => {
    ipcRenderer.on('docker-status', (_, status) => callback(status));
  },
  
  // 监听 Docker 日志
  onDockerLog: (callback) => {
    ipcRenderer.on('docker-log', (_, log) => callback(log));
  },
  
  // 监听 Docker 错误
  onDockerError: (callback) => {
    ipcRenderer.on('docker-error', (_, error) => callback(error));
  },
});

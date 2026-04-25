/**
 * Electron 主进程
 * 负责创建窗口、管理应用生命周期、启动 Docker 服务等
 */

const { app, BrowserWindow, ipcMain, Menu, Tray } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

// 判断是否开发环境
const isDev = require('electron-is-dev');

// 主窗口
let mainWindow = null;
// 系统托盘
let tray = null;
// Docker 进程
let dockerProcess = null;

/**
 * 创建主窗口
 */
function createWindow() {
  // 创建浏览器窗口
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    icon: path.join(__dirname, 'build/icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  // 加载应用
  if (isDev) {
    // 开发环境 - 加载本地服务
    mainWindow.loadURL('http://localhost:3000');
    // 打开开发工具
    mainWindow.webContents.openDevTools();
  } else {
    // 生产环境 - 先启动 Docker，然后加载本地服务
    startDockerAndLoad();
  }

  // 窗口关闭事件
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // 创建系统托盘
  createTray();
}

/**
 * 启动 Docker 并加载页面
 */
function startDockerAndLoad() {
  // 检查 Docker 是否运行
  checkDockerRunning((running) => {
    if (running) {
      // Docker 已运行，直接加载页面
      mainWindow.loadURL('http://localhost');
    } else {
      // Docker 未运行，尝试启动
      startDockerServices();
    }
  });
}

/**
 * 检查 Docker 是否运行
 * @param {Function} callback 回调函数
 */
function checkDockerRunning(callback) {
  const req = http.get('http://localhost/health', (res) => {
    callback(true);
  });
  
  req.on('error', () => {
    callback(false);
  });
  
  req.end();
}

/**
 * 启动 Docker 服务
 */
function startDockerServices() {
  // 显示启动进度
  mainWindow.webContents.send('docker-status', 'starting');
  
  // 执行 docker-compose up -d
  const dockerComposePath = path.join(process.resourcesPath, 'docker');
  
  dockerProcess = spawn('docker-compose', ['up', '-d'], {
    cwd: dockerComposePath,
    shell: true,
  });
  
  dockerProcess.stdout.on('data', (data) => {
    console.log(`Docker: ${data}`);
    mainWindow.webContents.send('docker-log', data.toString());
  });
  
  dockerProcess.stderr.on('data', (data) => {
    console.error(`Docker Error: ${data}`);
    mainWindow.webContents.send('docker-error', data.toString());
  });
  
  dockerProcess.on('close', (code) => {
    if (code === 0) {
      // 启动成功，等待服务就绪
      waitForServices();
    } else {
      // 启动失败
      mainWindow.webContents.send('docker-status', 'error');
    }
  });
}

/**
 * 等待服务就绪
 */
function waitForServices() {
  let attempts = 0;
  const maxAttempts = 30;
  
  const checkInterval = setInterval(() => {
    attempts++;
    
    checkDockerRunning((running) => {
      if (running) {
        clearInterval(checkInterval);
        mainWindow.webContents.send('docker-status', 'ready');
        mainWindow.loadURL('http://localhost');
      } else if (attempts >= maxAttempts) {
        clearInterval(checkInterval);
        mainWindow.webContents.send('docker-status', 'timeout');
      }
    });
  }, 2000);
}

/**
 * 创建系统托盘
 */
function createTray() {
  tray = new Tray(path.join(__dirname, 'build/icon.png'));
  
  const contextMenu = Menu.buildFromTemplate([
    {
      label: '打开主窗口',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      },
    },
    {
      label: '重启服务',
      click: () => {
        restartDockerServices();
      },
    },
    {
      type: 'separator',
    },
    {
      label: '退出',
      click: () => {
        app.quit();
      },
    },
  ]);
  
  tray.setToolTip('API Platform');
  tray.setContextMenu(contextMenu);
  
  tray.on('click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

/**
 * 重启 Docker 服务
 */
function restartDockerServices() {
  const dockerComposePath = path.join(process.resourcesPath, 'docker');
  
  spawn('docker-compose', ['restart'], {
    cwd: dockerComposePath,
    shell: true,
  });
}

/**
 * 停止 Docker 服务
 */
function stopDockerServices() {
  const dockerComposePath = path.join(process.resourcesPath, 'docker');
  
  spawn('docker-compose', ['down'], {
    cwd: dockerComposePath,
    shell: true,
  });
}

// ==================== 应用生命周期事件 ====================

// 应用就绪
app.whenReady().then(() => {
  createWindow();
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// 所有窗口关闭
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// 应用退出前
app.on('before-quit', () => {
  stopDockerServices();
});

// ==================== IPC 通信 ====================

// 获取应用版本
ipcMain.handle('get-version', () => {
  return app.getVersion();
});

// 获取 Docker 状态
ipcMain.handle('get-docker-status', () => {
  return new Promise((resolve) => {
    checkDockerRunning((running) => {
      resolve(running ? 'running' : 'stopped');
    });
  });
});

// 重启 Docker 服务
ipcMain.on('restart-docker', () => {
  restartDockerServices();
});

// 停止 Docker 服务
ipcMain.on('stop-docker', () => {
  stopDockerServices();
});

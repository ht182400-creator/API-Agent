# API Platform - Electron 桌面应用

## 📦 项目简介

将 API Platform 包装为桌面应用程序，方便私有化部署和离线使用。

## 🚀 快速开始

### 开发模式

```bash
# 安装依赖
npm install

# 启动应用 (需要本地已运行 Docker)
npm start
```

### 打包应用

```bash
# Windows
npm run dist:win

# macOS
npm run dist:mac

# Linux
npm run dist:linux

# 所有平台
npm run dist:all
```

生成的安装包位于 `dist/` 目录。

## 📋 功能特性

- ✅ 双击安装，无需命令行
- ✅ 自动检查并安装 Docker Desktop
- ✅ 系统托盘快速访问
- ✅ 自动启动 Docker 服务
- ✅ 内置健康检查
- ✅ 支持离线部署

## 📁 目录结构

```
electron/
├── main.js                    # 主进程
├── preload.js                 # 预加载脚本
├── package.json               # 项目配置
├── build/                     # 打包资源
│   ├── icon.ico              # Windows 图标
│   ├── icon.icns             # macOS 图标
│   ├── icon.png              # Linux 图标
│   ├── installer.nsh         # NSIS 安装脚本
│   └── dmg-background.png    # DMG 背景图
├── dependencies/              # 依赖安装包
│   └── DockerDesktopInstaller.exe
└── dist/                      # 生成的安装包
    ├── API Platform Setup 1.0.0.exe
    ├── API Platform-1.0.0.dmg
    └── API Platform_1.0.0_amd64.deb
```

## ⚙️ 配置说明

### 环境变量

在 `main.js` 中可以配置：

```javascript
// Docker 启动超时时间 (毫秒)
const DOCKER_START_TIMEOUT = 300000; // 5分钟

// 健康检查间隔 (毫秒)
const HEALTH_CHECK_INTERVAL = 2000; // 2秒
```

### 自定义安装步骤

编辑 `build/installer.nsh` 文件，添加自定义安装步骤。

## 🔧 故障排查

### Docker 启动失败

1. 检查 Docker Desktop 是否已安装
2. 检查 WSL2 是否启用 (Windows)
3. 查看日志: `docker logs -f`

### 应用无法打开

1. 检查端口 80 是否被占用
2. 检查防火墙设置
3. 以管理员身份运行

## 📞 技术支持

- **邮箱**: support@api-platform.com
- **文档**: https://docs.api-platform.com
- **GitHub**: https://github.com/your-org/api-platform

## 📄 许可协议

MIT License - 详见 LICENSE 文件

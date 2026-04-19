# Windows 前端安装与测试完整指南

本文档提供在 Windows 系统上设置 API Platform Web 前端环境的完整步骤，面向新人快速上手。

---

## 目录

1. [环境要求](#环境要求)
2. [快速开始](#快速开始)
3. [详细安装步骤](#详细安装步骤)
4. [项目结构](#项目结构)
5. [开发命令](#开发命令)
6. [测试配置](#测试配置)
7. [常见问题](#常见问题)

---

## 环境要求

### 必需软件

| 软件 | 版本 | 下载地址 | 备注 |
|------|------|----------|------|
| Node.js | 18+ LTS | https://nodejs.org/ | 包含 npm |
| Git | 2.0+ | https://git-scm.com/ | 版本控制 |

### 检查安装

打开 PowerShell，运行：

```powershell
# 检查 Node.js 版本
node --version
# 输出示例: v20.10.0

# 检查 npm 版本
npm --version
# 输出示例: 10.2.3
```

---

## 快速开始

复制以下命令，一键完成前端环境设置：

```powershell
# ==================== 第1步：进入前端目录 ====================
cd d:\Work_Area\AI\API-Agent\api-platform\web

# ==================== 第2步：安装依赖 ====================
npm install

# ==================== 第3步：安装 Playwright ====================
npm install -D @playwright/test
npx playwright install --with-deps

# ==================== 第4步：构建验证 ====================
npm run build

# ==================== 第5步：启动开发服务器 ====================
npm run dev

# 浏览器打开: http://localhost:3000
```

---

## 详细安装步骤

### 步骤 1: 打开项目目录

```powershell
# 使用 Windows Terminal 或 PowerShell
cd d:\Work_Area\AI\API-Agent\api-platform\web

# 确认当前目录
pwd
```

### 步骤 2: 安装 npm 依赖

```powershell
npm install
```

**预计耗时**: 3-5 分钟

**输出示例**:
```
added 1256 packages in 3m
62 packages are looking for funding
```

### 步骤 3: 安装 E2E 测试框架

```powershell
# 安装 Playwright
npm install -D @playwright/test

# 安装 Chromium 浏览器
npx playwright install chromium
```

**预计耗时**: 5-10 分钟（首次需要下载浏览器）

### 步骤 4: 构建验证

```powershell
npm run build
```

**预期输出**:
```
vite v5.x.x building for production...
transforming...
✓ 728 modules transformed.
dist/index.html                 0.54 kB
dist/assets/index-xxxxx.js     xxx.xx kB
✓ built in xx.xxs
```

### 步骤 5: 启动开发服务器

**先启动后端**（新终端）:
```powershell
cd d:\Work_Area\AI\API-Agent\api-platform
python -m uvicorn src.main:app --reload --port 8000
```

**启动前端**（另一个终端）:
```powershell
cd d:\Work_Area\AI\API-Agent\api-platform\web
npm run dev
```

**访问应用**: http://localhost:3000

---

## 项目结构

```
api-platform/
├── web/                          # 前端项目
│   ├── src/
│   │   ├── api/                  # API 请求封装
│   │   │   ├── auth.ts          # 认证 API
│   │   │   ├── billing.ts       # 计费 API
│   │   │   ├── client.ts        # HTTP 客户端
│   │   │   ├── quota.ts         # 配额 API
│   │   │   └── repo.ts          # 仓库 API
│   │   ├── components/          # 公共组件
│   │   │   └── Layout.tsx       # 布局组件
│   │   ├── pages/               # 页面组件
│   │   │   ├── admin/          # 管理后台
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── Users.tsx
│   │   │   │   ├── Repos.tsx
│   │   │   │   └── Settings.tsx
│   │   │   ├── auth/            # 认证页面
│   │   │   │   ├── Login.tsx
│   │   │   │   └── Register.tsx
│   │   │   ├── developer/       # 开发者面板
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── Keys.tsx
│   │   │   │   ├── Logs.tsx
│   │   │   │   ├── Quota.tsx
│   │   │   │   └── Billing.tsx
│   │   │   └── owner/           # 仓库所有者
│   │   │       ├── Dashboard.tsx
│   │   │       ├── Repos.tsx
│   │   │       ├── Analytics.tsx
│   │   │       └── Settlement.tsx
│   │   ├── stores/              # 状态管理
│   │   │   ├── app.ts          # 应用状态
│   │   │   └── auth.ts         # 认证状态
│   │   ├── App.tsx             # 根组件
│   │   ├── main.tsx            # 入口文件
│   │   └── vite-env.d.ts       # Vite 类型
│   ├── e2e/                    # E2E 测试
│   │   ├── auth.spec.ts
│   │   ├── navigation.spec.ts
│   │   └── components.spec.ts
│   ├── docs/                   # 前端文档
│   │   ├── E2E_TEST_GUIDE.md
│   │   └── FRONTEND_SETUP.md
│   ├── dist/                   # 构建输出
│   ├── playwright.config.ts    # Playwright 配置
│   ├── vite.config.ts         # Vite 配置
│   ├── tsconfig.json          # TypeScript 配置
│   └── package.json
└── docs/                       # 项目文档
    ├── WINDOWS_TEST_ENVIRONMENT.md
    └── TEST_REPORT.md
```

---

## 开发命令

### 基础命令

```powershell
# 安装依赖
npm install

# 开发模式（热重载）
npm run dev

# 生产构建
npm run build

# 预览构建结果
npm run preview

# 代码检查
npm run lint

# 代码格式化
npm run format
```

### 测试命令

```powershell
# 运行所有 E2E 测试
npx playwright test

# 运行特定测试
npx playwright test e2e/auth.spec.ts
npx playwright test e2e/navigation.spec.ts

# UI 模式（可视化）
npx playwright test --ui

# 调试模式
npx playwright test --debug

# 只用 Chromium
npx playwright test --project=chromium

# 生成 HTML 报告
npx playwright show-report
```

### 快捷脚本（package.json 中定义）

```powershell
npm run test:e2e           # 运行 E2E 测试
npm run test:e2e:ui        # UI 模式
npm run test:e2e:debug      # 调试模式
npm run test:e2e:chromium    # Chromium 单浏览器
npm run test:e2e:report      # 打开测试报告
```

---

## 测试配置

### Playwright 配置 (playwright.config.ts)

```typescript
export default defineConfig({
  testDir: './e2e',           // 测试目录
  baseURL: 'http://localhost:3000',
  timeout: 30000,
  retries: 0,
  use: {
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry',
  },
  projects: ['chromium', 'edge', 'firefox'],
})
```

### 测试环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BASE_URL` | http://localhost:3000 | 测试基础 URL |
| `API_URL` | http://localhost:8000 | API 地址 |

### 设置环境变量

```powershell
# PowerShell
$env:BASE_URL = "http://localhost:3000"
$env:API_URL = "http://localhost:8000"

# 运行测试
npx playwright test
```

---

## 常见问题

### Q1: npm install 失败

**解决方案**:
```powershell
# 清除缓存
npm cache clean --force

# 删除 node_modules
Remove-Item -Recurse -Force node_modules

# 删除 package-lock.json
Remove-Item -Force package-lock.json

# 重新安装
npm install
```

### Q2: Playwright 浏览器下载失败

**解决方案**:
```powershell
# 使用代理
npx playwright install --with-deps --proxy http://127.0.0.1:7890

# 或者手动安装
npx playwright install chromium
npx playwright install firefox
npx playwright install edge
```

### Q3: 端口被占用

**解决方案**:
```powershell
# 查找占用端口的进程
netstat -ano | findstr :3000

# 结束进程 (替换 PID)
taskkill /PID <PID> /F

# 或者使用其他端口启动
# 修改 vite.config.ts 中的 port
```

### Q4: 构建失败

**解决方案**:
```powershell
# 检查 TypeScript
npx tsc --noEmit

# 清理缓存
Remove-Item -Recurse -Force dist
Remove-Item -Recurse -Force .vite

# 重新构建
npm run build
```

### Q5: 测试超时

**解决方案**:
```powershell
# 增加超时时间
npx playwright test --timeout=60000
```

### Q6: 找不到模块

**解决方案**:
```powershell
# 检查 node_modules
dir node_modules | Select-Object -First 10

# 重新安装
npm install
```

---

## 数据库连接信息

| 参数 | 开发环境值 |
|------|-----------|
| 数据库 | api_platform |
| 用户 | api_user |
| 密码 | api_password |
| 连接串 | `postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform` |

---

## API 端点

| 端点 | 说明 | 地址 |
|------|------|------|
| 前端 | Web 应用 | http://localhost:3000 |
| 后端 | REST API | http://localhost:8000 |
| API 文档 | Swagger | http://localhost:8000/docs |

---

## 下一步

1. 启动后端服务: `python -m uvicorn src.main:app --reload --port 8000`
2. 启动前端服务: `npm run dev`
3. 访问 http://localhost:3000
4. 运行测试: `npm run test:e2e`

---

## 相关文档

| 文档 | 路径 |
|------|------|
| 后端测试指南 | `docs/WINDOWS_TEST_ENVIRONMENT.md` |
| 测试报告 | `docs/TEST_REPORT.md` |
| E2E 测试指南 | `web/docs/E2E_TEST_GUIDE.md` |
| 前端变更记录 | `web/docs/CHANGELOG.md` |

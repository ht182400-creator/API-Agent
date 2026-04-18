# Windows 前端安装与 E2E 测试指南

本文档提供在 Windows 系统上设置 API Platform Web 前端环境的完整步骤，包括依赖安装、E2E 测试配置和运行。

---

## 目录

1. [环境要求](#环境要求)
2. [安装前端依赖](#安装前端依赖)
3. [启动开发服务器](#启动开发服务器)
4. [E2E 测试设置](#e2e-测试设置)
5. [运行 E2E 测试](#运行-e2e-测试)
6. [常见问题](#常见问题)
7. [快速命令汇总](#快速命令汇总)

---

## 环境要求

### 软件依赖

| 软件 | 版本要求 | 用途 |
|------|----------|------|
| Node.js | 18+ | JavaScript 运行时 |
| npm | 9+ | 包管理器 |

### 检查 Node.js 版本

```powershell
node --version
# v20.x.x 或更高

npm --version
# 9.x.x 或更高
```

### 安装 Node.js (如果未安装)

1. 访问 https://nodejs.org/
2. 下载 LTS 版本 (18.x 或 20.x)
3. 运行安装程序
4. 验证安装：

```powershell
node --version
npm --version
```

---

## 安装前端依赖

### 1. 进入 web 目录

```powershell
cd d:\Work_Area\AI\API-Agent\api-platform\web
```

### 2. 安装依赖

```powershell
npm install
```

这将安装以下依赖：

| 依赖类别 | 包名 | 用途 |
|---------|------|------|
| 框架 | react, react-dom | UI 框架 |
| 路由 | react-router-dom | 页面路由 |
| UI 组件 | antd, @ant-design/icons | Ant Design 组件库 |
| HTTP | axios | API 请求 |
| 状态管理 | zustand | 状态管理 |
| 图表 | recharts, echarts | 数据可视化 |
| 国际化 | i18next, react-i18next | 多语言支持 |
| 工具 | dayjs | 日期处理 |

### 3. 安装 E2E 测试依赖 (Playwright)

```powershell
# 安装 Playwright 测试框架
npm install -D @playwright/test

# 安装浏览器 (Chromium, Firefox, Edge)
npx playwright install --with-deps
```

> **注意**: 首次运行 `playwright install` 需要下载浏览器，可能需要几分钟。

---

## 启动开发服务器

### 1. 确保后端服务运行

如果需要 API 代理，确保后端服务在 `http://localhost:8080` 运行。

```powershell
# 在后端目录启动
cd d:\Work_Area\AI\API-Agent\api-platform
python -m uvicorn src.main:app --reload --port 8080
```

### 2. 启动前端开发服务器

```powershell
cd d:\Work_Area\AI\API-Agent\api-platform\web
npm run dev
```

应该看到类似输出：

```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: http://192.168.x.x:3000/
  ➜  API:     http://localhost:8080/api/v1
```

### 3. 访问应用

在浏览器中打开 http://localhost:3000

---

## E2E 测试设置

### 1. Playwright 配置

项目根目录已有 `playwright.config.ts` 配置文件。

主要配置：

```typescript
// 测试目录
testDir: './e2e'

// 基础 URL
baseURL: 'http://localhost:3000'

// 浏览器
projects: ['chromium', 'edge', 'firefox']

// 超时
timeout: 30000
```

### 2. 测试文件结构

```
web/
├── e2e/
│   ├── auth.spec.ts        # 认证测试
│   ├── navigation.spec.ts  # 导航测试
│   ├── components.spec.ts  # 组件测试
│   ├── adminLogs.spec.ts   # 日志管理测试
│   └── keys.spec.ts        # API Keys 管理测试
├── playwright.config.ts    # Playwright 配置
└── package.json
```

### 3. 配置 API 代理 (可选)

如果需要测试真实的 API 调用，确保 vite.config.ts 中的代理配置正确：

```typescript
// vite.config.ts
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8080',
      changeOrigin: true,
    },
  },
},
```

---

## 运行 E2E 测试

### 1. 确保服务运行

```powershell
# 终端 1: 启动后端
cd d:\Work_Area\AI\API-Agent\api-platform
python -m uvicorn src.main:app --reload --port 8080

# 终端 2: 启动前端
cd d:\Work_Area\AI\API-Agent\api-platform\web
npm run dev
```

### 2. 运行所有 E2E 测试

```powershell
cd d:\Work_Area\AI\API-Agent\api-platform\web
npx playwright test
```

### 3. 运行特定测试

```powershell
# 只运行认证测试
npx playwright test auth.spec.ts

# 只运行导航测试
npx playwright test navigation.spec.ts

# 运行匹配关键词的测试
npx playwright test -g "登录"
```

### 4. 交互模式 (UI 模式)

```powershell
npx playwright test --ui
```

### 5. 查看测试报告

```powershell
# 在浏览器中打开 HTML 报告
start playwright-report\index.html
```

### 6. 调试模式

```powershell
# 显示所有操作
npx playwright test --debug
```

---

## 常见问题

### 1. Playwright 浏览器安装失败

```powershell
# 使用管理员权限安装
npx playwright install --with-deps
```

如果仍然失败，手动安装浏览器：

```powershell
npx playwright install chromium
npx playwright install firefox
npx playwright install edge
```

### 2. 端口被占用

```powershell
# 查找占用端口的进程
netstat -ano | findstr :3000

# 结束进程 (PID 是最后一列)
taskkill /PID <PID> /F
```

### 3. npm install 失败

```powershell
# 清除缓存
npm cache clean --force

# 删除 node_modules 和 package-lock.json
Remove-Item -Recurse -Force node_modules
Remove-Item -Force package-lock.json

# 重新安装
npm install
```

### 4. 测试超时

增加超时时间：

```typescript
// playwright.config.ts
timeout: 60000,  // 60 秒
```

### 5. 截图和视频

测试报告包含失败时的截图和视频：

```powershell
# 查看报告
start playwright-report\index.html
```

---

## 快速命令汇总

```powershell
# ==================== 设置 ====================

# 1. 安装前端依赖
cd d:\Work_Area\AI\API-Agent\api-platform\web
npm install

# 2. 安装 E2E 测试框架
npm install -D @playwright/test
npx playwright install --with-deps

# ==================== 开发 ====================

# 3. 启动后端 (新终端)
cd d:\Work_Area\AI\API-Agent\api-platform
python -m uvicorn src.main:app --reload --port 8080

# 4. 启动前端 (新终端)
cd d:\Work_Area\AI\API-Agent\api-platform\web
npm run dev

# 5. 访问应用
# 浏览器打开 http://localhost:3000

# ==================== 测试 ====================

# 6. 运行 E2E 测试
npx playwright test

# 7. 运行特定测试文件
npx playwright test e2e/auth.spec.ts

# 8. 查看测试报告
start playwright-report\index.html

# ==================== 构建 ====================

# 9. 构建生产版本
npm run build

# 10. 预览生产构建
npm run preview
```

---

## 测试结果示例

运行 `npx playwright test` 应该看到：

```
  Playwright Test Runner v1.x.x

  Running 28 tests using 3 browsers

  auth.spec.ts
    ✓ 登录页面加载正常 (2.1s)
    ✓ 登录表单验证 (1.5s)
    ✓ 导航到注册页面 (1.2s)
    ...

  navigation.spec.ts
    ✓ 页面标题正确 (0.5s)
    ✓ 响应式布局 - Desktop HD (0.8s)
    ✓ 响应式布局 - Mobile (0.6s)
    ...

  components.spec.ts
    ✓ 按钮组件可用 (0.3s)
    ✓ 输入框组件可用 (0.4s)
    ✓ API Keys 页面 (1.1s)
    ...

  28 passed in 45.2s (3 browsers)
```

---

## 测试覆盖范围

### 已实现的测试

| 模块 | 测试项 | 说明 |
|------|--------|------|
| 认证 | 登录页面加载 | 检查页面正常渲染 |
| 认证 | 表单验证 | 检查空表单提交 |
| 认证 | 导航注册 | 检查跳转功能 |
| 导航 | 页面标题 | 检查标题正确性 |
| 导航 | 控制台错误 | 检查无严重错误 |
| 导航 | 响应式设计 | 测试 4 种视口 |
| 组件 | 按钮/输入框 | 检查组件可用 |
| 组件 | 开发者页面 | 检查各功能页面 |

### 可扩展的测试

| 模块 | 待实现测试 |
|------|-----------|
| 认证 | 完整登录流程 |
| 认证 | 注册流程 |
| 开发者 | API Key 创建/删除 |
| 开发者 | 配额查看 |
| 所有者 | 仓库管理 |
| 管理员 | 用户管理 |

---

## 后续扩展

### 添加更多测试

1. 创建新测试文件：`e2e/new-feature.spec.ts`

2. 添加测试用例：

```typescript
import { test, expect } from '@playwright/test'

test('新功能测试', async ({ page }) => {
  await page.goto('/new-feature')
  // 测试代码
})
```

3. 运行新测试：

```powershell
npx playwright test e2e/new-feature.spec.ts
```

### 集成到 CI/CD

添加 GitHub Actions 工作流：

```yaml
# .github/workflows/e2e.yml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - run: npm install
      - run: npx playwright install --with-deps
      - run: npx playwright test
```

---

## 相关文档

- [Windows 后端测试环境](./WINDOWS_TEST_ENVIRONMENT.md)
- [测试报告](./TEST_REPORT.md)
- [API 文档](../api/)

---

## 附录：错误处理测试

### 测试统一错误提示 UI

```typescript
// e2e/error-handling.spec.ts
import { test, expect } from '@playwright/test'

test.describe('统一错误处理测试', () => {
  test('API 401 错误显示登录提示', async ({ page }) => {
    await page.goto('/developer/keys')
    
    // 等待错误弹窗出现
    await expect(page.getByText('登录已过期')).toBeVisible()
    await expect(page.getByText('请重新登录后继续操作')).toBeVisible()
  })

  test('网络错误显示网络提示', async ({ page, context }) => {
    // 模拟离线状态
    await context.setOffline(true)
    
    await page.goto('/developer/keys')
    await page.waitForTimeout(1000)
    
    // 检查错误提示
    await expect(page.getByText('网络连接失败')).toBeVisible()
  })

  test('重试按钮功能', async ({ page }) => {
    // 模拟 API 失败
    await page.route('**/api/v1/quota/keys', route => {
      route.fulfill({ status: 500, body: 'Server Error' })
    })
    
    await page.goto('/developer/keys')
    
    // 点击重试
    const retryButton = page.getByRole('button', { name: '重试' })
    await expect(retryButton).toBeVisible()
  })
})
```

### 错误场景测试清单

| 错误类型 | 触发场景 | 预期结果 |
|----------|----------|----------|
| 401 认证失败 | Token 过期 | 显示"登录已过期"，提供重新登录按钮 |
| 403 权限不足 | 无权限操作 | 显示"您没有权限执行此操作" |
| 404 资源不存在 | 访问不存在的资源 | 显示"资源不存在" |
| 422 验证失败 | 提交无效数据 | 显示"数据验证失败" |
| 429 请求限流 | 频繁请求 | 显示"请求过于频繁" |
| 500 服务器错误 | 后端异常 | 显示"服务器开小差了" |
| 0 网络错误 | 离线状态 | 显示"网络连接失败" |

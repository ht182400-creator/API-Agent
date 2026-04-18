# 通用API服务平台 - 完整测试方案

## 测试概述

本测试方案涵盖前端 E2E 测试和后端 API 测试，包含正常案例和异常案例。

---

## 目录结构

```
tests/
├── test_auth.py              # 认证模块测试
├── test_billing.py           # 计费模块测试
├── test_repositories.py      # 仓库模块测试
├── test_quota_api.py         # 配额管理 API 测试 [新增]

web/e2e/
├── auth.spec.ts              # 认证 E2E 测试
├── components.spec.ts       # 组件 E2E 测试
├── navigation.spec.ts        # 导航 E2E 测试
├── adminLogs.spec.ts         # 日志管理 E2E 测试
└── keys.spec.ts              # API Keys 管理 E2E 测试 [新增]
```

---

## 一、后端 API 测试

### 1.1 测试环境准备

```bash
# 进入后端目录
cd d:/Work_Area/AI/API-Agent/api-platform

# 安装依赖
pip install pytest pytest-asyncio httpx

# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_quota_api.py -v

# 运行并生成报告
pytest tests/ -v --html=docs/test_report.html --self-contained-html
```

### 1.2 配额管理 API 测试用例

| 用例ID | 测试名称 | 分类 | 预期结果 |
|--------|----------|------|----------|
| TC-001 | 获取 API Keys 列表 - 空列表 | 正常 | 返回空列表 |
| TC-002 | 获取 API Keys 列表 - 有数据 | 正常 | 返回 Keys 列表 |
| TC-003 | 分页功能 | 正常 | 正确分页 |
| TC-004 | 成功创建 API Key | 正常 | 创建成功，返回 Key 和 Secret |
| TC-005 | 创建 HMAC 类型 Key | 正常 | 创建成功 |
| TC-006 | 创建带配额限制的 Key | 正常 | 配额正确设置 |
| TC-007 | 获取 Key 详情 | 正常 | 返回详情 |
| TC-008 | 获取不存在的 Key | 异常 | 返回 404 |
| TC-009 | 更新 Key | 正常 | 更新成功 |
| TC-010 | 禁用 Key | 正常 | 状态变为 disabled |
| TC-011 | 启用 Key | 正常 | 状态变为 active |
| TC-012 | 删除 Key | 正常 | 删除成功 |
| TC-013 | 设置配额限制 | 正常 | 配额更新 |
| TC-014 | 未授权访问 | 异常 | 返回 401 |
| TC-015 | 无效 Token | 异常 | 返回 401 |
| TC-016 | 创建 Key 不提供名称 | 异常 | 返回验证错误 |
| TC-017 | 删除其他用户的 Key | 异常 | 返回 404 |
| TC-018 | 无效的分页参数 | 异常 | 返回 422 |
| TC-019 | 设置零速率限制 | 边界 | 按业务规则处理 |
| TC-020 | 获取配额概览 | 正常 | 返回概览数据 |
| TC-021 | 配额概览 - 无 Keys | 正常 | 返回空列表 |
| TC-022 | 获取使用历史 | 正常 | 返回历史数据 |
| TC-023 | 获取不存在 Key 的历史 | 边界 | 返回空数据 |
| TC-024 | 获取调用日志 | 正常 | 返回日志列表 |
| TC-025 | 带过滤条件的日志查询 | 正常 | 返回过滤结果 |
| TC-026 | 获取使用量最高的仓库 | 正常 | 返回仓库列表 |

---

## 二、前端 E2E 测试

### 2.1 测试环境准备

```bash
# 进入前端目录
cd d:/Work_Area/AI/API-Agent/api-platform/web

# 安装依赖
npm install

# 安装 Playwright（如果尚未安装）
npx playwright install

# 运行所有 E2E 测试
npx playwright test

# 运行特定测试文件
npx playwright test e2e/keys.spec.ts

# 交互模式（推荐）
npx playwright test --ui

# 生成报告
npx playwright test --reporter=html
start playwright-report/index.html
```

### 2.2 API Keys 页面测试用例

#### 正常案例

| 用例ID | 测试名称 | 步骤 | 预期结果 |
|--------|----------|------|----------|
| TC-001 | 页面加载正常 | 访问 /developer/keys | 页面正确加载，创建按钮可见 |
| TC-002 | 点击创建按钮打开弹窗 | 点击创建按钮 | 弹窗正确打开 |
| TC-003 | 成功创建 API Key | 填写表单并提交 | 创建成功，显示 Key |
| TC-004 | 分页功能正常 | 点击下一页 | 正确切换页面 |
| TC-005 | 查看 Key 详情 | 等待列表加载 | 操作按钮可见 |

#### 异常案例

| 用例ID | 测试名称 | 步骤 | 预期结果 |
|--------|----------|------|----------|
| TC-006 | 空名称提交验证 | 不填名称直接提交 | 显示验证错误 |
| TC-007 | 未登录访问 | 清除登录状态后访问 | 跳转登录页 |
| TC-008 | 网络错误处理 | 断开网络后刷新 | 显示错误提示 |
| TC-009 | 快速连续点击 | 快速点击创建按钮多次 | 弹窗只出现一次 |
| TC-010 | 取消按钮功能 | 点击取消 | 弹窗正确关闭 |
| TC-011 | 删除确认对话框 | 点击删除按钮 | 显示确认对话框 |

#### 边界测试

| 用例ID | 测试名称 | 步骤 | 预期结果 |
|--------|----------|------|----------|
| TC-012 | 超长名称输入 | 输入500字符名称 | 按业务规则处理 |
| TC-013 | 特殊字符输入 | 输入 @#$%^&*() 等字符 | 按业务规则处理 |
| TC-014 | 页面响应式布局 | 调整不同视口 | 布局自适应 |

---

## 三、测试数据准备

### 3.1 测试用户

```python
TEST_USER = {
    "email": "test@example.com",
    "password": "TestPassword123"
}
```

### 3.2 测试数据清理

```bash
# 清理测试数据
psql -U api_user -d api_platform -c "DELETE FROM api_keys WHERE key_name LIKE 'Test%';"
psql -U api_user -d api_platform -c "DELETE FROM users WHERE email LIKE '%@test.com';"
```

---

## 四、持续集成

### 4.1 GitHub Actions 配置示例

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx
      - name: Run tests
        run: pytest tests/ -v

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Use Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm ci
      - name: Install Playwright
        run: npx playwright install --with-deps
      - name: Run E2E tests
        run: npx playwright test
```

---

## 五、测试报告

### 5.1 运行测试并生成报告

```bash
# 后端测试报告
pytest tests/ -v --html=docs/test_report.html --self-contained-html

# 前端测试报告
npx playwright test --reporter=html
```

### 5.2 查看测试覆盖率

```bash
# 后端覆盖率
pip install pytest-cov
pytest tests/ --cov=src --cov-report=html

# 查看报告
start htmlcov/index.html
```

---

## 六、日志文件命名规范

### 6.1 当前格式（已更新）

备份文件名格式: `{模块名}_{YYYYMMDD}.log`

示例:
```
logs/
├── backups/
│   ├── api_platform_20260418.log      # 主日志当日备份
│   ├── auth_20260418_143022.log       # 当日第二份备份（带时间戳）
│   ├── billing_20260418.log           # 计费模块当日备份
│   └── quota_20260418.log             # 配额模块当日备份
```

### 6.2 日志配置位置

- 主配置: `src/config/logging_config.py`
- 日志目录: `api-platform/logs/`
- 模块日志: `api-platform/logs/modules/`
- 备份目录: `api-platform/logs/backups/`

---

## 七、故障排查

### 7.1 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 404 错误 | 后端服务未重启 | 重启 uvicorn |
| 401 错误 | Token 过期 | 重新登录 |
| 数据库连接失败 | PostgreSQL 未运行 | 检查数据库服务 |
| 前端代理失败 | Vite 服务未运行 | 启动 `npm run dev` |

### 7.2 重启服务

```powershell
# 停止后端
taskkill /F /IM python.exe

# 重启后端
cd d:/Work_Area/AI/API-Agent/api-platform
python -m uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload

# 重启前端（另一个终端）
cd d:/Work_Area/AI/API-Agent/api-platform/web
npm run dev
```

---

## 八、联系人

如有问题，请联系开发团队。

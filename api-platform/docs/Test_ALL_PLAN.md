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
├── test_payment.py           # 支付 API 测试
└── test_environment_guard.py # 环境隔离与生产安全门控测试 [V1.0 新增]

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
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# 重启前端（另一个终端）
cd d:/Work_Area/AI/API-Agent/api-platform/web
npm run dev
```

---

## 八、环境隔离与支付门控测试（V1.0 新增）

> 对应改造：环境分层 + 生产启动强校验 + 账单环境隔离 + 模拟回调门控。
> 详细设计见 [环境隔离与支付模式设计文档](./ENVIRONMENT_AND_PAYMENT_MODE.md)。

### 8.1 运行方式

```bash
cd d:/Work_Area/AI/API-Agent/api-platform

# 运行全部新增用例
pytest tests/test_environment_guard.py -v

# 仅运行无需数据库的单元用例
pytest tests/test_environment_guard.py -v -k "not Callback"
```

> 说明：`TestPaymentCallbackGuard` 为集成用例，依赖 PostgreSQL（与既有测试一致）；
> 其余用例为纯单元用例，无外部依赖。

### 8.2 用例清单

| 用例ID | 测试名称 | 分类 | 类型 | 预期结果 |
|--------|----------|------|------|----------|
| TC-ENV-001 | 账单环境标识由运行环境决定（与 mock 解耦） | 环境 | 单元 | 非生产→simulation，生产→production |
| TC-ENV-002 | 生产环境识别 | 环境 | 单元 | production/PROD 为真，其余为假 |
| TC-ENV-003 | 非生产环境跳过强校验 | 环境 | 单元 | 不抛异常 |
| TC-ENV-004 | 生产 + 模拟支付 | 安全 | 单元 | 抛 RuntimeError |
| TC-ENV-005 | 生产 + 沙箱网关 | 安全 | 单元 | 抛 RuntimeError |
| TC-ENV-006 | 生产 + 默认密钥 | 安全 | 单元 | 抛 RuntimeError |
| TC-ENV-007 | 生产安全配置 | 安全 | 单元 | 校验通过 |
| TC-ENV-008 | 默认配置非生产 | 环境 | 单元 | is_production 为假 |
| TC-ENV-009 | 不传环境 → 当前环境 | 环境 | 单元 | 等于 current_environment() |
| TC-ENV-010 | 空字符串 → 当前环境 | 环境 | 单元 | 等于 current_environment() |
| TC-ENV-011 | all 通配 | 环境 | 单元 | 返回 all |
| TC-ENV-012 | 合法具体值 | 环境 | 单元 | 原样返回（大小写不敏感） |
| TC-ENV-013 | 非法值降级 | 环境 | 单元 | 降级为当前环境并告警 |
| TC-ENV-014 | 与 settings 一致 | 环境 | 单元 | 两处取值一致 |
| TC-ENV-015 | env_match(all) | 环境 | 单元 | 恒真条件 |
| TC-ENV-016 | env_match(具体值) | 环境 | 单元 | 等值条件，绑定值正确 |
| TC-PAY-GUARD-001 | 生产环境通用回调 | 支付 | 集成 | HTTP 404 |
| TC-PAY-GUARD-002 | 非生产匿名调用 | 支付 | 集成 | HTTP 401 |
| TC-PAY-GUARD-003 | 内部令牌错误 | 支付 | 集成 | HTTP 401 |
| TC-PAY-GUARD-004 | 内部令牌正确 | 支付 | 集成 | 200，订单不存在时返回业务提示 |
| TC-ENV-017 | 充值落库账单 environment == billing_environment | 环境 | 集成(DB) | 开发环境落 `simulation` |
| TC-ENV-018 | 显式传入 environment 时以显式值为准 | 环境 | 集成(DB) | 落库为 `production` |
| TC-ENV-019 | 落库账单可被当前环境命中、另一环境不命中、all 命中 | 环境 | 集成(DB) | 1 / 0 / 1 |
| TC-ENV-020 | 模型默认值改为「跟随环境」的可调用对象 | 环境 | 单元 | `Bill`/`MonthlyBill` 默认值可调用 |
| TC-ENV-021 | 生产环境下默认值为 `production` | 环境 | 单元 | 漏传也不会漏账 |
| TC-ENV-022 | 未显式传 `environment` 时按当前环境**落库** | 环境 | 集成(DB) | development → `simulation` |
| TC-ENV-023 | 写入守卫：生产写 simulation 账单记录 **ERROR** | 环境 | 单元 | 触发 ERROR 日志 |
| TC-ENV-024 | 写入守卫：`environment` 为空时按当前环境补全 | 环境 | 单元 | 补为当前环境 |
| TC-ENV-025 | 响应携带 `X-Environment` / `X-Billing-Environment` | 环境 | 集成 | 头值等于当前环境 |
| TC-ENV-026 | `/health` 暴露环境标识（供前端徽标） | 环境 | 集成 | 含 `billing_environment` / `is_production` |

### 8.3 手工回归清单

| 编号 | 验证项 | 预期 |
|------|--------|------|
| R1 | 开发环境模拟充值 | 余额增加，生成 simulation 账单 |
| R2 | 重复提交同一回调 | 幂等，不重复加钱 |
| R3 | 未登录且无内部令牌调用回调 | 401 |
| R4 | 错误内部令牌调用回调 | 401 |
| R5 | 已登录用户触发他人订单 | 403 |
| R6 | 生产环境调用通用回调 | 404 |
| R7 | 生产环境 mock 未关闭 | 服务拒绝启动 |
| R8 | 生产环境使用默认密钥 | 服务拒绝启动 |
| R9 | `GET /billing/bills` 不传 environment | 仅当前环境数据 |
| R10 | `GET /billing/bills?environment=all` | 返回两个环境数据 |
| R11 | `GET /billing/bills?environment=xxx` | 降级当前环境 |
| R12 | `POST /admin/billing/monthly-bills/generate?environment=all` | 400 拒绝 |

### 8.4 测试环境修复记录（2026-09-15）

修复前 `pytest` 报 `ValueError: I/O operation on closed file` 且收集 0 条用例。根因为两个代码缺陷叠加：

| 缺陷 | 位置 | 修复 |
|------|------|------|
| 包文件误写入 conftest 内容并在顶层 `from src.main import app`，收集阶段即触发应用初始化 | `tests/__init__.py` | 清空为纯包标记，fixtures 统一放 `conftest.py` |
| Windows 分支用 `io.TextIOWrapper(sys.stdout.buffer)` 包裹标准输出，GC 时关闭真实 stdout | `src/config/logging_config.py` | 新增 `create_console_handler()`，改用 `sys.stdout.reconfigure(...)`，不包裹 buffer |

同时修复恢复收集能力后暴露的 26 条历史用例缺陷（`test_user.access_token` 不存在、`/api/v1/quota` 路径错误、`bill_type` 断言值错误）。

**当前状态**：

```bash
cd api-platform
python -m pytest tests/ -v
# => collected 88 items / 88 passed in ~72s
```

详见 [环境隔离与支付模式设计文档](./ENVIRONMENT_AND_PAYMENT_MODE.md) 附录。

---

## 九、联系人

如有问题，请联系开发团队。

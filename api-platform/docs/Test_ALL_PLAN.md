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
├── keys.spec.ts              # API Keys 管理 E2E 测试
└── api-contract.spec.ts      # 前后端联测（API 契约）[新增]

web/src/**/*.spec.ts(x)       # 前端单元测试（Vitest）[新增]
├── src/test/renderWithProviders.tsx  # 组件测试统一挂载助手（Router + ErrorProvider）
├── src/config/permissions.spec.ts   # 权限判定（越权防护第一道门）
├── src/api/client.spec.ts           # 请求层（认证头/统一解包/错误文案/401 自动登出）
├── src/hooks/useDevice.spec.ts      # 响应式断点判定
├── src/pages/auth/Login.spec.tsx    # 登录页（类型→落地页、邮箱/用户名判别、写 store）
├── src/pages/admin/Analytics.spec.tsx          # 分析页冒烟（三数据源 / 报错不白屏）
└── src/pages/admin/analytics/chartData.spec.ts # 图表数据整形纯函数

web/tests/cases/frontend_cases.json  # 前端测试用例库（全量页面清单 + 优先级 + 覆盖状态）[新增]
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

## 二、前端测试（E2E + 单元测试 + 前后端联测）

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

### 2.3 前端单元测试（Vitest）[新增]

```bash
cd d:/Work_Area/AI/API-Agent/api-platform/web
npm run test:unit          # 单次运行（CI 用）
npm run test:unit:watch    # 监听模式（本地开发）
```

**基建**：`vitest.config.ts`（jsdom 环境 + `@vitejs/plugin-react` + `@testing-library/react`）+ `src/test/setup.ts`
（注入 jest-dom 断言，并补齐 jsdom 缺失的 `matchMedia` / `ResizeObserver` / `IntersectionObserver`）。

> ⚠️ 配置中**必须显式排除 `e2e/**`**：那里是 Playwright 用例，混入 vitest 会因缺少 Playwright 运行期而全部报错。

**优先覆盖"越权防护 + 全站请求入口"两类纯逻辑**（影响面最大、最适合用单测锁死语义）。

| 用例ID | 测试名称 | 输入/操作 | 预期结果 |
|--------|----------|-----------|----------|
| TC-FE-PERM-001 | 通配权限放行 | `hasPermission(['*'], SYSTEM_SETTINGS)`；且要求多权限 | 均 `true` |
| TC-FE-PERM-002 | 持有权限命中 | `hasPermission([DEV_API_KEYS], DEV_API_KEYS)` | `true` |
| TC-FE-PERM-003 | 未持有权限 | `hasPermission([DEV_QUOTA], DEV_API_KEYS)` | `false` |
| TC-FE-PERM-004 | 多权限为"与" | 持有 `{DEV_API_KEYS, DEV_QUOTA}`，要求 `{DEV_API_KEYS, SYSTEM_LOGS}` | `false`（every 语义） |
| TC-FE-PERM-005 | 空权限列表（边界） | `hasPermission([], DEV_QUOTA)` | `false` |
| TC-FE-PERM-006 | 空要求列表（边界） | `hasPermission([], [])` | `true`（`[].every()` 语义，改动需同步用例） |
| TC-FE-PERM-007 | 角色权限矩阵关键断言 | 读 `RolePermissions` | super_admin=`['*']`；admin 含 `USER_MANAGE`/`REPO_APPROVE` 且不含 `BILLING_RECHARGE`；developer 含 `OWNER_REPO` 不含 `REPO_APPROVE`；各角色列表非空 |
| TC-FE-PERM-008 | 高等级满足低要求 | `hasRole('admin','developer')` | `true` |
| TC-FE-PERM-009 | 低等级不满足 | `hasRole('user','developer')` | `false` |
| TC-FE-PERM-010 | 同等级满足 | 4 个角色各自 `hasRole(r, r)` | 全 `true` |
| TC-FE-PERM-011 | 数组要求任一满足 | `hasRole('developer', ['admin','developer'])` | `true`（some 语义） |
| TC-FE-PERM-012 | 非法角色（异常输入） | `hasRole('ghost' as Role, 'user')` | `false`（等级按 0） |
| TC-FE-PERM-013 | 配置一致性 | 校验 `UserTypeDefaultRole` / `RoutePermissions` | 映射合法（owner→developer）；路由 path 唯一；userTypes 非空合法；关键路由存在 |
| TC-FE-API-001 | 已登录注入 Bearer | `store.accessToken='token-abc'` 后 GET | 请求头 `Authorization: Bearer token-abc` |
| TC-FE-API-002 | 未登录不发送空 Bearer | 清空 token 后 GET | 无 `Authorization` 头 |
| TC-FE-API-003 | 统一响应解包 | 响应 `{code:0,data:{id:7,name:'repo'}}` | `api.get` 直接返回 `{id:7,name:'repo'}` |
| TC-FE-API-004 | 列表响应原样返回 | 响应 `{items[],pagination{}}`（无 code） | 原样返回 |
| TC-FE-API-005 | 业务错误码非 0 | 响应 `{code:42901,message:'请求过于频繁',request_id:'req-1'}` | reject，且携带 `code/userMessage/request_id` |
| TC-FE-API-006 | 401 自动登出 | 带 token GET 受保护接口返回 401 | `accessToken` 被清空、`isAuthenticated=false` |
| TC-FE-API-007 | 401 不误登出 | POST `/auth/login` 返回 401 | token 保持（登录接口自身失败不触发登出） |
| TC-FE-API-008 | 状态码文案映射（参数化 10 条） | 400/403/404/422/429/500/502/503/504/418（响应体无 message） | 分别得到约定的 `message` + `userMessage`（如 400→"请求参数错误"/"数据验证失败，请检查输入"；418→"请求失败 (418)"） |
| TC-FE-API-009 | 后端 message 优先 | 400 且 `{message:'余额不足，请先充值'}` | `message` = `userMessage` = 后端文案（不被默认文案覆盖） |
| TC-FE-API-010 | FastAPI `detail` 兼容 | 422 且 `{detail:'field required'}` | `message` = `'field required'` |
| TC-FE-API-011 | 网络错误 | adapter 抛 `ERR_NETWORK`（无 response） | `message='网络连接失败'`、`userMessage='网络连接失败，请检查网络'` |
| TC-FE-API-012 | 请求配置错误 | adapter 抛 `ERR_CONFIG`（无 response/request） | `message='请求配置错误'` |
| TC-FE-API-013 | 各方法均解包 | `api.post/put/delete/patch` 各一次 | 均返回解包后的 `{done:true}` |

**当前结果**：`npm run test:unit` → **292 passed**（30 个测试文件 = 29 个组件 spec + `tests/cases/frontend_cases.spec.ts` 用例库自检 7 条），
即 **285 条组件用例**（= 292 − 7），全部登记在 `tests/cases/frontend_cases.json` 的 `meta.stats.cases`，**库中已无 `planned` 项**。
> 上表对应的最初 14 个 spec 口径为：permissions 13 + client 22 + Layout 6 + ErrorContext 13 + useDevice 5 + Login 8 + Analytics 7 + chartData 5 + paymentErrors 16 + ApiTester 8 + ConsumptionDetails 8 + admin/Repos 8 + owner/Repos 9 + Recharge 16 = 144（其中 TC-FE-API-008 参数化展开为 10 条）；此后按用例库清单持续增补至 **285** 条（截至 2026-09-17）。

> ⚠️ **用例有效性由变异检验保障**：`npm run verify:fixes` 会把每个已修复的缺陷**改回缺陷形态**，
> 再跑对应用例 —— 用例必须变红，否则判定为"空测试"。详见 `web/scripts/dev/verify-fixes.mjs`。
**类型检查**：新增 spec 位于 `src/`，纳入 `npm run typecheck`（`tsc --noEmit`）→ 通过。

> 本节只覆盖**工具层**（权限判定 / 请求层）。**页面级**用例见 **§2.5**；
> 全量页面清单、优先级与覆盖状态见用例库 `web/tests/cases/frontend_cases.json`。

### 2.4 前后端联测（API 契约）[新增]

**为什么单独做这一层**：前端单测用 mock adapter、后端测试只保证自身模型自洽 —— 一旦契约改名
（如 `data`→`result`、分页结构变化、token 字段拼写变化），**两边测试都还是绿的，但页面会白屏**。
本层直接打**真后端**，用前端代码中声明的类型去校验真实响应，专门堵这条缝。

```bash
# 前置：后端需在 8000 运行（前端 dev server 由 Playwright webServer 自动拉起/复用）
cd d:/Work_Area/AI/API-Agent/api-platform/web
npx playwright test e2e/api-contract.spec.ts --project=chromium --reporter=list
```

- **跳过策略**：`beforeAll` 探测 `${API_URL}/health`，后端未启动时**整组跳过**（不误报为失败）。
- **账号**：使用 `scripts/init_db_with_data.py` 种子账号；可用 `E2E_ADMIN_EMAIL` / `E2E_ADMIN_PASSWORD` / `API_URL` / `BASE_URL` 覆盖。

| 用例ID | 测试名称 | 请求 | 预期结果 |
|--------|----------|------|----------|
| TC-E2E-API-001 | 存活探针契约 | `GET /health` | 200；含 `billing_environment`（∈`{simulation,production}`）与 `is_production`(bool) —— 前端环境徽标依赖 |
| TC-E2E-API-002 | 就绪探针 | `GET /ready` | 200（DB 必需） |
| TC-E2E-API-003 | 响应头环境标识 | `GET /health` | 含 `x-environment`、`x-billing-environment` |
| TC-E2E-API-004 | 未认证拦截 | `GET /api/v1/auth/me`（无 token） | 401 |
| TC-E2E-API-005 | 登录契约 ↔ 前端 `TokenResponse` | `POST /api/v1/auth/login`（种子账号） | 200；`code=0`；`data.access_token`(str，长度>10)、`refresh_token`(str)、`expires_in`(number) |
| TC-E2E-API-006 | 登录失败可展示 | `POST login`（错误密码） | 非 2xx；响应含 `message` 或 `detail`（否则前端无文案可显示） |
| TC-E2E-API-007 | 当前用户契约 ↔ 前端 `User` | `GET /auth/me`（带 token） | `data.{id:str, email:str, user_type, role, permissions:[]}` |
| TC-E2E-API-008 | 分页契约 ↔ 前端 `PaginatedResponse` | `GET /api/v1/repositories?page=1&page_size=5` | `data.items[]`；`data.pagination.{page,page_size,total,total_pages}` 均为 number 且 `page=1/page_size=5` |
| TC-E2E-API-009 | 参数校验 | `GET /repositories?page_size=1000` | 422（前端按"数据格式不正确"提示） |
| TC-E2E-API-010 | 未知路由 | `GET /api/v1/__not_exists__` | 404/401 |
| TC-E2E-API-011 | CORS 预检（联调必需） | `OPTIONS login` + `Origin=前端源` | 状态 <400 且回显 `access-control-allow-origin` |
| TC-E2E-API-012 | 登出契约 ↔ 前端 `authApi.logout` | `POST /auth/logout`（带 token） | 200；`code=0` |

**当前结果**：**36 passed**（2026-09-16 对真实后端 development / simulation 环境实测；
套件已从最初 12 条扩展至 36 条，覆盖鉴权 / 分页 / 参数校验 / CORS / 登出等契约面）。

### 2.5 前端页面测试（组件级，Vitest）[新增]

**为什么补这一层**：截至 2026-09-15，前端有 **51 个页面/组件**，但单测只覆盖
`permissions` / `client` 两个工具模块 —— **没有任何页面级测试**。后果是：
`tsc --noEmit` 只保证类型自洽，而**页面白屏 / 渲染错位 / 接口没被调用**这类缺陷
只能靠人工点或 E2E 兜（E2E 依赖真实后端与浏览器，跑得慢，不适合当提交前防线）。

**基建（`src/test/renderWithProviders.tsx`）**：统一在 `MemoryRouter + ErrorProvider`
下渲染组件 —— `useError` 在 Provider 外会直接 throw，而页面普遍依赖二者，
手写包裹层既啰嗦又容易漏（漏了表现为测试内白屏，错误信息还不指向真实原因）。

**用例编号**：`TC-FE-<模块>-NNN`（沿用既有 `TC-FE-PERM` / `TC-FE-API` 约定）。
**用例库**：`web/tests/cases/frontend_cases.json` —— 全量 51 个文件按 P0~P3 分级，
逐项标注关键用例与**覆盖状态**，未覆盖项一律可见，避免"没人认领的盲区"。

**覆盖优先级（为什么这么排）**：
1. **P0 入口 / 骨架 / 全局机制** —— 坏了全站不可用：`Login`、`Register`、
   `Layout`（菜单按权限渲染，属**越权可见性**）、`ErrorContext`、`useDevice`；
2. **P1 巨型页面 + 资金/审核链路** —— 改动频繁、影响面大：`Recharge`(2001→**1697**，拆分中)、
   `owner/Repos`(1059→**704**)、`admin/Repos`(924→**589**)、`Analytics`(964→**309**，三者均已拆完)、
   `ApiTester`、`ConsumptionDetails`、`paymentErrors`；
3. **P2 一般业务页**、**P3 展示型组件**。

| 用例ID | 用例 | 被测文件 | 类型 | 状态 |
|--------|------|----------|------|------|
| TC-FE-DEVICE-001~005 | 4 个断点边界 / 布尔标志互斥 / 横竖屏 / resize 同步 / 卸载清监听 | `hooks/useDevice.ts` | 纯逻辑 | ✅ |
| TC-FE-LOGIN-001 | 用户类型 → 落地页映射（含 unknown 兜底） | `pages/auth/Login.tsx` | 纯逻辑 | ✅ |
| TC-FE-LOGIN-002~007 | 渲染 / 空表单被拦截 / 邮箱判别 / 用户名判别 / 成功写 store / 缺 token 不写 store | 同上 | 组件 | ✅ |
| TC-FE-LOGIN-008 | 逐字符真实输入长邮箱不被自动清空截断（已修缺陷的回归） | 同上 | 组件 | ✅ |
| TC-FE-ANA-001~004 | 首屏渲染+三数据源 / 数据落卡片 / 刷新追加请求 / 报错不白屏 | `pages/admin/Analytics.tsx` | 组件 | ✅ |
| TC-FE-ANA-005~007 | 切「趋势分析」出趋势卡片与周期控件 / 切「仓库明细」出表格+行数据+分页总数 / 点「查看明细」开弹窗并加载该仓库趋势 | 同上 | 组件 | ✅ |
| TC-FE-ANA-008 | 明细状态筛选 / 排序字段 / 排序次序变化后带参重查（antd Select 交互） | 同上 | 组件 | ✅ |
| TC-FE-ANA-DATA-001~005 | 图表整形纯函数（null / 对齐 / 补齐 / avgLatency） | `pages/admin/analytics/chartData.ts` | 纯逻辑 | ✅ |
| TC-FE-LAYOUT-001~006 | 各角色菜单可见性（超管/admin/developer/owner/普通用户/未知兜底）：越权入口不得出现 | `components/Layout.tsx` | 纯逻辑 | ✅ |
| TC-FE-LAYOUT-007~008 | 组件渲染菜单入口（DOM 无越权入口）/ 登出清空登录态 | 同上 | 组件 | ✅ |
| TC-FE-CASES-001~007 | 用例库自检：JSON 可解析 / 结构完整 / id 唯一 / file·specFile 真实存在 / specFiles 与磁盘一致 | `tests/cases/frontend_cases.json` | 元测试 | ✅ |
| TC-FE-ERRCTX-001~010 | 状态码分类矩阵 / 业务码区间 / 关键词兜底 / 文案提取与截断 / 认证码映射 / 兜底文案表完整性 | `contexts/ErrorContext.tsx` | 纯逻辑 | ✅ |
| TC-FE-ERRCTX-011~013 | Provider 外抛错 / 认证错误弹窗文案 / 服务器错误弹窗 | 同上 | 组件 | ✅ |
| TC-FE-RECHARGE-001~015 | 套餐/配置/余额并行加载并过滤未启用套餐 / **到账金额（固定赠送 + 比例赠送）** / 套餐下单参数 / 自定义金额上下限（UI 层 min/max）/ 自定义下单参数 / 两者互斥 / 失败不白屏 / 自定义到账计算 / **日志异常不拦截下单** / **不丢单链路（写入暂存 / 恢复并用暂存单号确认 / 超 30 分钟作废清理）** / **取消订单后扫码轮询真正停止** / **组件卸载后定时器统一清理** / **自定义赠送比例按百分比显示** | `pages/developer/Recharge.tsx` | 组件 | ✅ |
| TC-FE-AREPO-001~008 | 列表与各状态统计加载 / 行与状态标签 / 状态筛选 / **通过审核（带备注）** / **拒绝审核（带原因）** / **上线（Modal.confirm）** / 操作后自动刷新 / 失败不白屏 | `pages/admin/Repos.tsx` | 组件 | ✅ |
| TC-FE-OREPO-001~008 | 列表与统计 / 删除经 Popconfirm 确认（未确认不发请求）/ 编辑并行加载端点与限流 / 详情用 slug / **图标上传三分支（非图片拒、200KB 边界、base64 回填）** / 失败不白屏 | `pages/owner/Repos.tsx` | 组件 | ✅ |
| TC-FE-TESTER-001~008 | 渲染与统计 / 分类筛选 / 端点列表 / Key 配置面板 / 请求头占位 / **proxy URL 与 X-Access-Key 正确** / 成功响应与历史 / 失败仍记历史 | `pages/developer/ApiTester.tsx` | 组件 | ✅ |
| TC-FE-CONSUME-001~008 | 汇总统计与仓库明细 / Token 计费模式推断（含反面） / getUsage 失败不白屏 / 切「按日期」带分页查询 / **客户端按日期聚合（同日合并且倒序）** / 明细失败不崩 / 重置回第 1 页 | `pages/developer/ConsumptionDetails.tsx` | 组件 | ✅ |
| TC-FE-PAYERR-001~016 | 支付错误码映射 / 字段别名 / 关键词分类 / 优先级 / 详情提取与截断 / 配置与消息级别 / isPaymentError / 默认导出完整性 | `utils/paymentErrors.tsx` | 纯逻辑 | ✅ |
| TC-FE-ADMINMISC / DEVMISC-001~002 | 其余 21 个页面：首屏渲染 + 报错不白屏（统一骨架） | 各页面 | 组件 | 📋 |

**⚠️ 本层挖出的真实缺陷：4 条，**全部已修复**（详见用例库 `knownDefects` 字段）**：

1. **✅ `Login.tsx` 的自动清空定时器会截断用户输入** —— 挂载后 300/1000/2000ms 各执行一次
   `clearAutofillData()`（为对抗浏览器自动填充）。实测用 `user.type` 逐字符输入
   `admin@example.com`，300ms 的定时器把已输入内容清空，**最终只提交了 `username="com"`**；
   5 字符的 `admin` 因耗时 <300ms 而未受影响（慢速输入 / 移动端 / 弱网真实会踩）。
   **修法**：新增 `userInteractedRef` —— 由 `Form` 的 `onValuesChange` 置位，
   `clearAutofillData()` 首行早返回（**用户一旦交互即停止干预**）。
   **回归用例：`TC-FE-LOGIN-008`**（刻意保留真实 `user.type` 逐字符输入，修复前必失败）。
2. **✅ `Analytics.tsx` 首屏 `getTrend` 重复请求** —— `[]` 与 `[trendPeriod, trendDays]`
   两个 `useEffect` 都会触发它；已从 `[]` 中移除该调用（挂载时由另一个 effect 负责，行为等价），
   首屏只请求一次。**回归断言：`TC-FE-ANA-001`**。
3. **✅ `ErrorContext.parseErrorType` 的超时分支不可达** —— 原写成
   `case 'ECONNABORTED'` / `case 'Network Error'`，实际是拿这两个值与 `status` 比较，
   而 axios 把该错误码放在 **`error.code`** 上 → 分支永不命中，请求超时会被显示为
   "操作失败（未知错误）"而非"网络连接失败"。已在 `switch` 前显式识别
   `ECONNABORTED` / `ETIMEDOUT` / `ERR_NETWORK` / `ERR_CONNECTION_REFUSED`，
   并删除原先不可达的 case。**回归断言：`TC-FE-ERRCTX-001`**。
4. **✅ `Layout` 死代码** —— `developerWithoutReposMenu` 自 V5.0 起无任何引用
   （developer 统一走 `developerWithReposMenu`），`getMenuItems` 的 `userHasRepos` 参数
   也不再影响任何分支。二者已移除，并**连带清理**只为该参数服务的 `hasRepos` 状态、
   `fetchHasRepos()` 与 `/user/has-repos` 请求（少一次无谓请求）。

**运行**：
```bash
cd d:/Work_Area/AI/API-Agent/api-platform/web
npm run test:unit        # 单次运行（当前 292 passed / 30 个测试文件 = 29 组件 spec + 用例库自检）
npm run typecheck        # 新增 spec 位于 src/ 下，自动纳入 tsc --noEmit
```

### 2.6 测试警告预算与回归治理 [2026-09-16 新增]

**警告预算**（`npm run test:budget` + `test-warnings-baseline.json`）：
单元测试只校验断言、不检查 stderr，警告可年复一年堆积（实测曾达 **458 条 / 16 种**）。
机制：警告按种类归一化后与基线比对，**基线外新种类 → 失败**；修好一类就从基线删除
→ **只减不增**。

**治理成果**：458 → **157**（-66%），以下 7 类**彻底清零**并上基线（再出现即失败）：

| 清零项 | 数量 | 备注 |
|---|---|---|
| `Modal.destroyOnClose` | 108 | 改 `destroyOnHidden` |
| `Card.bordered` | 28 | antd v5 默认已无框 |
| `Spin.tip` 误用 | 16 | ⚠️ **真缺陷**：`tip` 单独使用不渲染，12 处 loading 文字用户根本看不到 → 全部改为自行渲染 |
| react-router future flag | 16 | 来源是测试环境的 `MemoryRouter` |
| `Card.bodyStyle` | 8 | 改 `styles.body` |
| 重复 key | 4 | 真实缺陷 |
| rc-collapse children | 2 | 改 `items`（属性是 `label` 不是 `header`） |

**剩余两类（接受，已论证）**：`act`(102，**几乎全部集中在 Recharge spec** —— 该组件重异步
特性所致，非测试写法问题) 与 `jsdom`(62，getComputedStyle 伪元素为环境限制)。
（96→102 / 61→62 的增量来自 D/A/B 轮新增用例，基线已同步。）

**回归与变异检验**（`npm run run verify:fixes` → `scripts/dev/verify-fixes.mjs`）：
把已修复的缺陷**改回缺陷形态**再跑用例 —— 用例必须变红，否则判定为"空测试"。
4 个 Recharge 缺陷的回归用例 **4/4 全部变红**（无空测试）。

**全量回归报告**：`docs/regression-2026-09-16.md` —— 9-15/9-16 两天全部修复项
（后端 B1~B8 / 前端 F1~F12）逐条映射到测试，含负向验证与过程留痕。
结论：后端 269 passed / 前端 144 passed / 契约联测 36 passed，无一回归；
回归过程另抓出并修复 1 个时区敏感 flaky（TC-STATQ-006）。

### 2.7 测试环境与生产的一致性（2026-09-17 修正）

**问题**：`renderWithProviders` 此前只包了 `ConfigProvider theme={{ motion: false }}`，
**没带 `locale`** → 测试跑在 antd **默认英文**下（`main.tsx` 生产是 `zhCN`）。
后果：Modal 按钮是 `OK`/`Cancel`、Table 空态是 `No data` —— 与真实界面的
`确定`/`取消`/`暂无数据` 不符。若用例断言这些文案，等于"测了一个线上不存在的界面"。

**修正**：`renderWithProviders` 加 `locale={zhCN}`，与 `main.tsx` 对齐；
既有 200 余条用例**全部照常通过**（此前无任何用例依赖英文文案）。

**约定**：测试渲染助手必须与 `main.tsx` 的全局 Provider 配置保持一致
（Router future flags / locale / motion）；每加一项就回看一次 `main.tsx`。

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
| TC-TZ-001 | 北京某日半开区间 = 对应 UTC 区间（含亚秒不丢失） | 时区 | 单元 | `[00:00, 次日00:00)` 精确 1 天 |
| TC-TZ-002 | `cst_day_range_utc` 与 `from_date` 两 API 同日结果一致 | 时区 | 单元 | 相等 |
| TC-TZ-003 | `cst_day_start_utc(days_ago=N)` 与区间起点一致 | 时区 | 单元 | 相等 |
| TC-TZ-004 | 北京自然月的 UTC 区间 | 时区 | 单元 | 月首/月末正确 |
| TC-TZ-005 | 所有转换值均为 aware | 时区 | 单元 | `tzinfo is not None` |
| TC-TZ-006 | `cst_date_expr` SQL 显式含 `Asia/Shanghai` | 时区 | 单元 | 编译 SQL 含时区字面量 |
| TC-TZ-007 | **落库**：UTC 9-14 20:00（北京 9-15 04:00）按北京日界归入 9-15，UTC 日界查 9-15 丢失 | 时区 | 集成(DB) | 命中 1 / 0 |
| TC-TZ-008 | **落库**：`cst_date_expr` 分组返回北京日期 9-15 | 时区 | 集成(DB) | `date(2026, 9, 15)` |
| TC-ENV-027 | 对账条件只命中当前环境账单（另一环境同窗口同渠道不命中） | 环境 | 集成(DB) | 1 笔 / 环境=当前 |
| TC-ENV-028 | `generate_bill_no` 存活回归（死代码清理后唯一出口） | 计费 | 单元 | `BILL` + 14 位时间戳 + 6 位随机 |
| TC-PSRC-001 | `GET /payment-config/status` 显示 settings 实际生效值 | 配置 | 集成 | == `settings.payment_mock_mode` |
| TC-PSRC-002 | settings 变化时 `/status` 跟随（同一权威源） | 配置 | 集成 | 跟随变化 |
| TC-PSRC-003 | `GET /detail` 与 `/status` 口径一致 | 配置 | 集成 | 两接口 mock_mode 相等 |
| TC-PSRC-004 | `PUT` 传不同 mock_mode → 400 拒绝 | 配置 | 集成 | 提示含 `PAYMENT_MOCK_MODE` |
| TC-PSRC-005 | `PUT` 传相同值 → 幂等放行 | 配置 | 集成 | 200 |
| TC-PSRC-006 | `DEFAULT_CONFIGS` 不再播种 `payment.mock_mode` | 配置 | 单元 | key 不存在 |
| TC-IP-001 | 白名单未配置/空 = 校验关闭，一律放行 | 支付安全 | 单元 | True（含 unknown） |
| TC-IP-002 | 精确 IP 命中 / 不命中 | 支付安全 | 单元 | True / False |
| TC-IP-003 | CIDR 网段命中（IPv4 + IPv6） | 支付安全 | 单元 | 命中/不命中 |
| TC-IP-004 | fail-closed：来源未知/非法、配置条目非法 | 支付安全 | 单元 | 一律不放行（合法条目不受影响） |
| TC-IP-005 | 多条目 + 空白容错 | 支付安全 | 单元 | 正确判定 |
| TC-IP-006 | `/alipay/callback` 白名单开启且来源不在名单 → 403 | 支付安全 | 集成 | 403 |
| TC-IP-007 | `/alipay/callback` 白名单关闭 → 放行（非 403） | 支付安全 | 集成 | 与改造前一致 |
| TC-IP-008 | `/callback` IP 校验先于鉴权门控 | 支付安全 | 集成 | 403（非 401/404） |
| TC-IP-009 | `/callback` 白名单关闭 → 既有 401 门控（零回归） | 支付安全 | 集成 | 401 |
| TC-STAT-001 | 单小时聚合：计数/成败/成本/时延/tokens 正确 | 统计 | 集成(DB) | 值精确匹配 |
| TC-STAT-002 | 跨小时 + 多仓库按 (repo, hour) 分组 | 统计 | 集成(DB) | 行数与键正确 |
| TC-STAT-003 | **幂等**：重复聚合行数与值不变 | 统计 | 集成(DB) | 1 行 / 值不被累加 |
| TC-STAT-004 | 空区间聚合安全 | 统计 | 集成(DB) | upserted=0 |
| TC-STAT-005 | 唯一约束存在（模型 + 数据库双侧） | 统计 | 集成(DB) | `uq_repo_stats_repo_hour` |
| TC-STAT-006 | `aggregate_recent_hours` 窗口边界 | 统计 | 集成(DB) | 完整历史小时被聚合 |
| TC-STATQ-001 | 无水位（从未聚合）→ 整段实时查询 | 统计查询 | 集成(DB) | `split_window` 返回 `(None, start)`；数值 = 实时基准 |
| TC-STATQ-002 | 水位覆盖整个窗口 → 全走预聚合 | 统计查询 | 集成(DB) | `agg_end == 水位`；数值仍 = 实时基准 |
| TC-STATQ-003 | **混合窗口**（预聚合段 + 实时尾部） | 统计查询 | 集成(DB) | 数值 = 实时全量（4 条 / 1.00 元）—— 阶段 2 最易错分支 |
| TC-STATQ-004 | `repo_ids` 过滤 / 空列表边界 | 统计查询 | 集成(DB) | 只统计指定仓库；`[]` → 全 0（不越权） |
| TC-STATQ-005 | **独立用户数不可加**：同一用户跨 2 小时 | 统计查询 | 集成(DB) | 返回 1（预聚合求和会得 2，属错误） |
| TC-STATQ-006 | 按天分组：预聚合段 + 实时段合并 | 统计查询 | 集成(DB) | 总调用 3 / 成本 0.60；跨 2 个自然日 |
| TC-STATQ-006b | 按小时分组：分段合并后每小时值 | 统计查询 | 集成(DB) | 3 个小时各 1 条，成本合计 0.60 |
| TC-STATQ-007 | 按仓库分组：分段合并 + 成功数 | 统计查询 | 集成(DB) | A: 2 单 0.30 元；B: 1 单且 500 不算成功 |
| TC-STATQ-008 | 首次聚合：水位从最早日志整点初始化并推进到当前整点 | 统计查询 | 集成(DB) | `aggregated_until == 当前整点`；repo_stats 覆盖该小时 |
| TC-STATQ-009 | 历史回填分批推进 | 统计查询 | 集成(DB) | 单轮最多 `max_hours_per_run` 小时；`remaining_hours` 可观测 |
| TC-STATQ-010 | 水位只增不减 | 统计查询 | 集成(DB) | 强制回退被忽略，水位不变 |
| TC-STATQ-011 | **成功口径统一 2xx** | 统计查询 | 集成(DB) | 200/302/500 → success=1、failed=2；预聚合与实时一致 |
| TC-STATQ-012 | 空/倒置窗口与非法分组粒度 | 统计查询 | 集成(DB) | 全 0 / 空列表；非法 period 抛 `ValueError` |

> 对应实现：`src/services/stats_query_service.py`、`src/services/stats_aggregation_service.py`；
> 对应用例库：`tests/cases/stats_query_cases.json`；对应测试：`tests/test_stats_query_service.py`。
> **P1-6 阶段 2/3 核心验收：数值与"直接实时查询 api_call_logs"逐值一致（零回归）。**

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

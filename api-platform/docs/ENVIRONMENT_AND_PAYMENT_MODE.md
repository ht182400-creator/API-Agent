# 环境隔离与支付模式设计文档

**文档编号**：ENV-PAY-API-2026-001
**版本**：V1.1
**状态**：已实施
**关联文档**：[角色权限系统设计文档](./ROLE_PERMISSION_GUIDE.md)、[测试方案](../docs/Test_ALL_PLAN.md)

---

## 1. 背景

平台同时存在两套运行态：

- **模拟（测试）态**：本地开发、联调、预发环境。允许模拟支付、使用默认密钥。
- **生产（真实）态**：真实资金流转。必须关闭模拟支付、使用正式网关与安全密钥。

改造前存在的问题：

| 编号 | 问题 | 风险 |
|------|------|------|
| 1 | `payment_mock_mode` 与环境（`environment`）**完全解耦** | 生产环境可能忘记关闭模拟支付 |
| 2 | `/payments/callback` 在模拟模式下**匿名可调用** | 任何人可伪造回调给账户充值 |
| 3 | 账单列表**自动跟随开关过滤** | 切换环境后，历史模拟/真实数据在界面"消失"，无法对账核对 |
| 4 | 账户/账单/月度账单的环境标识**逻辑分散在多处** | 口径漂移，数据不一致 |
| 5 | 敏感配置使用**默认值**（JWT 密钥、加密密钥、DB 密码） | 生产环境密钥可被猜测，凭证泄露 |
| 6 | `system_configs.payment.mock_mode` 与 `settings.payment_mock_mode` **双数据源** | 运维改错地方，误以为生效 |

**核心结论**：模拟能力不应删除，而应被"**隔离 + 显式 + 失败安全**"。通过"环境分层 + 启动强校验 + 数据隔离 + 回调门控"，实现**模拟测试可继续验证、生产环境不可被误用**。

---

## 2. 设计原则

1. **单一数据源**：账单环境标识统一由 `settings.billing_environment` 提供；该值**由 `ENVIRONMENT` 决定**，与 `payment_mock_mode` 解耦（见 §6.1）。
2. **失败安全（Fail-Fast）**：生产环境配置不安全时，**拒绝启动**，而不是运行时告警。
3. **默认安全**：查询默认只看"当前环境"；跨环境查询必须**显式**指定 `environment=all`。
4. **代码同源、配置隔离**：模拟与生产共用同一套代码，仅通过配置与数据隔离区分。
5. **写操作必须落定**：生成账单等写操作不接受 `all` 通配。

---

## 3. 环境分层模型

```
┌────────────────────────────────────────────────────────────────────┐
│ local / development     → mock=on,  alipay_sandbox=on   （本地开发）  │
│ staging / 预发           → mock=on,  alipay_sandbox=on   （★模拟测试场）│
│ production / 生产        → mock=off, alipay_sandbox=off  （真实支付）  │
└────────────────────────────────────────────────────────────────────┘
                                   │
                    启动时由 validate_for_production() 强校验
                                   │
              不满足 → RuntimeError 中断启动（fail-fast）
```

**关键点**：生产环境**关闭 mock 后**，模拟测试改在 `staging`（或本地）执行，两者互不影响。

---

## 4. 关键配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `environment` | `development` | 运行环境：`development` / `staging` / `production`（兼容 `prod`） |
| `payment_mock_mode` | `true` | 支付模拟模式。**生产必须 `false`** |
| `alipay_sandbox` | `true` | 支付宝沙箱网关。**生产必须 `false`** |
| `debug` | `true` | 调试开关，生产建议 `false` |
| `internal_api_token` | 空 | 非生产环境调用模拟回调接口所需的内部令牌 |
| `jwt_secret_key` | 默认值 | **生产必须更换** |
| `secret_key` | 默认值 | **生产必须更换** |
| `api_key_encryption_secret` | 默认值 | **生产必须更换** |
| `database_url` / `redis_url` | 本地默认值 | **生产必须更换** |

完整模板见 [`api-platform/.env.example`](../.env.example)。

---

## 5. 生产环境启动强校验（Fail-Fast）

实现位置：`src/config/settings.py::validate_for_production()`，于 `src/main.py` 的 `lifespan` 启动阶段调用。

校验项（`environment=production` 时全部生效）：

| 校验项 | 不满足时 |
|--------|----------|
| `payment_mock_mode` 必须为 `false` | 拒绝启动 |
| `alipay_sandbox` 必须为 `false` | 拒绝启动 |
| `debug` 建议为 `false` | 拒绝启动 |
| `jwt_secret_key` 非默认值 | 拒绝启动 |
| `secret_key` 非默认值 | 拒绝启动 |
| `api_key_encryption_secret` 非默认值 | 拒绝启动 |
| `database_url` / `redis_url` 非默认值 | 拒绝启动 |

失败示例：

```
RuntimeError: 生产环境配置校验失败，拒绝启动：
  - PAYMENT_MOCK_MODE 仍为 true：生产环境必须关闭模拟支付
  - JWT_SECRET_KEY 仍为默认值，必须更换为安全值
```

> 非生产环境（development/staging）仅打印告警，不影响启动，保证本地开发与模拟测试不受阻。

---

## 6. 账单环境隔离

### 6.1 环境标识的来源

`bills` 与 `monthly_bills` 的 `environment` 字段取值**由运行环境决定**：

```python
settings.billing_environment
#   environment=production/prod  → "production"
#   其余（development/staging）  → "simulation"
```

> **⚠️ V1.1 修正：与支付模式解耦**
>
> 早期实现为 `payment_mock_mode ? "simulation" : "production"`。这在
> **开发/预发中联调真实（沙箱）支付**时会产生错误归属 —— 关闭 mock 只代表
> "不放行模拟回调"，**并不代表**本地产生的账单属于生产数据，会导致
> **生产账单口径被污染**（本地测试账单混入 production）。
>
> 现在两者职责严格分离：
>
> | 配置项 | 决定什么 |
> |--------|----------|
> | `environment` | 账单数据归属（`billing_environment`） |
> | `payment_mock_mode` | 通用回调 `/payments/callback` 是否放行模拟 |
>
> 因此 `development` + `PAYMENT_MOCK_MODE=false`（本地联调真实支付宝沙箱）
> 产生的账单**仍归属 `simulation`**，不会污染生产口径。

所有**写入**点（账户充值、试用赠送、API 调用扣费、手动充值）统一使用该属性，
避免原先散落在 `account_service` / `user` / `repositories` / `billing` 中的三目表达式造成口径漂移。

### 6.2 环境过滤规则（查询）

统一由 `src/utils/environment.py` 提供：

| 入参 | 结果 | 说明 |
|------|------|------|
| 不传 / 空字符串 | 当前环境 | 默认只查当前态数据（安全默认） |
| `simulation` | simulation | 显式查询模拟数据 |
| `production` | production | 显式查询真实数据 |
| `all` | 不过滤（恒真条件） | 同时查看模拟与真实数据，用于对账与排查 |
| 其他非法值 | 降级为当前环境 | 记录告警，不抛异常、不越权 |

**前后对比**：

| 场景 | 改造前 | 改造后 |
|------|--------|--------|
| 模拟期产生的账单，切到生产后 | 界面看不到 | `?environment=all` 或 `?environment=simulation` 可查 |
| 传入非法环境值 | 静默查空 | 降级为当前环境并告警 |

### 6.3 写操作约束

生成月度账单（`POST /admin/billing/monthly-bills/generate`）为**写操作**，
若传入 `environment=all` 直接返回 `400`，避免生成环境标识为非法的账单。

---

### 6.3 防漏传五层防御（L1~L5）

> 背景：`AccountService.deduct_balance()` 曾漏传 `environment`，而它被"用户升级扣费"、
> "退款"**真实调用** —— 生产环境下这类账单会被静默写成 `simulation`，
> 默认查询看不到（**对账漏账**），且**无任何报错**。

账单环境错误属于典型的"**静默失败**"，因此从根因到界面建立了五层防御：

| 层 | 措施 | 效果 |
|----|------|------|
| **L1 根因** | 模型默认值改为**跟随运行环境**（`default=_current_billing_environment`） | 漏传不再落错：生产→`production`，开发→`simulation` |
| **L2 修复** | 补齐所有活代码漏传点（`deduct_balance` 等） | 源头写清，不依赖默认值 |
| **L3 守卫** | `before_insert` 钩子：为空则补全；**生产写 simulation → ERROR 日志** | 兜住任何漏网，且让问题"发声" |
| **L4 可见** | 启动横幅 + 响应头 `X-Environment` / `X-Billing-Environment` + `/health` 暴露环境 | 程序与人都能感知当前环境 |
| **L5 界面** | 前端顶栏常驻**环境徽标** + 生产环境顶部**红色警示条** | 操作时一眼可见，防误操作 |

**核心设计思想**：

> **默认值必须指向"当前上下文"，而不是某个固定值。**
> 固定值必然在某个环境下成为错误答案 —— 这正是旧实现（`default="simulation"`）的缺陷。

**注意**：若确需在生产库补录历史 `simulation` 数据，L3 记录的 ERROR 属**预期行为**，
可按日志中的 `bill_no` / `user_id` 核对来源。

**长期建议**：`development`/`staging` 与 `production` **分库**。
当前"同一库仅靠 `environment` 字段隔离"是"漏传即静默落错抽屉"的根本土壤。

### 6.4 环境标识使用速查

| 场景 | 用法 |
|------|------|
| 账单写入 | `environment=settings.billing_environment`（省略时由 L1 默认值兜底） |
| 查询过滤 | `resolve_environment(param)` + `env_match(Bill.environment, env)` |
| 前端展示 | `GET /health` → `billing_environment` / `is_production` |
| 脚本/客户端感知 | 响应头 `X-Environment` / `X-Billing-Environment` |
| 静态核查 | 数据库 `information_schema`（勿只靠 grep：跨行写法会漏检） |

### 6.5 分库（环境 ↔ 数据库 隔离）

> 这是"防漏传"的**架构级解法**：各环境使用独立数据库后，
> "漏传导致数据落进另一个环境"的土壤从根上消失（跨库物理不可达）。

#### 库命名约定

| 环境 | 数据库 | 用途 |
|------|--------|------|
| `development` / `staging` | `api_platform_dev` | 本机开发 / 联调 |
| 自动化测试（pytest） | `api_platform_test` | 每用例后 `DROP ALL`，**必须专用** |
| `production` | `api_platform_prod` | 真实生产库（服务器上同名库） |

#### 启动护栏（fail-fast）

`src/config/settings.py::validate_database_separation()` —— **所有环境**启动时执行：

| 场景 | 结果 |
|------|------|
| 非生产环境连到疑似**生产库**（库名含 `prod`） | **拒绝启动**（防误操作生产数据） |
| 生产环境连到疑似**开发/测试库**（库名含 `dev`/`test`/`staging`/`local`） | **拒绝启动**（并入生产强校验） |
| 配置匹配 | 通过 |

**豁免**：`ALLOW_PRODUCTION_DATABASE=true`（仅限确需连接生产库排查的场景）。

#### 创建数据库（Windows 示例）

```powershell
$env:PGPASSWORD='postgres'
$pg = "D:\Program Files\PostgreSQL\16\bin"

# 开发库：新建 + 从原库复制数据
& "$pg\psql.exe"  -h localhost -U postgres -c "CREATE DATABASE api_platform_dev OWNER api_user;"
& "$pg\pg_dump.exe" -h localhost -U postgres -d api_platform -f dump.sql
& "$pg\psql.exe"  -h localhost -U postgres -d api_platform_dev -f dump.sql

# 测试库 / 生产库
& "$pg\psql.exe" -h localhost -U postgres -c "CREATE DATABASE api_platform_test OWNER api_user;"
& "$pg\psql.exe" -h localhost -U postgres -c "CREATE DATABASE api_platform_prod OWNER api_user;"
```

#### 测试用例

| 用例 | 验证 |
|------|------|
| TC-DB-001 | 非生产 + 生产库 → 拒绝启动 |
| TC-DB-002 / 003 | 生产 + dev / test 库 → 判定为问题 |
| TC-DB-004 | 非生产 + dev 库 → 通过 |
| TC-DB-005 | `ALLOW_PRODUCTION_DATABASE=true` 放行 |
| TC-DB-006 | 库名提取（含连接串 query 参数） |
| TC-DB-007 | 当前实际配置通过护栏 |

## 7. 支付回调门控

### 7.1 决策表

| 环境 | 请求条件 | 结果 |
|------|----------|------|
| 生产（mock=off） | 任意 | **404**（通用回调接口下线，真实支付走 `/payments/alipay/callback`） |
| 非生产（mock=on） | 无登录态且无内部令牌 | **401** |
| 非生产（mock=on） | `X-Internal-Token` 不等于配置值 | **401** |
| 非生产（mock=on） | 已登录，但订单不属于该用户 | **403** |
| 非生产（mock=on） | 内部令牌正确，或已登录且订单归属正确 | 200，正常处理回调 |

### 7.2 安全性提升

- 生产环境**彻底下线**通用回调接口（返回 404，不暴露接口存在性）。
- 非生产环境由"匿名可调用"变为**必须登录或持内部令牌**，并**校验订单归属**，防止越权触发他人订单。
- 真实支付链路仍由 `/payments/alipay/callback` 承担（**RSA 验签**已实现），不受本次改造影响。

### 7.3 前端影响

前端充值页 `web/src/pages/developer/Recharge.tsx` 的"模拟支付"按钮调用 `/payments/callback`，
用户在充值时处于**已登录**状态，JWT 自动携带 → 满足门控条件，**前端无需改动**。
生产环境该按钮不会出现（`mock_mode=false`）。

---

## 8. 模拟测试如何验证（操作手册）

> 目标：生产关闭模拟能力后，仍能在非生产环境完整验证支付与账单流程。

### 8.1 本地/预发验证模拟充值

```bash
# 1. 确认环境（非生产）
ENVIRONMENT=development
PAYMENT_MOCK_MODE=true

# 2. 启动服务
uvicorn src.main:app --reload --port 8000

# 3. 前端登录后进入「充值中心」，选择套餐 → 点击「模拟支付」
#    等价于：
#    POST /api/v1/payments/callback
#    Authorization: Bearer <用户JWT>
#    { "payment_no": "PAY...", "transaction_id": "MOCK_xxx", "status": "success" }
```

### 8.2 使用内部令牌（自动化脚本推荐）

```bash
# .env: INTERNAL_API_TOKEN=dev-internal-token
curl -X POST http://localhost:8000/api/v1/payments/callback \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: dev-internal-token" \
  -d '{"payment_no":"PAY2026xxx","transaction_id":"MOCK_1","status":"success"}'
```

### 8.3 支付宝沙箱验证真实链路

```bash
ALIPAY_SANDBOX=true
PAYMENT_MOCK_MODE=false     # 走真实(沙箱)支付：下单 → 沙箱付款 → RSA验签回调 → 补账
```

### 8.4 回归验证清单

| 编号 | 验证项 | 预期 |
|------|--------|------|
| R1 | 开发环境模拟充值 | 余额增加，生成 `environment=simulation` 账单 |
| R2 | 重复提交同一回调 | 幂等，余额不重复增加（`Bill.source_id` 幂等） |
| R3 | 未登录 + 无内部令牌调用回调 | 401 |
| R4 | 错误内部令牌调用回调 | 401 |
| R5 | 用户A 触发用户B 的订单（已登录） | 403 |
| R6 | 生产环境调用通用回调 | 404 |
| R7 | 生产环境 mock 未关闭 | 服务拒绝启动 |
| R8 | 生产环境使用默认密钥 | 服务拒绝启动 |
| R9 | `GET /billing/bills` 不传 environment | 仅当前环境数据 |
| R10 | `GET /billing/bills?environment=all` | 同时返回模拟与真实数据 |
| R11 | `GET /billing/bills?environment=xxx` | 降级当前环境 + 告警日志 |
| R12 | `POST /admin/billing/monthly-bills/generate?environment=all` | 400 拒绝 |

---

## 9. 测试用例索引

新增测试：`api-platform/tests/test_environment_guard.py`

| 用例ID | 名称 | 类型 |
|--------|------|------|
| TC-ENV-001 | 账单环境标识由支付模式唯一决定 | 单元 |
| TC-ENV-002 | 生产环境识别（大小写/prod 兼容） | 单元 |
| TC-ENV-003 | 非生产环境跳过强校验 | 单元 |
| TC-ENV-004 | 生产 + 模拟支付 → 拒绝启动 | 单元 |
| TC-ENV-005 | 生产 + 沙箱网关 → 拒绝启动 | 单元 |
| TC-ENV-006 | 生产 + 默认密钥 → 拒绝启动 | 单元 |
| TC-ENV-007 | 生产安全配置 → 校验通过 | 单元 |
| TC-ENV-008 | 仓库默认配置不判定为生产 | 单元 |
| TC-ENV-009~014 | 环境解析（默认/all/合法/非法/一致性） | 单元 |
| TC-ENV-015 | `env_match` all → 恒真条件 | 单元 |
| TC-ENV-016 | `env_match` 具体值 → 等值条件 | 单元 |
| TC-PAY-GUARD-001 | 生产环境通用回调 404 | 集成 |
| TC-PAY-GUARD-002 | 非生产匿名调用 → 401 | 集成 |
| TC-PAY-GUARD-003 | 内部令牌错误 → 401 | 集成 |
| TC-PAY-GUARD-004 | 内部令牌正确 → 通过门控 | 集成 |

---

## 10. 变更文件清单

### 后端

| 文件 | 变更 |
|------|------|
| `src/config/settings.py` | 新增 `internal_api_token`；新增 `is_production` / `billing_environment` 属性；新增 `collect_production_warnings()` / `validate_for_production()` |
| `src/utils/environment.py` | **新增**：环境解析（`current_environment` / `resolve_environment` / `env_match`） |
| `src/utils/__init__.py` | 导出环境工具 |
| `src/main.py` | 启动阶段打印环境信息 + 调用生产强校验（fail-fast） |
| `src/services/auth_service.py` | 新增 `get_current_user_optional`（可选登录依赖） |
| `src/api/v1/payment.py` | `/payments/callback` 增加生产下线 + 模拟门控 + 订单归属校验 |
| `src/services/account_service.py` | 环境标识改用 `settings.billing_environment` |
| `src/api/v1/user.py` | 试用账单环境标识统一 |
| `src/api/v1/repositories.py` | 调用扣费账单环境标识统一 |
| `src/api/v1/billing.py` | 环境过滤统一（支持 `all`）+ 环境标识统一 |
| `src/api/v1/admin_billing.py` | 环境过滤统一（支持 `all`）+ 写操作拒绝 `all` |
| `.env.example` | **新增**：环境变量模板 |

### 测试

| 文件 | 变更 |
|------|------|
| `tests/test_environment_guard.py` | **新增**：17+ 条环境与门控用例 |

---

## 11. 兼容性与注意事项

1. **前端无需改动**：模拟支付按钮在登录态下调用，自动满足门控。
2. **历史数据不受影响**：`environment` 字段值语义未变（仍是 simulation/production），仅查询口径改为可控。
3. **`system_configs.payment.mock_mode` 仍为遗留配置**：实际生效的开关是 `settings.payment_mock_mode`（环境变量）。建议后续统一为单一数据源（见待办）。
4. **非生产环境告警不影响启动**，避免阻塞本地开发。
5. **生产首次部署务必**：设置 `ENVIRONMENT=production`、`PAYMENT_MOCK_MODE=false`、`ALIPAY_SANDBOX=false`，并替换全部密钥。

### 待办（后续迭代）

- [ ] 收敛 `system_configs.payment.mock_mode` 与 `settings.payment_mock_mode` 双数据源
- [ ] 支付回调补充 IP 白名单校验（支付宝/微信渠道段）
- [ ] 对账/结算任务显式限定 `environment=production`
- [ ] 生产环境审计日志记录"配置校验"事件

---

---

## 附：测试环境修复记录（2026-09-15）

### 问题现象

执行 `python -m pytest tests/` 时输出 `collected 0 items`，并在会话结束时抛出
`ValueError: I/O operation on closed file`，导致**任何用例都无法运行**（`tests/test_auth.py` 等既有用例同样受影响）。

### 根本原因

两个缺陷叠加，属**代码缺陷而非环境问题**：

**缺陷一：`tests/__init__.py` 内容错误**

该文件本应仅作为 Python 包标记（可为空），却被写入了 `conftest.py` 的全部内容，
并在模块顶层执行 `from src.main import app`。
由于 `tests` 是包，pytest 在**收集阶段**导入该包时即触发应用初始化与日志初始化。

**缺陷二：`src/config/logging_config.py` 关闭了真实 stdout**

Windows 分支使用 `io.TextIOWrapper(sys.stdout.buffer, ...)` 包裹标准输出。
`TextIOWrapper` 会**接管底层 buffer 的所有权**，在其被垃圾回收时会关闭真实 `stdout`，
导致 pytest 的 `TerminalReporter` 在 `sys.stdout.isatty()` 处抛出
`ValueError: I/O operation on closed file`，收集流程中断。

### 修复方案

| 文件 | 修复内容 |
|------|----------|
| `tests/__init__.py` | 清空为纯包标记；所有 fixtures 统一由 `tests/conftest.py` 提供 |
| `src/config/logging_config.py` | 新增 `create_console_handler()`：改用 `sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)` 调整编码与行缓冲，**不再包裹 `buffer`**，从根本上避免关闭标准输出；`setup_module_loggers()` 与 `setup_logger()` 均改用该函数 |

### 验证结果

| 阶段 | 收集用例数 | 结果 |
|------|-----------|------|
| 修复前 | 0 | 崩溃，无法运行 |
| 修复后 | 88 | **88 passed / 0 failed**（耗时约 72s） |

### 顺带修复的历史用例缺陷

恢复收集能力后，暴露出 26 条历史用例编写缺陷（非本次改造引入），一并修复：

| 用例 | 问题 | 修复 |
|------|------|------|
| `test_quota_api.py`（24 条） | 直接使用不存在的 `test_user.access_token` 构造请求头 | 在模块内覆盖 `test_user` fixture，动态附加有效 JWT（兼容垫片，注释说明新用例应使用 `auth_headers`） |
| `test_repositories.py::test_get_quota` | 请求路径 `/api/v1/quota` 不存在 | 更正为 `/api/v1/quota/overview` |
| `test_billing.py::test_create_consumption` | 断言 `bill_type == "consumption"` 与实际取值不符 | 更正为 `"consume"` |

### 回归命令

```bash
cd api-platform
python -m pytest tests/ -v          # 全量：88 条
python -m pytest tests/test_environment_guard.py -v   # 环境与支付门控专项
```

---

**文档结束**

# 优化跟踪与待办清单

**文档编号**：OPT-BACKLOG-API-2026-001
**版本**：V1.0
**更新日期**：2026-09-15
**关联文档**：[评审报告](../../项目评审代码评审与优化建议报告.md)、[环境隔离与支付模式](./ENVIRONMENT_AND_PAYMENT_MODE.md)、[安全加固记录](./SECURITY_HARDENING.md)

---

## 0. 使用说明

本清单是**评审建议落地的唯一跟踪入口**。状态约定：

| 状态 | 含义 |
|------|------|
| ✅ 已完成 | 已编码 + 已有测试覆盖 + 已验证 |
| 🚧 进行中 | 已部分实施，尚需补齐 |
| 📋 待办 | 已明确方案，排期待实施 |
| 👤 需人工 | 涉及外部系统/凭据/运维动作，需人工执行 |
| ⏸ 暂缓 | 需产品决策或存在较高回归风险，暂不实施 |

---

## 1. 状态总览

| 编号 | 项目 | 优先级 | 状态 | 说明 |
|------|------|:------:|:----:|------|
| P0-1 | 默认密钥硬编码 | P0 | ✅ 已完成 | 生产启动强校验 fail-fast |
| P0-2 | 模拟支付默认可被利用 | P0 | ✅ 已完成 | 生产下线 + 回调门控 |
| P0-3 | 限流未落地，依赖 DB 计数 | P0 | ✅ 已完成 | Redis 固定窗口 + 内存降级 |
| P0-4 | 密钥/DB 文件进入版本库 | P0 | ✅ 已完成 | 移出索引 + gitignore；**密钥轮换待人工** |
| P0-5 | 仓库转发 SSRF | P0 | ✅ 已完成 | 出站地址校验 + 策略开关 |
| P1-1 | 路由重复挂载/无前缀暴露 | P1 | ✅ 已完成 | 单一注册入口 |
| P1-2 | 模型字段与 Service 漂移 | P1 | ✅ 已完成（部分） | 已修正 RepoService 字段 + 死代码可用化 |
| P1-3 | 权限判断分散 | P1 | ✅ 已完成 | 收敛 `auth_service.check_admin_permission` |
| P1-4 | 巨型文件 | P1 | 📋 待办 | 计划见 §3.1 |
| P1-5 | 缓存层未落地 | P1 | ✅ 已完成（示范） | 缓存基建 + 套餐列表接入，见 §2 |
| P1-6 | 统计实时聚合 | P1 | 📋 待办 | 计划见 §3.2 |
| P1-7 | 根目录脚本污染 | P1 | ✅ 已完成 | 脚本归档 + **node_modules 去跟踪**，见 §2.5 |
| P1-8 | 迁移来源不统一 | P1 | 📋 待办 | 计划见 §3.4 |
| P1-9 | 日志未脱敏 | P1 | ✅ 已完成 | 脱敏工具 + 关键落库点接入 |
| P2-1 | 分页响应结构不一致 | P2 | ✅ 已完成 | superadmin 已扁平化，待全量对齐 |
| P2-2 | 前端无独立 router | P2 | 📋 待办 | 计划见 §3.5 |
| P2-3 | 权限模型双份 | P2 | 📋 待办 | 计划见 §3.5 |
| P2-8 | i18n 未落地 | P2 | 📋 待办 | 计划见 §3.5 |
| P2-9 | 大表无分区 | P2 | 📋 待办 | 计划见 §3.6 |
| P3 | CI/CD、链路追踪、压测 | P3 | 📋 待办 | 计划见 §3.7 |
| 👤-1 | **轮换已泄露的支付宝密钥** | P0 | 👤 需人工 | 见 §4.1 |
| 👤-2 | 清理 git 历史中的密钥 | P1 | 👤 需人工 | 见 §4.2 |

---

## 2. 已完成项摘要（本轮）

### 2.1 P0-3 限流迁移 Redis

| 项 | 内容 |
|----|------|
| 新增 | `src/core/redis_manager.py`（连接单例 + 可用性冷却 + 优雅关闭） |
| 新增 | `src/core/rate_limiter.py`（Redis 固定窗口 + Lua 原子计数 + 进程内降级） |
| 改造 | `RateLimitMiddleware` 落地 IP 维度限流（默认关闭，避免误伤 SPA） |
| 改造 | `AuthService._check_rate_limit` 的 RPM/RPH 走 Redis，不可用回落 DB 计数 |
| 配置 | `RATE_LIMIT_BACKEND` / `RATE_LIMIT_REDIS_PREFIX` / `RATE_LIMIT_IP_ENABLED` / `RATE_LIMIT_IP_PER_MINUTE` / `RATE_LIMIT_EXEMPT_PATHS` |
| 测试 | `tests/test_rate_limit_redis.py`（18 条） |

**行为保证（无回归）**：Redis 不可用或显式配置 `RATE_LIMIT_BACKEND=database` 时，行为与改造前完全一致（数据库计数）。

### 2.2 P1-9 日志脱敏

| 项 | 内容 |
|----|------|
| 新增 | `src/utils/sanitize.py`（键名识别 + 值内联掩码 + 深度/条目/长度上限） |
| 接入 | `api_call_logs.request_params`（仓库转发 2 处）、`audit_logs` 系统配置变更新旧值、`RepoService._log_api_call` |
| 测试 | `tests/test_sanitize.py`（41 条） |

### 2.3 P1-5 缓存基建

| 项 | 内容 |
|----|------|
| 新增 | `src/core/cache.py`（`cache_get/set/get_json/set_json/delete/delete_prefix`，全程优雅降级） |
| 接入 | `GET /payments/packages`（TTL 300s），套餐创建后前缀失效 |
| 配置 | `CACHE_ENABLED` / `CACHE_DEFAULT_TTL` / `CACHE_KEY_PREFIX` |
| 测试 | `tests/test_cache.py`（12 条） |

> **安全决策记录**：`GET /superadmin/configs` **刻意不做缓存**——系统配置包含支付宝私钥、API 密钥等敏感值，
> 缓存会把密钥复制到 Redis，扩大泄露面。如需缓存，应先实现"按 `is_encrypted` 分流"再评估。

### 2.5 第四轮：仓库卫生 + 双重防护 + 就绪探针

| 编号 | 内容 | 产出 |
|------|------|------|
| **P1-7** | 根目录脚本治理：正式工具迁入 `scripts/`、26 个调试脚本迁入 `scripts/dev/`（`git mv` 保留历史）、生成产物归档到 `logs/artifacts/` | `scripts/dev/README.md` |
| **P1-7（加深）** | **`web/node_modules` 去跟踪**：原 **16,977 个文件**被提交（占 web 跟踪文件 99%），现为 **0**；新增 `web/.gitignore` | `api-platform/web/.gitignore` |
| **N-1** | 仓库 `endpoint_url` **写入侧**校验：`_validate_endpoint_url()` 在创建/更新时即拦截非法地址，与请求侧形成双重防护；同时修复 `RepositoryCreate.endpoint_url` **被接收但未落库**的缺陷 | `src/api/v1/repositories.py` |
| **N-8** | `/ready` 就绪探针：DB 为必需依赖、Redis 默认非强依赖（`READY_REQUIRE_REDIS`）；与 `/health`（存活）职责分离；默认免限流 | `src/main.py`、`src/config/settings.py` |
| 测试 | 新增 15 条用例 | `tests/test_repo_endpoint_guard.py` |

**仓库卫生收益**：`api-platform/web` 跟踪文件数 **17,122 → 145**；根目录由 40+ 文件收敛为配置与入口文件。

### 2.6 第五轮：修复"测试清空开发库"及连带的数据时间缺陷（N-10 / N-11 / N-12）

> 本轮由一次**真实事故**触发：例行冒烟时 `/api/v1/payments/packages` 返回 500，
> 报错为 `关系 "recharge_packages" 不存在` —— 排查发现**开发库被测试套件清空了**。

| 编号 | 问题 | 影响 | 修复 |
|------|------|------|------|
| **N-10** | `tests/conftest.py` 的 `TEST_DATABASE_URL` 默认指向**开发库** `api_platform`，而 `test_engine` fixture 每个用例后执行 `Base.metadata.drop_all` | **跑一次 `pytest` 即清空开发库全部 30 张表**（已实测发生） | 默认改为 `api_platform_test`；新增**安全护栏**：库名不含 `test` 时抛出 `RuntimeError` 拒绝运行（除非 `ALLOW_NON_TEST_DATABASE=1` 显式放行） |
| **N-11** | `role` / `system_config` / `pricing_config` / `notification` / `audit_log` / `adapter` / `user_operation_log` 使用 `Column(DateTime)`（无时区）+ `default=get_utc_now()`（**aware** UTC） | 这些表的插入**必然报错** `can't subtract offset-naive and offset-aware datetimes`（开发库重建时即在 `roles` 处失败） | **补齐遗漏的 `timezone=True`**，统一为项目既有唯一方案 `DateTime(timezone=True)` + `get_utc_now()`（见 §2.7 纠正说明） |
| **N-12** | `scripts/init_db_with_data.py` 中 `now = datetime.now()`（本地时间）写入 UTC 列 | 种子数据时间偏差 **8 小时** | 改为 `datetime.now(timezone.utc)`（aware UTC，语义明确，不依赖会话时区） |

**恢复动作**：创建 `api_platform_test` 库 → 重建开发库（`python scripts/init_db_with_data.py --drop`）→ 重跑测试验证隔离。

**验证结果**：

| 检查项 | 结果 |
|--------|------|
| `pytest tests/ -q` | **213 passed** |
| 跑完测试后开发库 | **30 张表 / 5 用户 / 5 角色**（完好，未被清空） |
| `/api/v1/payments/packages` | 500 → **200** |
| `/ready` | 200（DB up / Redis down 非强依赖） |

**教训**：测试库与开发库**必须物理隔离**，且应有护栏防止误指向；这也解释了此前"用户表查询为空"的现象。

### 2.7 时区方案的纠正说明（重要）

> 本节记录一次**方向性纠正**：修复 N-11 时曾引入自创的 `get_utc_now_naive()`，
> 经复核项目既有文档与代码后**已回退**，改为对齐项目既有唯一方案。

**权威依据**：

| 来源 | 结论 |
|------|------|
| `api-platform/docs/BUG_FIXES.md`「时区问题说明」 | "系统采用 **UTC 内部存储 + 本地时间显示**"、"数据库统一用 UTC 存储是最佳实践"、"当前实现是正确的" |
| 项目现有代码 | 20+ 个时间列**已统一**为 `Column(DateTime(timezone=True), default=get_utc_now())`（users / repositories / bills / api_keys / payments …） |
| `MEMORY.md` 技术约定 #1 | 全后端统一 UTC（`datetime.now(timezone.utc)` / `get_utc_now()`） |

**结论**：这 7 个模型的时间列**只是漏写了 `timezone=True`**，属既有 UTC 改造的遗漏，
**不是**"需要引入 naive UTC 新方案"。自创第三套方案会造成语义分裂，故已回退。

**最终做法**：

- 删除自创的 `helpers.get_utc_now_naive()`
- 全部时间列统一为 `Column(DateTime(timezone=True), default=get_utc_now())`
- 数据库层面 **100% 使用 `TIMESTAMP WITH TIME ZONE`**（72 列，`naive=0`）
- 种子脚本 `now` 改为 **aware UTC**（`datetime.now(timezone.utc)`，不依赖会话时区）

**顺带修复的同类隐患**（同一根因，均已修正）：

| 位置 | 问题 |
|------|------|
| `notification.read_at` | 被赋 `datetime.now(timezone.utc)`（aware）却声明为 naive 列 → 插入报错 |
| `notification.expire_at`、`adapter.last_health_check` | 同上，naive 列 |
| `pricing_configs.valid_from` / `valid_until` | **跨行写法**遗漏；且 `PricingConfig.is_valid()` 用 `datetime.now(timezone.utc)` 与其比较 → **aware 比 naive 必然抛 `TypeError`** |

> ⚠️ 核查提示：`valid_from/valid_until` 使用跨行 `Column(\n DateTime, ...)` 写法，
> 单行 `grep "Column(DateTime,"` 会漏检。**最终依据请以数据库 `information_schema.columns` 为准**：
>
> ```sql
> SELECT count(*) FILTER (WHERE data_type='timestamp without time zone') AS naive_cols
> FROM information_schema.columns WHERE table_schema='public';
> ```

### 2.8 账单环境与支付模式解耦（设计修正）

> 触发：启动日志暴露 `Environment=development` 却 `BillingEnvironment=production`
> （因 `.env` 中 `PAYMENT_MOCK_MODE=false`）。

**问题**：`billing_environment` 原先由 `payment_mock_mode` 派生：

```python
return "simulation" if self.payment_mock_mode else "production"   # 语义错位
```

`payment_mock_mode` 描述的是"**通用回调是否放行模拟**"，与"**账单数据是否属于生产**"是两件事。
后果：本地/预发联调真实（沙箱）支付时关闭 mock，会让本地账单被标记为 `production`，
**污染生产账单口径**（对账、月度账单会混入测试数据）。

**修正**：改为由运行环境决定，两者职责分离。

```python
@property
def billing_environment(self) -> str:
    return "production" if self.is_production else "simulation"   # 由 ENVIRONMENT 决定
```

| 配置项 | 职责 |
|--------|------|
| `ENVIRONMENT` | 决定账单数据归属（`billing_environment`） |
| `PAYMENT_MOCK_MODE` | 决定通用回调 `/payments/callback` 是否放行模拟 |

**涉及文件**：`src/config/settings.py`、`src/utils/environment.py`（注释）、
`docs/ENVIRONMENT_AND_PAYMENT_MODE.md` §6.1、根 `README.md` §13.6。

**新增/改写测试（数据库记录级）**：

| 用例 | 验证内容 |
|------|----------|
| TC-ENV-001（改写） | 非生产 + `mock=false` → 仍为 `simulation`（验证解耦） |
| TC-ENV-017 | 充值经 `AccountService.add_balance` 落库，**查库确认** `environment == billing_environment`（开发环境必为 `simulation`） |
| TC-ENV-018 | 显式传 `environment` 时以显式值为准（补录/迁移场景） |
| TC-ENV-019 | 落库账单能被「当前环境」命中、不被另一环境命中、`all` 可命中 |

**验证结果**：`tests/test_environment_guard.py` **25 passed**；全量 **216 passed**；
开发库 2 条种子账单均为 `simulation`（与新规则一致，**无需数据迁移**）。

### 2.9 账单环境「防漏传」五层防御（L1~L5 全套实施）

> 触发：排查发现**真实漏洞** —— `AccountService.deduct_balance()` 漏传 `environment`，
> 而它被 `api/v1/user.py`（用户升级扣费）与 `payment_service`（退款）真实调用。
> 生产环境下这类账单会被静默写成 `simulation`，默认查询看不到 → **对账漏账且无报错**。

#### 2.9.1 排查结果

| 写入点 | 活代码 | 是否传 `environment` |
|--------|--------|---------------------|
| `account_service.deduct_balance()` | ✅ 活（升级扣费 / 退款） | ❌ 漏传 → **已修复** |
| `billing_service.py`（6 处 `Bill(`） | ⚠️ 死代码（类无实例化） | ❌ 全部漏传 → **已补齐** |
| `repo_service._deduct_balance()` | ⚠️ 废实现（`account_id` 字段不存在，必抛错） | ❌ → **已加废弃标注**（不修补，见下） |
| `add_balance()` / `user.py` 试用 ×2 / `repositories.py` | ✅ 活 | ✅ 已传（原本正确） |

**根因**：`Bill.environment` / `MonthlyBill.environment` 的 `default="simulation"` **硬编码** ——
漏传时任何环境都落 `simulation`。

> 为什么 `repo_service._deduct_balance()` 只加标注不修补：它同时缺少 3 个 NOT NULL 字段
> （`user_id` / `bill_no` / `balance_before`）且字段名错误（`account_id`），**补 1 个
> `environment` 并不能让它可用**；修补需推测业务意图，风险大于收益。
> 建议单独排期**删除**该废实现，届时同步移除其调用点。

**✅ 调用链取证结论（2026-09-15 补充）：确认为死代码链**

```text
RepoService（类）                    ← 全项目 0 处实例化（仅在 services/__init__.py 被导出）
  └─ call_repository()               ← 全项目 0 处调用（仅定义）
       └─ _process_billing()         ← 仅被上面的 call_repository 调用
            └─ _deduct_balance()     ← 构造 Bill(account_id=...) → 字段不存在，必抛 TypeError
```

**取证方式**：

- `Select-String -Pattern 'RepoService'`（全部 `.py`）→ 仅命中 `repo_service.py:32` 类定义 + `services/__init__.py` 的导出语句
- `Select-String -Pattern 'call_repository'` → 仅命中 `repo_service.py:267` 方法定义本身
- `Select-String -Path src/api/v1/*.py -Pattern 'RepoService|repo_service\.'` → **0 命中**

**结论**：真实仓库转发与扣费由 `src/api/v1/repositories.py` 承担（该实现**正确**传入 `environment`）。
`RepoService` 是**被取代的旧实现**。

**清理建议**（单独排期，非本轮）：

1. 删除 `call_repository()` + `_process_billing()` + `_deduct_balance()` 三者；
2. 评估 `RepoService` 其余方法（`get_repository` 等）是否可一并删除 —— 该类**无任何实例化**，理论上整体可删；
3. 若暂不删除，至少保持现有 `⚠️ 废弃实现` 标注，**禁止新代码参照**。

**✅ 已执行清理（2026-09-15）**

- 工具：`scripts/dev/remove_dead_repo_service_code.py`（一次性脚本，按方法名定位删除，可复现）
- 删除范围：自 `async def call_repository(` 至 `async def get_repo_stats(` 之前的**连续区块，共 289 行**，含：
  `call_repository` / `check_rate_limit` / `_build_auth_headers` / `_log_api_call` / `_process_billing` / `_deduct_balance`
- 连带清理因删除而失效的导入：`httpx`、`selectinload`、`Account/Bill/Quota`、`QuotaExceededError`、`RateLimitError`、
  `RepositoryUnavailableError`、`RepositoryTimeoutError`、`AdapterResponse`、`sanitize`
- 保留：`BaseAdapter` / `HTTPAdapter` / `GRPCAdapter`（`__init__` 的 `_adapters` 仍在用）
- 验证：`py_compile` 通过；`RepoService` 可正常导入，剩余 7 个方法；**全量 230 passed**；lint 0 问题
- 备份：原文件已备份到 `%TEMP%\repo_service.py.bak`

> 备注：`RepoService` 类整体仍**无任何实例化**（仅 `services/__init__.py` 导出），其剩余方法目前也无调用方。
> 是否整类删除需结合后续规划决定（可能作为"服务层标准实现"保留）。

#### 2.9.2 五层防御

| 层 | 措施 | 实现位置 |
|----|------|----------|
| **L1 根因** | 模型默认值改为**跟随运行环境**（`default=_current_billing_environment`），不再硬编码 `simulation` | `src/models/billing.py` |
| **L2 修复** | 补齐活代码漏传（`deduct_balance` 增加 `environment` 参数与解析）；`billing_service` 6 处批量补齐 | `account_service.py` / `billing_service.py` |
| **L3 守卫** | `before_insert` 钩子：为空则按当前环境补全；**生产环境写入 simulation 账单 → ERROR 日志** | `src/models/billing.py` |
| **L4 可见** | 启动环境横幅（终端）；所有响应加 `X-Environment` / `X-Billing-Environment`；`/health` 暴露环境信息；CORS `expose_headers` | `src/main.py` / `src/core/middleware.py` |
| **L5 界面** | 前端顶栏**常驻环境徽标**（测试=橙 / 生产=红）+ 生产环境顶部**红色警示条** | `web/src/components/Layout.tsx` / `Layout.module.css` / `vite.config.ts`（新增 `/health` 代理） |

**设计要点**：

- **默认值必须指向"当前上下文"，而不是固定值** —— 固定值必然在某个环境下变成错误答案。
- 账单环境错误属于"**静默失败**"（数据不报错，只是落进另一个环境），因此 L3 必须让它"发声"。
- 补录历史 simulation 数据到生产库时，L3 的 ERROR 属**预期**，可按日志中的 `bill_no` / `user_id` 核对。

#### 2.9.3 测试与验证

| 用例 | 验证内容 |
|------|----------|
| TC-ENV-020 | 模型默认值为「跟随环境」的可调用对象 |
| TC-ENV-021 | 生产环境下默认值为 `production` |
| TC-ENV-022 | **落库验证**：未传 `environment` 时按当前环境写入 |
| TC-ENV-023 | 守卫：生产写 simulation 账单记录 ERROR |
| TC-ENV-024 | 守卫：`environment` 为空时补全 |
| TC-ENV-025 | 响应头 `X-Environment` / `X-Billing-Environment` |
| TC-ENV-026 | `/health` 暴露 `billing_environment` / `is_production` |

**实测结果**：

- `tests/test_environment_guard.py` → **32 passed**
- 全量 → **223 passed**（此前 216）
- `/health` → `{"environment":"development","billing_environment":"simulation","is_production":false,...}`
- 响应头 → `X-Environment: development` / `X-Billing-Environment: simulation`
- 启动横幅在 development / production 下显示不同（生产为 `!!! PRODUCTION !!!` 警示）

#### 2.9.4 长期建议

**分库**：`development`/`staging` 与 `production` 使用独立数据库。
当前是"同一库仅靠 `environment` 字段隔离"，这正是"漏传即静默落错抽屉"的根本土壤。
分库后环境由连接串决定，可从架构上消除该类问题（涉及部署与数据迁移，需单独排期）。

### 2.10 前端类型错误：被「语法错误」掩盖的 48 项既有债务（✅ 已全部修复）

> 触发：修复 `src/config/permissionHooks.ts`（**JSX 写在 `.ts` 里**）的语法错误后，
> `tsc --noEmit` 从"4 个错误"暴增到 **48 个错误 / 23 个文件**。

#### 2.10.1 根本原因（重要机制）

TypeScript 的 `tsc` **一旦发现语法错误（syntactic diagnostics），就会跳过全部语义（类型）检查**。
因此：

```
permissionHooks.ts 含 JSX（.ts 不允许）
        ↓
产生语法错误 TS1110 / TS1161
        ↓
tsc 跳过所有语义诊断  →  只报那 4 个语法错误
        ↓
项目里积累的 48 个类型错误「全部隐身」
```

**为什么之前完全没暴露**：该文件**从未被任何代码 import**（0 引用），
vite/esbuild 只做转译、不做类型检查，因此开发/构建全程无感。

**修复**：`git mv src/config/permissionHooks.ts src/config/permissionHooks.tsx`（重命名后语法错误消失）。

> 💡 **教训**：`tsc --noEmit` 必须纳入 CI。只要工程里存在 1 个语法错误，
> 整个项目的类型检查就形同虚设 —— **一个语法错误能让 48 个类型错误隐身**。

#### 2.10.2 错误分类（48 项）

**A. 疑似运行时真 Bug（建议优先，共 14 项）**

| 文件 | 问题 | 风险 |
|------|------|------|
| `pages/admin/AdminMonthlyBills.tsx(23)` | `adminApi` 未从 `api/superadmin` 导出 | **页面运行时崩溃** |
| `hooks/useDevice.ts(208)` | 访问 `tablet`，但类型只有 `table` | 取到 undefined |
| `pages/developer/RepoDetail.tsx(573)` ×2 | `api_docs_url` 不存在（应为 `docs_url`） | 显示 undefined |
| `pages/developer/Recharge.tsx(533,557)` ×2 | 状态比较 `"completed"` 与联合类型无交集 → **恒为 false** | 逻辑永不生效 |
| `pages/developer/Recharge.tsx(373)` | `created_at_timestamp` 不存在 | 显示异常 |
| `pages/auth/Login.tsx(149,184)` ×2 | 表单字段 `email` 不存在（实际为 `identifier`） | 提交取值为 undefined |
| `pages/auth/Login.tsx(147)` | 构造的 user 缺 `permissions` | 类型/权限异常 |
| `pages/developer/ApiTester.tsx(166,190)` ×2 | `User.name` 不存在 | 显示 undefined |
| `pages/developer/CreateRepo.tsx(120)` | `Repository.message` 不存在 | 错误提示异常 |
| `config/repos/logistics.config.ts(6)` / `weather.config.ts(8)` | 找不到模块 `../../../types/api-tester` | **模块缺失** |
| `pages/admin/DevTools.tsx(44)` | `{filename, content}` 不是 `BlobPart`（应 `JSON.stringify`） | 下载内容异常 |

**B. 类型不严谨（运行基本正常，共约 24 项）**

- antd `Table.columns` 的 `align: string` 应为字面量类型 → `ConsumptionDetails.tsx`(6) / `Usage.tsx`(3) 等
- `Layout.tsx(125,142)`：`label` 不在 `MenuDividerType`（antd 分割线不支持 label）
- `pages/admin/Users.tsx(54)`：查询参数 `user_status` 不在类型内
- `pages/owner/Repos.tsx(152)`：`logo_url` 不在 `UpdateRepoConfigRequest`
- `pages/auth/Register.tsx(85)`：`string` 不能赋给 `'user'｜'owner'｜'developer'`
- `pages/PaymentSuccess.tsx(71)`：`PaymentStatus` 与 `SetStateAction<PaymentStatus>` 不兼容
- `pages/developer/Billing.tsx(23)` / `owner/Settlement.tsx(9)`：`Account` 未从 `api/billing` 导出
- `api/client.ts(77)`：`Type 'any' is not assignable to type 'never'`
- `utils/logger.ts(370-373)` ×4：spread 参数需元组类型
- `config/permissions.ts(71)` / `config/permissionHooks.tsx(106)`：`"*"` 通配符未纳入 `PermissionKey`
- `pages/developer/Billing.tsx(421)`：RangePicker `onClear` 属性
- `pages/developer/Recharge.tsx(809,869,1116)`：`payment_method` / `status` 联合类型不匹配
- `pages/developer/Recharge.tsx(1968)`：`(showError?) => Promise<void>` 赋给 `MouseEventHandler`

**C. 环境/依赖缺失（2 项）**

| 项 | 说明 |
|----|------|
| `pages/developer/Recharge.tsx(110,129)`：`Cannot find namespace 'NodeJS'` | `@types/node` 未纳入 tsconfig `types` |
| `types/api-tester` 模块缺失 | `src/config/repos/*.config.ts` 引用了一个不存在的类型目录 |

#### 2.10.3 建议

1. **把 `tsc --noEmit` 加入 CI / pre-commit**（否则此类债务会持续隐身）；
2. 按 A → B → C 的顺序修复，A 类属功能性 Bug；
3. 修复前先确认各 API 类型的"唯一出口"（如 `Account` 应从哪个模块导出），避免各处重复定义。

#### 2.10.4 ✅ 修复记录（2026-09-15，48 → 0）

**验证结果**：`npx tsc --noEmit` **0 错误**；`npm run build`（`tsc && vite build`）**通过**，4002 modules transformed。

**关键修复（按根因归类）**：

| 根因类型 | 代表案例 | 修法 |
|----------|----------|------|
| **类型名写错/不存在** | `Billing.tsx`/`Settlement.tsx` 导入 `Account`（实际叫 `UserAccount`）；`RepoDetail.tsx` 用 `repo.api_docs_url`（实际 `docs_url`）；`ApiTester.tsx` 用 `user.name`（`User` 无此字段） | 改用正确的类型名/字段名 |
| **属性名冲突导致 `never`** | `client.ts` 用 `AxiosError & { code?: number }` —— `AxiosError` 自带 `code?: string`，交叉后变 `never` | 改为 `Omit<AxiosError, 'code'>` |
| **残留的错误导入** | `AdminMonthlyBills.tsx` 导入不存在的 `adminApi`（实际用 `billingApi`），且该导入**无处使用** | 删除该 import |
| **重名但结构不同的类型** | `PaymentSuccess.tsx` 自定义 `PaymentStatus` 与 `api/payment.ts` 同名不同构 → API 返回值无法赋值 | 改为 `interface PaymentStatus extends ApiPaymentStatus` |
| **枚举值不存在** | `Recharge.tsx` 用 `status: 'completed'`（实际枚举为 `'paid'`）；`PaymentSuccess` 同理 | 改用正确枚举值；删除恒 false 的冗余比较 |
| **后端已支持但前端类型漏声明** | `admin.ts` 缺 `user_status`（后端 `admin.py` 支持）；`repo.ts` 缺 `logo_url`（后端 `RepositoryUpdate` 支持）；`PaymentStatus` 缺 `created_at_timestamp` | 补类型声明 / 改为解析已有的 `created_at` |
| **"修了一半"** | `useDevice.ts` 的 `BREAKPOINTS` 已改 `tablet`，但函数参数类型仍是 `table`（而函数体用 `values.tablet`） | 补齐参数类型 |
| **路径多一级** | `config/repos/*.config.ts` 用 `'../../../types/api-tester'`（解析到 `web/types/`，不存在） | 改为 `'../../types/api-tester'` |
| **缺失联合类型成员** | `permissions.ts` 的 `PermissionKey` 未含通配符 `'*'` | 联合类型补 `｜ '*'` |
| **antd 类型要求字面量** | 多处 `align: 'right'` 被推断为 `string`（要求 `AlignType`） | 加 `as const` |
| **antd 不支持的 prop** | `divider` 上写 `label`；`RangePicker` 上写 `onClear` | 移除无效 prop |
| **rest 参数展开报错** | `logger.ts` 的 `log.debug = (...args) => logger.debug(...args)`（首参是具名参数） | 显式声明首参 `(message, ...args)` |
| **blob 传错对象** | `DevTools.tsx` 把 `{ filename, content }` 整个传给 `Blob` | 取 `content` 字段，用 `filename` 作下载名 |
| **表单字段名与取值不一致** | `Login.tsx` 表单字段为 `identifier`，代码却读 `values.email`（恒 `undefined`） | 改用 `values.identifier` |
| **类型收窄** | `Register.tsx` 的 `user_type: string` → 联合类型；`Recharge.tsx` 的 `paymentMethod: string` → `'wechat'｜'alipay'｜'bankcard'` | 收窄为字面量联合 |

> 💡 **附带收益**：`weather.config.ts` 在修正模块路径后**新暴露** 4 个 `options.value` 类型错误（number 传给了 `string`），
> 说明该文件此前因模块解析失败而**完全未被类型检查**。
> 现已修正 `types/api-tester.ts` 的 `options.value` 为 `string | number`（与同处 `defaultValue` 的联合类型一致）。

### 2.11 分库落地（环境 ↔ 数据库 隔离）

> 承接 §2.9.4 的长期建议：从"同一库靠字段隔离"升级为**各环境独立数据库**，
> 从根本上消除"漏传/配错导致数据落进另一个环境"的土壤。

**新建数据库**：

| 环境 | 数据库 | 说明 |
|------|--------|------|
| development / staging | `api_platform_dev` | 已从原 `api_platform` 复制全部数据（30 表 / 5 用户 / 2 账单 / 3 仓库） |
| 自动化测试 | `api_platform_test` | 既有；每用例后 `DROP ALL` |
| production | `api_platform_prod` | 新建（真实生产库位于服务器，本地同名库仅作模拟） |

**代码护栏**（`src/config/settings.py`）：

- 新增 `database_name` 属性（从 `DATABASE_URL` 提取库名）
- 新增 `collect_database_separation_issues()` / `validate_database_separation()`
- 规则：
  - 生产环境禁止连接疑似开发/测试库（库名含 `dev` / `test` / `staging` / `local`）
  - **非生产环境禁止连接疑似生产库（库名含 `prod`）** ← 最关键，防误操作生产数据
- 豁免开关：`ALLOW_PRODUCTION_DATABASE=true`
- `src/main.py` lifespan 中调用 → **所有环境 fail-fast**

**配置变更**：

- `.env` 的 `DATABASE_URL` → `api_platform_dev`
- `.env.example` 新增「4.1 分库约定」；并修正一处**已过时说明**（原写"PAYMENT_MOCK_MODE 决定账单 environment"，实际 V1.1 起已解耦）

**测试**：新增 `TC-DB-001~007`（7 条）。

**实测结果**：`database_name = api_platform_dev`、`environment = development`、
`separation_issues = []`、`/health` 正常、全量 **230 passed**。

> ⚠️ 原 `api_platform` 库**保留未删**（作为数据备份），确认无误后可手工删除。

### 2.12 类型检查纳入自动化防线（三层）

> 承接 §2.10 的教训：**只要工程里存在 1 个语法错误，`tsc` 就会跳过全部语义检查**。
> 因此"类型检查能被真正执行"本身必须成为**机制**，而不能靠人记得跑。

#### 三层防线

| 层 | 载体 | 触发时机 | 说明 |
|----|------|----------|------|
| ① 命令入口 | `api-platform/web/package.json` → `npm run typecheck` | 手动 | 统一调用方式，避免各处写 `npx tsc --noEmit` |
| ② **本地提交** | `.githooks/pre-commit` | `git commit` | **本次新增的关键防线**；仅当提交涉及 `api-platform/web/src/**/*.ts(x)` 时执行；未装 `node_modules` 时跳过并提示 |
| ③ CI | `.github/workflows/cicd.yml` → `test-frontend` job | push / PR 到 main·develop | **早已存在**，但项目为本地开发、未触发过 Actions，故此前形同虚设 |

#### 为什么重点是本地 hook

CI 中其实**一直有** `npx tsc --noEmit`（`cicd.yml` 第 124-127 行），
但它只在 push / pull_request 时运行；本项目纯本地开发 → 从未执行 → 48 个类型错误得以长期积累。
**本地提交环节才是真正能拦住问题的位置。**

#### 交付物

| 文件 | 说明 |
|------|------|
| `api-platform/web/package.json` | 新增 `"typecheck": "tsc --noEmit"` |
| `.githooks/pre-commit` | 仓库内 hook 脚本（LF 换行，纳入版本控制） |
| `.git/hooks/pre-commit` | 本机转发器（76 B），指向 `.githooks/pre-commit`，**当前机器立即生效** |
| `.gitattributes` | 新增 `.githooks/* text eol=lf`，避免 Windows 下 CRLF 导致 `bad interpreter: /bin/sh^M` |
| `api-platform/scripts/dev/setup_git_hooks.bat` | 一键启用（设置 `core.hooksPath`），供换机器 / 他人使用 |

> 说明：`core.hooksPath` 属**本地 Git 配置**、不随 clone 分发，
> 故同时提供"仓库内 hook + 启用脚本 + 文档"三条路径。

#### 验证结果（实测）

| 场景 | 结果 |
|------|------|
| 提交涉及前端变更、类型正确 | hook 执行 `tsc` → 通过 → 放行（`HOOK_EXIT=0`） |
| 提交涉及前端变更、**存在类型错误** | hook **拒绝**（`HOOK_EXIT=1`），打印错误位置与操作提示 |
| 提交不涉及前端 TS/TSX | 跳过检查（不拖慢后端/文档提交） |
| 未安装 `node_modules` | 跳过并提示（不阻断） |

### 2.4 P1-2 字段对齐（部分）

- `RepoService.call_repository`：`repo.status != "active"` → `!= "online"`；`repo.adapter_type` → `repo.adapter_id`；
  `repo.endpoint` → `repo.endpoint_url`（原字段不存在，方法一旦被调用必然报错）。
- 该方法同时接入 SSRF 校验。
- 遗留：该方法目前**仍无调用方**（死代码）。见 §3.1 处置建议。

---

## 3. 待办项详细计划

### 3.1 P1-4 巨型文件拆分 📋

| 文件 | 现状 | 拆分方案 | 风险 |
|------|------|----------|------|
| `src/api/v1/repositories.py` | ≈ 78KB / 2300+ 行 | 按子域拆为 `repositories/`（crud / endpoints / limits / approval / proxy）包 | 高（同文件大量共享辅助函数，需先抽 `_shared.py`） |
| `src/services/payment_service.py` | ≈ 44KB | 拆为 `payment/`（packages / alipay / callback / query） | 中 |
| `web/src/pages/developer/Recharge.tsx` | ≈ 76KB | 拆组件 + 抽 `useRechargeFlow` Hook | 中 |
| `web/src/pages/owner/Repos.tsx` | ≈ 38KB | 拆为列表/表单/详情三个组件 | 中 |
| `web/src/pages/admin/Analytics.tsx` | ≈ 34KB | 拆图表组件 | 低 |

**建议做法**：每次只拆一个文件，拆分后跑全量测试（当前 198 条）+ 前端构建 + 手工回归对应页面；
`repositories.py` 建议放在最后，并先补齐该模块的测试覆盖。

**并行建议**：`RepoService.call_repository` 为死代码，建议在第 3.1 步中**直接删除**（连同 `services/__init__.py` 的导出），
或改为内部薄封装委托到 `repositories.py` 的实现，避免两套转发逻辑并存。

---

### 3.2 P1-6 统计预聚合 📋

**问题**：`dashboard/stats`、`analytics/*` 直接对 `repositories` / `accounts` / `api_keys` / `api_call_logs` 做实时 `COUNT/SUM/GROUP BY`，数据量增长后会拖垮主库。

**方案**（分三步，逐步落地）：

1. **落库**：复用已有 `repo_stats` 表，新增定时任务（APScheduler，已有依赖）按小时聚合 `api_call_logs` → `repo_stats`；
2. **读切换**：`analytics` 的"趋势/排行"类接口优先读 `repo_stats`，缺失时回落实时查询；
3. **缓存**：聚合结果写 Redis（TTL 60s），进一步降低库压（可复用 `src/core/cache.py`）。

**验收标准**：
- 造 10 万条 `api_call_logs`，`GET /api/v1/analytics/overview` P95 < 200ms；
- 聚合任务幂等（重复执行不产生重复统计）。

**风险**：统计口径变更需同步前端文案；建议先在 staging 验证数值一致性。

---

### 3.3 P1-7 根目录脚本治理 📋

**现状**：`api-platform/` 根目录存在 `check_*.py`、`debug_*.py`、`test_*.py`、`migrate_*.py`、`*.txt` 等 20+ 临时脚本。

**方案（保守，避免破坏现有习惯）**：

1. 新建 `scripts/dev/`，将根目录临时脚本**移动**过去（保留文件名，不删代码）；
2. 根目录只保留 `README.md` / `Makefile` / 配置文件 / 明确的正式入口脚本；
3. 在 `scripts/dev/README.md` 说明这些脚本的用途与使用前提；
4. `.gitignore` 已忽略 `pytest_run.txt` / `diag*.txt` / `test_run_output.txt` 等产物。

**注意**：移动前先 `git grep` 确认没有其它脚本 / 文档以相对路径引用它们（文档中的命令需同步更新）。

---

### 3.4 P1-8 迁移来源统一 📋

**现状**：`migrations/versions/`（Alembic）+ `migrations/add_*.py`（手写）+ `scripts/migrate_*.py` 三处并存。

**方案**：

1. 以 Alembic 为唯一 schema 迁移入口（`alembic revision --autogenerate`）；
2. 历史手写脚本归档到 `migrations/legacy/` 并标注"仅用于历史环境重放"；
3. 纯数据迁移（如 V4 owner→developer）保留为显式命名的一次性脚本，并在文档登记执行顺序；
4. CI 增加 `alembic check`（校验模型与迁移一致）。

---

### 3.5 前端优化（P2-2 / P2-3 / P2-8）📋

| 项 | 方案 |
|----|------|
| P2-2 路由抽离 | 将 `App.tsx` 中的路由表抽到 `src/router/routes.tsx` + `ProtectedRoute.tsx`，`App.tsx` 只做挂载 |
| P2-3 权限源统一 | 合并 `App.tsx` 的角色判断与 `config/permissions.ts`，保留单一 `usePermissions()` Hook 作为唯一出口 |
| P2-8 i18n | 先统一抽取菜单/按钮文案到 `locales/zh-CN.json`，再补 `en-US`；采用渐进式（新页面必须走 i18n） |

**验收**：`npm run build` 通过 + 各角色登录后菜单与页面可达性无变化（用 Playwright E2E 覆盖 5 类角色各 1 条冒烟）。

---

### 3.6 P2-9 大表分区 📋

**对象**：`api_call_logs`（增长最快）、`key_usage_logs`、`audit_logs`。

**方案**：
1. 按 `created_at` 做**月度范围分区**（PostgreSQL 声明式分区）；
2. 编写 `migrations/` 分区迁移脚本 + 未来分区预创建定时任务；
3. 增加归档策略（超过 `logging.retention_days` 的分区 `DETACH` 后归档到冷存储）。

**风险**：分区改造需要重建主表，务必在**维护窗口**执行并提前全量备份；建议先在 staging 演练。

---

### 3.7 P3 CI/CD 与可观测性 📋

| 项 | 方案 |
|----|------|
| CI | GitHub Actions / GitLab CI：`flake8 + mypy + pytest`（后端）、`lint + tsc + build`（前端）、构建镜像 |
| 契约 | 以 `openapi.json` 生成前端请求类型，防止前后端字段漂移 |
| 链路追踪 | 接入 OpenTelemetry，打通 `X-Request-ID` 全链路 |
| 压测 | k6 / Locust 脚本，验证 10,000 QPS / P99 < 500ms 目标 |
| 就绪探针 | 区分 `/health`（存活）与 `/ready`（依赖就绪：DB + Redis） |

---

## 4. 需人工处理（👤）

### 4.1 轮换已泄露的支付宝密钥 👤 P0

**背景**：`api-platform/keys/alipay_private_key.pem` 等文件曾被提交进 git 仓库（已 `git rm --cached` 移出索引），
但**历史提交中仍可检出**，必须按"已泄露"处置。

**操作步骤**：

1. 登录蚂蚁金服开放平台 → 应用 → 重新生成**应用私钥**与**公钥**；
2. 将新私钥转换为 PKCS1 格式（`openssl rsa -in app_private_key.pem -traditional -out app_private_key_pkcs1.pem`）；
3. 更新本地 `keys/alipay_private_key_pkcs1.pem`、`keys/alipay_public_key.pem`（或使用 `.env` 内联方式）；
4. 在平台配置新的公钥，验证沙箱下单 → 回调 → 补账全链路；
5. 作废旧密钥对；
6. 通知所有协作者重新获取密钥文件（密钥文件已不再随仓库分发）。

> 状态：**待人工执行**（本次按用户要求暂缓）。

### 4.2 清理 git 历史中的密钥 👤 P1

```bash
# 使用 git-filter-repo（推荐）
git filter-repo --path api-platform/keys --invert-paths --path OwnerServer/users.db --invert-paths

# 清理后强制推送（注意：会改写历史，需提前通知所有协作者）
git push --force-with-lease origin main
```

> 若仓库为私有且仅本地使用，可评估后跳过；但**密钥轮换不可跳过**。

---

## 5. 本轮新增待办（评审外发现）

| 编号 | 项目 | 优先级 | 状态 | 说明 |
|------|------|:------:|:----:|------|
| N-1 | 仓库 `endpoint_url` **写入侧**校验 | P1 | ✅ 已完成 | 创建/更新仓库时即拒绝非法地址（见 §2.5） |
| N-2 | SSRF 校验结果缓存 | P2 | 📋 待办 | 每次转发都做 DNS 解析，建议按 host 缓存校验结果（TTL 60s） |
| N-3 | 支付渠道回调 IP 白名单 | P1 | 📋 待办 | `/payments/alipay/callback` 增加渠道来源 IP 段校验 |
| N-4 | `payment_callbacks` 报文脱敏 | P2 | 📋 待办 | 回调原始报文落库前需评估脱敏（对账需要，可能需保留部分字段） |
| N-5 | 限流迁移至网关层 | P2 | ⏸ 暂缓 | APISIX 已在架构文档中规划，多实例部署时更合适 |
| N-6 | `system_configs.payment.mock_mode` 双数据源收敛 | P2 | 📋 待办 | 实际生效的是 `settings.payment_mock_mode`，DB 配置项为遗留 |
| N-7 | 对账/结算任务显式限定 `environment=production` | P1 | 📋 待办 | 避免模拟数据参与对账 |
| N-8 | `/ready` 就绪探针 | P2 | ✅ 已完成 | 输出 DB / Redis 依赖状态（见 §2.5） |
| N-9 | 类型检查噪音（basedpyright 307 项） | P2 | 📋 待办 | 项目使用 SQLAlchemy 传统 `Column` 声明，导致 `Column[str]` ≠ `str` 类告警遍布全项目；另有隐式相对导入告警。**属既有问题，非某次改动引入**。建议：改用 SQLAlchemy 2.0 `Mapped[...]` / `mapped_column` 声明式类型，或为 `basedpyright` 配置 `reportGeneralTypeIssues`/`reportArgumentType` 降级，并在 CI 中只对**新增代码**做严格检查 |
| **N-10** | **测试直接清空开发库** | **P0** | ✅ 已完成 | `tests/conftest.py` 默认把测试库指向开发库 `api_platform`，且每个用例后 `DROP ALL` → **跑一次 pytest 就清空开发库**（实测已造成开发库 0 张表）。修复：默认改为专用库 `api_platform_test` + 安全护栏（库名不含 `test` 时拒绝运行）；并新建测试库、恢复开发库。见 §2.6 |
| **N-11** | 时间列类型不统一导致插入失败 | P1 | ✅ 已完成 | 7 个模型（`role` / `system_config` / `pricing_config` / `notification` / `audit_log` / `adapter` / `user_operation_log`）漏写 `timezone=True`，却用返回 **aware UTC** 的 `get_utc_now()` 作默认值 → asyncpg 抛 `can't subtract offset-naive and offset-aware datetimes`。修复：**补齐 `DateTime(timezone=True)`**（对齐项目既有唯一方案），并顺带修复 `notification.read_at/expire_at`、`adapter.last_health_check`、`pricing_configs.valid_from/valid_until`。**详见 §2.7 纠正说明** |
| **N-12** | 种子脚本用本地时间当 UTC | P1 | ✅ 已完成 | `scripts/init_db_with_data.py` 的 `now = datetime.now()`（本地时间，UTC+8）被写入 UTC 列 → 种子数据时间偏差 8 小时。修复：改为 `datetime.now(timezone.utc)`（aware UTC） |

---

## 6. 回归与验收

### 6.1 后端

```bash
cd api-platform
python -m pytest tests/ -v          # 当前：213 passed
python -m pytest tests/ -q --cov=src --cov-report=term
```

> **⚠️ 前置条件（必读）**：测试会**在每个用例后 DROP 所有表**，因此必须使用**独立的测试库**。
> 默认测试库为 `api_platform_test`，首次使用需创建：
>
> ```powershell
> $env:PGPASSWORD='postgres'
> & "D:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d postgres `
>     -c "CREATE DATABASE api_platform_test OWNER api_user;"
> ```
>
> `tests/conftest.py` 已内置安全护栏：若目标库名不含 `test`，将**直接拒绝运行**并给出提示
> （确需对其它库执行时可用 `ALLOW_NON_TEST_DATABASE=1` 显式放行）。

测试文件与覆盖范围：

| 文件 | 用例数 | 覆盖 |
|------|:------:|------|
| `test_environment_guard.py` | 22 | 环境隔离、生产强校验、账单环境、回调门控 |
| `test_url_safety.py` | 39 | SSRF、权限统一、路由去重 |
| `test_rate_limit_redis.py` | 18 | 限流 Redis/内存/中间件/配置 |
| `test_sanitize.py` | 41 | 敏感信息脱敏 |
| `test_cache.py` | 12 | 缓存读写/失效/降级 |
| `test_repo_endpoint_guard.py` | 15 | 写入侧地址校验、`/ready` 就绪探针 |
| 既有用例 | 66 | 认证、计费、配额、仓库、支付、代理 |

### 6.1.1 探针说明

| 端点 | 类型 | 行为 |
|------|------|------|
| `/health` | 存活探针（liveness） | 仅表示进程在运行，**不校验依赖** |
| `/ready` | 就绪探针（readiness） | 校验依赖：DB 必需；Redis 默认非必需（`READY_REQUIRE_REDIS`）。未就绪返回 **503** |

### 6.2 前端

```bash
cd api-platform/web
npm run lint
npm run build
npm run test:e2e
```

### 6.3 关键手工回归

| 编号 | 场景 | 预期 |
|------|------|------|
| R1 | 开发环境模拟充值 | 余额增加，生成 simulation 账单 |
| R2 | 生产环境启动（mock 未关） | 拒绝启动 |
| R3 | 仓库配置内网地址（生产） | 转发返回 403 |
| R4 | `/api/v1/files` | 404（无前缀暴露已消除） |
| R5 | 新建套餐后立即查套餐列表 | 返回最新数据（缓存已失效） |
| R6 | 通用代理携带 `password` 字段 | `api_call_logs.request_params` 中该字段为 `***` |

---

**文档结束**

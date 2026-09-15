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
| P0-4 | 密钥/DB 文件进入版本库 | P0 | ⚠️ 部分完成 | 索引已清理（§2.22 复查确认为 0）；**但历史对象仍在 → 密钥轮换 + 历史重写待人工** |
| P0-5 | 仓库转发 SSRF | P0 | ✅ 已完成 | 出站地址校验 + 策略开关 |
| P1-1 | 路由重复挂载/无前缀暴露 | P1 | ✅ 已完成 | 单一注册入口 |
| P1-2 | 模型字段与 Service 漂移 | P1 | ✅ 已完成（部分） | 已修正 RepoService 字段 + 死代码可用化 |
| P1-3 | 权限判断分散 | P1 | ✅ 已完成 | 收敛 `auth_service.check_admin_permission` |
| P1-4 | 巨型文件 | P1 | 🔄 后端 4/4 ✅；前端 4 项中 3 项已启动 | 后端 `payment_service.py`/`analytics.py`/`billing.py`/`repositories.py` 已拆包（§2.20/§2.23/§2.24）；**前端巨型组件拆分进行中（§2.25）**：`Analytics.tsx` 964→477、`Recharge.tsx` 2001→1739、`owner/Repos.tsx` 1059→985；剩余 `admin/Repos.tsx`(924) 见 §3.1 |
| P1-5 | 缓存层未落地 | P1 | ✅ 已完成（示范） | 缓存基建 + 套餐列表接入，见 §2 |
| P1-6 | 统计实时聚合 | P1 | ✅ 已完成 | 三步全落地：落库聚合（§2.17）+ 读切换 + 结果缓存（§2.19）；与实时查询逐值一致 |
| P1-7 | 根目录脚本污染 | P1 | ✅ 已完成 | 脚本归档 + **node_modules 去跟踪**，见 §2.5 |
| P1-8 | 迁移来源不统一 | P1 | ✅ 已完成 | Alembic 统一（基线 + 首个增量迁移已实践），见 §2.15/§2.17 |
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

### 2.11 查询侧时区口径收敛：`func.date` → `time_range` 半开区间（✅ 已完成）

> 承接 §2.7（写入侧 UTC 统一）。完整论证见 `docs/TIMEZONE_DESIGN.md`。

**问题**：查询侧残留 3 类口径缺陷（均为活代码）——

1. `func.date(created_at)` 按**会话时区**（应用=UTC）取日期 → "今日/按天"边界比北京自然日早 8 小时；
   且实证：psql 直连（服务器时区 Asia/Shanghai）与应用返回**不同日期**（隐式依赖）。
2. `created_at <= 23:59:59` 闭区间 → 丢失最后一秒内的**亚秒数据**。
3. Python 侧对读出的 aware UTC 直接 `strftime` 取日期（consumption-trend）→ 同样偏 8 小时。

**收敛清单**：

| 文件 | 收敛内容 |
|------|----------|
| `admin.py` | 今日调用：`cst_day_range_utc()` 半开区间 |
| `repositories.py` | 今日调用：同上 |
| `quota.py` usage-history | `cst_day_start_utc` 窗口 + `cst_date_expr` 分组（**复用对象**）+ `cst_now()` 补标签 |
| `quota.py` consumption-trend | 窗口 `cst_day_start_utc` + `created_at.astimezone(CST)` 取日期 |
| `admin_reconciliation.py` ×2 接口 | `cst_day_range_utc_from_date`；`day_start` 同时是 `reconcile_date` **写入锚点**（3 处），写入/查询同源 |
| `reconciliation_scheduler.py` | 同上 + "昨天"改 `cst_now() - 1d` |
| `analytics.py` | `_cst_date` 三次独立调用点改**复用同一对象**（GroupingError 防御） |

**⚠️ 新踩坑（已写入 `time_range.py` docstring）**：`cst_date_expr` 每次调用生成**新的绑定参数**
（`'Asia/Shanghai'` 字面量）→ `select/group_by/order_by` 各调一次会触发
`GroupingError: 字段必须出现在 GROUP BY 子句中`。必须复用同一表达式对象。
旧写法 `func.date(col)` 无绑定参数所以从不报错 —— 该坑此前不可见的原因。

**验证**：新增 `tests/test_time_range.py` 8 条（TC-TZ-001~008，含 2 条**落库级**日界归属证明）；
全量 **238 passed**。

**合理保留**：`logging_config.py` 的 `datetime.now()`（日志文件按本地日期切割，与数据口径无关）。

### 2.12 死代码清理 + 对账环境隔离（✅ 已完成）

> 承接 §2.9.1（当时 `repo_service._deduct_balance` 只加标注不修补）与遗留待办
> 「对账/结算任务显式限定 environment」。

#### 2.12.1 死代码清理

| 对象 | 处置 | 依据 |
|------|------|------|
| `src/services/repo_service.py`（261 行，`RepoService` 类） | **整文件删除** | 全项目 0 处实例化（仅 `__init__` 导出）；字段漂移；`_deduct_balance` 为必抛错的废实现。实际转发在 `api/v1/repositories.py` |
| `BillingService` 类（billing_service.py 内约 600 行） | **删除** | 生产代码 0 处实例化（计费统一由 `AccountService` 负责）；6 处 `Bill(...)` 构造缺 NOT NULL 字段，误用必抛错 |
| `tests/test_billing.py`（171 行 / 11 用例） | **删除** | 仅测试被删除的死代码类 |
| `generate_bill_no()` | **保留** | 活代码：`api/v1/user.py` ×2 引用 |
| `scripts/dev/remove_dead_repo_service_code.py` | **删除** | 一次性清理脚本，使命完成 |

`services/__init__.py` 同步移除两个导出并留有清理说明。全项目 `RepoService` / `BillingService` 引用清零。

#### 2.12.2 对账环境隔离（遗留待办落地）

对账模块的「本地交易查询」原本**完全不过滤 environment** —— 同库内若混有两类环境的账单，
对账统计会被另一环境的交易污染。已在 4 处查询条件统一追加：

```python
env_match(Bill.environment, current_environment())
```

| 文件 | 位置 |
|------|------|
| `api/v1/admin_reconciliation.py` | 充值明细查询 / 渠道收款汇总 / 对账执行（local_conditions） |
| `services/reconciliation_scheduler.py` | 定时对账 local_conditions |

**设计说明**：`ReconciliationRecord` 本身无 environment 列 —— 无需加列：
分库后（dev/prod 各自独立库）每库只有本环境数据，对账记录天然隔离；
仅需过滤 **Bill 来源数据**即可。

#### 2.12.3 验证

- 新增 TC-ENV-027（**落库级**：同窗口同渠道两笔账单，对账条件只命中当前环境）、
  TC-ENV-028（`generate_bill_no` 存活回归）
- 全量 **229 passed**（删 11 条死代码用例、增 2 条新用例）

### 2.13 支付模式双数据源收敛（✅ 已完成）

> 遗留待办落地：`system_configs("payment","mock_mode")` 与 `settings.payment_mock_mode` 双源。

#### 2.13.1 问题（三个叠加）

1. **假开关**：管理后台 `PUT /payment-config/update` 改 mock_mode 只写 DB，
   而实际支付行为（`payment.py` 创建模拟支付）读 `settings.payment_mock_mode`
   → **改了不生效**，管理员以为切到了真实支付。
2. **同库两个 key**：`GET /status` 读 `"mock_mode"`、`GET /detail` 读 `"payment.mock_mode"`
   → 两行数据可能不同，接口间口径漂移。
3. **权威性归属**：启动 fail-fast 校验、启动横幅、回调门控全部依赖 settings
   → 它才是事实上的权威源，DB 侧只是"看起来可配"。

#### 2.13.2 收敛决策：settings 为唯一权威源

理由：支付模式是**部署级配置**（换环境必须改 `.env` 并重启，与 `ENVIRONMENT` 同级），
不是运行时业务参数；且生产 fail-fast 校验（`PAYMENT_MOCK_MODE 仍为 true → 拒绝启动`）
只有在 settings 侧才可能实现。

| 接口 | 原行为 | 收敛后 |
|------|--------|--------|
| `GET /status` | 读 DB `"mock_mode"`（缺省 true） | `mock_mode = settings.payment_mock_mode` |
| `GET /detail` | 读 DB `"payment.mock_mode"` | 同上（两接口口径归一） |
| `PUT /update` | 静默写 DB（假开关） | 传不同值 → **400** 并指引"修改 `.env` 的 `PAYMENT_MOCK_MODE` 并重启"；传相同值 → 幂等放行 |
| `DEFAULT_CONFIGS` | 播种 `"payment.mock_mode": "true"` | **移除播种**（存量库旧行无人读取，重建时自然清理） |

其余渠道配置（alipay/wechat/bankcard）仍走 system_configs 运行时管理，不在本收敛范围。

#### 2.13.3 连带修复：测试基建隐患（重要）

新测试单跑时暴露：`conftest.test_engine` 的 `Base.metadata.create_all`
**依赖测试模块的 import 副作用**注册模型 —— 收集阶段碰巧 import 了 `src.main` 才建全表；
单跑某新测试文件时只建部分表 → `关系 "system_configs" 不存在`。

修复：`create_all` 前**显式** `import src.models`（`models/__init__` 已聚合全部模型）。
该修复只可能"多建表"，对所有既有 DB 用例无回归（全量 235 passed 验证）。

#### 2.13.4 测试与验证

新增 `tests/test_payment_config_source.py`（TC-PSRC-001~006）：

| 用例 | 验证 |
|------|------|
| TC-PSRC-001 | `GET /status` 显示 settings 实际生效值 |
| TC-PSRC-002 | settings 变化时 `/status` 跟随（同一权威源） |
| TC-PSRC-003 | `GET /detail` 与 `/status` 口径一致 |
| TC-PSRC-004 | `PUT` 传不同 mock_mode → 400，提示含 `PAYMENT_MOCK_MODE` |
| TC-PSRC-005 | `PUT` 传相同值 → 幂等放行（200） |
| TC-PSRC-006 | `DEFAULT_CONFIGS` 不再播种 `payment.mock_mode` |

全量 **235 passed**。

### 2.14 支付回调来源 IP 白名单（✅ 已完成，遗留待办清零）

> 遗留待办「支付回调渠道 IP 白名单」落地。

**威胁模型**：支付回调接口（`/payments/alipay/callback` 真实验签、`/payments/callback` 模拟补账）
公网可达，仅有验签/令牌门控。IP 白名单提供**验签之前的第一道门**——
未持有渠道密钥的扫描器/攻击者连验签环节都进不来。

**实现**：

| 组件 | 内容 |
|------|------|
| 配置 | `PAYMENT_CALLBACK_IP_ALLOWLIST`（逗号分隔 IPv4/IPv6 地址或 CIDR；**留空 = 关闭校验**，零回归） |
| 工具 | `helpers.is_ip_allowed(client_ip, allowlist)` —— `ipaddress` 模块，支持 CIDR/精确 IP/IPv6；来源缺失或非法一律 **fail-closed**；配置条目非法跳过（不因脏数据放行） |
| 接入 | `payment.py` 两个回调入口：白名单拒绝 → `403`（在验签/鉴权门控之前） |

**⚠️ 安全决策**：只基于**直连 IP**（`request.client.host`），**不使用 `X-Forwarded-For`**
（可伪造）。反代/负载均衡部署时将代理出口 IP 加入名单。文档已写入 `.env.example` 与代码注释。

**测试**（`tests/test_payment_callback_allowlist.py`，TC-IP-001~009）：
- 单元：关闭放行 / 精确 IP / CIDR（含 IPv6）/ fail-closed / 多条目空白容错
- 集成：白名单开启 → 两接口均 403（且 IP 层先于鉴权层）；白名单关闭 → 与改造前行为一致（401 既有门控），**零回归**

**验证**：全量 **244 passed**。

> ✅ 至此，遗留待办中的轻量项（双数据源收敛、对账环境隔离、回调 IP 白名单）**全部清零**。
> 剩余均为大型工程项：P1-8 Alembic 迁移统一、P1-6 统计预聚合、P1-4 巨型文件拆分、P2-9 分区、CI/CD。

### 2.15 P1-8 迁移来源统一（Alembic）（✅ 已完成）

> 详细工作流见 `docs/DATABASE_MIGRATIONS.md`（含踩坑记录与验证数据）。

**历史问题**：建表来源分裂（`create_all` + `migrations/` 手写散装脚本并存）；
旧 `migrations/versions/` 是从未接入运行链的伪 alembic 文件（`down_revision=None`）。

**改造**：

| 项 | 内容 |
|----|------|
| 标准环境 | `alembic init alembic` + `alembic.ini`；`env.py` 读 `settings.database_url`（同步化）+ 全量模型元数据 + `-x url=` 覆盖 |
| 基线迁移 | `fec917d3faaf`（对临时空库 autogenerate 全量 create），临时库升级后与 dev 库 **information_schema 对比：30 表 / 全部列零差异** |
| 存量库接入 | `api_platform_dev` / `api_platform_prod` 均 `stamp head` → `fec917d3faaf` |
| 脚本切换 | `init_db_with_data.py` 建表改为 **alembic upgrade head**（不再 create_all）；`--drop` 增加 `DROP TABLE IF EXISTS alembic_version`（否则残留版本戳 → upgrade no-op → 业务表缺失，踩坑已记录） |
| 旧脚本归档 | `migrations/` 9 个散装文件 → `scripts/legacy_migrations/`（仅历史记录）；伪目录删除 |
| 守护测试 | `tests/test_alembic_infra.py`（TC-MIG-001~003：ini 存在 / 基线含建表 / env.py 可编译） |

**验证**：`--drop` 全流程重建（alembic 建表 + 种子 5 用户 / 2 账单）通过；全量 **247 passed**。

> 测试库（conftest）继续 create_all（每用例 drop_all，迁移链无意义）。

### 2.16 Redis 冷却期绕过修复（用户日志暴露的真实缺陷）

> 用户日志：`连接失败，30 秒内不再重试` 每 5 秒重复出现 —— 冷却形同虚设。

**根因**：冷却检查只在 `RedisManager.is_available()`（仅 `/ready` 探针使用），
而 `rate_limiter.py:120`、`cache.py ×4` **直接调用 `get_client()` 绕过冷却**
→ 冷却期内每个请求仍真实尝试连接、白等 `socket_connect_timeout=2` 秒
→ **重复 WARNING 日志 + 接口延迟劣化**（不只是噪音）。

**修复**：`get_client()` 加锁前短路检查 `_unavailable_until`（锁内双重检查）。
一处修复，全部调用方受益。

**为什么 247 个测试没发现**（回答用户质询）：
1. Redis 限流 18 条用例用 `_FakeRedis` monkeypatch `get_client` —— 验证限流逻辑，不碰真 Redis；
2. "Redis 缺席时降级"本身是被测行为 —— 降级正确 = 功能断言全绿；
3. **测试盲区**：无耗时断言、单用例请求少 → 2 秒×N 的延迟劣化不可见。
   本组新用例用连接计数器（attempts==0）堵住该盲区。

**新增测试**（`tests/test_redis_cooldown.py`，TC-RED-001~003）：
冷却期内 `get_client` 短路且零连接尝试 / 冷却结束恢复重试 / `is_available` 与
`get_client` 行为一致。全量 **250 passed**。

**用户环境说明（2026-09-15 已落地）**：Redis 已安装于 WSL (Ubuntu-20.04, v5.0.7)，
`.env` 为 `redis://:redis123@127.0.0.1:6379/0`（localhost → 127.0.0.1：Python 解析 localhost
可能走 IPv6，而 WSL2 转发只走 IPv4）。**两个关键坑**：
1. WSL2 的 localhost 转发**不覆盖绑定 127.0.0.1 的服务** → redis.conf 改 `bind 0.0.0.0` + `requirepass`；
2. WSL 发行版空闲自动关闭 → Redis 消失（wslrelay 监听还在但转发失败 → Timeout）。
已建常驻保活（`wsl --exec sleep infinity`）+ 一键脚本 `scripts/dev/start_redis.bat`。
验证：`/ready` redis **up**，日志 `[Redis] 连接成功`。

### 2.17 P1-6 统计预聚合 —— 阶段 1「落库聚合」完成

> 方案三步走（§3.2）：① 落库聚合 ✅ → ② 读切换 ✅ → ③ 结果缓存 ✅
> （② ③ 见 §2.19；本节的 `aggregate_recent_hours` 仍保留，但调度已改用带水位的 `aggregate_until_now`）。

**本次落地**：

| 项 | 内容 |
|----|------|
| 唯一约束 | `repo_stats` 新增 `uq_repo_stats_repo_hour (repo_id, stat_hour)` —— 幂等聚合的前提。**用新 Alembic 工作流完成首次增量迁移**（autogenerate 精确检测 → 人工审查 → dev/prod `upgrade head`，链 `fec917d3faaf → 86af5456b080`） |
| 聚合服务 | `src/services/stats_aggregation_service.py`：SQL 层按 (repo_id, UTC 整点) 聚合 count/成败/成本/时延/tokens/独立用户 → upsert `repo_stats`；`aggregate_range`（半开区间）+ `aggregate_recent_hours(N)`（补最近 N 个完整小时，默认 2，防调度间隙漏数据） |
| 调度 | `main.py` lifespan 后台 asyncio 循环：启动 60s 后首跑，此后每小时一次；异常只记日志下轮重试；优雅停止（lifespan shutdown cancel） |
| 幂等保证 | 唯一约束 + 先查后覆盖：**重复执行行数与值不变**（TC-STAT-003 落库级验证） |

**⚠️ 又见 GroupingError 坑**：`func.date_trunc("hour", col)` 的 `"hour"` 字面量同样是绑定参数 ——
select 与 group_by 各写一次即触发 `GroupingError`（与 `cst_date_expr` 同机制，见 §2.11 / TIMEZONE_DESIGN §7.2）。
规则统一为：**带字面量参数的 SQL 函数表达式在同一条查询内必须复用同一对象**。

**测试**（`tests/test_stats_aggregation.py`，TC-STAT-001~006，全部落库级）：
单小时聚合值 / 跨小时多仓库分组 / 幂等重跑 / 空区间 / 约束存在（模型+数据库双侧）/ recent_hours 窗口。

**验证**：全量 **256 passed**。

**后续（阶段 2/3，待排期）**：analytics 趋势/排行优先读 `repo_stats`（缺失回落实时）；聚合结果 Redis 缓存 TTL 60s。

### 2.18 Redis 启动脚本编码修复（桌面启动乱码）+ 取消开机自启

**现象（用户反馈）**：把 `scripts/dev/start_redis.bat` 拷到桌面双击运行，cmd 中文乱码，且出现
`'(buntu-20.04)' 不是内部或外部命令`、`'localhost' 不是内部或外部命令`，脚本"看起来没执行"。

**根因**：bat 文件被保存为 **UTF-8（无 BOM）**，而 cmd 按系统 ANSI 代码页（CP936）解码 bat **字节流**
→ 中文字节被错误配对（3 字节 UTF-8 被拆成 1.5 个 GBK 字符，行尾残留半字符会"吃掉"下一行行首的 ASCII 字节，
如 `Ubuntu-20.04` → `(buntu-20.04)`）→ 不仅注释乱码，**行首 `REM` 被吞掉后注释文本被当成命令执行**，即上述报错。

**修复**：
1. `start_redis.bat` 转存为 **ANSI/GBK(CP936) + CRLF**，并在 `@echo off` 后加 `chcp 936 >nul` 显式固定代码页；
2. 移除 GBK 无法表示的 emoji（`⚠️` → `【重要】`），`→` 统一写 `->`；文件头写明编码约定（防再次另存为 UTF-8）；
3. 桌面副本同步为修复版；
4. **取消开机自启**（用户明确要求"不用做成开机自启"）：删除
   `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\start_redis.bat`
   （该副本为此前助手擅自复制的文件，非用户要求；且"复制而非快捷方式"会导致改源文件后不自同步）。

**验证**：用 `@echo on` 副本实机执行 —— 所有中文 `REM` 行均被正确识别、无任何"不是内部或外部命令"；
`wsl -e redis-cli -a redis123 ping` → **PONG**。

**遗留提示（未改，保持最小改动）**：脚本内 `timeout /t 2 /nobreak >nul` 在"被重定向/非交互式调用"时会报
`不支持输入重新定向`，双击运行不受影响；若将来需要脚本化调用，可换成 `ping -n 3 127.0.0.1 >nul`。

### 2.19 P1-6 阶段 2/3：读切换 + 结果缓存（✅ 已完成）

> 承接 §2.17（阶段 1 落库聚合）。backlog §3.2 的「三步走」至此**全部落地**。

**新增基座：聚合水位（连续性保证）**

`repo_stats` 只对「该小时有调用」的 (repo, hour) 写行，无调用的小时**没有行** ——
因此表内 `max(stat_hour)` 无法证明中间没有空洞（停机数日后重新聚合，max 会直接跳到最新，
中间的洞在读侧完全不可见 → 直接求和会**静默漏算**）。

- 新表 `stats_aggregation_state`（单行水位：`aggregated_until` = 已**连续**聚合到的排他上界）；
  迁移 `9478c3e10b0f`（链 `86af5456b080 → 9478c3e10b0f`，dev 已 `upgrade head`）。
- 聚合服务新增 `aggregate_until_now()`：从水位连续聚合到当前整点（单轮上限 30 天，
  防首次历史回填把调度循环/数据库拖住）；`main.py` 调度循环在追赶期改用
  `CATCHUP_INTERVAL_SECONDS=60` 加快轮询，追平后恢复 1 小时。
- 水位**只增不减**（回退被忽略并告警）；初始化取「最早日志所在整点」。

  ⚠️ **绝不能**把水位直接置为当前整点 —— 那是"谎报已聚合"，会让读侧把未聚合窗口当成有效数据 → 静默漏算。

**新服务：`src/services/stats_query_service.py`（预聚合优先 + 实时兜底）**

窗口切分：`[start, end)` → 预聚合段 `[start, agg_end)` + 实时段 `[agg_end, end)`，
其中 `agg_end = min(watermark, end)`。切分点固定在整点水位上，因此**非整点窗口也严格等价**。

三条铁律（零回归的关键）：
1. 只用**可加量**：`total_calls` / `success_calls` / `total_cost` → 两段求和 == 直接实时求和；
2. **独立用户数不可加**（`unique_users` 是每仓库每小时的去重数）→ 一律实时 `COUNT(DISTINCT)`，绝不求和；
3. 水位诚实：水位之后的尾部必须回落实时；无水位则整段实时。

**analytics 接入（`src/api/v1/analytics.py`）**

| 接口 | 改造 | 效果 |
|------|------|------|
| `/overview` | 11 条全表 COUNT/SUM → 4 次窗口求和；活跃用户走实时 | 大表只承担尾部查询 |
| `/trend` | 分组改 `group_by_period`（预聚合 + 实时自动合并，label 规则不变） | 长窗口趋势不再全表扫 |
| `/repo-details` | **消除 N×3 查询**（20 个仓库 60 条 SQL → 最多 2 条，走 `group_by_repo`） | 主要瓶颈消除 |
| `/repo-ranking` | `group_by_repo` + 内存排序 + 仓库信息批量查（消除 N+1） | SQL 条数恒定 |
| `/user-ranking` | 维度不支持预聚合（表只有 repo/hour）→ 保持实时；**修掉用户信息 N+1** | 减少 N 次查询 |
| `/repo/{id}/trend` | 保持实时（单仓库数据量小；`avg_latency` 平均值不可加），加缓存 | 命中即返回 |

**结果缓存（阶段 3）**：上述接口统一 60 秒缓存（`ANALYTICS_CACHE_TTL_SECONDS`），
key 含**数据可见范围**（`_cache_scope`：管理员 `admin`；开发者 `user:{id}:{仓库集合指纹}`）
—— 指纹随仓库增删变化，杜绝"范围变了仍命中旧缓存"的越权/串号。

**口径修正（重要）**：`repo_stats.success_calls` 由阶段 1 的 `< 400` 统一为 **2xx**
（与 analytics 既有口径一致，否则预聚合值与实时值不一致 = 回归）。口径变更使历史行不可用，
迁移中已 `DELETE FROM repo_stats` 强制重算（水位为空 → 读侧自动回落实时 → 期间数值仍 100% 正确）。

**顺手修复**：
1. `/trend` 越权隐患：开发者传**非法** `repo_id` 时原实现 `pass` → 过滤条件为空 → 返回**全部仓库**数据；
   改为显式 400（`repo/{id}/trend` 早有此校验，两条路径现已一致）。
2. 消除两处 naive `datetime(2000,1,1)`（ranking 的"全部时间"锚点）→ 统一 aware 锚点 `_ALL_TIME_START_UTC`。
3. 删除本模块与 `utils/time_range.py` **重复**的 `_cst_date` / `_cst_hour` 私有实现（统一走公共函数）。

**测试**：`tests/test_stats_query_service.py` 13 条（TC-STATQ-001~012，落库级），
核心断言为"任意路径结果 == 直接实时查询基准"（基准刻意用 `FILTER` 写法，与实现解耦）；
用例库 `tests/cases/stats_query_cases.json`；测试计划 §8.2 已登记。
全量 **269 passed**（256 + 13）。
另修复 `test_redis_cooldown::TC-RED-002` 的**环境耦合**（原断言依赖"本机 Redis 未运行"，Redis 一启动即失败）。

**预期收益**：`/overview`、`/repo-details`（原 N×3）、排行类的 DB 负载不再随 `api_call_logs` 增长而线性恶化；
缓存命中时响应为 Redis 往返量级。

**遗留（后续可做）**：`analytics.py` 已 715 行（>500 行约定），后续可随 P1-4 一并按端点拆分。

### 2.20 P1-4 巨型文件拆分（1/5）：payment_service.py → payment/ 包（✅ 已完成）

> P1-4 共 5 个巨型文件，按「风险从低到高」逐个拆，本次完成第 1 个（总计划见 §3.1）。

**为什么先拆它**：`src/services/payment_service.py` 1170 行 / 44.6KB，
但**全项目只有一处引用**（`src/api/v1/payment.py`）→ 改动面最小。

**拆分方式：Mixin 组合（纯搬移，行为零改变）**

原文件只有一个类 `PaymentService`，方法之间大量互相调用（`self.xxx`）；
若拆成多个独立类必须改造这些调用（高风险）。改用 Mixin 后**所有方法仍挂在同一个
`PaymentService` 上**，`self.xxx` 与外部 `PaymentService(db)` 用法完全不变：

    src/services/payment/
    ├── __init__.py      # re-export（对外路径变为 src.services.payment）
    ├── service.py       # 27 行：组合 5 个 Mixin + __init__ 注入 self.db
    ├── _orders.py       # 272 行：单号/下单/支付链接/取消/退款/自定义充值
    ├── _packages.py     # 191 行：套餐 CRUD/金额校验/默认套餐
    ├── _alipay.py       # 414 行：当面付/二维码/交易查询/状态同步
    ├── _callback.py     # 279 行：回调入账（幂等）/余额更新/用户升级
    └── _query.py        # 92 行：支付查询/列表分页

拆分后单文件最大 414 行（原 1170 行），全部满足「单文件 ≤500 行」。

**怎么保证"没搬错"（三层验证）**：
1. **AST 级等价校验**（`scripts/dev/verify_payment_split.py`）：用 `ast.unparse` 对**全部 26 个方法**
   与拆分前备份做结构化比较（忽略格式差异，只在 AST 不同时报警），并校验
   「组合类上每个方法都可访问」+「无方法被组合类自身覆盖」→ 结果 **26/26 完全一致**。
2. 编译 + 导入测试：`py_compile` 全过；`import src.api.v1.payment` 正常（router prefix `/payments`）。
3. 全量 **269 passed**（与拆分前完全一致）。

> 生成由 `scripts/dev/split_payment_service.py` 完成（AST 定位方法边界 → 按分组精确截取源码 →
> 按实际使用筛选 import），内置**覆盖性校验**：分组若漏掉/夹带任何方法立即报错退出，防止静默丢代码。

**同步更新**：`src/api/v1/payment.py` 的 import 改为 `from src.services.payment import PaymentService`；
旧文件已删除（不留兼容 shim，避免新旧代码混存）。

**下一个目标**：`src/services/...` 或前端组件（见 §3.1 剩余 4 项）。

### 2.21 前端单元测试 + 前后端联测基建补齐（✅ 已完成）

> 动机：前端此前**只有 E2E、没有单测框架** —— 这会让 P1-4 剩余的前端组件拆分**拿不到零回归证据**；
> 同时"前后端契约漂移"这条缝隙无人把关（前端单测用 mock adapter、后端测试只保证自身模型自洽，
> 契约改名时两边都绿、页面白屏）。

**1. 前端单元测试（Vitest，从 0 到 1）**

- 依赖：`vitest@2` + `jsdom` + `@testing-library/react` + `@testing-library/jest-dom` + `user-event`。
  ⚠️ npm 默认解析出 `vitest@5`，与项目 `vite@5` / `playwright@1.59` 存在 peer 冲突 → 明确锁定 **vitest 2.x**。
- 配置：`web/vitest.config.ts`（jsdom + 别名 `@` 与 vite 一致）与 `web/src/test/setup.ts`
  （jest-dom 断言 + 补齐 jsdom 缺失的 `matchMedia` / `ResizeObserver` / `IntersectionObserver`）。
  **关键一条**：显式 `exclude: ['e2e/**']` —— 否则 Playwright 用例会被 vitest 收集并全量报错。
- 用例：`src/config/permissions.spec.ts`（13 条）+ `src/api/client.spec.ts`（22 条）= **35 passed**。
  选点理由：权限判定是**越权防护的第一道门**；请求层是全站出入口（认证头 / 统一解包 / 错误文案 / 401 自动登出）。
  手法：**不引入额外 mock 库**，直接替换 axios `adapter`，覆盖「成功 / HTTP 错误 / 网络错误 / 配置错误」四条路径。
- `package.json` 新增 `test:unit` / `test:unit:watch`；新增 spec 位于 `src/` → 已被 `tsc --noEmit` 覆盖（typecheck 通过）。

**2. 前后端联测（API 契约，12 条）**

- `web/e2e/api-contract.spec.ts`：用 Playwright `request` 直接打**真后端**，用前端代码中声明的类型校验真实响应。
- 覆盖：`/health`（环境字段，前端徽标依赖）、`/ready`、响应头 `X-Environment`/`X-Billing-Environment`、
  未认证 401、登录 `TokenResponse`、登录失败文案可解析、`/auth/me` 的 `User`、
  分页 `{items, pagination}`、参数校验 422、未知路由 404、CORS 预检、登出。
- **跳过策略**：`beforeAll` 探测 `/health`，后端未启动时整组跳过（不误报为失败）；
  账号用 `scripts/init_db_with_data.py` 种子账号，可用 `E2E_ADMIN_EMAIL` / `E2E_ADMIN_PASSWORD` / `API_URL` 覆盖。
- **实测**：**12 passed**（对真实后端 development / simulation 环境）。

**3. 顺带核对**：后端 `RepositoryListResponse` = `{items, pagination}` 与前端 `PaginatedResponse` **一致**
（文档中"分页用扁平结构"是旧约定，目前仅 `/repositories/pending` 等个别接口仍是扁平形态）。

**意义**：P1-4 剩余的前端组件拆分（Recharge.tsx / Repos.tsx / Analytics.tsx）至此**有了可复用的回归网**；
下一步先做**后端**（`billing.py` / `analytics.py`，有 269 条 pytest 兜底），再做
`repositories.py`（按同一思路先补契约用例），最后处理前端组件。

### 2.22 git 仓库治理（.gitignore 例外修正 + 产物去跟踪 + .gitattributes）

> 起因：提交前后反复出现"测试产物污染 `git status`"。系统性排查
> `git ls-files -i -c --exclude-standard`（列出**既被跟踪又匹配忽略规则**的文件）后，命中 31 个、分 6 类。

**1. 其中两类是 `.gitignore` 误伤（应保留而非删除）**

| 文件 | 为什么是误伤 | 处理 |
|------|--------------|------|
| `electron/build/installer.nsh` | electron 的 `build/` 是**打包源目录**（NSIS 安装脚本 / 图标），被通用规则 `build/` 整目录忽略 | 根 `.gitignore` 加 `!electron/build/` + `!electron/build/**` |
| `api-platform/web/.env.development`、`.env.production` | 只含公开的 `VITE_API_URL`（`VITE_` 变量本就会编译进浏览器产物），属**必须随仓库分发的构建输入** | 在 `api-platform/.gitignore` 加 `!web/.env.*` 例外 |

**⚠️ 两个 `.gitignore` 机制坑（本次实测，务必记住）**
1. **子目录 `.gitignore` 优先于根目录**：把前端 env 例外写在**根** `.gitignore` 会被
   `api-platform/.gitignore` 的 `.env.*` 覆盖而**完全失效**（`git check-ignore -v` 会显示实际命中的是子目录规则）；
   必须写在**该文件所在子目录**的 `.gitignore` 里。
2. **父目录被整目录忽略时，`!某文件` 无效**：必须先 `!electron/build/` 重新包含目录，再 `!electron/build/**`。

**2. 产物类移出索引**（`git rm --cached`，**只动索引、磁盘文件保留**）

`OwnerServer/weather-api/logs/*.log`(12) + `api-platform/web/test-results/**`(5) +
`OwnerServer/weather-api/src/**/__pycache__/*.pyc`(10) + `通用API服务平台文档/.vscode/settings.json`(1) = **28 个**。
复查：`git ls-files -i -c --exclude-standard` → **0**。

**3. 新增 `.gitattributes`（行尾保护，规则**优先于**各机器的 `core.autocrlf`）**

```
.githooks/*   → text eol=lf     # hooks 必须 LF（CRLF 会 bad interpreter: /bin/sh^M）
*.bat *.cmd   → text eol=crlf   # Windows 批处理必须 CRLF（另见其 ANSI/GBK 编码约定）
*.ps1         → text eol=crlf
*.sh          → text eol=lf
图片/文档/db  → binary           # 禁止行尾转换（docx/png 被当文本处理会损坏）
```

**为什么必需**：本仓库刚因 bat 的编码/行尾踩过坑（LF-only 的 `.bat` 在部分 cmd 版本下解析异常）；
二进制文档若被当文本做行尾转换会直接损坏。验证：`git check-attr` 显示 `*.bat → eol:crlf`、`.githooks/* → eol:lf`，
且 `git status` 变更条目未暴增（无"行尾重写风暴"）。

**4. ⚠️ 安全排查发现高危遗留（需人工决策）**

`git log --all --diff-filter=A` 查明历史中**曾被新增**（虽已在 `831d1776` 移出索引，但**历史对象仍在**，
public 仓库下 `git log -p` 即可取回）：

```
api-platform/keys/alipay_private_key.pem        ← 支付宝私钥
api-platform/keys/alipay_private_key_pkcs1.pem
api-platform/keys/alipay_public_key.pem
OwnerServer/users.db                            ← 用户数据库
```

- **唯一止损手段是轮换支付宝密钥**（在支付宝开放平台重新生成密钥对并更新部署配置）——清理历史无法收回已克隆者手里的私钥。
- 彻底清理需重写历史（`git filter-repo` 移除 `keys/` 与 `node_modules`）：会变更**所有 commit hash**、
  需 `push --force`、协作者要重新 clone → **破坏性操作，待用户批准后执行**。
- `.git` 体积重写前实测 **70.8MB**，主因是历史中 **9 个 `node_modules` 提交**（此前记录的 37.7MB 只统计了部分目录）。

**5. 历史重写已执行（2026-09-15，用户授权）**

工具：`git-filter-repo 2.47.0`（`pip install git-filter-repo`；本机 `git filter-repo` **不在 PATH**，改用 `python -m git_filter_repo` 调用）。

```bash
# 前置①：工作树必须干净 → 先提交基线快照
# 前置②：备份（写入已被忽略的目录）→ git clone --mirror . .codebuddy/git-mirror-backup.git
python -m git_filter_repo --force --invert-paths \
    --path-glob '*node_modules*' \
    --path 'api-platform/keys' \
    --path 'OwnerServer/users.db'
# filter-repo 出于安全会移除 remote → 需恢复
git remote add origin https://github.com/ht182400-creator/API-Agent.git
```

**结果**：

| 指标 | 重写前 | 重写后 |
|------|--------|--------|
| `.git` 体积 | **70.8 MB** | **4.4 MB**（-94%） |
| 提交数 | 23 | 23（历史完整保留，hash 全变） |
| 历史中 `node_modules` 提交 | 9 | **0** |
| 历史中密钥 / `users.db` | 有（`.pem`×3、`users.db`） | **0** |
| 工作区磁盘文件 | — | 全部保留（`keys/`、`users.db` 未被删） |

**验证**：`git fsck` 无报错；后端 **269 passed**；前端单测 **35 passed** + `tsc --noEmit` 通过；
回滚依据保留在 `.git/filter-repo/`（`commit-map` 记录旧→新 hash 映射）。

**⚠️ 未执行的收尾（需人工决策）**：
1. **远端未同步** —— GitHub 上仍是旧历史（含 node_modules 与密钥），需 `git push --force`。
   本机 HTTPS 不通，实际命令：
   `git push git@github.com:ht182400-creator/API-Agent.git main --force`
   —— **破坏性操作（覆盖远端历史），未擅自执行**。
2. **即便 force push，旧对象在 GitHub 侧仍可能短期可访问** → **支付宝密钥轮换仍是唯一的止损手段**（待人工）。
3. 本地备份 `.codebuddy/git-mirror-backup.git`（约 70MB）确认无误后可自行删除。

### 2.23 P1-4 扩展：`billing.py` 拆分（第 3 个巨型文件）

> §3.1 原清单只有 5 项，但排查发现另有 3 个文件同样超过「单文件 ≤500 行」：
> `src/api/v1/repositories.py`(2426) / `billing.py`(956) / `analytics.py`(716)。
> 本次完成 `billing.py`（`analytics.py` 见 §2.20 之后的记录）。

**拆分**：`src/api/v1/billing.py`（956 行 / 12 个端点）→ `src/api/v1/billing/` 包

| 文件 | 行数 | 职责 |
|------|------|------|
| `_shared.py` | 31 | 共享辅助（`_to_utc_iso_string`） |
| `account.py` | 191 | 账户信息与充值 |
| `bills.py` | 227 | 账单查询与导出 |
| `stats.py` | 246 | 账单统计与趋势 |
| `usage.py` | 189 | 用量统计与消费明细 |
| `monthly.py` | 199 | 月度账单（列表 / 明细 / 可查周期） |
| `__init__.py` | 27 | 汇总 router |

最大 246 行（原 956）。函数体逐字搬移；**挂载方式未变**（prefix 仍由 `src/api/v1/__init__.py` 的
`include_router(billing_router, prefix="/billing", tags=["Billing"])` 传入）。

**新增可复用工具**：`scripts/dev/split_api_router.py`（AST 定位成员边界 → 按分组精确截取 →
按使用情况筛选 import + 覆盖性校验）。改配置区即可**复用于 `repositories.py`**。

**⚠️ 踩坑（两个都是"编译期不报、运行期 NameError"）**：
1. 文件头固定写 `logger = get_logger("billing")`，而成员体里只出现 `logger.xxx` →
   按使用情况筛选 import 必然漏掉 `get_logger`；
2. 同理漏掉 `APIRouter`（成员体里只出现 `@router.get(...)`）。
→ 修复：脚本对这两个名字**强制补齐**（`_ensure_import`），不受筛选影响；`_shared.py` 不再生成多余 router。

**验证**：路由快照对比 **12 条完全一致**（应用共 147 条路径未变）；`py_compile` 通过；
权限守卫 + 环境门控子集 **80 passed**；`pytest --collect-only` 收集 **269 用例**（导入链零错误）。

### 2.24 P1-4 完成：`repositories.py` 拆分（第 4 个后端巨型文件）

> 承接 §2.23。`src/api/v1/repositories.py` **2426 行 / 29 个成员 / 23 个端点**，
> 是 P1-4 中体量最大、耦合最深的一个（文件内共享 5 个辅助函数 + 一条 catch-all 兜底路由）。

**拆分产物**：`src/api/v1/repositories/` 包（最大 476 行，原 2426 行）

| 文件 | 行数 | 职责 |
|------|------|------|
| `_shared.py` | 216 | 共享辅助：`_validate_endpoint_url` / `calculate_and_charge` / `_check_repo_owner_permission` / `_get_repo_by_id` |
| `catalog.py` | 476 | 仓库列表与详情（`list_repositories` / `list_my_repositories` / `get_repository_stats` / `get_repository`） |
| `invoke.py` | 264 | 能力调用（`chat` / `translate` / `recognize`） |
| `crud.py` | 239 | 创建 / 更新 / 删除 |
| `admin.py` | 404 | 管理员列表与审核（通过 / 驳回 / 上线 / 下线） |
| `endpoints.py` | 302 | 端点配置（列表 / 增删改 / 批量） |
| `limits.py` | 141 | 限流配置 |
| `config.py` | 208 | 配置更新（端点 + 限流 + 定价一次性提交） |
| `proxy.py` | 236 | **catch-all 兜底路由**（`/{repo_slug}/{path:path}`） |

**本文件特有的 3 个硬约束（都已踩坑并固化为工具防线）**：

1. **catch-all 必须最后注册** —— `proxy_repository_endpoint` 用
   `@router.api_route("/{repo_slug}/{path:path}", methods=[...])`，匹配任意两段路径。
   若它先于 `/admin/all`、`/{repo_id}/stats` 等注册，这些静态路由**永远不可达**。
   → 工具新增「**分组顺序自检**」：各分组最小成员行号必须单调递增，否则报错退出。

2. **空路径路由 + 空 prefix 被 FastAPI 拒绝** —— `catalog.py` 含 `@router.get("")`（即 `/repositories` 本身）。
   中间层 `include_router` 的 prefix 为空时抛 `Prefix and path cannot be both empty`。
   ⚠️ 给**中间层 router** 设 prefix **无效**（校验只看 `include_router(prefix)` 与子路由**原始 path**）→
   必须写 `router.include_router(catalog.router, prefix="/repositories")`，
   并**移除** `src/api/v1/__init__.py` 挂载处的 `prefix=`（否则双重前缀）。

3. **文件中部的模块级 import** —— 原文件 L999（位于两个函数之间）有
   `from src.schemas.request import RepositoryCreate, ...`。
   只搬"函数 / 类"的旧版工具会把这类 import **静默丢弃** → 运行期
   `NameError: RepositoryCreate is not defined`（编译期不报）。
   → 工具改为**从源文件 AST 自动派生 import 候选**（不再手工维护清单），任何位置/形式的顶层 import 不再漏。

**工具本轮新增的 4 道防线**（`scripts/dev/split_api_router.py`）：

| 防线 | 作用 |
|------|------|
| 分组顺序自检 | 分组顺序 ≠ 源码顺序 → 报错（保护 catch-all 与静态路由的匹配顺序） |
| 模块级语句检查 | 源文件存在"非成员、非 import"的顶层语句（常量/映射表）→ 报错（这些**不会**被搬移，会静默丢失） |
| 未绑定名字自检（**作用域感知**） | 生成文件出现"引用但未绑定"的名字 → 报错；**基线豁免**源文件本身就有的（既有缺陷不算拆分引入） |
| 兼容导出 | 拆包前位于模块顶层、被外部引用的符号在包根 re-export，避免破坏既有 import |

> ⚠️ 「未绑定名字」检测必须**作用域感知**。最初用"全文件绑定"近似，会掩盖
> "某函数内 import、另一函数直接用"的缺陷（正是本案踩到的坑）；改为逐层收集作用域绑定后才准确。

**顺带修复与清理（均由自检暴露，属源文件既有缺陷）**：

1. **活代码缺陷**：`proxy.py`（原 `proxy_repository_endpoint`）内
   `datetime.now(timezone.utc)` 用到 `timezone`，而该处只 `from datetime import datetime, timedelta`
   → 走到该分支即 `NameError`（500）。该路径无测试覆盖，缺陷潜伏至今 → **已补 import**。
2. **死代码清理**：`_check_repo_update_permission`（原 L530-613，**全项目 0 调用**，
   仅定义 + 本文档工具配置各命中一次）函数体内使用未导入的 `timedelta` / `db`。
   按 §2.12 同口径（0 调用即删）**已删除 84 行**。

**验证（零回归证据链）**：

- 路由快照：拆分前后 `/api/v1/repositories` **18 条路径逐字一致**（应用共 147 条未变）；
- `py_compile` 全部通过；**lint 0 诊断**；
- **全量 269 passed**；
- `tests/test_url_safety.py::TestPermissionUnification` 通过 —— 它直接
  `import src.api.v1.repositories.check_admin_permission`，正是「兼容导出」防线的验证。

**P1-4 进度**：后端 4 个巨型文件**全部拆完**（`payment_service.py` / `analytics.py` / `billing.py` / `repositories.py`），
已由 §2.21 的前端单测 + 联测基建兜底；**前端巨型组件拆分进展见 §2.25**。

### 2.25 P1-4 前端巨型组件拆分 🔄（进行中）

> 承接 §2.24。前端巨型组件与后端的关键差异：**状态集中在组件内部**，
> 不能像后端那样按"端点 / 方法"直接切文件。

#### 拆分策略（与后端的差异）

| | 后端巨型模块 | 前端巨型组件 |
|---|---|---|
| 拆分依据 | 按端点 / 方法切文件 | **按"依赖数量"排序，从最少的开始切** |
| 状态处理 | 本来就在类 / 模块上 | 多数在组件内 → 抽 hook，或以 prop 传入 |
| 主要风险 | 漏搬代码 | 循环依赖；跨组件共享状态被"本地化" |

⚠️ **不要一次抽"最大那块"**：最大的块往往依赖十几个状态与回调，
硬抽会把 props 摊成一张大表、review 成本高、回归面大。
实测下来**按依赖数量从少到多切，每一步都能稳稳通过测试**。

#### 当前进度

| 组件 | 拆分前 → 现在 | 抽出模块数 / 行数 |
|------|--------------|------------------|
| `developer/Recharge.tsx` | 2001 → **1739** | 7 个 / 566 行 |
| `admin/Analytics.tsx` | 964 → **477**（**减半**） | 5 个（含复用）/ 652 行 |
| `owner/Repos.tsx` | 1059 → **985** | 1 个 / 127 行 |
| `admin/Repos.tsx` | 924（未开始） | — |

**已抽出模块**：

- `developer/recharge/`：`constants.tsx`(50) · `rechargeLogger.ts`(48) · `useRechargeData.ts`(77) ·
  `paymentSession.ts`(75) · `components/PackageCard.tsx`(84) · `components/PaymentSummary.tsx`(97) ·
  `components/PaySuccessView.tsx`(135)
- `admin/analytics/`：`constants.ts`(25) · `chartData.ts`(50，带单测) · `repoDetailColumns.tsx`(119) ·
  `OverviewTab.tsx`(246) · `RepoDetailModal.tsx`(291)
- `owner/repos/`：`repoColumns.tsx`(127)

#### ⚠️ 三条复用经验（都是实际踩出来的）

1. **需要组件内回调的"配置块"用工厂函数，不要用模块级常量**
   —— 列定义、弹窗内容等常要调 `navigate` / 某个 handler，
   写成常量就得反过来 import 组件 → **形成循环依赖**。
   统一写法：`createXxxColumns({ onEdit, onDelete })`。

2. **跨 Tab / 跨组件共享的状态必须仍作为"受控 prop"**
   —— `Analytics` 的 `trendPeriod` / `trendDays` 由"概览"与"趋势分析"两个 Tab 共用；
   若图省事改成组件内部 state，会出现"在概览选了近 30 天、切 Tab 又变回 7 天"这类
   **无报错、界面也不异常**的静默回归。

3. **拆分不夹带重构 / 行为变更**
   —— 遇到可疑逻辑（如把"金额"按 `%` 显示、antd 已废弃的 `bodyStyle`）一律
   **原样保留 + 代码注释标注 + 单独汇报**，改与不改由人决定。

#### 拆分过程中抓出的真实缺陷（4 个，全部"先补用例暴露"）

| # | 缺陷 | 危害 |
|---|------|------|
| 1 | 日志异常中断下单（`clientLog` 返回非 Promise → `.catch` TypeError） | 点充值**完全没反应**，后端请求都没发出 |
| 2 | 取消订单后扫码轮询停不下来（局部 `isPolling` vs `setState`） | 轮询 32 秒；可能把**已取消订单**标记为支付成功 |
| 3 | 组件卸载不清理定时器 | 切走页面后持续请求后端 |
| 4 | 自定义赠送比例拿"金额"冒充百分比 | 显示随充值额变化，**永远不可能正确** |

> 这 4 个都属于"**页面看着正常、日志里也没报错**"的静默失效 —— 恰恰是测试最该拦的类型。
> 做法统一为：**先写一条会失败的用例坐实它 → 再修 → 用例转绿**。
> 另抓出 1 个 flaky（`TC-FE-ANA-002` 同步 `getByText` 导致全量跑偶挂，已统一改 `findBy*`）。

#### 记录但尚未合并的重复（可后续单独做）

- `statusMap`（pending/approved/… → 颜色与文案）在 **3 处**各写一份：
  `owner/repos/repoColumns.tsx`、`admin/analytics/constants.ts`、`admin/Repos.tsx`；
- 折线图（概览预览 / 趋势 Tab / 明细弹窗）写法**高度重复**，可提为共用 `TrendChart` 组件。

## 3. 待办项详细计划

### 3.1 P1-4 巨型文件拆分 🔄（后端 4/4 ✅，前端 4 项中 3 项已启动｜详见 §2.25）

| 文件 | 现状 | 拆分方案 | 风险 |
|------|------|----------|------|
| ~~`src/api/v1/repositories.py`~~ | ✅ **已拆分**（§2.24） | → `src/api/v1/repositories/` 包（`_shared` + 8 子模块，最大 476 行；catch-all 兜底路由独立成 `proxy.py` 并最后注册） | 高 |
| ~~`src/services/payment_service.py`~~ | ✅ **已拆分**（§2.20） | → `src/services/payment/` 包（组合入口 + 5 个 Mixin，最大 414 行） | 中 |
| ~~`src/api/v1/analytics.py`~~（清单外） | ✅ **已拆分** | → `src/api/v1/analytics/` 包（`_shared` + 5 子模块，最大 194 行） | 中 |
| ~~`src/api/v1/billing.py`~~（清单外） | ✅ **已拆分**（§2.23） | → `src/api/v1/billing/` 包（`_shared` + 5 子模块，最大 246 行） | 中 |
| `web/src/pages/developer/Recharge.tsx` | 🔄 **拆分中**：2001 → **1739** 行（§2.25） | 已抽 `constants`/`rechargeLogger`/`useRechargeData`/`paymentSession` + `PackageCard`/`PaymentSummary`/`PaySuccessView`；剩余：支付弹窗剩余小块、`usePaymentPolling` | 中 |
| `web/src/pages/owner/Repos.tsx` | 🔄 **已起步**：1059 → **985** 行（§2.25） | 已抽 `repos/repoColumns.tsx`；剩余：`BasicInfoTab`/`EndpointsTab`/`LimitsTab` 三个 Tab | 中 |
| `web/src/pages/admin/Analytics.tsx` | ✅ **基本完成**：964 → **477** 行（**减半**，§2.25） | 已抽 `analytics/`（`constants`/`chartData`/`repoDetailColumns`/`OverviewTab`/`RepoDetailModal`）；剩余：趋势 Tab（约 110 行） | 低 |
| `web/src/pages/admin/Repos.tsx` | 📋 待开始（924 行） | 已有 8 条用例兜底，可随时开拆 | 中 |

**建议做法**：每次只拆一个文件（前端则按"依赖数量"切最小的一块，见 §2.25），
拆分后跑全量测试（后端 269 条 `pytest`；前端 142 条 `npm run test:unit`）
+ 前端构建 + 手工回归对应页面。

> 💡 前端拆分**尤其依赖先有测试**：后端 `repositories.py` 与前端 `Recharge`/`Analytics`
> 都是在补齐用例后才动刀的 —— 否则"静默失效"类问题（页面正常、日志无错）无从发现。

**并行建议**：`RepoService.call_repository` 为死代码，建议在第 3.1 步中**直接删除**（连同 `services/__init__.py` 的导出），
或改为内部薄封装委托到 `repositories.py` 的实现，避免两套转发逻辑并存。

---

### 3.2 P1-6 统计预聚合 ✅（三步已全部落地，保留供追溯）

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

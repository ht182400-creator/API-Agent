# 时区方案设计文档（分析、论证与收敛记录）

**文档编号**：TZ-DESIGN-API-2026-001
**版本**：V1.0
**日期**：2026-09-15
**状态**：已实施（查询侧口径收敛完成）
**关联文档**：`BUG_FIXES.md`（时区问题说明）、`ENVIRONMENT_AND_PAYMENT_MODE.md`、`OPTIMIZATION_BACKLOG.md`

---

## 1. 一句话结论

> **存储统一 UTC（timestamptz），业务口径统一北京时间，全部经 `src/utils/time_range.py` 显式转换。**
> 该架构与 Django `USE_TZ=True`、Stripe 同一主流路线，**无需推翻**；
> 本文记录"为何如此"的完整论证，以及从 `BUG_FIXES.md` 原始方案到现行方案的演进关系。

---

## 2. 基础概念：三种"时间语义"必须区分

| 语义 | 例子 | 正确的存储 | 正确的计算方式 |
|------|------|-----------|---------------|
| **瞬间（instant）** | 创建时间、支付时间 | `timestamptz`（UTC） | aware datetime（UTC 或任意时区） |
| **业务日界** | "今日调用"、"本月账单" | 仍是 timestamptz | 显式换算为 UTC 区间查询 |
| **展示** | 用户看到的时间 | 不存储 | 前端按本地时区渲染 |

混淆这三种语义是本项目历史时区 bug 的总根源：
把"瞬间"当"naive 本地时间"写入（偏 8 小时）、把"业务日界"交给 `func.date()`（依赖会话时区）。

---

## 3. 原理：为何"数据库和本地北京时间不兼容"？

### 3.1 timestamptz 的本质

PostgreSQL 的 `TIMESTAMP WITH TIME ZONE` **不存储时区**，只存一个 UTC 瞬间；
显示与 `func.date()` 的结果由**会话时区**（`TimeZone` 参数）决定。

### 3.2 naive datetime 的信息丢失

Python `datetime.now()`（无 `tzinfo`）不含时区信息。
asyncpg 收到 naive 值时**按会话时区解释**：

```
开发者意图：北京时间 2026-09-15 14:03:00（= UTC 06:03）
asyncpg 解释：naive → 按 UTC 补齐 → UTC 14:03
结果：偏移 8 小时（写入侧真实 bug，见 OPTIMIZATION_BACKLOG §2.7）
```

### 3.3 实证：同一句 SQL 两种结果（2026-09-15 实测）

数据库**服务器**时区 = `Asia/Shanghai`，而应用会话被 `database.py::get_db()` 强制 `SET TIME ZONE 'UTC'`：

| 客户端 | 会话时区 | `func.date(created_at)` 结果 |
|---|---|---|
| 应用连接 | UTC（代码强制） | **UTC 日期** |
| psql 直连 | Asia/Shanghai（服务器默认） | **北京日期** |

> 例：北京 9-16 早晨 06:00 = UTC 9-15 22:00 → psql 返回 `9-16`，应用返回 `9-15`。

**这就是"不兼容"的实质**：不是数据库不支持北京日期，而是
`func.date()` 的结果依赖一个**隐式的会话配置**，不同客户端答案不同。
结论：**显式优于隐式** —— 业务口径必须用 `timezone('Asia/Shanghai', col)` 显式声明，
或用半开区间换算，绝不把正确性押在会话配置上。

---

## 4. 复盘 `BUG_FIXES.md` 的原始方案

### 4.1 当时的做法与理由

修 `/billing/bills` 日期筛选失效时建立了系统基调：

```
前端传北京日期 2026-05-08
  → 后端手工换算 UTC 区间 [2026-05-07 16:00, 2026-05-08 15:59:59]
  → WHERE created_at BETWEEN（timestamptz 内部只存 UTC）
  → 返回 UTC，前端 dayjs 转本地显示
```

文档同时否决了两个备选：会话设 `Asia/Shanghai`（仅显示层换皮）、
`TIMESTAMP WITHOUT TIME ZONE` 存北京时间（不支持跨时区，反模式）。

### 4.2 为何当时测试是通过的（三个正确做法）

| 原方案做对的 | 对比后来出问题的写法 |
|---|---|
| 传 **aware UTC 值**与 timestamptz 比较，类型匹配 | naive `datetime.now()` 被会话时区解释 → 偏 8 小时 |
| 用**范围查询**，未触碰 `func.date()` | `func.date(created_at)` 按会话时区取日期 → 隐式依赖 |
| 固定 `+8` 偏移在**无夏令时**的中国恒正确 | 有 DST 地区手工 timedelta 会错 |

### 4.3 原方案的三个局限（→ 现行方案的演进点）

1. **亚秒丢失**：`created_at <= '...15:59:59'` 闭区间，timestamptz 有微秒精度
   → 最后一秒内的 `15:59:59.001~999999` 记录被漏掉。
   ✅ 修正：**半开区间** `[起, 次日0点)`（`cst_day_range_utc`）。
2. **手工 `timedelta(hours=8)` 散落各接口**：复制粘贴易错、不可复用。
   ✅ 修正：统一工具 `src/utils/time_range.py`。
3. **无法防 `func.date()` 隐式依赖**（§3.3 的实证）。
   ✅ 修正：分组用 `cst_date_expr`（显式 `timezone('Asia/Shanghai', col)`），过滤用半开区间。

> **评价**：原方案方向正确（业界主流），它就是现行方案的手工版；
> 现行方案 = 原方案的"工程化 + 语义显式化"，而非推翻重来。

---

## 5. 业界方案对比

| 方案 | 代表 | 评价 |
|---|---|---|
| **UTC 存储 + 应用层显式转换**（本项目现行） | Django `USE_TZ=True`、Stripe | ✅ 主流正确做法 |
| 会话时区设本地 | `BUG_FIXES.md` 方案 A | ⚠️ `func.date` 依赖连接配置；本项目 psql 与应用已实测不一致 |
| `TIMESTAMP WITHOUT TIME ZONE` 存本地 | `BUG_FIXES.md` 方案 B | ❌ 反模式，文档自己已否决 |
| 生成列 / 表达式索引 | 大数据量优化 | 性能层（§8），不改变语义 |

---

## 6. 现行规范（写入 `MEMORY.md`，代码唯一入口 `src/utils/time_range.py`）

| 场景 | 正确写法 | 禁止写法 |
|------|---------|---------|
| 列定义 | `Column(DateTime(timezone=True), default=get_utc_now())` | 无时区 `DateTime`；硬编码 `default="simulation"` 类固定值 |
| 当前时刻 | `cst_now()` / `datetime.now(timezone.utc)` / `get_utc_now()` | `datetime.now()`（naive 本地时间） |
| "今天/某天"过滤 | `cst_day_range_utc()` / `cst_day_range_utc_from_date(d)` 半开区间 | `func.date(col) == ...`（会话时区依赖 + 索引失效 + 闭区间丢亚秒） |
| 按天分组/图表 label | `cst_date_expr(col)` | `func.date(col)` |
| 指定月统计 | `cst_month_range_utc(y, m)` | 手工拼 `timedelta(hours=8)` |
| 展示 | 前端 dayjs 转本地 | 后端拼字符串时间 |

---

## 7. 查询侧口径收敛记录（2026-09-15 本轮）

此前已完成：写入侧 100% UTC（76 aware / 0 naive 列）；
`admin_billing` / `analytics` / `billing` / `repositories`（主流程）接入 `time_range`。

### 7.1 本轮收敛清单

| 文件 | 原写法 | 问题 | 收敛后 |
|------|--------|------|--------|
| `api/v1/admin.py` | `func.date(created_at) == utc.now().date()` | UTC 日界 + 索引失效 | `cst_day_range_utc()` 半开区间 |
| `api/v1/repositories.py` | `func.date(created_at) == today` | 同上 | 同上 |
| `api/v1/quota.py`（usage-history） | 窗口起点 UTC 0 点截断 + `func.date` 分组 ×3 + 标签用 UTC now 补齐 | 窗口与分组日界均偏 8 小时 | `cst_day_start_utc(days)` + `cst_date_expr`（复用对象） + `cst_now()` 补标签 |
| `api/v1/quota.py`（consumption-trend） | 窗口 UTC 0 点截断 + **Python 侧** `created_at.strftime()` 直接取 UTC 日期 | 同上（聚合在应用层完成，读出的 aware UTC 未转时区） | `cst_day_start_utc(days)` + `created_at.astimezone(CST)` 再取日期 |
| `api/v1/admin_reconciliation.py` | `day_start/day_end` naive（被会话时区解释）+ `<= 23:59:59` 闭区间 ×3 + `func.date(reconcile_date)` ×2 | 对账窗口错位 8 小时 + 亚秒丢失 | `cst_day_range_utc_from_date()`；`day_start` 同时是 `reconcile_date` 写入锚点，**写入/查询同源** |
| `services/reconciliation_scheduler.py` | 同上（含 `target_date = utc.now() - 1d`） | "昨天"早 8 小时切换 | `cst_now() - 1d` + 同上半开区间 |

### 7.2 本轮踩坑：`cst_date_expr` 的 GroupingError

`cst_date_expr` 内部的 `'Asia/Shanghai'` 是**绑定参数**，每次**调用**都会生成新的参数占位符。
同一条查询的 `select` / `group_by` / `order_by` 若各自调用一次，PostgreSQL 判定三者表达式不一致：

```
asyncpg.exceptions.GroupingError: 字段 "api_call_logs.created_at" 必须出现在 GROUP BY 子句中
```

**正确写法**（复用同一表达式对象，`time_range.py` docstring 已写入该警告）：

```python
date_col = cst_date_expr(APICallLog.created_at).label("date")
select(date_col, ...).group_by(date_col).order_by(date_col)   # ✅
```

旧写法 `func.date(col)` 无绑定参数，同列编译文本相同故能通过 —— 这也是该坑此前未暴露的原因。
已同步修复 `analytics.py` 中同构的 `_cst_date` 三次调用点。

### 7.3 对账模块的关键设计点

`reconcile_date` 的**写入锚点**（`reconcile_date=day_start`，共 3 处）与**查询边界**必须来自同一函数：

```
day_start, day_end = cst_day_range_utc_from_date(date.date())   # 北京 0 点的 UTC 时刻
写入：reconcile_date = day_start
查询：reconcile_date >= day_start AND reconcile_date < day_end
```

原实现的锚点是 naive 值（被会话时区 UTC 解释为 UTC 0 点），查询用 `func.date()`（UTC 日界）——
两者虽然"歪打正着"互相匹配，但都与"对账单 = 北京自然日"的业务语义错位 8 小时。
本轮改为**双侧同源、语义显式**。

### 7.4 验证

- 全项目残留复查：`datetime.now()` naive 仅剩 `logging_config.py`（日志文件名，**合理保留**）；
  `func.date(` 仅剩 `time_range.py` 自身实现与死代码（`billing_service.py` / `repo_service.py`）。
- 新增 `tests/test_time_range.py` **8 条**（TC-TZ-001~008），
  其中 TC-TZ-007/008 为**落库级**：构造 `created_at = UTC 9-14 20:00（= 北京 9-15 04:00）`的账单，
  证明它按北京日界归入 9-15，而旧 UTC 日界口径下查"9-15"会**丢失**这条记录。
- 全量 pytest：**238 passed**。

---

## 8. 性能说明与后续优化（未实施）

- `cst_date_expr`（`func.date(func.timezone(...))`）**不能命中普通索引**，但它只用于
  `GROUP BY`（分组前已被 WHERE 的半开区间限定到小范围），可接受；
  而 `WHERE func.date(col) == ...` 这种**过滤**写法会全表扫描 —— 半开区间写法可命中 `created_at` 索引。
- 若未来按天统计量级大：考虑表达式索引
  `CREATE INDEX ON api_call_logs ((created_at AT TIME ZONE 'Asia/Shanghai'))`
  或生成列 / 预聚合表（OPTIMIZATION_BACKLOG P1-6）。

---

## 9. 剩余注意事项

1. **`logging_config.py` 的 `datetime.now()` 保留**：日志文件按本地日期切割是运维惯例，与数据口径无关。
2. **会话时区双轨现状**：应用强制 UTC、psql 直连为服务器默认（Asia/Shanghai）。
   保持现状即可 —— 显式写法不依赖它；**不要**为了"顺手"把服务器时区改掉或给连接串加时区参数。
3. **死代码中的旧写法**（`billing_service.py` / `repo_service.py`）：随死代码清理任务一并删除，
   不单独修补。

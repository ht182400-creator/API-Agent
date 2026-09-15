# 回归测试报告 — 2026-09-16

> **目的**：对 9-15 / 9-16 两天内所有提交修复的问题做系统性回归验证，
> 并以**负向验证**（变异检验）证明测试非"为通过而通过"。
> **方法**：正向全量重跑 + 逐缺陷变异（把修复改回缺陷形态，用例必须变红）+ 预算机制拦截验证。
> **结论**：**后端 269 passed / 前端 144 passed / 变异 4/4 有效 / 预算拦截有效**；
> 回归发现并修复 **1 个时间敏感 flaky**（详见 §5）。

---

## 1. 环境与命令

| 项 | 值 |
|---|---|
| 基线提交 | `9c2e3ec`（HEAD，9-16 03:13） |
| 后端 | Python 3.13.3 + pytest 9.0.2，`python -m pytest tests -q --tb=short` |
| 前端 | `npm run typecheck` / `npm run test:unit` / `npm run test:budget` |
| 变异检验 | `node scripts/dev/verify-fixes.mjs [--only FIX-n] [--log <json>]`（自动变异→跑用例→还原→复跑确认） |
| 运行时间 | 2026-09-16 03:17 ~ 03:40（本地 UTC+8；⚠️ 此时刻本身构成了 §5 的触发条件） |

---

## 2. 覆盖范围（问题 → 提交 → 验证方式 → 结果）

### 2.1 后端（9-15，提交 `d7e3f17` ~ `dc8e0e1`）

| # | 问题 / 改动 | 来源提交 | 覆盖测试（正向） | 结果 |
|---|---|---|---|---|
| B1 | 测试清空开发库事故（三缺陷：无库 guard / truncate 误用 / 时间列） | `d7e3f17` 等 | `test_environment_guard.py` 41 条 | ✅ 全过 |
| B2 | 账单 environment 防漏传五层防御 L1~L5 | 9-15 授权实施 | `test_environment_guard.py` + `test_payment_config_source.py` 6 条 | ✅ 全过 |
| B3 | 支付回调来源 IP 白名单 | `d7e3f17` | `test_payment_callback_allowlist.py` 9 条 | ✅ 全过 |
| B4 | Redis 冷却期绕过修复 + Redis 接入 | `dc8e0e1` | `test_redis_cooldown.py` 3 条 + `test_rate_limit_redis.py` 18 条 | ✅ 全过 |
| B5 | 限流 / 脱敏 / URL 安全 | 第二~三轮加固 | `test_rate_limit.py` 3 / `test_sanitize.py` 41 / `test_url_safety.py` 39 | ✅ 全过 |
| B6 | P1-4 后端拆分：payment / billing / repositories → 包 | `438bedf` `9c5c774` | `test_payment.py` 4 / `test_repositories.py` 5 / 全量 | ✅ 全过 |
| B7 | P1-6 统计预聚合（阶段 1~3：聚合 / 读切换 / 缓存） | `dc8e0e1` | `test_stats_aggregation.py` + `test_stats_query_service.py` | ⚠️→✅ 抓出 1 个 flaky，修复后全过（§5） |
| B8 | 时区口径收敛（按北京时间分组） | 9-15 §十五 | `test_time_range.py` 8 条 + 分组用例 | ✅ 全过（行为符合设计） |

### 2.2 前端（9-15 ~ 9-16）

| # | 问题 / 改动 | 来源提交 | 覆盖测试 | 正向 | 负向（变异） |
|---|---|---|---|---|---|
| F1 | Login 自动清空定时器截断用户输入 | `0999eb5` | `TC-FE-LOGIN-008`（真实 user.type 逐字符） | ✅ | — |
| F2 | ErrorContext `ECONNABORTED` 分支不可达 | `7dcd5f0` | `TC-FE-ERRCTX-001` | ✅ | — |
| F3 | paymentErrors 两条局限（code 识别 / isPaymentError 严格 boolean） | `7dcd5f0` | paymentErrors spec 16 条 | ✅ | — |
| F4 | Analytics 首屏 `getTrend` 重复请求 | `0999eb5` | `TC-FE-ANA-001` | ✅ | — |
| F5 | ANA-002 时序 flaky（同步 getBy 混用） | `9f9c759` | analytics spec 7 条 | ✅ | — |
| F6 | **缺陷①** 支付日志异常中断下单 | `f101bca` | `TC-FE-RECHARGE-009/016` | ✅ | **FIX-1 ✅ 变异后红** |
| F7 | **缺陷②** 取消订单后扫码轮询停不下来 | `0c9baad` | `TC-FE-RECHARGE-013` | ✅ | **FIX-2 ✅ 变异后红** |
| F8 | **缺陷③** 卸载不清理轮询定时器 | `f17043e` | `TC-FE-RECHARGE-014` | ✅ | **FIX-3 ✅ 变异后红** |
| F9 | **缺陷④** 赠送比例拿金额冒充百分比 | `b24aab2` | `TC-FE-RECHARGE-015` | ✅ | **FIX-4 ✅ 变异后红** |
| F10 | 前端 48 项 TS 类型错误 + typecheck 入防线 | `d7e3f17` / `65f709e` | `npm run typecheck` | ✅ 0 错误 | — |
| F11 | P1-4 前端拆分（Recharge 7 模块 / Analytics 3 模块 / owner·Repos 3 模块） | `87ff182`~`50b98ac` 等 10 提交 | 前端全量 144 条 | ✅ | — |
| F12 | 警告清理 7 类（destroyOnClose 108 / keys 4 / bodyStyle 8 / bordered 28 / react-router 16 / Spin.tip 16 / rc-collapse 2） | `ab15170`~`63218bb` | `npm run test:budget` | ✅ 0 条残留 | **预算拦截 ✅（§4.2）** |

---

## 3. 正向验证结果（原始输出摘要）

```
后端  python -m pytest tests -q
  → 269 passed in 109.46s          （首跑 268 passed / 1 failed，见 §5）

前端  npm run typecheck
  → 0 错误（TC_EXIT=0）

前端  npm run test:unit
  → Test Files  14 passed (14)
    Tests  144 passed (144)
    Duration  36.87s

前端  npm run test:budget
  → [warn-budget] ✅ 警告在预算内
       96  act: update not wrapped in act
       61  jsdom: getComputedStyle pseudo-elements
```

---

## 4. 负向验证（证明测试不是虚拟的）

### 4.1 变异检验：4/4 有效

`verify-fixes.mjs` 把修复**改回缺陷形态** → 对应用例**必须变红**；随后自动还原源码并复跑确认恢复绿色。

| 变异 | 回退的修复 | 期望用例 | 变异后 | 还原后 | 判定 |
|---|---|---|---|---|---|
| FIX-1 | `sendPaymentLog` 去掉 try/catch 与 Promise.resolve（回到 `.catch` TypeError 中断下单） | 009 / 016 | 🔴 2 failed | 🟢 2 passed | ✅ 有效 |
| FIX-2 | `stopQrcodePolling` 不再置 `qrcodePollingRef`（轮询取消后继续跑） | 013 | 🔴 1 failed | 🟢 1 passed | ✅ 有效 |
| FIX-3 | 卸载 cleanup 不再清理定时器 | 014 | 🔴 1 failed | 🟢 1 passed | ✅ 有效 |
| FIX-4 | 赠送比例回到 `+{金额×ratio}%` 的错误显示 | 015 | 🔴 1 failed（`Unable to find "+5%"`） | 🟢 1 passed | ✅ 有效 |

**汇总：4 个有效 / 0 个空测试**。每条变异的 firstError 均指向对应断言（如 FIX-4 的
`Unable to find an element with the text: +5%`），证明失败原因正是"行为回退"，而非环境噪音。

> ⚠️ 过程留痕：FIX-2 首次运行为 **SKIPPED**（find 上下文在轮询实现演化后命中 2 处，
> 脚本按设计拒绝歧义变异）→ 已把变异规则收紧到 `stopQrcodePolling` 函数体唯一匹配 → 复跑有效。
> 该防护本身也是检验机制健壮性的一部分。

### 4.2 警告预算拦截验证

向 `Recharge.tsx` 故意注入 `<Modal destroyOnClose ...>`（该种类已从基线清除）：

```
BUDGET_EXIT=1
[warn-budget] ❌ 警告预算超标：
  - 新增警告种类：antd: Modal.destroyOnClose deprecated（140 次）——
    基线中已不存在，说明修复被回退或引入了新问题
```

→ 预算机制**真实拦截**（exit 1 + 指认具体种类与次数），注入后源码已还原
（`git diff` 仅剩本报告相关的 2 个合法改动）。

---

## 5. 回归发现的问题与修复（本次回归的实际产出）

### 5.1 现象

后端首跑 `test_stats_query_service.py::test_group_by_day_merges_segments`（TC-STATQ-006）失败：

```
assert len(rows) == 2   →   实际 3
rows key: 2026-09-15 / 2026-09-16 / 2026-09-17
```

### 5.2 定性：**测试自身的时区敏感 flaky**，不是产品回归

- `group_by_period` 按**北京时间自然日**分组 —— 这是 9-15 时区口径收敛的**有意设计**（docstring 明确）；
- 测试 helper `_hour_base()` 用 **UTC 当前整点 − 3h** 构造数据。当 UTC 处于
  **16:00~20:00（= 北京 0:00~4:00）** 时，`h-1` 与 `h+24` 的数据横跨 **3 个**北京自然日；
- 本次回归恰好在该窗口运行（本地 03:2x = UTC 19:2x）→ 必然失败；
- 该测试在 9-15 晚间创建并通过（当时 UTC ≈14:3x，安全窗）→ 缺陷潜伏至今。

### 5.3 修复（沿用"先建证据链"）

1. 新增 `_day_base()`：锚定**北京时间 12:00** 对应的 UTC —— `h-1`/`h` 同日、`h+24` 次日，
   **任意时刻运行都不跨界**；仅"跨自然日"用例（TC-STATQ-006）使用；
2. `_hour_base()` 保持原语义（UTC now−3h）—— 水位/追赶用例（008/009）隐式依赖
   "h 距 now 约 3 小时"（第一版修复曾全局换锚点，立即暴露这 2 个用例失败，遂回退收窄）；
3. `test_stats_aggregation.py` 的同名 helper 依赖 `recent_hours` 的 now 窗口，**不照改**（已注释说明）。

### 5.4 修复后

```
python -m pytest tests/test_stats_query_service.py tests/test_stats_aggregation.py -q
  → 19 passed
python -m pytest tests -q（全量）
  → 269 passed in 109.46s
```

---

## 6. 残余风险与说明（不粉饰）

1. **act 警告 96 条**：全部为 antd 内部组件（CSSMotion 72 / EllipsisMeasure 24 / Notifications 18 等）
   在 jsdom 的异步行为；根治需 mock antd 内部模块，风险 > 收益，**已接受并受预算看管**（只减不增）；
2. **jsdom 61 条**：环境限制（`getComputedStyle` 不支持伪元素），无法根治；
3. **未覆盖区**：144 条前端用例覆盖的是"写了断言的行为"；`Spin.tip` 其余 10 处修复
   （无测试文件）本次仅验证"不产生警告"，**未验证 UI 文字显示**（它们不被任何测试渲染）；
4. **API 契约联测**（`e2e/api-contract.spec.ts`，12 条）需要真实后端运行，本次未跑
   （回归以单元层为主）；如需可在后端启动后补跑。

---

## 7. 结论

| 维度 | 结果 |
|---|---|
| 后端全量 | **269 passed**（0 失败） |
| 前端全量 | **144 passed / 14 spec**，typecheck 0 错误 |
| 缺陷回归用例有效性 | **变异 4/4 全部变红**（无空测试） |
| 警告预算机制 | **负向拦截验证通过**（exit 1 + 指认种类） |
| 回归新发现 | **1 个**（STATQ 时区敏感 flaky）→ 已修复并全量复跑 |
| 两天全部问题（B1~B8 / F1~F12） | 无一回归 ✅ |

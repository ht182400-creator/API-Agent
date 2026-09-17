# 发布说明（Release Notes）

> 本文件记录对外可见的版本级变更。日常开发的细粒度记录见各专题文档与
> `docs/test-log-*.md`；议题全貌见 [`OPTIMIZATION_BACKLOG.md`](OPTIMIZATION_BACKLOG.md)。

---

## v1.1.0（2026-09-17）—— 支付流程重构收口 + 巨型页拆分 + 前端测试体系成型

**范围**：`v1.0.3..v1.1.0` 共 34 个提交。主题三条线：① `Recharge` 支付流程行为重构（M1~M5 全部完成）；② P1-4 巨型页拆分；③ 前端测试体系（用例库 + 变异检验 + 警告预算）成型。

### 一、支付流程行为重构（核心，M1~M5）

| 里程碑 | 交付 | 关键收益 |
|---|---|---|
| **M1** | 显式状态机 `paymentMachine.ts`（8 状态 × 13 事件）+ 纯函数用例 | 终态不可逆 / 单结算入口 / 探测开关派生 等不变式被用例锁住 |
| **M2** | 编排 hook `usePaymentFlow.ts`；35 处生命周期写入收敛为语义 action | 页面不再直接写状态；act 警告 102 → 88 |
| **M3** | 探测策略统一（同一条规则 11 处 → 1 处）、两套轮询合并为 `usePaymentProbe`、删 `paymentStateRef`、延迟刷新收敛 `useDelayedReload` | 修掉 3 处真实行为漂移（含 `pollPaymentStatus` 漏判 `completed`）；页面里"第二份真相"清零 |
| **M4** | 倒计时派生化 `useCountdown`（由 `expiresAt` 派生 + 关弹窗即停表）；窗口管理收编 `usePaymentWindow` | 修掉自减式倒计时"漂移"与"关弹窗后定时器空转"两个真实问题 |
| **M5** | 资金链路安全加固：`localStorage` / `postMessage` / `storage` 事件等**客户端可写信号不再直接结算**，统一走 `confirmPaymentWithServer()`（进 confirming → 向后端求证 → 仅后端说 paid/completed 才结算） | 堵住"控制台伪造一条 localStorage 记录即可白嫖余额显示"的安全缺口 |

**代码量**：`Recharge.tsx` 2001 → 1419 行（-29%）；职责拆为 状态机 / 编排 hook / 探测 hook / 窗口 hook / 倒计时 hook / 弹窗组件。

### 二、安全与缺陷修复

- **M5 资金链路加固**（见上表，含 3 条针对性用例 + 变异规则 FIX-10/11）。
- **`closePayWindow` 自关用户窗口缺陷**（`FE-BUG-CLOSE-PAY-WINDOW-CLOSE-SELF`）：无支付窗口引用时错误调用 `window.close()` 关闭当前主窗口 —— 已修，storage/postMessage 跨窗口通知路径不再触发关窗。
- 首屏账单重复请求、负数金额显示顺序、一次性密钥关闭后残留 DOM、种子脚本 `api_docs_url` 不随网关更新 等 6 处顺带修复。

### 三、P1-4 巨型页拆分

| 文件 | 前 → 后 |
|---|---|
| `developer/Analytics.tsx` | 964 → 309 行 |
| `owner/Repos.tsx` | 1059 → 704 行 |
| `AdminLogs.tsx` | 904 → 694 行 |
| `developer/Recharge.tsx` | 2001 → 1419 行（经三线拆分） |

### 四、前端测试体系

- **用例库**：`tests/cases/frontend_cases.json` 收敛为 **31 套件 / 320 条用例 / 无 planned / 0 开放缺陷**；总测试 **35 文件 / 327 passed**。
- **变异检验**：`scripts/dev/verify-fixes.mjs` **13/13 有效 / 0 空测试** —— 每条关键修复都有"缺陷形态回放"规则。
- **警告预算**：`test:budget` 门禁 + 基线只减不增（当前 act 86 / jsdom 181）；⚠️ 已知 act 绝对数字受线程调度影响大，只作同口径对比（详见架构文档 §7.5）。
- **测试留痕**：`docs/test-logs/` 纳入版本库（`.gitignore` 例外）。

### 五、文档

- **新增** [`payment-flow-architecture.md`](payment-flow-architecture.md)：架构 / 状态机 / 信号流转 6 张图 + 小白与专家双视角解读 + act 警告专题。
- [`payment-flow-refactor.md`](payment-flow-refactor.md)：M1~M5 方案书与状态表（全部 ✅）。
- 旧版 [`支付流程文档.md`](支付流程文档.md) 加时效声明与语义更正（内容已被上述两份取代）。
- README ×2、`OPTIMIZATION_BACKLOG.md`、`Test_ALL_PLAN.md`、`test-log-2026-09-16/17.md` 全部与代码同步（经全景交叉复核）。

### 质量闸门（发布时点实测）

```
typecheck        0 错误
测试             35 files / 327 passed
用例库自检        7 passed（31 套件 / 320 条 / 0 planned / 0 开放缺陷）
变异检验          13/13 有效 / 0 空测试
警告预算          ✅ act 86 / jsdom 181（基线锁定）
```

### 升级说明

纯前端行为加固与重构，无数据库迁移、无 API 破坏性变更、无新依赖。支付沙箱联调注意事项见
[`支付宝沙箱支付问题解决记录.md`](支付宝沙箱支付问题解决记录.md) 与
[`支付宝回调签名验证问题修复记录.md`](支付宝回调签名验证问题修复记录.md)。

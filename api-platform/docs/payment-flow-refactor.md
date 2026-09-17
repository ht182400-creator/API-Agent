# 支付流程行为重构方案（`developer/Recharge.tsx`）

> 立项背景：P1-4 的搬运式拆分已把 `Recharge.tsx` 从 2001 行降到 1571 行，
> 且 [`OPTIMIZATION_BACKLOG.md` §2.25 / §3.1](OPTIMIZATION_BACKLOG.md) 已判定
> 「**可独立切出的部分已抽尽**」。继续降行数必须动**行为结构**，故立此议题。
>
> 本文是**规划书**：先讲清现状问题（附证据）、目标架构、迁移步骤与风险，
> 落地按 M1→M4 分步进行，**每一步都必须全量绿灯**（前端 292 条用例 + 警告预算 + 变异检验）。

---

## 1. 现状：一个业务事实，七处各自实现

「用户支付成功」这件事，代码里有 **7 个来源**各自把它翻译成状态变更：

| # | 来源 | 触发点 | 位置 |
|---|---|---|---|
| 1 | 支付宝同步回调（URL 参数） | 从支付宝跳回 | `handleAlipayCallback` |
| 2 | `localStorage` 存储事件 | 支付页写了 `payment_success_result` | `handleStorageChange` |
| 3 | 挂载时读 `localStorage` | 页面刷新回来 | `checkPaymentResult` |
| 4 | 窗口获得焦点 | 关闭支付窗口 | `handleWindowFocus` |
| 5 | 页面可见性变化 | 从别的标签页切回 | `handleVisibilityChange` |
| 6 | `postMessage`（3 种消息类型） | 支付页主动通知 | `handleMessage` |
| 7 | 轮询 | 扫码 8 次递进 / 跳转每 3 秒 | `startQrcodePolling` · `startPaymentPoll` → `handleRefreshStatus` |

**每一处都自己写一遍**这段"结算"逻辑：

```ts
setCurrentPayment({ ...payment, status: 'paid' })
clearPaymentFromSession()
fetchBalance()
// 扫码 → setPayModalVisible(false) + message.success('充值成功！')
// 跳转 → setPaySuccess(true)（显示大界面，不关弹窗）
```

据实际代码统计，这段分支在文件里**重复 7 次**（`handleMessage` 内部还重复两份）。
由此产生的具体问题：

### 1.1 状态被切碎 → 需要 `paymentStateRef` 绕闭包

生命周期事实分散在 **9 个 useState / useRef** 里：
`currentPayment` · `payModalVisible` · `paySuccess` · `isProcessingCallback` · `qrcodePolling` ·
`countdown` · `payError` · `paymentStateRef` · `creatingOrder`。

因为 4 类事件监听在 `useEffect(..., [])` 里注册（为了只注册一次），回调拿到的是**首帧闭包** →
只好再造一个 `paymentStateRef` 用 effect 手工同步"最新状态"（源码第 86-100 行）。
**这是"状态切碎"的典型症状**：需要人工维护第二份真相。

### 1.2 状态组合非法 · 只能靠 if 兜

- `paySuccess=true` 时 `qrcodePolling` 也可能是 true（两份状态各管一半）；
- 已取消的订单仍可能被轮询回报 `paid` → 把**取消单标记成成功**（`TC-FE-RECHARGE-013` 就是抓这个的）；
- `pollPaymentStatus` 里边查状态边决定是否 `setPaySuccess`，与 `handleRefreshStatus` 职责重叠。

### 1.3 停止/清理靠"记得"而非结构

停止轮询要同时做三件事：`qrcodePollingRef.current = false`、`clearInterval`、`setState(false)`。
组件卸载清理集中在**一个** effect 里手工列举 3 个定时器 + 1 个 ref（第 120-176 行）。
凡是"新加一个定时器就得回来给它补一行清理"的结构，长期必然漏（历史上已漏过一次：
曾只在关闭弹窗时清理，切页面就泄漏）。

---

## 2. 目标架构

### 2.1 依赖决策：**不引入 XState / TanStack Query**（附理由）

| 候选 | 为什么不用 |
|---|---|
| **XState** | 它的价值在**并行/复合/历史状态**；本流程是一条**线性生命周期**（下单→等待→确认→终态），用 `useReducer` 手写即可表达。引入后所有状态读写都要过 `actor`，而当前只在**一个页面**用 —— 成本高、收益低。 |
| **TanStack Query** | 它的价值在**服务端状态的缓存/去重/失效**。而支付状态轮询是**事件驱动 + 受窗口状态门控**的（弹窗关/成功即停），不是可缓存的数据；引入后要为它加 `QueryClientProvider`（影响全部 18 个页面 spec 的渲染助手），爆炸半径远大于收益。 |
| **zustand**（已在依赖里） | 适合跨组件共享的全局态；支付流程是**单页局部态**，放全局反而扩大作用域。 |

**结论：沿用"手写状态机 + 专用 hook"** —— 即所谓 **"You don't need a library for a state machine"**
路线：把这几家库的核心思想（显式状态、单向数据流、副作用集中在 hook、派生值不落库）**搬进本项目的约定**，
零新增依赖、零爆炸半径、与现有测试网完全兼容。若将来第二个页面需要复用整条支付流程，
再把 machine 平移进 `src/features/payment/` 即可（本方案的 machine 是**纯函数**，平移成本为零）。

### 2.2 分层

```
recharge/payment/
  paymentMachine.ts        纯函数：状态/事件类型 + reducer + 派生选择器（零 React、可单测）
  usePaymentFlow.ts        编排：useReducer(machine) + 副作用（下单/探测/结算/倒计时），对外只暴露窄接口
  usePaymentProbe.ts       唯一"成功信号探测"：4 类监听 + 1 个定时器（内含各自的 cleanup）
  useCountdown.ts          订单有效期倒计时（由 machine 的 expiresAt 驱动）
  usePaymentWindow.ts      支付窗口句柄 + 关窗轮询
```

**页面只做三件事**：① 调 `usePaymentFlow()` 拿 `{ state, actions }`；② 渲染；
③ 把 action 接到按钮上。**所有 setState 不出现在页面里**。

### 2.3 状态表（唯一真相）

| 状态 | 含义 | 弹窗 | 探测中 | 可关闭弹窗 |
|---|---|---|---|---|
| `idle` | 无进行中的订单 | 关 | ✗ | — |
| `creating` | 正在创建订单 | 关 | ✗ | — |
| `awaiting` | 订单已创建，等用户支付（扫码 / 跳转） | 开 | **✓** | ✓ |
| `confirming` | 已收到成功信号，正在向后端确认 | 开 | ✓ | ✗ |
| `succeeded` | 支付成功 | 开（大界面） | ✗ | ✗ |
| `failed` | 创建/支付失败 | 关 | ✗ | ✓ |
| `cancelled` | 用户取消 | 关 | ✗ | ✓ |
| `expired` | 订单超时 | 开 | ✗ | ✓ |

> `paySuccess` → `phase === 'succeeded'`；`isProcessingCallback` → `phase === 'confirming'`；
> `qrcodePolling` → `phase === 'awaiting' && mode === 'qrcode' && probing`。
> **派生值不落库**，从根上消灭"两份状态能同时为真"的非法组合。

### 2.4 事件与不变式

事件：`CREATE_START` · `CREATE_SUCCESS` · `CREATE_FAILURE` · `RESTORE_FOUND` ·
`STATUS_PAID` · `STATUS_PENDING` · `STATUS_FAILED` · `CONFIRM_START` · `CANCEL` ·
`CLOSE` · `OPEN` · `EXPIRE` · `RESET`

**核心不变式（写进 reducer 的单测）**：

1. **终态不可逆**：`succeeded` / `cancelled` / `expired` 收到任何 `STATUS_*` 都**原样返回**
   → 从根上杜绝「取消后又被轮询标记成功」（TC-FE-RECHARGE-013 锁的就是它）。
2. **非 `awaiting`/`confirming` 不探测**：`isProbing(state)` 是探测定时器的**唯一开关**
   → 「取消/关闭/成功后不再请求后端」不再依赖谁记得调 `stop()`。
3. **`probeCount` 单调递增**，扫码模式按 8 段递进间隔取自 state（不再是循环里的局部数组）
   → 间隔表可单测、可观测。
4. **结算只有一个入口**：`STATUS_PAID`。7 处来源全部改为"派发事件"，
   不再各自 `setCurrentPayment + clearSession + fetchBalance`。

### 2.5 与主流支付架构经验的对照

参照主流系统设计资料（Stripe 类支付系统设计 / webhook 可靠性 / 幂等与对账）的共识要点逐条自查：

| 主流共识 | 本实现 | 结论 |
|---|---|---|
| 支付生命周期用**显式状态机**表达，禁止自由组合的布尔量 | 8 阶段机器 + 派生值全部不落库（M1/M2） | ✅ |
| **幂等**：同一事件重复到达不得重复生效 | 终态不可逆 + 单结算入口 + `confirming` 去重 | ✅（`TC-FE-PAYMACH-008/009`） |
| **绝不以客户端信号判定支付成功**，必须服务端确认 | ⚠️ `handleStorageChange` / `checkPaymentResult` / `handleMessage` 三条路径**直接结算**，未再向后端求证 | ❌ **见 M5** |
| 轮询要**渐进退避 + 有终止条件** | 扫码 8 段递进 `[2,2,2,3,3,5,5,10]s`、跳转 3s；跑满给人工刷新指引（`nextProbeDelay` / `isProbeExhausted` 均单测） | ✅ |
| 服务端回调（webhook）才是入账真相，前端只做**呈现** | 余额一律 `fetchBalance()` 取自服务端，前端从不自行加减 | ✅ |
| 前端要能**对账**：展示与服务端不一致时以服务端为准 | 结算后强制刷新余额；「刷新状态」可随时向后端求证 | ✅ |
| 副作用与状态迁移分离，便于测试 | 纯函数 machine（21 条零 jsdom 用例）；M3 再把 I/O 收进 `usePaymentProbe` | ✅ |

**唯一缺口 → M5（新增步骤）**：

- **问题**：上面三条路径把**客户端可写的数据**（`localStorage` / `postMessage` 都同源可写）
  直接当成支付成功。
- **影响面（说清楚，不夸大）**：**不会造成真实资损** —— 余额来自服务端 `fetchBalance()`，
  订单在后端也仍是 pending；但会让**界面说谎**（显示"充值成功"而实际未到账），
  可能诱导用户以为已到账而不去核查。
- **修法（M3 的自然产物）**：这三条路径改为"**只作为触发探测的信号**" —— 先进入 `confirming`
  并立即 `getPaymentStatus` 求证，由**服务端回答**决定是否 `STATUS_PAID`。
  即把 `confirming` 从"去重层"升级为"**验证层**"（这正是机器当初预留它的原因）。

---

## 3. 迁移步骤（每步独立绿灯 + 独立提交）

| 步 | 内容 | 行为变化 | 验证 |
|---|---|---|---|
| **M1** | 新增 `paymentMachine.ts` + 单测（纯函数，零 jsdom） | 无（尚未接线） | 新 spec + 全量 + 预算 |
| **M2** | `usePaymentFlow` 接管生命周期状态：`paySuccess` / `isProcessingCallback` / `qrcodePolling` / `currentPayment` 由 machine 提供；**保留**旧的两套轮询实现（只换数据来源） | 无 | 18 条 Recharge 用例 |
| **M3** | 用 `usePaymentProbe` **替换** 4 类监听 + 2 个轮询，删除 `paymentStateRef`；7 处结算收敛为 `dispatch({type:'STATUS_PAID'})` | 无（对外行为等价） | 18 条 + **变异规则 FIX-2 / FIX-3 必须随实现更新并复验** |
| **M4** | 收编 `useCountdown` / `usePaymentWindow`；页面成为纯组合层；补 hook 级单测 | 无 | 全量 + 预算 + 变异 7/7 |
| **M5** | ⚠️ **安全加固**：`storage` / 挂载读 `localStorage` / `postMessage` 三条路径改为"只触发探测"——进 `confirming` 并向后端求证后才结算（见 §2.5 唯一缺口） | **有**（这几条路径会多一次 `getPaymentStatus`；界面不再抢先说"成功"） | 新增针对性用例（伪造 localStorage 不得直接显示成功）+ 全量 + 预算 |

### 3.1 风险与对策

| 风险 | 对策 |
|---|---|
| 支付是资金链路，改坏即资损 | 18 条既有用例 + 7 条变异规则是安全网；M2/M3 都要求「行为等价」，**不顺带改任何业务规则** |
| `TC-FE-RECHARGE-013/014` 用**真实定时器**（等 2.6s / 4.2s） | 探测间隔表必须与原实现数值一致（扫码 `[2,2,2,3,3,5,5,10]` 秒；跳转 3 秒）；M3 前先单测间隔表 |
| 变异规则 `FIX-2`（扫码停止）/ `FIX-3`（卸载清理）绑在原代码文本上 | M3 落地时**同步改规则的 `file`/`find`** 并 `--only` 逐条复验；规则不能命中时必须显式处理（脚本跳过≠通过，退出码仍为 0） |
| 旧实现"多重来源同时触发"的副作用（如 storage + focus 双触发） | 用 `confirming` 态**去重**：同一订单已进入确认/终态时，重复事件被 reducer 忽略（这正是现状缺的） |

---

### 3.2 M2 接线映射表（已逐处核对，执行时照做即可）

> 现状共 **35 处**写生命周期状态（`setCurrentPayment` / `setPaySuccess` / `setPayModalVisible` /
> `setIsProcessingCallback`）。下表的"动作"就是目标写法。

| 现位置（旧调用） | 语义 | M2 动作 |
|---|---|---|
| 4 个 `useState`（payment / paySuccess / payModalVisible / isProcessingCallback） | — | **删除**，改由 `usePaymentFlow` 只读派生 |
| 下单成功 ×2（套餐 / 自定义） | 订单落地 | `flow.created(payment)` |
| 挂载恢复 sessionStorage（成功 / 查询失败两分支） | 恢复订单 | `flow.restored(order)`（原先随后那句 `setPayModalVisible(true)` 由 action 内含） |
| 同步回调入口（`setIsProcessingCallback(true)` + 开弹窗） | 进入确认中 | `flow.restored(占位单)` + `flow.startConfirming()`（占位单是原实现就有的形态，用于"只有 order_no"的场景） |
| 同步回调 `handlePaymentSuccess`（`setPaySuccess(true)`） | **跳转**成功（保留弹窗） | `flow.settlePaid(patch, { closeModal: false })` |
| 同步回调超时 `showTimeoutDialog` | 仍是未支付 + 订单补丁 | `flow.settlePending({ payment_no })` |
| 同步回调超时弹窗「返回充值中心」 | 关弹窗 | `flow.closeModal()` |
| 同步回调 catch（占位单 + 开弹窗） | 占位订单 | `flow.restored({ payment_no:'', order_no, status:'pending' })` |
| 同步回调 finally（`setIsProcessingCallback(false)`） | 退出确认中 | `flow.settlePending()`（终态下该事件被机器忽略） |
| storage 事件 ×2 / postMessage ×2（每处各含扫码 / 跳转两分支） | **成功** | `flow.settlePaid(patch)`（弹窗去留**按 mode 自动**：扫码关、跳转留）＋ 扫码分支补 `message.success('充值成功！')` |
| `checkPaymentResult`（挂载读 localStorage） | 成功（关弹窗） | `flow.settlePaid(patch, { closeModal: true })` |
| 刷新二维码（`setCurrentPayment({...currentPayment, qr_code})`） | 订单补丁 | `flow.settlePending({ qr_code })` |
| 模拟支付成功（`setPaySuccess(true)`，不动弹窗） | 跳转语义成功 | `flow.settlePaid(undefined, { closeModal: false })` |
| `handleOpenPay`「该订单已支付」 | 成功（显式关弹窗） | `flow.settlePaid(undefined, { closeModal: true })` |
| `handleRefreshStatus`：无订单但有 `out_trade_no` | 占位订单 | `flow.restored({ payment_no:'', order_no, status:'pending' })` |
| `handleRefreshStatus`：拿到新状态（`setCurrentPayment(updatedPayment)`） | 订单补丁 | `flow.settlePending(updatedPayment)` |
| `handleRefreshStatus`：paid（跳转 / 意外扫码两分支） | 成功 | `flow.settlePaid(undefined, { closeModal: false \| true })` |
| `handlePayModalClose`（`setPayModalVisible(false)`） | 关弹窗 | `flow.closeModal()`（**保留**它原有的"停两路轮询"职责） |
| `handleCancelOrder` | 取消 | `flow.cancelOrder()` |
| `useQrcodePolling({ setCurrentPayment, setPaySuccess })` | 扫码成功 / 补丁 | 接口改为 `{ onPaid, onOrderPatch }`，传 `flow.settlePaid` / `flow.settlePending` |

⚠️ **M2 必须整体完成，不能只改一半**：只要机器与旧 `useState` 同时存在，同一事实就有两个真相
（正是本次要消灭的缺陷）。若中途必须停下，用 `git checkout -- src/pages/developer/Recharge.tsx`
回到接线前状态，不要留下半接线的文件。

---

## 4. 完成定义（DoD）

1. 页面内**不再有任何** `setCurrentPayment` / `setPaySuccess` / `setQrcodePolling` 之类生命周期 setState；
2. `paymentStateRef`、`qrcodePollingRef` 等"第二份真相"全部删除；
3. 「支付成功」只有一处实现（reducer 的 `STATUS_PAID` 分支）；
4. 探测只有一处实现（`usePaymentProbe`），停止语义由 `isProbing` 派生而非手工 `stop()`；
5. 全量 **292+ passed**、typecheck 0、警告预算内、变异检验 **7/7 有效（0 跳过）**；
6. `paymentMachine` 有独立单测，用例库登记；`Recharge.tsx` 行数下降且**页面无业务分支**。

---

## 5. 进度

| 步 | 状态 | 提交 |
|---|---|---|
| M1 状态机 + 单测 | ✅ 已完成（231 行 machine + 18 条纯函数用例，全量 310 passed） | 见 `docs/test-log-2026-09-17.md`「轮次 M1」 |
| M2 flow 接管状态 | ✅ **已完成**（M2-1 编排层 + M2-2 全量接线：35 处写入改 action，`Recharge.tsx` 1571 → 1525 行，act 警告 102 → 88） | 见 test-log「轮次 M2-1 / M2-2」 |
| M3 探测统一 + 删 ref | ⏳ 待做 | — |
| M4 收编剩余 hook | ⏳ 待做 | — |
| M5 安全加固（客户端信号不得直接结算） | ⏳ 待做（缺口见 §2.5） | — |

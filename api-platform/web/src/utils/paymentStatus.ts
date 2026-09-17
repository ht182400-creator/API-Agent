/**
 * 支付状态判定（M3-a：探测策略统一 —— 纯函数层）。
 *
 * ## 为什么要有这个文件
 *
 * 「到底算不算支付成功」是同一条业务规则，但改造前它在代码里被**抄了 10 处**：
 *
 * ```
 * status.status === 'paid' || status.status === 'completed'
 * ```
 *
 * 出现在：同步回调的轮询、首次查询、M5 的后端求证、挂载恢复、`handleOpenPay`、
 * `handleRefreshStatus`、`useQrcodePolling`、`PaymentSuccess` 页（两处）……
 * 而「终态」（用于决定"还要不要继续探测"）又是另一种写法：
 * `['paid', 'completed', 'failed', 'expired'].includes(...)`（只出现在一处，但没人知道还有没有别的）。
 *
 * 同一规则多处实现的问题不是"啰嗦"，而是**会漂移**：新增一个成功状态（比如后端将来加
 * `'settled'`）时必须记得改 10 个地方，漏一处就出现"这里算成功、那里不算"的诡异 bug ——
 * 这正是本项目支付流程重构要消灭的主题（与"七处各自结算"同源）。
 *
 * 现在统一到这里：**判定规则只写一次**，各处只调用 `isPaidStatus` / `isTerminalStatus`。
 *
 * ⚠️ 注意与 `paymentMachine` 里的 `isPaid(state)` 区分：
 *    - `isPaid(state)` 判断的是**状态机的 phase**（UI 状态）；
 *    - `isPaidStatus(status)` 判断的是**后端返回的订单状态字符串**（业务事实）。
 *    两者不是一回事，别混用。
 */

/**
 * 视为"已支付成功"的后端状态。
 *
 * ⚠️ `completed` 也要算成功：后端在不同支付通道下会返回这两种之一
 * （支付宝同步/异步回调给 `paid`，部分通道给 `completed`），
 * 改造前正是因此到处写成 `=== 'paid' || === 'completed'`。
 */
export const PAID_STATUSES = ['paid', 'completed'] as const

/**
 * 终态：**不必再探测**的状态（用于"还要不要继续轮询"的判定）。
 *
 * ⚠️ `cancelled` 刻意**不算**终态：它可能是"超时"造成的，而用户实际上可能已经付款成功
 * （原实现 `usePaymentPolling` 里的注释与这层考虑一致，此处照搬，勿"顺手修正"）。
 */
export const TERMINAL_STATUSES = ['paid', 'completed', 'failed', 'expired'] as const

/** 后端状态是否代表"支付成功" */
export function isPaidStatus(status?: string | null): boolean {
  return !!status && (PAID_STATUSES as readonly string[]).includes(status)
}

/** 后端状态是否已到终态（不会再变化 → 可以停止探测） */
export function isTerminalStatus(status?: string | null): boolean {
  return !!status && (TERMINAL_STATUSES as readonly string[]).includes(status)
}

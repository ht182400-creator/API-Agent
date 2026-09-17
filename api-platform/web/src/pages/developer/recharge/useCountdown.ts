/**
 * 剩余有效期倒计时（M4-lite）。
 *
 * ## 为什么不用改造前的写法
 *
 * 改造前是页面里的一句：
 * ```tsx
 * const [countdown, setCountdown] = useState(0)
 * useEffect(() => {
 *   if (countdown > 0 && currentPayment?.status === 'pending') {
 *     const timer = setTimeout(() => setCountdown(c => c - 1), 1000)
 *     return () => clearTimeout(timer)
 *   }
 * }, [countdown, currentPayment])
 * ```
 * 两个真实问题：
 *
 * ① **会漂移（永不自我纠正）**：它把"过了几秒"记在 state 里、每次只做 `c - 1`。
 *    只要有一次 tick 迟到或被吞（主线程忙、标签页进后台被浏览器节流到 1 次/分钟），
 *    显示值就永久偏大 —— 用户看到"还有 300 秒"，实际订单可能早已过期。
 *    现在改为**由 `expiresAt` 派生**：每次 tick 用 `Date.now()` 重算，天然自我纠正。
 *
 * ② **没有开关**：旧条件的另一半是"订单还 pending"，**与弹窗开关无关** ——
 *    用户关掉弹窗后（此时秒数根本不显示）定时器仍在每秒写一次 state。
 *    生产上是白耗的定时器 + 无意义重渲染；测试里每个用例都会因此多出
 *    `not wrapped in act` 警告（详见 `docs/payment-flow-architecture.md` §7）。
 *    现在只在 `active`（弹窗打开且订单未终结）时挂表，关弹窗/终态**立即清理**。
 *
 * ## 边界约定
 *
 * - `orderKey`：订单唯一标识。**换单才重置**兜底截止时间 —— 同一单的字段补丁
 *   （`ORDER_PATCH`：刷新二维码等）不应把时间重置回 600 秒。
 * - `expiresAt === null`：后端没给 `expires_in`（机器的既定语义，见 `paymentMachine.spec`
 *   `TC-FE-PAYMACH-004`）→ 按 {@link FALLBACK_SECONDS} 兜底，保持与改造前
 *   `constants.calculateRemainingSeconds` 的默认值一致。
 * - 关弹窗后重新打开：因为是从 `expiresAt` 派生的，显示的是**真实剩余**秒数（不会像"暂停计时"那样虚高）。
 */
import { useEffect, useState } from 'react'

/** 后端未返回 `expires_in` 时的兜底有效期（秒）—— 与改造前 `calculateRemainingSeconds` 的默认值一致 */
export const FALLBACK_SECONDS = 600

/** 走秒间隔（ms） */
export const TICK_MS = 1000

export interface UseCountdownParams {
  /** 订单唯一标识（`payment_no`）；为 null 表示当前无订单 */
  orderKey: string | null
  /** 状态机给出的过期时间戳（ms）；`null` = 后端未给 `expires_in` */
  expiresAt: number | null
  /** 是否需要走秒（弹窗打开且订单未终结）—— 关弹窗 / 进终态即停表 */
  active: boolean
}

export function useCountdown({ orderKey, expiresAt, active }: UseCountdownParams): number {
  const [deadline, setDeadline] = useState<number | null>(null)
  const [now, setNow] = useState(() => Date.now())

  // ① 换单时确定截止时间（优先后端 expiresAt，缺失按 FALLBACK_SECONDS 兜底）。
  //    依赖里用 orderKey 而不是整个 payment 对象：字段补丁会产生新对象，但订单没变。
  useEffect(() => {
    if (!orderKey) {
      setDeadline(null)
      return
    }
    setDeadline(expiresAt ?? Date.now() + FALLBACK_SECONDS * TICK_MS)
  }, [orderKey, expiresAt])

  // ② 只在 active 时走秒 —— 这是"关弹窗即停表"的落点；重新激活会立刻对齐真实时间。
  useEffect(() => {
    if (!active) return
    setNow(Date.now())
    const timer = setInterval(() => setNow(Date.now()), TICK_MS)
    return () => clearInterval(timer)
  }, [active])

  if (deadline === null) return 0
  return Math.max(0, Math.ceil((deadline - now) / TICK_MS))
}

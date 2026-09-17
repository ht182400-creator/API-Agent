/**
 * 支付探测统一调度器（M3-b）—— 两套轮询（扫码 8 段递进 / 跳转 3 秒）的**调度**合并于此，
 * 但**探测动作本身保留各自的业务分支**（扫码：直接查单+结算收尾；跳转：走 handleRefreshStatus，
 * 含成功大界面/二维码意外路径等分支）—— 那些差异是本质的，强行合并才是假统一。
 *
 * ## 设计要点
 *
 * - **一次 start 捕获一次上下文**（`mode` + `paymentNo`）：下单成功的当次渲染里
 *   `currentPayment` 还是旧值，所以模式/单号必须由调用方在 start 时显式给出，
 *   而不能依赖"下一次渲染的状态"。
 * - `probeOnce(ctx)` 返回 **false = 探测应停止**（已成功 / 条件不再满足）。
 * - `stop()` 是外部叫停的唯一入口（取消订单 / 关闭弹窗 / 成功收尾）。
 * - **卸载即停**（本 hook 内部的 cleanup）—— 页面不再需要为轮询定时器写清理代码。
 *   ⚠️ 变异规则 FIX-3 盯的就是这个 cleanup；FIX-2 盯的是 stop() —— 改这里必须同步改规则。
 *
 * ## 时序契约（TC-FE-RECHARGE-013/014 用真实定时器锁着，改时序会直接红）
 *
 * - 扫码：attempt 0 立即探测，之后间隔取 `QR_PROBE_INTERVALS[attempt-1]`；
 *   跑满 `QR_PROBE_INTERVALS.length`（8）次 → `onExhausted`（提示手动刷新）。
 * - 跳转：每次探测前等 `REDIRECT_PROBE_INTERVAL`（3 秒，含第一次），不限次数（由条件收口）。
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import type { PaymentMode } from './paymentMachine'

export interface ProbeContext {
  mode: PaymentMode
  /** 支付单号（扫码探测用；跳转模式由探测动作自行从页面状态取） */
  paymentNo?: string
}

export interface UsePaymentProbeOptions {
  /** 一次探测；返回 false = 停止（已成功 / 条件不再满足） */
  probeOnce: (ctx: ProbeContext) => Promise<boolean>
  /** 第 attempt 轮（0 起）探测**前**的等待毫秒数 */
  intervalOf: (attempt: number, ctx: ProbeContext) => number
  /** 最大探测次数；0 = 不限 */
  maxAttempts: (ctx: ProbeContext) => number
  /** 跑满 maxAttempts（扫码超时）时回调 */
  onExhausted?: (ctx: ProbeContext) => void
}

export function usePaymentProbe(options: UsePaymentProbeOptions) {
  const [running, setRunning] = useState(false)
  const runningRef = useRef(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const ctxRef = useRef<ProbeContext>({ mode: 'redirect' })
  // 选项每次渲染都是新闭包 → 用 ref 取最新，避免"老闭包读旧状态"
  const optionsRef = useRef(options)
  optionsRef.current = options

  const stop = useCallback(() => {
    runningRef.current = false
    setRunning(false)
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const start = useCallback(
    (ctx: ProbeContext) => {
      if (runningRef.current) {
        return
      }
      runningRef.current = true
      setRunning(true)
      ctxRef.current = ctx

      const tick = async (attempt: number): Promise<void> => {
        if (!runningRef.current) return
        const opts = optionsRef.current
        let keep = false
        try {
          keep = await opts.probeOnce(ctxRef.current)
        } catch (error) {
          // 单次探测失败不终止轮询（与改造前一致：下一轮再试）
          console.error('[usePaymentProbe] 探测失败，继续下一轮:', error)
          keep = true
        }
        if (!runningRef.current) return
        if (!keep) {
          stop()
          return
        }
        const max = opts.maxAttempts(ctxRef.current)
        if (max > 0 && attempt + 1 >= max) {
          stop()
          opts.onExhausted?.(ctxRef.current)
          return
        }
        timerRef.current = setTimeout(() => {
          void tick(attempt + 1)
        }, opts.intervalOf(attempt + 1, ctxRef.current))
      }

      timerRef.current = setTimeout(() => {
        void tick(0)
      }, optionsRef.current.intervalOf(0, ctx))
    },
    [stop]
  )

  // 卸载即停：页面不再为轮询定时器写清理代码（⚠️ FIX-3 的新址）
  useEffect(
    () => () => {
      runningRef.current = false
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
    },
    []
  )

  return { running, start, stop }
}

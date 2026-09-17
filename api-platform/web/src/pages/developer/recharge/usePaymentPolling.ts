/**
 * 支付结果轮询（跳转支付的后备查询）—— P1-4 拆分抽出；M3-c② 改为「判定注入」。
 *
 * 内容：`startPaymentPoll`（每 3 秒查一次）+ `stopPaymentPoll` + 定时器 ref。
 *
 * ⚠️ M3-c②：不再接收 `paymentStateRef` 状态快照（页面里的"第二份真相"已删）。
 *    "要不要继续轮询"由页面以 `shouldContinue()` **注入** —— hook 内部用 ref 取最新闭包，
 *    于是"用最新状态做判定"与"定时器只建一次"这两件事不再互相绑架。
 *
 * ⚠️ `paymentPollIntervalRef` 仍**交还给父组件**：父组件「组件卸载时清理所有定时器」的
 *    effect 里有它，而**变异规则 FIX-3 的 find 正是那几行**（规则必须随代码形态同步，否则静默失效）。
 *
 * ⚠️ 调用时机约束同 `useQrcodePolling`：入参在调用时立即求值，而 `refreshStatus`
 *    （父组件的 `handleRefreshStatus`）是组件内的 const → 调用点必须在它**定义之后**。
 */
import { useRef } from 'react'
// 【M3-b₁】间隔统一取状态机常量（勿在本文件另写数字）
import { REDIRECT_PROBE_INTERVAL } from './payment/paymentMachine'

export interface UsePaymentPollingOptions {
  /** 是否继续轮询（页面每次渲染给出最新判定；内部用 ref 保证读到最新） */
  shouldContinue: () => boolean
  /** 真正去查状态的回调；自动轮询传 false 表示不弹错误提示（避免干扰用户） */
  refreshStatus: (showError: boolean) => void | Promise<void>
}

export function usePaymentPolling({ shouldContinue, refreshStatus }: UsePaymentPollingOptions) {
  // 【新增】轮询定时器 ref，用于检测支付结果
  const paymentPollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // setInterval 的回调是"启动那一刻的闭包"：直接用参数会读到旧状态 → 用 ref 取最新
  const shouldContinueRef = useRef(shouldContinue)
  shouldContinueRef.current = shouldContinue
  const refreshStatusRef = useRef(refreshStatus)
  refreshStatusRef.current = refreshStatus

  // 【新增】启动支付结果轮询
  const startPaymentPoll = () => {
    // 如果已经有轮询在运行，不再启动
    if (paymentPollIntervalRef.current) {
      console.log('[Recharge] 支付结果轮询已在运行，跳过启动')
      return
    }

    console.log('[Recharge] 启动支付结果轮询（每 3 秒一次）')
    paymentPollIntervalRef.current = setInterval(() => {
      if (shouldContinueRef.current()) {
        // 【优化】自动轮询时不显示错误提示，避免干扰用户
        refreshStatusRef.current(false)
      } else {
        // 条件不满足，停止轮询
        console.log('[Recharge] 停止支付结果轮询：条件不满足')
        stopPaymentPoll()
      }
    }, REDIRECT_PROBE_INTERVAL)
  }

  // 【新增】停止支付结果轮询
  const stopPaymentPoll = () => {
    if (paymentPollIntervalRef.current) {
      console.log('[Recharge] 停止支付结果轮询')
      clearInterval(paymentPollIntervalRef.current)
      paymentPollIntervalRef.current = null
    }
  }

  return { paymentPollIntervalRef, startPaymentPoll, stopPaymentPoll }
}

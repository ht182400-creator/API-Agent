/**
 * 支付结果轮询（跳转支付的后备查询）—— P1-4 巨型组件拆分（由 `../Recharge.tsx` 抽出，纯搬运）
 *
 * 内容：`startPaymentPoll`（每 3 秒查一次，只在"弹窗打开且未成功"时真查）+ `stopPaymentPoll`
 * + 定时器 ref。原先占约 46 行。
 *
 * ⚠️ 为什么 `paymentPollIntervalRef` 也**交还给父组件**（与 `useQrcodePolling` 同一理由）：
 *    父组件「组件卸载时清理所有轮询定时器」的 effect 里逐句写着
 *    `if (paymentPollIntervalRef.current) { clearInterval(...) ... }`，
 *    而**变异规则 FIX-3 的 find 正是"qrcodePollingRef 那行 + 这一行"组成的三行组合**。
 *    ref 留在 hook 内部就得重写清理 → FIX-3 命中 0 次 → 脚本打印"跳过"但退出码仍为 0。
 *
 * ⚠️ 调用时机约束同 `useQrcodePolling`：入参在调用时立即求值，而 `refreshStatus`
 *    （父组件的 `handleRefreshStatus`）是组件内的 const → hook 调用点必须在它**定义之后**。
 */
import { useRef } from 'react'
// 【M3-a】终态判定统一到纯函数模块（原先这里手写了一份 `['paid','completed','failed','expired']`）
import { isTerminalStatus } from '../../../utils/paymentStatus'
// 【M3-b₁】间隔统一取状态机常量（原先本文件里硬编码 3000）
import { REDIRECT_PROBE_INTERVAL } from './payment/paymentMachine'
import type { PaymentStateSnapshot } from './useQrcodePolling'

export interface UsePaymentPollingOptions {
  /** 每 3 秒读一次的最新状态快照（父组件用 effect 同步） */
  paymentStateRef: { current: PaymentStateSnapshot }
  /** 真正去查状态的回调；自动轮询传 false 表示不弹错误提示（避免干扰用户） */
  refreshStatus: (showError: boolean) => void | Promise<void>
}

export function usePaymentPolling({ paymentStateRef, refreshStatus }: UsePaymentPollingOptions) {
  // 【新增】轮询定时器 ref，用于检测支付结果
  const paymentPollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 【新增】启动支付结果轮询
  const startPaymentPoll = () => {
    // 如果已经有轮询在运行，不再启动
    if (paymentPollIntervalRef.current) {
      console.log('[Recharge] 支付结果轮询已在运行，跳过启动')
      return
    }

    console.log('[Recharge] 启动支付结果轮询（每3秒一次）')
    paymentPollIntervalRef.current = setInterval(() => {
      const state = paymentStateRef.current

      // 【关键修复】只要弹窗打开且未成功，就继续轮询
      // handleRefreshStatus 内部会处理 currentPayment 为空的情况
      // 它会检查 URL 中的 out_trade_no 参数
      if (state.payModalVisible && !state.paySuccess) {
        // 【M3-a】只有终态才跳过轮询（判定统一到 utils/paymentStatus）
        // cancelled 可能是因为超时，但用户可能已经支付，所以继续查询
        if (state.currentPayment && isTerminalStatus(state.currentPayment.status)) {
          console.log('[Recharge] 跳过轮询：订单状态已是终态', state.currentPayment.status)
          return
        }

        console.log('[Recharge] 轮询查询支付状态...（当前状态:', state.currentPayment?.status || '无订单')
        // 【优化】自动轮询时不显示错误提示，避免干扰用户
        refreshStatus(false)
      } else {
        // 条件不满足，停止轮询
        console.log('[Recharge] 停止支付结果轮询：条件不满足', {
          payModalVisible: state.payModalVisible,
          paySuccess: state.paySuccess
        })
        stopPaymentPoll()
      }
    }, REDIRECT_PROBE_INTERVAL) // 每 3 秒查询一次（间隔取自状态机常量，勿在此另写数字）
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

/**
 * 扫码支付轮询 —— P1-4 巨型组件拆分（由 `../Recharge.tsx` 抽出，纯搬运零行为改变）
 *
 * 内容：`startQrcodePolling`（8 次递进间隔轮询）+ `handleQrcodePaymentSuccess`（成功落库前的收尾）
 * + `stopQrcodePolling`（外部可随时叫停）+ 那个"是否继续"的 ref。
 *
 * ⚠️ 为什么 `qrcodePollingRef` 也**交还给父组件**（作为返回值导出）：
 *    父组件的**卸载清理 effect** 里有一句 `qrcodePollingRef.current = false`
 *    （回归用例 TC-FE-RECHARGE-014 锁的就是"卸载后不得继续轮询"）。
 *    把它留在 hook 内部会让那句清理无处落脚、必须整体重写 ——
 *    而**变异规则 FIX-3 正是盯那一行**（规则 find 命中不了就会被静默跳过）。
 *    故保持父组件清理原文不动，hook 只提供 ref。
 *
 * ⚠️ 调用时机有约束：本 hook 的入参（尤其 `closePayWindow`）在**调用时立即求值**，
 *    而 `closePayWindow` 是父组件内的 `const` → 调用点必须在它**定义之后**，否则 TDZ 报错。
 */
import { useRef, useState } from 'react'
import { message } from 'antd'
import { paymentApi, Payment } from '../../../api/payment'
// 【M3-a】"是否已支付"的判定统一到纯函数模块
import { isPaidStatus } from '../../../utils/paymentStatus'
import { clearPaymentFromSession } from './paymentSession'

/** 与父组件 `paymentStateRef` 同构：用于 5 秒后确认"仍是成功态"（避免闭包读到旧值） */
export interface PaymentStateSnapshot {
  currentPayment: Payment | null
  payModalVisible: boolean
  paySuccess: boolean
}

export interface UseQrcodePollingOptions {
  /** 当前订单：成功回写时兜底 payment_no / amount */
  currentPayment: Payment | null
  /**
   * 结算回调（**唯一结算入口**，来自 `usePaymentFlow.settlePaid`）。
   *
   * ⚠️ M2-2 之前这里直接收 `setCurrentPayment` / `setPaySuccess` 两个 setState ——
   *    那正是"同一业务事实多处实现"的载体；改为语义回调后，弹窗去留由状态机
   *    按支付方式推导（扫码 → 关弹窗），hook 不再关心"成功之后 UI 怎么变"。
   */
  onPaid: (payment?: Partial<Payment>) => void
  /** 成功后刷新余额（来自 useRechargeData） */
  fetchBalance: () => Promise<void> | void
  /** 成功后关闭支付宝支付窗口 */
  closePayWindow: () => void
  paymentStateRef: { current: PaymentStateSnapshot }
}

export function useQrcodePolling({
  currentPayment,
  onPaid,
  fetchBalance,
  closePayWindow,
  paymentStateRef,
}: UseQrcodePollingOptions) {
  // 扫码支付轮询
  const [qrcodePolling, setQrcodePolling] = useState(false)

  // 【P1-4 修复】扫码轮询的"是否继续"标志。
  // ⚠️ 必须用 ref 而非局部变量：`stopQrcodePolling` 是由「取消订单 / 关闭弹窗」从**外部**调用的，
  //    局部变量对它不可见。原实现用局部 `isPolling` + stop 里只 setState，
  //    导致**取消订单后轮询仍会跑满 8 次（约 32 秒）**，期间若后端返回 paid，
  //    还会把已取消的订单标记成支付成功（代码里"用户关闭弹窗时停止轮询"的注释与实现不符）。
  const qrcodePollingRef = useRef(false)

  // 扫码支付轮询
  const startQrcodePolling = async (paymentNo: string) => {
    console.log('[DEBUG] startQrcodePolling 函数被调用, paymentNo:', paymentNo)
    setQrcodePolling(true)
    qrcodePollingRef.current = true
    const intervals = [2000, 2000, 2000, 3000, 3000, 5000, 5000, 10000]

    for (let i = 0; i < intervals.length; i++) {
      if (!qrcodePollingRef.current) break // 用户取消订单 / 关闭弹窗时立即停止（外部可写）

      try {
        const status = await paymentApi.getPaymentStatus(paymentNo)
        console.log(`[QRCode Poll] 第 ${i + 1} 次:`, status)

        if (isPaidStatus(status.status)) {
          qrcodePollingRef.current = false
          setQrcodePolling(false)
          // 支付成功
          handleQrcodePaymentSuccess(status)
          return
        }
      } catch (error) {
        console.error(`[QRCode Poll] 第 ${i + 1} 次失败:`, error)
      }

      if (i < intervals.length - 1) {
        await new Promise(resolve => setTimeout(resolve, intervals[i]))
      }
    }

    // 轮询结束但未支付成功
    qrcodePollingRef.current = false
    setQrcodePolling(false)
    message.warning({ content: '支付状态查询超时，请点击"刷新状态"按钮确认', key: 'qrcodePoll' })
  }

  // 扫码支付成功处理
  const handleQrcodePaymentSuccess = async (status: any) => {
    setQrcodePolling(false)
    closePayWindow() // 关闭支付宝支付窗口（如果有）

    // 【M2-2】结算走状态机唯一入口（扫码 → 状态机会关闭弹窗，由页面给提示）
    onPaid({
      ...status,
      payment_no: status.payment_no || currentPayment?.payment_no,
      amount: status.amount || currentPayment?.amount,
    } as Partial<Payment>)
    
    // 刷新余额
    await fetchBalance()
    
    clearPaymentFromSession()

    // 5秒后自动刷新（使用 ref 确保正确检测状态）
    setTimeout(() => {
      if (paymentStateRef.current.paySuccess) {
        window.location.reload()
      }
    }, 5000)
  }

  // 停止扫码轮询
  const stopQrcodePolling = () => {
    // ⚠️ 先把 ref 置 false（循环随即退出），再同步 UI 状态
    qrcodePollingRef.current = false
    setQrcodePolling(false)
  }

  return { qrcodePolling, qrcodePollingRef, startQrcodePolling, stopQrcodePolling }
}

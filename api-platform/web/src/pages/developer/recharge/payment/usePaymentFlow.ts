/**
 * 支付流程编排（M2）—— 让状态机成为生命周期的**唯一真相**
 *
 * 职责边界：
 *   · 本 hook 只做一件事：**把 `paymentMachine` 接上 React** —— `useReducer` + 语义化 action + 派生值；
 *   · **不做**任何 I/O（不请求后端、不碰 sessionStorage）—— 那些留在页面的 effect 里（M3 再收进
 *     `usePaymentProbe`）。这样拆的好处是：状态迁移可纯函数单测，副作用集中可审查。
 *
 * 使用方式（M2 接线后页面里的样子）：
 * ```tsx
 * const flow = usePaymentFlow()
 * const { payment: currentPayment, isModalOpen: payModalVisible, isPaid: paySuccess } = flow
 * // 结算只有一个入口：
 * flow.settlePaid({ amount: status.amount }, { closeModal: false })
 * ```
 *
 * ⚠️ 强调：**页面里不应再出现 `setCurrentPayment` / `setPaySuccess` / `setPayModalVisible` 这类 setState** ——
 *    它们正是"同一事实七处实现"的载体。所有写入都必须走 action，才能保证非法状态组合不可能出现。
 */
import { useMemo, useReducer } from 'react'
import type { Payment } from '../../../../api/payment'
import {
  canDismiss,
  initialPaymentState,
  isConfirming,
  isPaid,
  isProbing,
  isProbeExhausted,
  isScanning,
  nextProbeDelay,
  paymentReducer,
  type PaymentState,
} from './paymentMachine'

/** 语义化 action —— 名字即"业务意图"，调用方不需要知道机器内部怎么转 */
export interface PaymentFlowActions {
  /** 开始创建订单（清掉上一单残留） */
  startCreate: () => void
  /** 下单成功：进"等待支付"，自动推导 mode / 开弹窗 / 算过期时间 */
  created: (payment: Payment) => void
  /** 下单失败 */
  createFailed: (error: string) => void
  /** 恢复一张已有订单（sessionStorage 恢复 / 只有 order_no 的占位单） */
  restored: (payment: Payment) => void
  /** ⚠️ 唯一结算入口。`closeModal` 缺省按支付方式推导（扫码关、跳转留） */
  settlePaid: (payment?: Partial<Payment>, options?: { closeModal?: boolean }) => void
  /** 探测完成但仍未支付（可带订单补丁，如刷新后才拿到的 payment_no） */
  settlePending: (payment?: Partial<Payment>) => void
  /** 只更新订单字段（如二维码刷新）—— 不推进探测计数、不改阶段 */
  patchOrder: (payment: Partial<Payment>) => void
  /** 进入"确认中"（收到同步回调 / postMessage 这类强信号时） */
  startConfirming: () => void
  /** 用户取消订单 */
  cancelOrder: () => void
  closeModal: () => void
  openModal: () => void
  /** 订单超时 */
  expire: () => void
  /** 回到初始态 */
  reset: () => void
}

/**
 * 对外 API：**扁平**（action 与派生值同层）——
 * 调用方写 `flow.settlePaid(...)` / `flow.isPaid` / `flow.state`。
 * 参照主流 hook 的用法（如 `useQuery()` 直接暴露 `refetch` / `isLoading`），
 * 少一层 `flow.actions.xxx` 的心智负担。
 */
export interface PaymentFlow extends PaymentFlowActions {
  state: PaymentState
  /** 当前订单 */
  payment: Payment | null
  /** 已支付成功（替代页面里散落的 `paySuccess`） */
  isPaid: boolean
  /** 确认中（替代 `isProcessingCallback`；此时不允许关闭弹窗） */
  isConfirming: boolean
  /** 弹窗是否打开 */
  isModalOpen: boolean
  /** 是否处于"该向后端探测"的阶段 —— 探测定时器的**唯一**开关 */
  isProbing: boolean
  /** 扫码等待中（替代 `qrcodePolling`） */
  isScanning: boolean
  /** 扫码探测已跑满（跑满即提示用户手动刷新） */
  isProbeExhausted: boolean
  /** 弹窗是否允许用户关闭 */
  canDismiss: boolean
  /** 下一次探测间隔（ms） */
  nextProbeDelay: number
}

export function usePaymentFlow(): PaymentFlow {
  const [state, dispatch] = useReducer(paymentReducer, initialPaymentState)

  // actions 只依赖 dispatch（引用稳定），用 useMemo 固定身份，便于作为 effect 依赖传入
  const actions = useMemo<PaymentFlowActions>(
    () => ({
      startCreate: () => dispatch({ type: 'CREATE_START' }),
      created: (payment) => dispatch({ type: 'CREATE_SUCCESS', payment }),
      createFailed: (error) => dispatch({ type: 'CREATE_FAILURE', error }),
      restored: (payment) => dispatch({ type: 'RESTORE_FOUND', payment }),
      settlePaid: (payment, options) =>
        dispatch({ type: 'STATUS_PAID', payment, closeModal: options?.closeModal }),
      settlePending: (payment) => dispatch({ type: 'STATUS_PENDING', payment }),
      patchOrder: (payment) => dispatch({ type: 'ORDER_PATCH', payment }),
      startConfirming: () => dispatch({ type: 'CONFIRM_START' }),
      cancelOrder: () => dispatch({ type: 'CANCEL' }),
      closeModal: () => dispatch({ type: 'CLOSE' }),
      openModal: () => dispatch({ type: 'OPEN' }),
      expire: () => dispatch({ type: 'EXPIRE' }),
      reset: () => dispatch({ type: 'RESET' }),
    }),
    []
  )

  return useMemo<PaymentFlow>(
    () => ({
      state,
      // action 平铺（与派生值同层）—— 调用方无需知道 hook 内部把它们放在 actions 下
      ...actions,
      payment: state.payment,
      isPaid: isPaid(state),
      isConfirming: isConfirming(state),
      isModalOpen: state.modalOpen,
      isProbing: isProbing(state),
      isScanning: isScanning(state),
      isProbeExhausted: isProbeExhausted(state),
      canDismiss: canDismiss(state),
      nextProbeDelay: nextProbeDelay(state),
    }),
    [state, actions]
  )
}

/**
 * 支付流程状态机 —— **纯函数、零 React 依赖**（可直接单测）
 *
 * 立项目的见 `docs/payment-flow-refactor.md` §2。要解决的问题：
 *   现状把「用户支付成功」这一个业务事实，在 7 个来源里各实现了一遍
 *   （同步回调 / storage / focus / visibility / postMessage ×3 / 轮询），
 *   每处都要自己 `setCurrentPayment + clearSession + fetchBalance + 关弹窗或显示大界面`；
 *   生命周期事实又被切碎在 9 个 state/ref 里，只好再造一个 `paymentStateRef` 手工同步"最新状态"。
 *
 * 本文件把生命周期收敛为**显式状态 + 显式事件 + 派生选择器**：
 *   · 派生值（isPaid / isConfirming / isScanning / 探测开关…）**不落库** → 从根上消灭
 *     "两份状态能同时为真"的非法组合；
 *   · 结算只有**一个入口**（`STATUS_PAID`）；
 *   · **终态不可逆**（succeeded/cancelled/expired 收到任何 STATUS_* 都原样返回）→
 *     杜绝「取消后又被轮询标记成功」这一类缺陷（TC-FE-RECHARGE-013 锁的就是它）。
 *
 * ⚠️ 本文件是 M1 步骤的产物：**尚未接线**（页面行为不变）。接线见 M2/M3。
 */
import type { Payment } from '../../../../api/payment'

/** 生命周期阶段（唯一真相） */
export type PaymentPhase =
  | 'idle' // 无进行中的订单
  | 'creating' // 正在创建订单
  | 'awaiting' // 订单已创建，等用户支付
  | 'confirming' // 已收到成功信号，正在向后端确认（原 isProcessingCallback）
  | 'succeeded' // 支付成功
  | 'failed' // 创建/支付失败
  | 'cancelled' // 用户取消
  | 'expired' // 订单超时

/** 支付方式：扫码 / 跳转（决定探测间隔与成功后的展示形式） */
export type PaymentMode = 'qrcode' | 'redirect'

export interface PaymentState {
  phase: PaymentPhase
  /** 当前订单（payment_no / amount / qr_code / pay_url …） */
  payment: Payment | null
  mode: PaymentMode
  /** 弹窗是否打开。⚠️ 与 phase **独立**：关弹窗只是收起 UI，不等于放弃订单 */
  modalOpen: boolean
  /** 已完成的探测请求次数（决定下一次间隔；扫码跑满即"查询超时"） */
  probeCount: number
  /** 订单过期时间戳（ms）；null 表示后端未给 expires_in */
  expiresAt: number | null
  /** 失败原因（展示用） */
  error: string | null
}

export type PaymentEvent =
  | { type: 'CREATE_START' }
  | { type: 'CREATE_SUCCESS'; payment: Payment; now?: number }
  | { type: 'CREATE_FAILURE'; error: string }
  /** 挂载时从 sessionStorage 恢复未完成订单（"不丢单"） */
  | { type: 'RESTORE_FOUND'; payment: Payment; now?: number }
  /** ⚠️ 唯一的结算入口。`closeModal` 缺省时按 mode 推导（扫码→关弹窗并提示；跳转→保留弹窗显示大界面） */
  | { type: 'STATUS_PAID'; payment?: Partial<Payment>; closeModal?: boolean }
  /** 探测完成但后端仍是未支付 → 推进 probeCount；可带订单补丁（如刷新后 payment_no 才拿到） */
  | { type: 'STATUS_PENDING'; payment?: Partial<Payment> }
  /** 仅更新订单字段（如二维码刷新），**不推进探测计数、不改阶段** */
  | { type: 'ORDER_PATCH'; payment: Partial<Payment> }
  | { type: 'STATUS_FAILED'; error?: string }
  | { type: 'CONFIRM_START' }
  | { type: 'CANCEL' }
  | { type: 'CLOSE' }
  | { type: 'OPEN' }
  | { type: 'EXPIRE' }
  | { type: 'RESET' }

export const initialPaymentState: PaymentState = {
  phase: 'idle',
  payment: null,
  mode: 'redirect',
  modalOpen: false,
  probeCount: 0,
  expiresAt: null,
  error: null,
}

/**
 * 扫码轮询的 8 段递进间隔（毫秒）。
 * ⚠️ 必须与原实现逐值一致（原为 `startQrcodePolling` 内的局部数组 `[2000,2000,2000,3000,3000,5000,5000,10000]`）——
 *    `TC-FE-RECHARGE-013/014` 用**真实定时器**（分别等 2.6s / 4.2s），改数值会直接改变用例语义。
 */
export const QR_PROBE_INTERVALS = [2000, 2000, 2000, 3000, 3000, 5000, 5000, 10000]

/** 跳转支付的后备探测间隔（毫秒）—— 原 `startPaymentPoll` 为 3 秒 */
export const REDIRECT_PROBE_INTERVAL = 3000

/** 由订单推导支付方式：有二维码即扫码，否则跳转 */
export function modeOf(payment: Payment | null | undefined): PaymentMode {
  const qr = payment?.qr_code
  return typeof qr === 'string' && qr.length > 0 ? 'qrcode' : 'redirect'
}

/** 终态：不可逆 */
export function isTerminal(phase: PaymentPhase): boolean {
  return phase === 'succeeded' || phase === 'cancelled' || phase === 'expired'
}

/** 探测开关 —— 探测定时器的**唯一**开关（不再依赖谁记得调 stop()） */
export function isProbing(state: PaymentState): boolean {
  return state.phase === 'awaiting' || state.phase === 'confirming'
}

/** 是否已支付成功（替代散落的 `paySuccess`） */
export function isPaid(state: PaymentState): boolean {
  return state.phase === 'succeeded'
}

/** 是否处于"确认中"（替代 `isProcessingCallback`） */
export function isConfirming(state: PaymentState): boolean {
  return state.phase === 'confirming'
}

/** 弹窗是否允许用户关闭（确认中/已成功时不允许 —— 与既有实现一致） */
export function canDismiss(state: PaymentState): boolean {
  return !isConfirming(state) && !isPaid(state)
}

/** 扫码轮询指示（替代 `qrcodePolling`：仅扫码 + 等待中 + 未跑满时为真） */
export function isScanning(state: PaymentState): boolean {
  return (
    state.phase === 'awaiting' &&
    state.mode === 'qrcode' &&
    state.probeCount < QR_PROBE_INTERVALS.length
  )
}

/** 扫码探测是否已跑满（跑满即"查询超时"，提示用户手动刷新） */
export function isProbeExhausted(state: PaymentState): boolean {
  return state.mode === 'qrcode' && state.probeCount >= QR_PROBE_INTERVALS.length
}

/** 下一次探测延迟（ms）：扫码按段递进，跑满后沿用最后一段 */
export function nextProbeDelay(state: PaymentState): number {
  if (state.mode === 'qrcode') {
    return QR_PROBE_INTERVALS[Math.min(state.probeCount, QR_PROBE_INTERVALS.length - 1)]
  }
  return REDIRECT_PROBE_INTERVAL
}

/** 由订单的 `expires_in`（秒）推算过期时间戳 */
function expiresAtOf(payment: Payment | null, now: number): number | null {
  const seconds = (payment as { expires_in?: number } | null)?.expires_in
  return typeof seconds === 'number' && seconds > 0 ? now + seconds * 1000 : null
}

/** 进入"等待支付"态（`CREATE_SUCCESS` 与 `RESTORE_FOUND` 共用的落地逻辑） */
function toAwaiting(state: PaymentState, payment: Payment, now: number): PaymentState {
  return {
    ...state,
    phase: 'awaiting',
    payment,
    mode: modeOf(payment),
    modalOpen: true,
    probeCount: 0,
    expiresAt: expiresAtOf(payment, now),
    error: null,
  }
}

export function paymentReducer(state: PaymentState, event: PaymentEvent): PaymentState {
  switch (event.type) {
    case 'CREATE_START':
      // 重新下单：清掉上一单的残留（等价于原 `setPayError(null)` + `setPaySuccess(false)`）
      return {
        ...state,
        phase: 'creating',
        payment: null,
        modalOpen: false,
        probeCount: 0,
        expiresAt: null,
        error: null,
      }

    case 'CREATE_SUCCESS':
      return toAwaiting(state, event.payment, event.now ?? Date.now())

    case 'RESTORE_FOUND':
      // 刷新/跳回后恢复未完成订单 → 同样进等待态并开弹窗（"不丢单"链路）
      return toAwaiting(state, event.payment, event.now ?? Date.now())

    case 'CREATE_FAILURE':
      return { ...state, phase: 'failed', error: event.error, modalOpen: false, probeCount: 0 }

    case 'CONFIRM_START':
      // 收到"可能成功"的强信号（同步回调 / postMessage）→ 进入确认中，
      // 由它挡住重复信号与用户的关闭操作（现状缺的就是这层去重）
      if (isTerminal(state.phase) || !state.payment) return state
      return { ...state, phase: 'confirming' }

    case 'STATUS_PAID': {
      // ⚠️ 唯一结算入口；终态不可逆
      if (isTerminal(state.phase)) return state
      const merged = {
        ...(state.payment ?? {}),
        ...(event.payment ?? {}),
        status: 'paid',
      } as Payment
      // ⚠️ 弹窗去留按**支付方式**推导（原实现把这条规则抄在 7 处，极易张冠李戴）：
      //    扫码 → 关弹窗 + 页面提示；跳转 → 保留弹窗显示成功大界面。
      //    个别路径有例外（如"订单已支付"分支要显式关掉）→ 用 closeModal 覆盖。
      const closeModal = event.closeModal ?? state.mode === 'qrcode'
      return { ...state, phase: 'succeeded', payment: merged, modalOpen: !closeModal, error: null }
    }

    case 'STATUS_PENDING':
      if (state.phase !== 'awaiting' && state.phase !== 'confirming') return state
      return {
        ...state,
        phase: 'awaiting',
        probeCount: state.probeCount + 1,
        // 订单补丁：刷新状态时后端可能才回传 payment_no / status
        payment: event.payment
          ? ({ ...(state.payment ?? {}), ...event.payment } as Payment)
          : state.payment,
      }

    case 'ORDER_PATCH':
      // 只改订单字段：不碰 phase / probeCount（"二维码刷新"这类动作与探测节奏无关）
      if (!state.payment) return state
      return { ...state, payment: { ...state.payment, ...event.payment } as Payment }

    case 'STATUS_FAILED':
      if (isTerminal(state.phase)) return state
      return { ...state, phase: 'failed', error: event.error ?? '支付失败', probeCount: 0 }

    case 'CANCEL':
      // ⚠️ 保留 payment 字段（与原实现一致：取消后 `currentPayment` 仍在，"支付异常"弹窗仍能显示单号）
      if (state.phase === 'succeeded') return state
      return { ...state, phase: 'cancelled', modalOpen: false, probeCount: 0 }

    case 'CLOSE':
      return { ...state, modalOpen: false }

    case 'OPEN':
      return { ...state, modalOpen: true }

    case 'EXPIRE':
      if (isTerminal(state.phase)) return state
      return { ...state, phase: 'expired', probeCount: 0 }

    case 'RESET':
      return initialPaymentState

    default:
      return state
  }
}

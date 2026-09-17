/**
 * 支付流程状态机单测（纯函数，**不需要 jsdom、不渲染组件**）
 *
 * 为什么值得单独锁：这 20 条不变式原来散落在 7 处重复实现里，靠 18 条页面级用例**只能间接覆盖**；
 * 而页面级用例用真实定时器（等 2.6s / 4.2s），回归慢且难以覆盖"非法事件序列"。
 * 状态机抽出来后可穷举"任意状态下收到任意事件"的行为。
 *
 * 用例编号：TC-FE-PAYMACH-001 ~ TC-FE-PAYMACH-018
 */
import { describe, it, expect } from 'vitest'
import {
  QR_PROBE_INTERVALS,
  REDIRECT_PROBE_INTERVAL,
  canDismiss,
  initialPaymentState,
  isConfirming,
  isPaid,
  isProbing,
  isProbeExhausted,
  isScanning,
  isTerminal,
  modeOf,
  nextProbeDelay,
  paymentReducer,
  type PaymentEvent,
  type PaymentState,
} from './paymentMachine'
import type { Payment } from '../../../../api/payment'

const NOW = 1_700_000_000_000

/** 扫码订单（带二维码） */
const qrPayment = {
  payment_no: 'PAY-QR',
  order_no: 'ORD-QR',
  amount: 10,
  status: 'pending',
  qr_code: 'data:image/png;base64,AAAA',
  expires_in: 600,
} as unknown as Payment

/** 跳转支付订单（无二维码，带收银台链接） */
const redirectPayment = {
  payment_no: 'PAY-RD',
  order_no: 'ORD-RD',
  amount: 100,
  status: 'pending',
  pay_url: 'https://pay.example.com/x',
  expires_in: 600,
} as unknown as Payment

/** 依次派发事件（便于表达"事件序列"） */
function run(state: PaymentState, ...events: PaymentEvent[]): PaymentState {
  return events.reduce(paymentReducer, state)
}

/** 进入"等待支付"态的常用前置 */
const awaitingQr = run(initialPaymentState, { type: 'CREATE_SUCCESS', payment: qrPayment, now: NOW })

describe('支付流程状态机', () => {
  it('TC-FE-PAYMACH-001: 初始为 idle 且字段干净；RESET 可回到初始态', () => {
    expect(initialPaymentState).toMatchObject({
      phase: 'idle',
      payment: null,
      modalOpen: false,
      probeCount: 0,
      expiresAt: null,
      error: null,
    })
    const dirty = run(awaitingQr, { type: 'STATUS_PAID' })
    expect(paymentReducer(dirty, { type: 'RESET' })).toEqual(initialPaymentState)
  })

  it('TC-FE-PAYMACH-002: CREATE_START 清掉上一单残留（payment/error/弹窗）', () => {
    const prev = run(awaitingQr, { type: 'STATUS_FAILED', error: '网关超时' })
    const next = paymentReducer(prev, { type: 'CREATE_START' })
    expect(next.phase).toBe('creating')
    expect(next.payment).toBeNull()
    expect(next.modalOpen).toBe(false)
    expect(next.error).toBeNull()
    expect(next.probeCount).toBe(0)
  })

  it('TC-FE-PAYMACH-003: CREATE_SUCCESS（扫码）→ awaiting + mode=qrcode + 开弹窗 + 过期时间由 expires_in 推算', () => {
    expect(awaitingQr).toMatchObject({
      phase: 'awaiting',
      mode: 'qrcode',
      modalOpen: true,
      probeCount: 0,
      error: null,
    })
    // expires_in = 600 秒
    expect(awaitingQr.expiresAt).toBe(NOW + 600_000)
  })

  it('TC-FE-PAYMACH-004: CREATE_SUCCESS（跳转）mode=redirect；后端没给 expires_in 时 expiresAt 为 null', () => {
    const st = run(initialPaymentState, { type: 'CREATE_SUCCESS', payment: redirectPayment, now: NOW })
    expect(st.mode).toBe('redirect')
    expect(st.expiresAt).toBe(NOW + 600_000)

    const noExpiry = { ...redirectPayment, expires_in: undefined } as unknown as Payment
    const st2 = run(initialPaymentState, { type: 'CREATE_SUCCESS', payment: noExpiry, now: NOW })
    expect(st2.expiresAt).toBeNull()
  })

  it('TC-FE-PAYMACH-005: CREATE_FAILURE → failed（带原因、关弹窗）', () => {
    const st = run(initialPaymentState, { type: 'CREATE_START' }, { type: 'CREATE_FAILURE', error: '网关超时' })
    expect(st.phase).toBe('failed')
    expect(st.error).toBe('网关超时')
    expect(st.modalOpen).toBe(false)
  })

  it('TC-FE-PAYMACH-006: RESTORE_FOUND（刷新回来恢复未完成订单）与下单成功同落地 —— 不丢单', () => {
    const st = run(initialPaymentState, { type: 'RESTORE_FOUND', payment: redirectPayment, now: NOW })
    expect(st).toMatchObject({ phase: 'awaiting', mode: 'redirect', modalOpen: true, probeCount: 0 })
    expect(st.payment?.payment_no).toBe('PAY-RD')
  })

  it('TC-FE-PAYMACH-007: STATUS_PAID 是唯一结算入口 —— 合并订单并置 status=paid', () => {
    const st = run(awaitingQr, { type: 'STATUS_PAID', payment: { amount: 12.5 } as Partial<Payment> })
    expect(st.phase).toBe('succeeded')
    expect(st.payment?.payment_no).toBe('PAY-QR') // 原订单字段保留
    expect(st.payment?.amount).toBe(12.5) // 后端回报的字段覆盖
    expect(st.payment?.status).toBe('paid')
  })

  it('TC-FE-PAYMACH-008: ⭐终态不可逆 —— 已取消的订单收到 STATUS_PAID 必须原样返回', () => {
    // 这就是 TC-FE-RECHARGE-013 在页面级锁的那类缺陷（取消后轮询回报 paid → 被标记成功）
    const cancelled = run(awaitingQr, { type: 'CANCEL' })
    expect(cancelled.phase).toBe('cancelled')
    expect(paymentReducer(cancelled, { type: 'STATUS_PAID' })).toBe(cancelled)
    expect(paymentReducer(cancelled, { type: 'STATUS_PENDING' })).toBe(cancelled)
    expect(paymentReducer(cancelled, { type: 'EXPIRE' })).toBe(cancelled)
  })

  it('TC-FE-PAYMACH-009: 已成功的重复结算幂等（同引用返回）', () => {
    const paid = run(awaitingQr, { type: 'STATUS_PAID' })
    expect(paymentReducer(paid, { type: 'STATUS_PAID' })).toBe(paid)
    expect(paymentReducer(paid, { type: 'CONFIRM_START' })).toBe(paid)
    expect(paymentReducer(paid, { type: 'CANCEL' })).toBe(paid) // 成功不可取消
  })

  it('TC-FE-PAYMACH-010: CONFIRM_START 仅在"有订单且未终态"时生效（这就是重复信号的去重层）', () => {
    expect(run(awaitingQr, { type: 'CONFIRM_START' }).phase).toBe('confirming')
    // 无订单 → 忽略（idle 下收到同步回调）
    expect(run(initialPaymentState, { type: 'CONFIRM_START' }).phase).toBe('idle')
    // 终态 → 忽略
    const cancelled = run(awaitingQr, { type: 'CANCEL' })
    expect(paymentReducer(cancelled, { type: 'CONFIRM_START' })).toBe(cancelled)
  })

  it('TC-FE-PAYMACH-011: STATUS_PENDING 推进 probeCount 并回到 awaiting；非探测态被忽略', () => {
    const confirming = run(awaitingQr, { type: 'CONFIRM_START' })
    const back = paymentReducer(confirming, { type: 'STATUS_PENDING' })
    expect(back.phase).toBe('awaiting')
    expect(back.probeCount).toBe(1)

    expect(paymentReducer(initialPaymentState, { type: 'STATUS_PENDING' })).toBe(initialPaymentState)
  })

  it('TC-FE-PAYMACH-012: 确认中收到 STATUS_PAID 仍能落成功（信号与结果不冲突时以结果为准）', () => {
    const st = run(awaitingQr, { type: 'CONFIRM_START' }, { type: 'STATUS_PAID' })
    expect(st.phase).toBe('succeeded')
  })

  it('TC-FE-PAYMACH-013: CANCEL 关弹窗、探测归零，但**保留 payment**（"支付异常"弹窗仍要显示单号）', () => {
    const st = run(awaitingQr, { type: 'CANCEL' })
    expect(st).toMatchObject({ phase: 'cancelled', modalOpen: false, probeCount: 0 })
    expect(st.payment?.payment_no).toBe('PAY-QR')
  })

  it('TC-FE-PAYMACH-014: CLOSE/OPEN 只动弹窗，不动订单与阶段（关弹窗 ≠ 放弃订单）', () => {
    const closed = run(awaitingQr, { type: 'CLOSE' })
    expect(closed.modalOpen).toBe(false)
    expect(closed.phase).toBe('awaiting')
    expect(closed.payment).toBe(awaitingQr.payment)
    expect(paymentReducer(closed, { type: 'OPEN' }).modalOpen).toBe(true)
  })

  it('TC-FE-PAYMACH-015: 派生选择器 —— isProbing / isPaid / isConfirming / canDismiss', () => {
    expect(isProbing(awaitingQr)).toBe(true)
    expect(isProbing(run(awaitingQr, { type: 'CONFIRM_START' }))).toBe(true)
    expect(isProbing(initialPaymentState)).toBe(false)

    const paid = run(awaitingQr, { type: 'STATUS_PAID' })
    expect(isPaid(paid)).toBe(true)
    expect(isProbing(paid)).toBe(false)

    const confirming = run(awaitingQr, { type: 'CONFIRM_START' })
    expect(isConfirming(confirming)).toBe(true)
    // 确认中与已成功都不允许关闭弹窗（与既有实现一致）
    expect(canDismiss(confirming)).toBe(false)
    expect(canDismiss(paid)).toBe(false)
    expect(canDismiss(awaitingQr)).toBe(true)

    expect(isTerminal('succeeded')).toBe(true)
    expect(isTerminal('cancelled')).toBe(true)
    expect(isTerminal('expired')).toBe(true)
    expect(isTerminal('awaiting')).toBe(false)
  })

  it('TC-FE-PAYMACH-016: isScanning 仅在"扫码 + 等待中 + 未跑满"时为真', () => {
    expect(isScanning(awaitingQr)).toBe(true)
    // 跑满 8 次后不再是"扫描中"（原实现此时提示用户手动刷新）
    let exhausted = awaitingQr
    for (let i = 0; i < QR_PROBE_INTERVALS.length; i++) {
      exhausted = paymentReducer(exhausted, { type: 'STATUS_PENDING' })
    }
    expect(isProbeExhausted(exhausted)).toBe(true)
    expect(isScanning(exhausted)).toBe(false)
    // 跳转支付不是"扫描中"
    const redirect = run(initialPaymentState, { type: 'CREATE_SUCCESS', payment: redirectPayment })
    expect(isScanning(redirect)).toBe(false)
  })

  it('TC-FE-PAYMACH-017: nextProbeDelay 扫码按 8 段递进、跑满沿用最后一段；跳转固定 3 秒', () => {
    let st = awaitingQr
    for (let i = 0; i < QR_PROBE_INTERVALS.length; i++) {
      expect(nextProbeDelay(st)).toBe(QR_PROBE_INTERVALS[i])
      st = paymentReducer(st, { type: 'STATUS_PENDING' })
    }
    // 跑满后取最后一段（10000ms），不会越界
    expect(nextProbeDelay(st)).toBe(QR_PROBE_INTERVALS[QR_PROBE_INTERVALS.length - 1])
    expect(nextProbeDelay(st)).toBe(10000)

    const redirect = run(initialPaymentState, { type: 'CREATE_SUCCESS', payment: redirectPayment })
    expect(nextProbeDelay(redirect)).toBe(REDIRECT_PROBE_INTERVAL)
  })

  it('TC-FE-PAYMACH-018: modeOf 只认"非空二维码字符串"为扫码', () => {
    expect(modeOf(qrPayment)).toBe('qrcode')
    expect(modeOf(redirectPayment)).toBe('redirect')
    expect(modeOf(null)).toBe('redirect')
    expect(modeOf({ qr_code: '' } as Payment)).toBe('redirect')
    expect(modeOf({} as Payment)).toBe('redirect')
  })
})

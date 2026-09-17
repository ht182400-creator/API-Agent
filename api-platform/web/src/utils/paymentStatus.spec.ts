import { describe, it, expect } from 'vitest'
import {
  PAID_STATUSES,
  TERMINAL_STATUSES,
  isPaidStatus,
  isTerminalStatus,
} from './paymentStatus'

/**
 * 支付状态判定（M3-a：探测策略统一）。
 *
 * 这几条用例的价值不在"测得多细"，而在**把业务规则钉在墙上**：
 * 以后有人想"顺手"把 `cancelled` 加进终态、或把 `completed` 从成功里去掉，
 * 都必须先改这里并面对这条注释，而不是在 10 个调用点里悄悄改一处。
 */
describe('支付状态判定（paymentStatus）', () => {
  it('TC-FE-PAYSTATUS-001: paid / completed 都算成功（两个通道两种写法）', () => {
    expect(isPaidStatus('paid')).toBe(true)
    // ⚠️ completed 必须也算成功：部分通道返回的是它，漏掉会导致"已付款却永远显示未付"
    expect(isPaidStatus('completed')).toBe(true)
    expect(PAID_STATUSES).toContain('paid')
    expect(PAID_STATUSES).toContain('completed')
  })

  it('TC-FE-PAYSTATUS-002: 未支付/失败/未知状态都不算成功', () => {
    expect(isPaidStatus('pending')).toBe(false)
    expect(isPaidStatus('failed')).toBe(false)
    expect(isPaidStatus('expired')).toBe(false)
    expect(isPaidStatus('cancelled')).toBe(false)
    expect(isPaidStatus('')).toBe(false)
    expect(isPaidStatus(undefined)).toBe(false)
    expect(isPaidStatus(null)).toBe(false)
    // 大小写敏感：后端给的是小写，别用 'PAID' 试探
    expect(isPaidStatus('PAID')).toBe(false)
  })

  it('TC-FE-PAYSTATUS-003: 终态用于"停止探测"，且 cancelled **刻意不算**终态', () => {
    expect(isTerminalStatus('paid')).toBe(true)
    expect(isTerminalStatus('completed')).toBe(true)
    expect(isTerminalStatus('failed')).toBe(true)
    expect(isTerminalStatus('expired')).toBe(true)

    // ⚠️ cancelled 不算终态：可能是"超时"造成的取消，而用户其实已经付款成功 ——
    //    若把它当终态就会**提前停止探测**，把一笔真付款漏掉（原实现刻意如此）
    expect(TERMINAL_STATUSES).not.toContain('cancelled')
    expect(isTerminalStatus('cancelled')).toBe(false)

    expect(isTerminalStatus('pending')).toBe(false)
    expect(isTerminalStatus(undefined)).toBe(false)
  })
})

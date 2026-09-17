import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { FALLBACK_SECONDS, TICK_MS, useCountdown, type UseCountdownParams } from './useCountdown'

/**
 * 剩余有效期倒计时（M4-lite）。
 *
 * ⚠️ 全用**假定时器**：本 hook 的核心就是"每 1 秒 tick 一次"的定时器逻辑，
 *    用真实定时器只能靠 `sleep` 去等，既慢又不稳 —— 而且"真实定时器 + 真实时间等待"
 *    正是 `act` 警告的高发区（见 docs/payment-flow-architecture.md §7）。
 *    假定时器还能用 `vi.getTimerCount()` **直接反证"没有空转的定时器"**。
 */
describe('剩余有效期倒计时（useCountdown）', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-09-17T10:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('TC-FE-RECHARGE-019: 关弹窗（active=false）立即停表 —— 无空转定时器、无多余重渲染', () => {
    const props: UseCountdownParams = {
      orderKey: 'p1',
      expiresAt: Date.now() + 600 * TICK_MS,
      active: true,
    }
    const { result, rerender } = renderHook((p: UseCountdownParams) => useCountdown(p), {
      initialProps: props,
    })

    // 打开弹窗：按 expires_in 显示 600 秒，且确实挂了一个走秒定时器
    expect(result.current).toBe(600)
    expect(vi.getTimerCount()).toBe(1)

    act(() => {
      vi.advanceTimersByTime(TICK_MS)
    })
    expect(result.current).toBe(599)

    // 关闭弹窗 → 立即清表（旧实现与弹窗开关无关：关掉后仍每秒写一次 state）
    rerender({ ...props, active: false })
    expect(vi.getTimerCount()).toBe(0)

    const frozen = result.current
    act(() => {
      vi.advanceTimersByTime(5 * TICK_MS)
    })
    // 停表期间不做任何状态更新 → 数值不变（重新打开会由真实时间重算，见下一条）
    expect(result.current).toBe(frozen)
  })

  it('TC-FE-RECHARGE-020: 后端未给 expires_in 时按 600 秒兜底；开关弹窗不重置截止时间', () => {
    const { result, rerender } = renderHook((p: UseCountdownParams) => useCountdown(p), {
      initialProps: { orderKey: 'p1', expiresAt: null, active: true } as UseCountdownParams,
    })
    expect(result.current).toBe(FALLBACK_SECONDS)
    expect(vi.getTimerCount()).toBe(1)

    act(() => {
      vi.advanceTimersByTime(30 * TICK_MS)
    })
    expect(result.current).toBe(FALLBACK_SECONDS - 30)

    // 关弹窗 5 分钟后再打开：截止时间**不能**重置
    // （否则等于给订单无限续期 —— 用户只要开关一下弹窗就又能看到一个满额的倒计时）
    rerender({ orderKey: 'p1', expiresAt: null, active: false })
    act(() => {
      vi.advanceTimersByTime(300 * TICK_MS)
    })
    rerender({ orderKey: 'p1', expiresAt: null, active: true })
    expect(result.current).toBe(FALLBACK_SECONDS - 330)
  })

  it('TC-FE-RECHARGE-021: 派生而非自减 —— tick 被节流丢失也不漂移', () => {
    const startedAt = Date.now()
    const { result } = renderHook((p: UseCountdownParams) => useCountdown(p), {
      initialProps: {
        orderKey: 'p1',
        expiresAt: startedAt + 600 * TICK_MS,
        active: true,
      } as UseCountdownParams,
    })
    expect(result.current).toBe(600)

    // 模拟标签页进后台被浏览器节流：120 秒里一次 tick 都没发生，之后才来一次
    act(() => {
      vi.setSystemTime(startedAt + 120 * TICK_MS)
      vi.advanceTimersByTime(TICK_MS)
    })

    // 真实经过 121 秒 → 剩余 479 秒。
    // ⚠️ 旧实现（state 自减 `c - 1`）这里会显示 599 —— 永久偏大 120 秒，
    //    用户以为还有 10 分钟，实际订单早已过期。派生实现每次用 Date.now() 重算，天然自我纠正。
    expect(result.current).toBe(479)
  })
})

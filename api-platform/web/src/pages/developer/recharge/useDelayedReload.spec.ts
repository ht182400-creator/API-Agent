import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { DEFAULT_RELOAD_DELAY_MS, useDelayedReload } from './useDelayedReload'

/**
 * 结算后延迟刷新（M3-c₁）。
 *
 * ⚠️ 注入假的 `reload`：jsdom 里 `window.location.reload` 不可 mock，
 *    而这里要断言的恰恰是「到点才刷新 / 卸载后不刷新」，所以把它做成可注入参数。
 *    ⚠️ 写注释时要避免让「星号紧邻斜杠」出现（那种序列会被当成块注释的结束标记，
 *      后续代码立刻变成语法垃圾，TS 报的还是一串离奇错误 —— 本轮实际踩到）。
 * 全用假定时器，并直接用 `vi.getTimerCount()` 反证"卸载后没有悬空定时器"。
 */
describe('结算后延迟刷新（useDelayedReload）', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('TC-FE-RELOAD-001: 到点才刷新一次（默认 5 秒前不得触发）', () => {
    const reload = vi.fn()
    const { result } = renderHook(() => useDelayedReload(reload))

    act(() => result.current())
    act(() => vi.advanceTimersByTime(DEFAULT_RELOAD_DELAY_MS - 1))
    expect(reload).not.toHaveBeenCalled() // 还没到点

    act(() => vi.advanceTimersByTime(1))
    expect(reload).toHaveBeenCalledTimes(1)
    // 只刷一次（定时器不重复）
    act(() => vi.advanceTimersByTime(DEFAULT_RELOAD_DELAY_MS * 2))
    expect(reload).toHaveBeenCalledTimes(1)
  })

  it('TC-FE-RELOAD-002: 卸载后不得再刷新（且不留悬空定时器）', () => {
    const reload = vi.fn()
    const { result, unmount } = renderHook(() => useDelayedReload(reload))

    act(() => result.current())
    expect(vi.getTimerCount()).toBe(1)

    unmount()
    // 反证"没有悬空定时器"：改造前这里是 1（定时器照旧挂着，5 秒后仍会导航）
    expect(vi.getTimerCount()).toBe(0)

    act(() => vi.advanceTimersByTime(DEFAULT_RELOAD_DELAY_MS * 2))
    expect(reload).not.toHaveBeenCalled()
  })

  it('TC-FE-RELOAD-003: 重复调度只保留最后一次（延迟按最后一次算）', () => {
    const reload = vi.fn()
    const { result } = renderHook(() => useDelayedReload(reload))

    act(() => result.current(800))
    act(() => vi.advanceTimersByTime(700)) // 第一次还没到（差 100ms）
    act(() => result.current(800)) // 重新调度：应从此刻起 800ms

    act(() => vi.advanceTimersByTime(100))
    // 若没做"取消上一次"，这里就会因为第一次的定时器而提前刷新
    expect(reload).not.toHaveBeenCalled()

    act(() => vi.advanceTimersByTime(700))
    expect(reload).toHaveBeenCalledTimes(1)
  })
})

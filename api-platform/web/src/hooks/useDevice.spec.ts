/**
 * 设备检测 Hook 单元测试
 *
 * 为什么优先测它：
 *   `useDevice` 决定全站响应式分支（移动端抽屉菜单 / 桌面端侧边栏、表格列数、
 *   登录页紧凑模式等）。它的核心是按 `window.innerWidth` 落进 4 个断点区间，
 *   属**纯边界逻辑** —— 最适合用单测把边界钉死（人工点不出 575 与 576 的差异）。
 *
 * 注意：断点口径必须与 `styles/breakpoints.css` 一致（改一处必须改另一处）。
 *
 * 用例编号：TC-FE-DEVICE-001 ~ TC-FE-DEVICE-005
 */
import { describe, it, expect, afterEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useDevice } from './useDevice'

/** 设置视口尺寸并触发 resize（模拟真实浏览器行为） */
function setViewport(width: number, height = 800): void {
  Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: width })
  Object.defineProperty(window, 'innerHeight', { writable: true, configurable: true, value: height })
  act(() => {
    window.dispatchEvent(new Event('resize'))
  })
}

const originalWidth = window.innerWidth
const originalHeight = window.innerHeight

afterEach(() => {
  Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: originalWidth })
  Object.defineProperty(window, 'innerHeight', { writable: true, configurable: true, value: originalHeight })
})

describe('useDevice 断点判定', () => {
  it('TC-FE-DEVICE-001: 宽度落在正确的断点区间（含 4 个边界）', () => {
    const cases: Array<[number, string, string]> = [
      [375, 'mobile', '典型手机宽度'],
      [575, 'mobile', '手机断点上界（<576）'],
      [576, 'tablet', '平板断点下界（=576）'],
      [767, 'tablet', '平板断点上界（<768）'],
      [768, 'desktop', '桌面断点下界（=768）'],
      [991, 'desktop', '桌面断点上界（<992）'],
      [992, 'largeDesktop', '大桌面断点下界（=992）'],
      [1920, 'largeDesktop', '典型大屏'],
    ]

    cases.forEach(([width, expected, reason]) => {
      setViewport(width)
      const { result } = renderHook(() => useDevice())
      expect(result.current.deviceType, `${width}px 应为 ${expected}（${reason}）`).toBe(expected)
    })
  })

  it('TC-FE-DEVICE-002: 四个布尔标志互斥，且 desktop/largeDesktop 都计入 isDesktop', () => {
    const cases: Array<[number, boolean, boolean, boolean, boolean]> = [
      // width, isMobile, isTablet, isDesktop, isLargeDesktop
      [375, true, false, false, false],
      [700, false, true, false, false],
      [900, false, false, true, false],
      [1400, false, false, true, true],
    ]

    cases.forEach(([width, mobile, tablet, desktop, largeDesktop]) => {
      setViewport(width)
      const { result } = renderHook(() => useDevice())
      expect(
        [
          result.current.isMobile,
          result.current.isTablet,
          result.current.isDesktop,
          result.current.isLargeDesktop,
        ],
        `${width}px 的四个标志`
      ).toEqual([mobile, tablet, desktop, largeDesktop])
    })
  })

  it('TC-FE-DEVICE-003: 横竖屏判定（高 > 宽为竖屏）', () => {
    setViewport(400, 900)
    const portrait = renderHook(() => useDevice())
    expect(portrait.result.current.isPortrait).toBe(true)
    expect(portrait.result.current.isLandscape).toBe(false)

    setViewport(1200, 800)
    const landscape = renderHook(() => useDevice())
    expect(landscape.result.current.isPortrait).toBe(false)
    expect(landscape.result.current.isLandscape).toBe(true)
  })

  it('TC-FE-DEVICE-004: resize 后 deviceType 与 screenSize 同步更新', () => {
    setViewport(1200, 900)
    const { result } = renderHook(() => useDevice())
    expect(result.current.deviceType).toBe('largeDesktop')

    setViewport(500, 700)
    expect(result.current.deviceType).toBe('mobile')
    expect(result.current.screenSize).toEqual({ width: 500, height: 700 })
  })

  it('TC-FE-DEVICE-005: 卸载时移除 resize / orientationchange 监听（防内存泄漏）', () => {
    const removeSpy = vi.spyOn(window, 'removeEventListener')
    const { unmount } = renderHook(() => useDevice())
    unmount()

    const removedEvents = removeSpy.mock.calls.map((call) => call[0])
    expect(removedEvents).toContain('resize')
    expect(removedEvents).toContain('orientationchange')
    removeSpy.mockRestore()
  })
})

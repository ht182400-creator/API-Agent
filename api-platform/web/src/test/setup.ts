/**
 * Vitest 全局测试环境初始化
 *
 * 职责：
 *   1. 注入 @testing-library/jest-dom 断言（toBeInTheDocument / toHaveTextContent 等）；
 *   2. 为 jsdom 补齐 antd / echarts 依赖、但 jsdom 未实现的浏览器 API；
 *   3. 每个用例后清理 DOM，避免相互污染。
 */
import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// ---------- jsdom 缺失的浏览器 API 补齐（antd 响应式组件依赖 matchMedia）----------
if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),      // 旧 API（antd 内部仍会调用）
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  })
}

// ResizeObserver（antd Table/Chart 组件依赖）
if (!(globalThis as any).ResizeObserver) {
  ;(globalThis as any).ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}

// IntersectionObserver（懒加载 / 虚拟列表依赖）
if (!(globalThis as any).IntersectionObserver) {
  ;(globalThis as any).IntersectionObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
      return []
    }
  }
}

afterEach(() => {
  // 卸载测试渲染的 React 树
  cleanup()
})

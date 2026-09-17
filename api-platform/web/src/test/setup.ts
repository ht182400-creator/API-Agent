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
import { cleanup, configure } from '@testing-library/react'

// ---------- 放宽"异步断言窗口"（消除全量并行下的假失败）----------
/**
 * `findBy*` / `waitFor` 默认只等 **1000ms**。单跑某个 spec 够用，但**全量并行跑**时机器被几十个
 * worker 压满，antd 表单校验 / 异步渲染的落地时间会翻几倍 —— 于是出现"单跑绿、全量红"的假失败。
 *
 * 实测（2026-09-17）：`TC-FE-CREATEREPO-001` 在全量下报
 * `Unable to find an element with the text: 请输入仓库名称`（11.9s 才失败），而**单跑该 spec 5 passed**；
 * 同类还有 `TC-FE-OREPO-007`(FileReader) 与 `TC-FE-PRICING-004`，都是"慢用例 + 满载"的组合。
 *
 * ⚠️ 放宽**不会掩盖逻辑缺陷**：文案/条件真错的话，3 秒后照样失败，只是等待更从容。
 *    这是"消除环境抖动"的常规做法，代价仅是失败时多等几秒。
 */
configure({ asyncUtilTimeout: 3000 })

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

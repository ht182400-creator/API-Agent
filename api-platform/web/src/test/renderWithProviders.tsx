/**
 * 组件测试统一渲染助手
 *
 * 为什么需要：
 *   页面组件普遍依赖 `react-router`（useNavigate/useLocation）与全局 `ErrorProvider`
 *   （`useError` 在 Provider 外会直接 throw）。若每个 spec 都手写包裹层，
 *   既啰嗦又容易漏（漏了就在测试里白屏，而错误信息不指向真实原因）。
 *   这里提供唯一入口，保证所有页面测试的挂载条件与真实 App 一致。
 *
 * 用法：
 * ```tsx
 * import { renderWithProviders } from '../../test/renderWithProviders'
 * const { container } = renderWithProviders(<Login />, { route: '/login' })
 * ```
 *
 * ⚠️ 顺序要求：`ErrorProvider` 内部使用 `useNavigate`，因此必须放在 Router **之内**。
 */
import type { ReactElement, ReactNode } from 'react'
import { render, type RenderOptions, type RenderResult } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ErrorProvider } from '../contexts/ErrorContext'

export interface ProviderOptions extends Omit<RenderOptions, 'wrapper'> {
  /** 初始路由（断言"渲染时使用了哪个路径"时有用） */
  route?: string
  /** 需要额外包裹的业务 Provider（如未来引入 QueryClient 等） */
  extraWrappers?: Array<(children: ReactNode) => ReactElement>
}

/**
 * 在「Router + ErrorProvider」环境下渲染组件。
 *
 * 说明：默认**不**渲染 `<Routes>` —— 被测组件通常只依赖 useNavigate/useLocation，
 * 直接渲染更接近单测语义（少一层路由匹配，失败信息也更直白）。
 */
export function renderWithProviders(
  ui: ReactElement,
  { route = '/', extraWrappers = [], ...options }: ProviderOptions = {}
): RenderResult {
  const wrapped = extraWrappers.reduce<ReactNode>(
    (acc, wrap) => wrap(acc as ReactElement),
    ui
  )

  return render(
    <MemoryRouter initialEntries={[route]}>
      <ErrorProvider>{wrapped}</ErrorProvider>
    </MemoryRouter>,
    options
  )
}

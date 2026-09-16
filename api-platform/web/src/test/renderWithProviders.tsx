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
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
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
    // ⚠️ 关闭 antd 动画（`motion: false`）：jsdom 下 CSSMotion 的异步状态更新
    //    既无意义又会产生大量 `not wrapped in act(...)` 警告（实测约 90 条，
    //    占全部 act 警告的四成），还干扰对"真实 act 问题"的判断。
    //
    // ⚠️ `locale={zhCN}` 必须与 `main.tsx` 一致：此前测试跑的是 antd **默认英文**，
    //    导致 Modal 按钮是 OK/Cancel、Table 空态是 No data —— 与真实界面（确定/取消、
    //    暂无数据）不符，用例若断言这些文案就会"测了个线上不存在的界面"。
    <ConfigProvider locale={zhCN} theme={{ token: { motion: false } }}>
      {/* ⚠️ 与 main.tsx 的 BrowserRouter 保持一致的 future flags：
          否则每次渲染都会刷两条 React Router Future Flag 警告（实测 16 条）。 */}
      <MemoryRouter
        initialEntries={[route]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <ErrorProvider>{wrapped}</ErrorProvider>
      </MemoryRouter>
    </ConfigProvider>,
    options
  )
}

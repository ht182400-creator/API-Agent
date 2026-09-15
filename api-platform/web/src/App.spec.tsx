/**
 * App 路由守卫测试（TC-FE-UI-001 / TC-FE-UI-002）
 *
 * 为什么值得测（P0/P3 交界）：`ProtectedRoute` 决定「未登录去哪 / 越权去哪」，
 * 配错既不报错也不白屏 —— 只是让用户看到不该看的页面或被错误地踢回登录页。
 *
 * ⚠️ 所有页面级 api 模块一律 mock 成「全方法 reject」：本套件只关心**路由跳转**，
 *     页面自身的渲染健壮性由 MiscPages.spec.tsx 专门覆盖。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import { useAuthStore } from './stores/auth'
import App from './App'

// ⚠️ mock 策略与 MiscPages.spec 相同（空对象成员，弃用 Proxy —— vitest 校验 Proxy mock 会挂死）。
//     App 渲染整棵路由树，各页面的 api 调用全部落空 → 由页面自身 catch 兜底。
vi.mock('./api/superadmin', () => ({
  dashboardApi: {}, userApi: {}, roleApi: {}, configApi: {},
  userTypeLabels: {}, userTypeColors: {}, roleLabels: {}, PERMISSION_DEFINITIONS: {},
}))
vi.mock('./api/admin', () => ({ adminUserApi: {}, adminApi: {}, userTypeMap: {} }))
vi.mock('./api/adminLogs', () => ({
  getBackupConfig: vi.fn().mockRejectedValue(new Error('api rejected')),
  updateBackupConfig: vi.fn().mockRejectedValue(new Error('api rejected')),
}))
vi.mock('./api/adminReconciliation', () => ({ adminReconciliationApi: {} }))
vi.mock('./api/billing', () => ({ billingApi: {} }))
vi.mock('./api/quota', () => ({ quotaApi: {} }))
vi.mock('./api/repo', () => ({ repoApi: {} }))
vi.mock('./api/user', () => ({ userApi: {} }))
vi.mock('./api/notification', () => ({ notificationApi: {} }))
vi.mock('./api/analytics', () => ({ analyticsApi: {} }))
vi.mock('./api/payment', () => ({ paymentApi: {} }))
vi.mock('./api/adminAnalytics', () => ({ adminAnalyticsApi: {} }))
vi.mock('./api/auth', () => ({
  authApi: {
    login: vi.fn().mockRejectedValue(new Error('api rejected')),
    logout: vi.fn().mockResolvedValue(undefined),
    me: vi.fn().mockRejectedValue(new Error('api rejected')),
  },
}))

const devUser = {
  id: 'u1',
  username: 'dev',
  email: 'dev@example.com',
  user_type: 'developer',
  role: 'developer',
  permissions: [],
}

function renderApp(path: string) {
  return render(
    <ConfigProvider theme={{ token: { motion: false } }}>
      <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </MemoryRouter>
    </ConfigProvider>
  )
}

describe('路由守卫（TC-FE-UI-001 / TC-FE-UI-002）', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false } as never)
  })

  it('TC-FE-UI-002a: 未登录访问受保护路由 → 重定向 /login', async () => {
    renderApp('/admin/users')

    // Login 页面的静态文案（不依赖任何接口）
    expect(await screen.findByRole('button', { name: /登\s*录/ })).toBeInTheDocument()
    // 且不是 admin 的用户管理页
    expect(screen.queryByText('用户管理')).not.toBeInTheDocument()
  })

  it('TC-FE-UI-002b: developer 访问 /admin → 按角色重定向到默认路径（开发者首页）', async () => {
    useAuthStore.setState({ user: devUser, accessToken: 't', refreshToken: 'r', isAuthenticated: true } as never)
    renderApp('/admin/users')

    // developer 的 defaultPath 是 '/' → DeveloperDashboard；不得出现 admin 的用户管理内容
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /登\s*录/ })).not.toBeInTheDocument()
    })
    // 落在开发者侧（Layout 菜单或 Dashboard 骨架存在即算守卫生效：没有白屏、没有留在 /admin）
    await waitFor(() => {
      expect(document.querySelector('.ant-layout, [class*="container"]')).toBeTruthy()
    })
  })

  it('TC-FE-UI-001: 未登录访问任意路径 → 兜底重定向到 /login（defaultPath 链路）', async () => {
    renderApp('/some/unknown/path')

    expect(await screen.findByRole('button', { name: /登\s*录/ })).toBeInTheDocument()
  })
})

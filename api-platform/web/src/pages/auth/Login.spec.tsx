/**
 * 登录页（Login.tsx）测试
 *
 * 为什么优先测它：登录是全站唯一入口，且内含三类"错了就致命"的逻辑
 *   ① 用户类型 → 落地页映射（错了会把用户送到无权访问的页面）；
 *   ② 邮箱 / 用户名**自动判别**（`identifier.includes('@')` → email，否则 username）；
 *   ③ 登录成功后写入 auth store（token/用户信息），失败必须走统一错误处理而不是静默。
 *
 * ⚠️ 关于输入方式（内含一个"已修缺陷"的回归用例）：
 *   组件为对抗浏览器自动填充，原本在挂载后 300/1000/2000ms **无条件**清空输入框，
 *   会把用户正在输入的内容一起清掉 —— 实测 `admin@example.com` 被截成 `com`。
 *   该缺陷**已修复**（改为"用户一旦交互即停止清空"，见 `Login.tsx` 的 userInteractedRef）。
 *   回归用例：**TC-FE-LOGIN-008**（刻意用真实的 `user.type` 逐字符输入，修复前必失败）。
 *   其余用例仍用同步的 `fireEvent.change`，避免每条都付 1 秒以上的逐字符输入开销。
 *
 * 用例编号：TC-FE-LOGIN-001 ~ TC-FE-LOGIN-008
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// 认证接口整体 mock（组件唯一外部数据源）
vi.mock('../../api/auth', () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    refresh: vi.fn(),
  },
}))

// logger 只产生副作用 → 整体替换，避免测试输出噪音
vi.mock('../../utils/logger', () => {
  const noop = () => {}
  return {
    logger: {
      debug: noop,
      info: noop,
      warn: noop,
      error: noop,
      setUserId: noop,
      clearUserId: noop,
      logRequest: noop,
      logResponse: noop,
      logApiError: noop,
    },
    LogLevel: { DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3 },
  }
})

import Login, { getRedirectPath } from './Login'
import { authApi } from '../../api/auth'
import { useAuthStore } from '../../stores/auth'
import { renderWithProviders } from '../../test/renderWithProviders'

const adminUser = {
  id: 'u-1',
  email: 'admin@example.com',
  user_type: 'admin' as const,
  user_status: 'active',
  role: 'admin',
  permissions: ['*'],
  email_verified: true,
  vip_level: 0,
  created_at: '2026-01-01T00:00:00Z',
}

/** 填入登录表单并提交（同步操作，避开组件的自动清空定时器） */
function fillAndSubmit(identifier: string, password = 'secret123'): void {
  fireEvent.change(screen.getByPlaceholderText('用户名或邮箱'), { target: { value: identifier } })
  fireEvent.change(screen.getByPlaceholderText('密码'), { target: { value: password } })
  fireEvent.click(screen.getByRole('button', { name: '登 录' }))
}

beforeEach(() => {
  // 每个用例从"未登录"开始
  useAuthStore.setState({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
  vi.mocked(authApi.login).mockResolvedValue({
    access_token: 'access-token-1',
    refresh_token: 'refresh-token-1',
    expires_in: 3600,
  })
  vi.mocked(authApi.me).mockResolvedValue(adminUser)
})

describe('getRedirectPath（用户类型 → 落地页）', () => {
  it('TC-FE-LOGIN-001: 各用户类型映射到与后端权限一致的落地页', () => {
    const cases: Array<[string, string]> = [
      ['super_admin', '/superadmin'],
      ['admin', '/admin'],
      ['owner', '/owner'],
      ['user', '/user'],
      ['developer', '/'],
      ['unknown-type', '/'], // 兜底分支
    ]
    cases.forEach(([userType, expected]) => {
      expect(getRedirectPath(userType), `${userType} 应落到 ${expected}`).toBe(expected)
    })
  })
})

describe('登录页渲染与提交', () => {
  it('TC-FE-LOGIN-002: 渲染标题、两个输入框、登录按钮与注册链接', () => {
    renderWithProviders(<Login />, { route: '/login' })

    expect(screen.getByText('API Platform')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('用户名或邮箱')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('密码')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '登 录' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '立即注册' })).toBeInTheDocument()
  })

  it('TC-FE-LOGIN-003: 空表单提交被前端校验拦截，不发起请求', async () => {
    renderWithProviders(<Login />, { route: '/login' })

    fireEvent.click(screen.getByRole('button', { name: '登 录' }))

    expect(await screen.findByText('请输入用户名或邮箱')).toBeInTheDocument()
    expect(await screen.findByText('请输入密码')).toBeInTheDocument()
    expect(authApi.login).not.toHaveBeenCalled()
  })

  it('TC-FE-LOGIN-004: 输入含 @ 时按邮箱登录（提交值必须完整，不被自动清空定时器截断）', async () => {
    renderWithProviders(<Login />, { route: '/login' })

    fillAndSubmit('admin@example.com')

    await waitFor(() => expect(authApi.login).toHaveBeenCalledTimes(1))
    expect(authApi.login).toHaveBeenCalledWith({
      email: 'admin@example.com',
      password: 'secret123',
    })
  })

  it('TC-FE-LOGIN-005: 输入不含 @ 时按用户名登录', async () => {
    renderWithProviders(<Login />, { route: '/login' })

    fillAndSubmit('admin')

    await waitFor(() => expect(authApi.login).toHaveBeenCalledTimes(1))
    expect(authApi.login).toHaveBeenCalledWith({ username: 'admin', password: 'secret123' })
  })

  it('TC-FE-LOGIN-006: 登录成功写入 token 与真实用户信息', async () => {
    renderWithProviders(<Login />, { route: '/login' })

    fillAndSubmit('admin@example.com')

    await waitFor(() => {
      const state = useAuthStore.getState()
      expect(state.accessToken).toBe('access-token-1')
      expect(state.refreshToken).toBe('refresh-token-1')
      expect(state.isAuthenticated).toBe(true)
    })
    // 用户信息来自 /auth/me()（先写占位再覆盖为真实数据）
    await waitFor(() => expect(useAuthStore.getState().user?.user_type).toBe('admin'))
    expect(authApi.me).toHaveBeenCalled()
  })

  it('TC-FE-LOGIN-007: 响应缺少 access_token 时视为失败，不写入登录态', async () => {
    vi.mocked(authApi.login).mockResolvedValue({} as never)
    renderWithProviders(<Login />, { route: '/login' })

    fillAndSubmit('admin@example.com')

    await waitFor(() => expect(authApi.login).toHaveBeenCalled())
    await waitFor(() => {
      const state = useAuthStore.getState()
      expect(state.accessToken).toBeNull()
      expect(state.isAuthenticated).toBe(false)
    })
    // 页面不崩（错误经统一 showError 呈现）
    expect(screen.getByText('API Platform')).toBeInTheDocument()
  })

  it('TC-FE-LOGIN-008: 逐字符真实输入长邮箱不被自动清空定时器截断（缺陷回归）', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />, { route: '/login' })

    // ⚠️ 必须用 user.type（逐字符），本用例的价值就在于重现"输入 vs 300/1000/2000ms 定时器"的竞态：
    //    修复前最终只会提交 `username: "com"`（被 300ms 那次清空后剩下的尾部）。
    await user.type(screen.getByPlaceholderText('用户名或邮箱'), 'admin@example.com')
    await user.type(screen.getByPlaceholderText('密码'), 'secret123')
    await user.click(screen.getByRole('button', { name: '登 录' }))

    await waitFor(() => expect(authApi.login).toHaveBeenCalledTimes(1))
    expect(authApi.login).toHaveBeenCalledWith({
      email: 'admin@example.com',
      password: 'secret123',
    })
  })
})

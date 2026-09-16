/**
 * 账单中心测试（TC-FE-BILL）
 *
 * 回归背景：环境标签原先读 `account.mock_mode`（支付模拟模式），而全局顶栏读
 * `/health` 的 billing_environment —— 两个数据源导致自相矛盾（顶栏「测试环境 · SIMULATION」
 * 而账单中心「生产环境 / 真实账户」，用户实测截图）。修复后标签与顶栏同源（useEnvInfo）。
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { billingApi } from '../../api/billing'
import { useAuthStore } from '../../stores/auth'
import { renderWithProviders } from '../../test/renderWithProviders'
import Billing from './Billing'

vi.mock('../../api/billing', () => ({
  billingApi: {
    getAccount: vi.fn(),
    getMonthlySummary: vi.fn(),
    getBalanceHistory: vi.fn(),
    getBills: vi.fn(),
  },
}))

const account = { balance: 20, mock_mode: false }

/** stub /health（useEnvInfo 用原生 fetch，不走 axios） */
function stubHealth(billingEnv: string, isProduction: boolean) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        environment: 'development',
        billing_environment: billingEnv,
        is_production: isProduction,
      }),
    })
  )
}

describe('账单中心（TC-FE-BILL）', () => {
  beforeEach(() => {
    vi.mocked(billingApi.getAccount).mockResolvedValue(account as never)
    vi.mocked(billingApi.getMonthlySummary).mockResolvedValue({} as never)
    vi.mocked(billingApi.getBalanceHistory).mockResolvedValue([] as never)
    vi.mocked(billingApi.getBills).mockResolvedValue({ items: [], total: 0 } as never)
    useAuthStore.setState({
      user: {
        id: 'u1',
        username: 'test2',
        email: 'test2@example.com',
        user_type: 'developer',
        role: 'developer',
        permissions: [],
      },
      accessToken: 't',
      refreshToken: 'r',
      isAuthenticated: true,
    } as never)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('TC-FE-BILL-001: simulation 环境（mock_mode=false）必须显示「测试环境/模拟账户」，不得显示「生产环境」', async () => {
    stubHealth('simulation', false)
    const { container } = renderWithProviders(<Billing />, { route: '/developer/billing' })

    // 账户标签（与顶栏 SIMULATION 徽标同源一致）
    expect(await screen.findByText('模拟账户')).toBeInTheDocument()
    expect(screen.getByText('测试环境（模拟账本）')).toBeInTheDocument()
    // 不再出现矛盾的旧文案
    expect(screen.queryByText('生产环境')).not.toBeInTheDocument()
    expect(screen.queryByText('真实账户')).not.toBeInTheDocument()
    // 余额正常显示（⚠️ antd Statistic 把 20 与 .00 拆成两个节点 → 用 textContent 断言）
    expect(await screen.findByText('账户余额')).toBeInTheDocument()
    await waitFor(() => expect(container.textContent).toContain('20.00'))
  })

  it('TC-FE-BILL-002: production 环境显示「生产环境/真实账户」', async () => {
    stubHealth('production', true)
    renderWithProviders(<Billing />, { route: '/developer/billing' })

    expect(await screen.findByText('生产环境')).toBeInTheDocument()
    expect(screen.getByText('真实账户')).toBeInTheDocument()
  })
})

/**
 * 开发者工作台测试（TC-FE-DASH）
 *
 * 回归背景：原先 fetchData 用裸 Promise.all —— 任一数据源失败会把 account 一起清成 null，
 * 余额显示 ¥0 +「模拟」标签，与账单中心的真实余额矛盾（用户实测：账单中心 ¥20 / 工作台 ¥0）。
 * 修复后各数据源独立兜底（.catch → null），单源失败只降级该卡片。
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { billingApi } from '../../api/billing'
import { quotaApi } from '../../api/quota'
import { useAuthStore } from '../../stores/auth'
import { renderWithProviders } from '../../test/renderWithProviders'
import DeveloperDashboard from './Dashboard'

vi.mock('../../api/billing', () => ({
  billingApi: {
    getAccount: vi.fn(),
  },
}))
vi.mock('../../api/quota', () => ({
  quotaApi: {
    getKeys: vi.fn(),
    getQuotaOverview: vi.fn(),
    getConsumptionTrend: vi.fn(),
    getTopRepos: vi.fn(),
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

describe('开发者工作台（TC-FE-DASH）', () => {
  beforeEach(() => {
    vi.mocked(billingApi.getAccount).mockResolvedValue(account as never)
    vi.mocked(quotaApi.getKeys).mockResolvedValue({ items: [] } as never)
    vi.mocked(quotaApi.getQuotaOverview).mockResolvedValue([] as never)
    vi.mocked(quotaApi.getConsumptionTrend).mockResolvedValue([] as never)
    useAuthStore.setState({
      user: {
        id: 'u1',
        username: 'dev',
        email: 'dev@example.com',
        user_type: 'developer',
        role: 'developer',
        permissions: [],
      },
      accessToken: 't',
      refreshToken: 'r',
      isAuthenticated: true,
    } as never)
  })

  it('TC-FE-DASH-001: 单一数据源失败（quota 挂了）不影响账户余额显示', async () => {
    vi.mocked(quotaApi.getQuotaOverview).mockRejectedValue(new Error('quota 服务不可用'))
    const { container } = renderWithProviders(<DeveloperDashboard />, { route: '/developer' })

    // 余额来自 billingApi.getAccount（成功）→ 必须显示 20.00，不得因 quota 失败被清成 0
    expect(await screen.findByText('账户余额')).toBeInTheDocument()
    await waitFor(() => expect(container.textContent).toContain('20.00'))
  })

  it('TC-FE-DASH-002: 全部数据源失败不白屏（余额卡片仍渲染）', async () => {
    vi.mocked(billingApi.getAccount).mockRejectedValue(new Error('billing 不可用'))
    vi.mocked(quotaApi.getQuotaOverview).mockRejectedValue(new Error('quota 不可用'))
    vi.mocked(quotaApi.getConsumptionTrend).mockRejectedValue(new Error('trend 不可用'))
    const { container } = renderWithProviders(<DeveloperDashboard />, { route: '/developer' })

    // 全挂 → account 为 null → 显示 0.00（降级），但页面骨架必须保留
    expect(await screen.findByText('账户余额')).toBeInTheDocument()
    await waitFor(() => expect(container.textContent).toContain('0.00'))
    expect(screen.getByText('账户余额')).toBeInTheDocument()
  })

  it('TC-FE-DASH-003: 正常路径渲染余额与标签', async () => {
    const { container } = renderWithProviders(<DeveloperDashboard />, { route: '/developer' })
    expect(await screen.findByText('账户余额')).toBeInTheDocument()
    await waitFor(() => expect(container.textContent).toContain('20.00'))
  })

  it('TC-FE-DASH-004: simulation 环境下余额标签显示「模拟」（mock_mode=false 不得影响）', async () => {
    stubHealth('simulation', false)
    // account.mock_mode = false（真实支付网关）也不能让标签变成「真实」——
    // 那会与顶栏「测试环境 · SIMULATION」矛盾（用户实测第二轮反馈）
    renderWithProviders(<DeveloperDashboard />, { route: '/developer' })

    expect(await screen.findByText('模拟')).toBeInTheDocument()
    expect(screen.queryByText('真实')).not.toBeInTheDocument()
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

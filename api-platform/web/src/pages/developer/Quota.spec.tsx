/**
 * 配额使用页（developer/Quota.tsx）测试 —— 用例库 FE-DEV-QUOTA
 *
 * 为什么值得测：本页把**原始计数换算成"人能看到的风险信号"**，换算错了运营会误判：
 *   ① `getQuotaData` 的百分比（含 `Math.min(100, …)` 截断 —— 超额不能画出 >100% 的条）；
 *   ② `getQuotaStatus` 的阈值分档（70 / 90 / 100 → 正常 / 使用中 / 即将用完 / 已用完）；
 *   ③ RPM/RPH 的"已达限"判断与**缺省限额回退**（`rpm_limit || 1000`）；
 *   ④ 余额提醒的触发条件与告警级别（<1 元 → error 级 + 充值引导）；
 *   ⑤ 首屏「取 Key 列表 → 自动选中第一个 → 按该 Key 拉三路数据」这条链。
 *
 * ⚠️ 顺带清掉移动端卡片的 `Card bodyStyle`（antd v5 废弃）。
 *
 * ⚠️ 断言技巧：进度条 `showInfo={false}` 时**没有百分比文字**，只能读 `.ant-progress-bg`
 *    的 `style.width`；而带 `format` 的进度条会渲染 `.ant-progress-text`（如 `75%`）。
 *    且「正常」这类文案会同时出现在状态 Tag 与 RPM/RPH 的 Badge 上 → **必须按卡片作用域断言**。
 *
 * 用例编号：TC-FE-QUOTA-001 ~ TC-FE-QUOTA-005
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'

const { showErrorSpy } = vi.hoisted(() => ({ showErrorSpy: vi.fn() }))

vi.mock('../../components/ErrorModal', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../components/ErrorModal')>()
  return {
    ...actual,
    useErrorModal: () => ({ showError: showErrorSpy, closeError: vi.fn(), ErrorModal: () => null }),
  }
})

vi.mock('../../api/quota', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/quota')>()
  return {
    ...actual,
    quotaApi: {
      getKeys: vi.fn(),
      getQuota: vi.fn(),
      getUsageHistory: vi.fn(),
      getTopRepos: vi.fn(),
      getKey: vi.fn(),
      createKey: vi.fn(),
      updateKey: vi.fn(),
      disableKey: vi.fn(),
      enableKey: vi.fn(),
      deleteKey: vi.fn(),
      revealKey: vi.fn(),
      getQuotaOverview: vi.fn(),
      setQuota: vi.fn(),
      getLogs: vi.fn(),
      getConsumptionTrend: vi.fn(),
    },
  }
})

import DeveloperQuota from './Quota'
import { quotaApi } from '../../api/quota'
import { useAuthStore } from '../../stores/auth'
import { renderWithProviders } from '../../test/renderWithProviders'

// ---------------- 测试数据 ----------------

const key1 = {
  id: 'k1',
  key_name: '生产应用',
  key_prefix: 'sk-live-abc',
  api_key: '',
  status: 'active',
  auth_type: 'api_key',
  rate_limit_rpm: 1000,
  rate_limit_rph: 10000,
  daily_quota: null,
  monthly_quota: null,
  created_at: '2026-09-10T08:30:00Z',
}
const key2 = { ...key1, id: 'k2', key_name: '测试Key', key_prefix: 'sk-test-xyz' }

/** 一份"各项都健康"的配额基线，各用例只改自己关心的字段 */
function quotaWith(overrides: Record<string, unknown> = {}) {
  return {
    api_key_id: 'k1',
    daily: { used: 700, limit: 1000, remaining: 300 },
    monthly: { used: 5000, limit: null, remaining: null },
    rpm_limit: 1000,
    rpm_used: 100,
    rph_limit: 10000,
    rph_used: 200,
    ...overrides,
  }
}

function renderPage() {
  return renderWithProviders(<DeveloperQuota />, { route: '/developer/quota' })
}

/** 按卡片内标题定位卡片 */
function cardOf(title: string): HTMLElement {
  const el = screen.getByText(title).closest('.ant-card')
  if (!el) throw new Error(`未找到卡片：${title}`)
  return el as HTMLElement
}

/** 读卡片内进度条的百分比（showInfo=false 时只能读宽度） */
function progressWidthIn(card: HTMLElement): number {
  const bg = card.querySelector('.ant-progress-bg') as HTMLElement | null
  if (!bg) throw new Error('卡片内无进度条')
  return Math.round(parseFloat(bg.style.width || '0'))
}

beforeEach(() => {
  useAuthStore.setState({ user: null })
  vi.mocked(quotaApi.getKeys).mockResolvedValue({
    items: [key1, key2],
    pagination: { page: 1, page_size: 100, total: 2, total_pages: 1 },
  } as never)
  vi.mocked(quotaApi.getQuota).mockResolvedValue(quotaWith() as never)
  vi.mocked(quotaApi.getUsageHistory).mockResolvedValue([] as never)
  vi.mocked(quotaApi.getTopRepos).mockResolvedValue([] as never)
})

describe('首屏取 Key 并自动选中第一个（TC-FE-QUOTA-001）', () => {
  it('TC-FE-QUOTA-001: 取 Key 列表 → 自动选中首个 → 按该 Key 拉配额/历史/Top 仓库', async () => {
    renderPage()

    await waitFor(() => expect(quotaApi.getKeys).toHaveBeenCalledWith({ page_size: 100 }))

    // 自动选中第一个 Key 后，三路数据都以它为参数（否则会展示到别的 Key 的用量）
    await waitFor(() => expect(quotaApi.getQuota).toHaveBeenCalledWith('k1'))
    expect(quotaApi.getUsageHistory).toHaveBeenCalledWith('k1', 'daily', 14)
    expect(quotaApi.getTopRepos).toHaveBeenCalledWith('k1', 10, 14)

    // 下拉回显「名称 (前缀...)」
    expect(await screen.findByText('生产应用 (sk-live-abc...)')).toBeInTheDocument()
    expect(screen.getByText('配额使用情况')).toBeInTheDocument()
  })
})

describe('配额百分比与状态分档（TC-FE-QUOTA-002）', () => {
  const cases: Array<{
    name: string
    daily: { used: number; limit: number | null; remaining: number | null }
    status: string
    percent: number
    valueText: string
  }> = [
    { name: '0% → 正常', daily: { used: 0, limit: 1000, remaining: 1000 }, status: '正常', percent: 0, valueText: '0/1000' },
    { name: '70% → 使用中', daily: { used: 700, limit: 1000, remaining: 300 }, status: '使用中', percent: 70, valueText: '700/1000' },
    { name: '90% → 即将用完', daily: { used: 900, limit: 1000, remaining: 100 }, status: '即将用完', percent: 90, valueText: '900/1000' },
    { name: '100% → 已用完', daily: { used: 1000, limit: 1000, remaining: 0 }, status: '已用完', percent: 100, valueText: '1000/1000' },
    { name: '超额 120% → 已用完且条宽截断到 100', daily: { used: 1200, limit: 1000, remaining: 0 }, status: '已用完', percent: 100, valueText: '1200/1000' },
    { name: 'limit=null → 无限制（不画进度）', daily: { used: 5, limit: null, remaining: null }, status: '无限制', percent: 0, valueText: '5/∞' },
  ]

  it('TC-FE-QUOTA-002: 每日配额的百分比与状态分档逐档正确（含 0/70/90/100 边界与超额截断）', async () => {
    for (const c of cases) {
      vi.mocked(quotaApi.getQuota).mockResolvedValue(quotaWith({ daily: c.daily }) as never)
      const { unmount } = renderPage()
      await screen.findByText('每日配额')

      const card = cardOf('每日配额')
      // 状态 Tag。
      // ⚠️ 两处坑：①「正常」也会出现在 RPM/RPH 的 Badge 上 → 必须按卡片作用域；
      //    ② limit=null 时卡片内「无限制」出现两次（状态 Tag + 底部"剩余: 无限制"）
      //      → 不用 getByText，直接读卡片内唯一的 `.ant-tag`。
      const tagTexts = [...card.querySelectorAll('.ant-tag')].map((t) => t.textContent)
      expect(tagTexts, `${c.name} 的状态 Tag`).toEqual([c.status])
      // 进度条宽度（showInfo=false → 只能读 width）
      expect(progressWidthIn(card), `${c.name} 的进度宽度`).toBe(c.percent)
      // 已用/上限
      expect(card.textContent?.replace(/\s/g, ''), `${c.name} 的 used/limit`).toContain(c.valueText)

      unmount()
    }
  })
})

describe('RPM / RPH 达限与缺省限额（TC-FE-QUOTA-003）', () => {
  it('TC-FE-QUOTA-003: 达到上限时标「已达限」；限额缺失时回退 1000/10000', async () => {
    vi.mocked(quotaApi.getQuota).mockResolvedValue(
      quotaWith({
        // 每日/每月给互不相同的状态，避免与 RPM/RPH 的 Badge 文案撞车
        daily: { used: 0, limit: 1000, remaining: 1000 },      // 正常
        monthly: { used: 1000, limit: 1000, remaining: 0 },     // 已用完
        rpm_limit: 1000,
        rpm_used: 1000,          // ≥ limit → 已达限
        rph_limit: undefined,    // 缺失 → 回退 10000
        rph_used: 5,
      }) as never
    )
    renderPage()
    await screen.findByText('每分钟请求 (RPM)')

    // RPM 达限
    const rpmCard = cardOf('每分钟请求 (RPM)')
    expect(within(rpmCard).getByText('已达限')).toBeInTheDocument()
    expect(progressWidthIn(rpmCard)).toBe(100)

    // RPH 未达限 + 限额回退到 10000
    const rphCard = cardOf('每小时请求 (RPH)')
    expect(within(rphCard).getByText('正常')).toBeInTheDocument()
    expect(within(rphCard).getByText('限制: 10000 次/小时')).toBeInTheDocument()

    // RPM 的限额文案（真实值 1000）
    expect(within(rpmCard).getByText('限制: 1000 次/分钟')).toBeInTheDocument()
  })
})

describe('余额提醒（TC-FE-QUOTA-004）', () => {
  it('TC-FE-QUOTA-004: 余额不足 1 元 → error 级提醒 + 充值引导；未启用余额扣费则不提醒', async () => {
    // ① 余额 0.5 元 → 明确提示不足
    vi.mocked(quotaApi.getQuota).mockResolvedValue(
      quotaWith({ balance_enabled: true, balance: 0.5 }) as never
    )
    const { unmount } = renderPage()
    await screen.findByText('每日配额')

    expect(screen.getByText(/余额不足，请及时充值/)).toBeInTheDocument()
    expect(screen.getByText('¥0.50')).toBeInTheDocument()
    expect(screen.getByText('余额扣费已启用')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /立即充值/ })).toBeInTheDocument()
    unmount()

    // ② 未启用余额扣费 → 不出现提醒
    vi.mocked(quotaApi.getQuota).mockResolvedValue(quotaWith() as never)
    renderPage()
    await screen.findByText('每日配额')
    expect(screen.queryByText('余额扣费已启用')).toBeNull()
  })
})

describe('趋势合计 / Top 仓库 / 无 Key 空态（TC-FE-QUOTA-005）', () => {
  it('TC-FE-QUOTA-005: 总调用合计与 Top 仓库占比排名正确；无 Key 时给空态引导', async () => {
    vi.mocked(quotaApi.getUsageHistory).mockResolvedValue([
      { date: '2026-09-15', call_count: 10 },
      { date: '2026-09-16', call_count: 32 },
    ] as never)
    vi.mocked(quotaApi.getTopRepos).mockResolvedValue([
      { repo_id: 'r1', repo_name: '天气服务', call_count: 75 },
      { repo_id: 'r2', repo_name: '翻译服务', call_count: 25 },
    ] as never)

    const { unmount } = renderPage()
    await screen.findByText('调用量最高的仓库（近14天）')

    // ① 趋势卡片右上角「总调用」= 各日之和
    expect(screen.getByText(/总调用: 42 次/)).toBeInTheDocument()

    // ② Top 仓库：占比按 (本仓库 / 合计) 四舍五入
    const topCard = cardOf('调用量最高的仓库（近14天）')
    expect(within(topCard).getByText('天气服务')).toBeInTheDocument()
    expect(within(topCard).getByText('翻译服务')).toBeInTheDocument()
    expect(within(topCard).getByText('75%')).toBeInTheDocument()
    expect(within(topCard).getByText('25%')).toBeInTheDocument()
    // 排名徽标 1 / 2
    expect(within(topCard).getByText('1')).toBeInTheDocument()
    expect(within(topCard).getByText('2')).toBeInTheDocument()
    unmount()

    // ③ 没有任何 Key → 空态 + 去创建的引导
    vi.mocked(quotaApi.getKeys).mockResolvedValue({
      items: [],
      pagination: { page: 1, page_size: 100, total: 0, total_pages: 0 },
    } as never)
    renderPage()
    expect(await screen.findByText('暂无API Key，请先创建API Key')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /创建API Key/ })).toBeInTheDocument()
  })
})

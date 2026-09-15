/**
 * 管理员分析报表页（Analytics.tsx）渲染与数据加载冒烟测试
 *
 * 为什么需要（P1-4 前端组件拆分的前置回归网）：
 *   本页是 P1-4 待拆的 3 个前端巨型组件之一（994 行）。原有 35 条前端单测只覆盖
 *   `permissions` / `client`（工具层），**没有任何页面组件级测试** —— 拆分时若把
 *   props / 状态接错，`tsc --noEmit` 仍会通过（类型对得上），而页面白屏只能靠人工发现。
 *   本文件锁住四条底线：渲染不崩、三个数据源被正确调用、关键文案出现、报错不白屏。
 *
 * 手法：
 *   - mock `src/api/adminAnalytics`（本组件唯一数据源），不启动后端；
 *   - 用 `<MemoryRouter>` 包裹（组件内调用 `useNavigate`），不 mock react-router；
 *   - recharts 在 jsdom 下容器宽高为 0（不实际绘制图表）属预期，只断言容器与文案。
 *
 * 用例编号：TC-FE-ANA-001 ~ TC-FE-ANA-004
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

// 组件唯一数据源 → 整体 mock（避免真实 axios 请求）
vi.mock('../../api/adminAnalytics', () => ({
  adminAnalyticsApi: {
    getOverview: vi.fn(),
    getTrend: vi.fn(),
    getRepoDetails: vi.fn(),
    getRepoTrend: vi.fn(),
  },
}))

import Analytics from './Analytics'
import { adminAnalyticsApi } from '../../api/adminAnalytics'

const overview = {
  repos: { total: 12, online: 7, pending: 3 },
  calls: { today: 1234, week: 8888, month: 30000, total: 99999, today_success: 1200, today_failed: 34 },
  revenue: { today: 12.5, week: 88.8, month: 300, total: 999.9 },
  active_users: 42,
  generated_at: '2026-09-15T00:00:00Z',
}

const trend = {
  labels: ['09-14', '09-15'],
  series: { calls: [10, 20], revenue: [1, 2] },
  period: 'day',
  days: 7,
  repo_id: null,
  generated_at: '2026-09-15T00:00:00Z',
}

const repoDetails = {
  items: [
    {
      repo_id: 'r1',
      name: '天气服务',
      slug: 'weather',
      status: 'online',
      owner_id: 'u1',
      total_calls: 100,
      success_calls: 95,
      failed_calls: 5,
      success_rate: 95,
      total_cost: 12.3,
      created_at: '2026-01-01T00:00:00Z',
    },
  ],
  pagination: { page: 1, page_size: 10, total: 1, total_pages: 1 },
  generated_at: '2026-09-15T00:00:00Z',
}

function renderPage() {
  return render(
    <MemoryRouter>
      <Analytics />
    </MemoryRouter>
  )
}

const repoTrend = {
  repo_id: 'r1',
  repo_name: '天气服务',
  labels: ['09-14', '09-15'],
  series: { calls: [3, 4], revenue: [0.3, 0.4], avg_latency: [120, 150] },
  days: 7,
  generated_at: '2026-09-15T00:00:00Z',
}

beforeEach(() => {
  vi.mocked(adminAnalyticsApi.getOverview).mockResolvedValue(overview as never)
  vi.mocked(adminAnalyticsApi.getTrend).mockResolvedValue(trend as never)
  vi.mocked(adminAnalyticsApi.getRepoDetails).mockResolvedValue(repoDetails as never)
  vi.mocked(adminAnalyticsApi.getRepoTrend).mockResolvedValue(repoTrend as never)
})

describe('管理员分析报表页', () => {
  it('TC-FE-ANA-001: 首屏渲染不崩，三个数据源均被调用', async () => {
    renderPage()

    // 静态文案（不依赖接口返回）
    expect(screen.getByText('数据分析')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /刷新数据/ })).toBeInTheDocument()

    await waitFor(() => {
      expect(adminAnalyticsApi.getOverview).toHaveBeenCalledTimes(1)
      expect(adminAnalyticsApi.getRepoDetails).toHaveBeenCalledTimes(1)
      // ✅ 已修（用例库 FE-BUG-ANALYTICS-DOUBLE-TREND）：原先 `[]` 与 `[trendPeriod, trendDays]`
      //    两个 useEffect 都会触发 getTrend → 首屏重复请求一次。现已从 `[]` 中移除该调用
      //    （挂载时由另一个 effect 负责），此处断言 1 次即该缺陷的回归防线。
      expect(adminAnalyticsApi.getTrend).toHaveBeenCalledTimes(1)
    })
  })

  it('TC-FE-ANA-002: 概览数据落到统计卡片与状态标签上', async () => {
    renderPage()

    // ⚠️ 这几处都必须用 findBy*（自带等待）：统计卡片、状态标签、Tab 文案由**不同的渲染分支**
    //    产出，加载完成时机并不一致 —— 用同步 getByText 会在机器忙时（如全量跑）偶发失败。
    //    （实测：全量跑偶现 `Unable to find an element with the text: 7 已上线`，而单跑该文件必过。）
    expect(await screen.findByText('仓库总数')).toBeInTheDocument()
    expect(await screen.findByText('今日调用')).toBeInTheDocument()
    // 标签文案由 overview.repos.online / pending 拼出（在页面中唯一）
    expect(await screen.findByText('7 已上线')).toBeInTheDocument()
    expect(await screen.findByText('3 待审核')).toBeInTheDocument()
  })

  it('TC-FE-ANA-003: 点击「刷新数据」每个数据源各追加一次请求', async () => {
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => expect(adminAnalyticsApi.getOverview).toHaveBeenCalledTimes(1))

    // 用"点击前计数 + 1"断言，避免把首屏的 useEffect 次数（如 getTrend 的 2 次）写死
    const before = {
      overview: vi.mocked(adminAnalyticsApi.getOverview).mock.calls.length,
      trend: vi.mocked(adminAnalyticsApi.getTrend).mock.calls.length,
      details: vi.mocked(adminAnalyticsApi.getRepoDetails).mock.calls.length,
    }
    await user.click(screen.getByRole('button', { name: /刷新数据/ }))

    await waitFor(() => {
      expect(vi.mocked(adminAnalyticsApi.getOverview).mock.calls.length).toBe(before.overview + 1)
      expect(vi.mocked(adminAnalyticsApi.getTrend).mock.calls.length).toBe(before.trend + 1)
      expect(vi.mocked(adminAnalyticsApi.getRepoDetails).mock.calls.length).toBe(before.details + 1)
    })
  })

  it('TC-FE-ANA-004: 接口报错时页面不白屏（仍渲染骨架文案）', async () => {
    vi.mocked(adminAnalyticsApi.getOverview).mockRejectedValue(new Error('后端不可用'))
    vi.mocked(adminAnalyticsApi.getTrend).mockRejectedValue(new Error('后端不可用'))
    vi.mocked(adminAnalyticsApi.getRepoDetails).mockRejectedValue(new Error('后端不可用'))

    renderPage()

    // 报错路径不得抛未捕获异常导致整树卸载
    await waitFor(() => expect(adminAnalyticsApi.getOverview).toHaveBeenCalled())
    expect(screen.getByText('数据分析')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /刷新数据/ })).toBeInTheDocument()
  })
})

describe('Tab 切换与仓库明细弹窗', () => {
  it('TC-FE-ANA-005: 切到「趋势分析」展示趋势卡片与周期控件', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('tab', { name: /趋势分析/ }))

    // ⚠️ 用 findAll：antd Tabs 会保留已渲染 Tab 的 DOM，且标题可能与表格/卡片重复
    expect((await screen.findAllByText('调用与收入趋势')).length).toBeGreaterThan(0)
    // 周期选择器当前值（默认「按天统计」）—— 该文本唯一，可证明趋势 Tab 内容已挂载
    expect(screen.getByText('按天统计')).toBeInTheDocument()
  })

  it('TC-FE-ANA-006: 切到「仓库明细」展示表格、数据与分页总数', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('tab', { name: /仓库明细/ }))

    expect(await screen.findByText('仓库调用与收入明细')).toBeInTheDocument()
    // 行数据来自 mock 的 repoDetails
    expect(screen.getByText('天气服务')).toBeInTheDocument()
    // 分页 showTotal
    expect(screen.getByText('共 1 条')).toBeInTheDocument()
  })

  it('TC-FE-ANA-007: 点击「查看明细」按仓库打开弹窗并加载其趋势', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('tab', { name: /仓库明细/ }))
    await user.click(await screen.findByText('查看明细'))

    // 默认 7 天
    await waitFor(() => expect(adminAnalyticsApi.getRepoTrend).toHaveBeenCalledWith('r1', 7))

    // 弹窗标题与基本信息（仓库 ID / Slug）出现；
    // ⚠️ repo_id / slug 在明细表格中也可能出现，故用 findAll 判定"至少出现一次"
    expect(await screen.findByText('仓库收入明细')).toBeInTheDocument()
    expect(screen.getAllByText('r1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('weather').length).toBeGreaterThan(0)
  })
})

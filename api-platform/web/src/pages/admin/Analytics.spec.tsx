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
 *   - 用 `<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>` 包裹（组件内调用 `useNavigate`），不 mock react-router；
 *   - recharts 在 jsdom 下容器宽高为 0（不实际绘制图表）属预期，只断言容器与文案。
 *
 * 用例编号：TC-FE-ANA-001 ~ TC-FE-ANA-004
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { ConfigProvider } from 'antd'

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
    // ⚠️ 与 renderWithProviders 一致关掉动画：曾导致 Select 下拉停在
    //    `ant-slide-up-appear-prepare` 帧，option 迟迟不进入可交互状态（ANA-008 实测）。
    <ConfigProvider theme={{ token: { motion: false } }}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Analytics />
      </MemoryRouter>
    </ConfigProvider>
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
    // 周期选择器当前值（默认「按天统计」）—— 能证明趋势 Tab 内容已挂载。
    // ⚠️ 用 getAllByText：B 轮把周期控件抽成共享的 `TrendControls` 并**统一了文案**后
    //    （缺陷 FE-BUG-ANALYTICS-DUP-TREND-CARD），概览卡里那个控件现在也是「按天统计」，
    //    同一文本在页面上出现两处 → `getByText` 会报 multiple elements。
    expect(screen.getAllByText('按天统计').length).toBeGreaterThan(0)
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

  it('TC-FE-ANA-008: 明细状态筛选与排序变化会带参重新查询', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('tab', { name: /仓库明细/ }))
    await waitFor(() => expect(adminAnalyticsApi.getRepoDetails).toHaveBeenCalled())

    // ⚠️ antd Select 交互的 jsdom 深坑（ANA-008 实测）：
    //   1. 打开下拉必须 `fireEvent.mouseDown(selector)`（userEvent.click 的 pointer 序列无效）；
    //   2. 弹层 option **渲染正常**但 dropdown 会停在 `ant-slide-up-appear-prepare` 动画帧
    //      （`ConfigProvider motion:false` 的 token 禁不掉 rc-motion 的 slide-up）→
    //      弹层容器不可见 → `getByRole('option')` 的可访问性判定**永远找不到**；
    //   3. 因此改为：mouseDown 打开 → 在未 hidden 的弹层里按文本找 option → fireEvent.click
    //      （fireEvent 不做可见性检查，React 的 onSelect 照常触发）。
    const pick = (selector: HTMLElement, optionText: string) => {
      fireEvent.mouseDown(selector)
      const dd = [...document.querySelectorAll('.ant-select-dropdown')].find((d) =>
        !d.className.includes('hidden')
      )
      if (!dd) throw new Error('Select 下拉未打开')
      const opt = [...dd.querySelectorAll('.ant-select-item-option')].find(
        (o) => o.textContent === optionText
      )
      if (!opt) throw new Error(`下拉中无 option：${optionText}`)
      fireEvent.click(opt)
    }
    // 用"当前可见文本"定位 Select（placeholder 或当前选中值的文案在页面内唯一）
    const comboOf = (visibleText: string): HTMLElement => {
      const el = screen.getByText(visibleText).closest('.ant-select')
      if (!el) throw new Error(`未找到 Select：${visibleText}`)
      const selector = el.querySelector('.ant-select-selector')
      if (!selector) throw new Error(`Select 缺少 selector：${visibleText}`)
      return selector as HTMLElement
    }

    // 1) 状态筛选（placeholder 唯一）→ 选「待审核」
    await pick(comboOf('状态筛选'), '待审核')
    // 2) 排序字段：当前值「按调用量排序」→ 按收入
    await pick(comboOf('按调用量排序'), '按收入排序')
    // 3) 排序次序：当前值「降序」→ 升序
    await pick(comboOf('降序'), '升序')

    // detailStatus / detailSortBy / detailSortOrder 任一变化都会触发 effect 重查
    await waitFor(() => {
      const calls = vi.mocked(adminAnalyticsApi.getRepoDetails).mock.calls
      const last = calls[calls.length - 1][0] as Record<string, unknown>
      expect(last.status).toBe('pending')
      expect(last.sort_by).toBe('total_cost')
      expect(last.sort_order).toBe('asc')
    })
  })
})

// ==================== C 轮新增：条件变更后的带参重查（TC-FE-ANA-009~011）====================
// 为什么补：005~008 只断言"展示了什么"，未覆盖另外三条"改条件 → 带新参数重查"的链路：
//   ① 趋势周期（按天/按小时）与天数；② 明细分页翻页；③ 弹窗内切换天数。

describe('Analytics 条件变更重查（TC-FE-ANA-009~011）', () => {
  // ⚠️ 本页**存在多处同文案的 Select**：「近7天」同时出现在 OverviewTab（概览 Tab）、
  //    趋势卡的 extra、以及 RepoDetailModal 里；而 antd Tabs 会保留已挂载的 Tab 面板 →
  //    直接在 body 上按文案找会命中多个（首跑报 "Found multiple elements with the text: 近7天"）。
  //    因此改为**限定作用域**查找。
  const comboIn = (scope: ParentNode, visibleText: string): HTMLElement => {
    const items = [...scope.querySelectorAll('.ant-select-selection-item')].filter(
      (n) => n.textContent === visibleText
    )
    if (items.length !== 1) {
      throw new Error(`作用域内文案为「${visibleText}」的 Select 命中 ${items.length} 个（应为 1）`)
    }
    const selector = items[0].closest('.ant-select')?.querySelector('.ant-select-selector')
    if (!selector) throw new Error(`未找到 Select 的 selector：${visibleText}`)
    return selector as HTMLElement
  }

  /**
   * 取**当前激活的 Tab 面板**作为作用域。
   *
   * ⚠️ 不能只用 `cardByTitle('调用与收入趋势')`：概览 Tab（OverviewTab.tsx）里**也有一张同名卡片**，
   *    同样带周期 + 天数选择器，而且两者共用同一份状态（`onPeriodChange`/`onDaysChange` 都接到
   *    `setTrendPeriod`/`setTrendDays`）。按标题取到的是文档里靠前的**概览**那张卡，
   *    于是"天数"能改（状态共用），但"周期"的文案对不上 ——
   *    概览卡的选项是「按天」/「按小时」，趋势卡才是「按天统计」/「按小时统计」
   *    （同一页同一个控件两套文案，属可改进的不一致，已记入用例库 knownDefects）。
   */
  const activePane = (): HTMLElement => {
    const pane = document.querySelector('.ant-tabs-tabpane-active')
    if (!pane) throw new Error('未找到激活的 Tab 面板')
    return pane as HTMLElement
  }

  // ⚠️ antd Select 交互沿用 ANA-008 结论：下拉必须 mouseDown 打开 → 在未 hidden 的弹层里
  //    按文本找 option → fireEvent.click（弹层停在动画帧，getByRole('option') 永远找不到）。
  const pick = (selector: HTMLElement, optionText: string) => {
    fireEvent.mouseDown(selector)
    const dd = [...document.querySelectorAll('.ant-select-dropdown')].find(
      (d) => !d.className.includes('hidden')
    )
    if (!dd) throw new Error('Select 下拉未打开')
    const opt = [...dd.querySelectorAll('.ant-select-item-option')].find(
      (o) => o.textContent === optionText
    )
    if (!opt) throw new Error(`下拉中无 option：${optionText}`)
    fireEvent.click(opt)
  }

  it('TC-FE-ANA-009: 趋势天数 7→30、周期「按天」→「按小时」均带新参数重查', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('tab', { name: /趋势分析/ }))
    await waitFor(() => expect(adminAnalyticsApi.getTrend).toHaveBeenCalled())
    const before = vi.mocked(adminAnalyticsApi.getTrend).mock.calls.length

    // 默认「按天统计」+「近7天」→ 改成近 30 天（限定在**趋势 Tab 面板**内）
    pick(comboIn(activePane(), '近7天'), '近30天')
    await waitFor(() => {
      const calls = vi.mocked(adminAnalyticsApi.getTrend).mock.calls
      expect(calls[calls.length - 1][0]).toEqual({ period: 'day', days: 30 })
    })

    // 周期改成「按小时统计」→ 天数沿用 30（源码：天数选择器只在 period==='day' 时出现）
    // ⚠️ 此处文案必须是「按天统计」：概览 Tab 那张同名卡用的是「按天」，
    //    靠全文查找会命中错的那个（首跑即如此）→ 用激活面板限定
    pick(comboIn(activePane(), '按天统计'), '按小时统计')
    await waitFor(() => {
      const calls = vi.mocked(adminAnalyticsApi.getTrend).mock.calls
      expect(calls[calls.length - 1][0]).toEqual({ period: 'hour', days: 30 })
    })
    expect(vi.mocked(adminAnalyticsApi.getTrend).mock.calls.length).toBeGreaterThan(before)
  })

  it('TC-FE-ANA-010: 明细分页翻到第 2 页时带 page=2 重查', async () => {
    // 默认 mock 只有 1 页（total=1）→ 必须给出多页数据才能点到第 2 页
    vi.mocked(adminAnalyticsApi.getRepoDetails).mockResolvedValue({
      ...repoDetails,
      pagination: { page: 1, page_size: 10, total: 25, total_pages: 3 },
    } as never)

    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('tab', { name: /仓库明细/ }))
    await waitFor(() => expect(adminAnalyticsApi.getRepoDetails).toHaveBeenCalled())

    const page2 = document.querySelector('.ant-pagination-item-2') as HTMLElement | null
    expect(page2, '总数 25 / 每页 10 → 应出现第 2 页').toBeTruthy()
    await user.click(page2 as HTMLElement)

    // repoPagination.page 是 effect 依赖 → 翻页必须带新 page 重查
    await waitFor(() => {
      const calls = vi.mocked(adminAnalyticsApi.getRepoDetails).mock.calls
      const last = calls[calls.length - 1][0] as Record<string, unknown>
      expect(last.page).toBe(2)
    })
  })

  it('TC-FE-ANA-011: 明细弹窗内切换天数按新天数重查该仓库趋势', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('tab', { name: /仓库明细/ }))
    await user.click(await screen.findByText('查看明细'))
    // 打开弹窗时用的是默认 7 天
    await waitFor(() => expect(adminAnalyticsApi.getRepoTrend).toHaveBeenCalledWith('r1', 7))

    // 弹窗内「近7天」→「近30天」（限定在弹窗内：页面上另有概览/趋势卡的同文案选择器）
    const modal = document.querySelector('.ant-modal-wrap')
    expect(modal, '明细弹窗应已挂载').toBeTruthy()
    pick(comboIn(modal as HTMLElement, '近7天'), '近30天')

    await waitFor(() =>
      expect(adminAnalyticsApi.getRepoTrend).toHaveBeenLastCalledWith('r1', 30)
    )
  })
})

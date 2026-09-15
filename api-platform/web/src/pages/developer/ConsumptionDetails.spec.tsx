/**
 * 消费明细页（ConsumptionDetails.tsx）测试
 *
 * 为什么优先测它（P1）：
 *   这是开发者对账的主要依据，且页面**在客户端做二次聚合**（按接口 / 按日期分组求和）——
 *   这类"前端自己算"的逻辑一旦算错，明细行看着对、汇总却是错的，很难靠肉眼发现。
 *   另外"计费模式"（按次 / 按Token）由数据推断得出，决定了汇总列展示哪些指标。
 *
 * 用例编号：TC-FE-CONSUME-001 ~ TC-FE-CONSUME-008
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'

vi.mock('../../api/billing', () => ({
  billingApi: {
    getUsage: vi.fn(),
    getConsumptionDetails: vi.fn(),
  },
}))

import ConsumptionDetails from './ConsumptionDetails'
import { billingApi } from '../../api/billing'
import { renderWithProviders } from '../../test/renderWithProviders'

const usage = {
  call_count: 5,
  total_tokens: 3000,
  total_cost: 12.5,
  by_repository: [
    { repo_id: 'r1', repo_name: '天气服务', call_count: 3, total_tokens: 3000, total_cost: 9.5 },
    { repo_id: 'r2', repo_name: '翻译服务', call_count: 2, total_tokens: 0, total_cost: 3.0 },
  ],
}

const usageNoTokens = {
  call_count: 2,
  total_tokens: 0,
  total_cost: 3.0,
  by_repository: [
    { repo_id: 'r2', repo_name: '翻译服务', call_count: 2, total_tokens: 0, total_cost: 3.0 },
  ],
}

/** 3 条明细：两条同日期（2026-09-15）便于验证日期聚合 */
const detailsResponse = {
  items: [
    {
      id: 1,
      repo_id: 'r1',
      repo_name: '天气服务',
      endpoint: '/weather',
      tokens_used: 100,
      cost: 1.5,
      created_at: '2026-09-15T10:00:00Z',
    },
    {
      id: 2,
      repo_id: 'r1',
      repo_name: '天气服务',
      endpoint: '/weather',
      tokens_used: 200,
      cost: 2.5,
      created_at: '2026-09-15T11:00:00Z',
    },
    {
      id: 3,
      repo_id: 'r1',
      repo_name: '天气服务',
      endpoint: '/forecast',
      tokens_used: 0,
      cost: 0.5,
      created_at: '2026-09-14T10:00:00Z',
    },
  ],
  pagination: { page: 1, page_size: 10, total: 3, total_pages: 1 },
}

beforeEach(() => {
  vi.mocked(billingApi.getUsage).mockResolvedValue(usage as never)
  vi.mocked(billingApi.getConsumptionDetails).mockResolvedValue(detailsResponse as never)
})

describe('仓库汇总（按仓库 Tab）', () => {
  it('TC-FE-CONSUME-001: 首屏加载 getUsage 并渲染汇总统计与仓库明细', async () => {
    renderWithProviders(<ConsumptionDetails />)

    await waitFor(() => expect(billingApi.getUsage).toHaveBeenCalledTimes(1))

    // ⚠️ 汇总统计在 3 个 Tab 中各渲染一份（antd Tabs 保留已渲染的 DOM）→ 必须用 findAll
    expect((await screen.findAllByText('总调用次数')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('总费用').length).toBeGreaterThan(0)
    // 按仓库 Tab 下渲染出仓库行（仓库名同时出现在汇总列表与表格中）
    expect((await screen.findAllByText('天气服务')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('翻译服务').length).toBeGreaterThan(0)
  })

  it('TC-FE-CONSUME-002: 任一仓库有 Token 消耗 → 判定为按 Token 计费，汇总多出「总 Tokens」', async () => {
    renderWithProviders(<ConsumptionDetails />)

    // 有 tokens → billingModel = per_token → 汇总出现「总 Tokens」列（多 Tab 各一份，用 findAll）
    expect((await screen.findAllByText('总 Tokens')).length).toBeGreaterThan(0)
    // 仓库行的计费模式标签
    expect((await screen.findAllByText('按Token计费')).length).toBeGreaterThan(0)
  })

  it('TC-FE-CONSUME-003: 全部无 Token → 按次计费，汇总不出现「总 Tokens」', async () => {
    vi.mocked(billingApi.getUsage).mockResolvedValue(usageNoTokens as never)

    renderWithProviders(<ConsumptionDetails />)

    expect((await screen.findAllByText('按次计费')).length).toBeGreaterThan(0)
    await waitFor(() => expect(screen.queryAllByText('总 Tokens')).toHaveLength(0))
  })

  it('TC-FE-CONSUME-004: getUsage 失败时页面不白屏', async () => {
    vi.mocked(billingApi.getUsage).mockRejectedValue(new Error('后端不可用'))

    renderWithProviders(<ConsumptionDetails />)

    await waitFor(() => expect(billingApi.getUsage).toHaveBeenCalled())
    // 页面骨架仍在（Tab 标签可见）
    expect(screen.getByText('按仓库')).toBeInTheDocument()
    expect(screen.getByText('按接口')).toBeInTheDocument()
    expect(screen.getByText('按日期')).toBeInTheDocument()
  })
})

describe('按日期 Tab（客户端聚合）', () => {
  /** 切到「按日期」Tab 并等待明细加载完成 */
  async function openDateTab(): Promise<void> {
    fireEvent.click(screen.getByText('按日期'))
    await waitFor(() => expect(billingApi.getConsumptionDetails).toHaveBeenCalled())
  }

  it('TC-FE-CONSUME-005: 切「按日期」触发明细查询，带上分页参数', async () => {
    renderWithProviders(<ConsumptionDetails />)
    await openDateTab()

    expect(billingApi.getConsumptionDetails).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1, page_size: expect.any(Number) })
    )
  })

  it('TC-FE-CONSUME-006: 明细按日期聚合 —— 同一天多条合并为一行，并倒序排列', async () => {
    renderWithProviders(<ConsumptionDetails />)
    await openDateTab()

    // 两条 09-15 + 一条 09-14 → 聚合后恰好两个日期分组
    expect(await screen.findByText('2026-09-15')).toBeInTheDocument()
    expect(screen.getByText('2026-09-14')).toBeInTheDocument()

    // 聚合后的调用次数：09-15 合计 2 次、09-14 为 1 次（表格渲染数字）
    await waitFor(() => {
      expect(screen.getAllByText('2').length).toBeGreaterThan(0)
      expect(screen.getAllByText('1').length).toBeGreaterThan(0)
    })
  })

  it('TC-FE-CONSUME-007: 明细接口失败时不崩（页面与 Tab 仍在）', async () => {
    vi.mocked(billingApi.getConsumptionDetails).mockRejectedValue(new Error('加载失败'))

    renderWithProviders(<ConsumptionDetails />)
    await openDateTab()

    expect(screen.getByText('按日期')).toBeInTheDocument()
  })

  it('TC-FE-CONSUME-008: 「重置」后重新查询（分页回到第 1 页）', async () => {
    renderWithProviders(<ConsumptionDetails />)
    await openDateTab()

    const callsBefore = vi.mocked(billingApi.getConsumptionDetails).mock.calls.length
    const resetButtons = screen.getAllByText('重置')
    fireEvent.click(resetButtons[resetButtons.length - 1])

    // 重置会触发一次新的查询（参数仍为第 1 页）
    await waitFor(() =>
      expect(vi.mocked(billingApi.getConsumptionDetails).mock.calls.length).toBeGreaterThan(callsBefore)
    )
    // ⚠️ 用索引而非 `Array.prototype.at()`：项目 tsconfig 的 lib 为 ES2020，
    //    `at()` 属 ES2022（vitest 运行期可用，但 `tsc --noEmit` 会报 TS2550，
    //    被 pre-commit 类型检查拦下 —— 实测踩过）。
    const allCalls = vi.mocked(billingApi.getConsumptionDetails).mock.calls
    const lastCall = allCalls[allCalls.length - 1]?.[0] as Record<string, unknown>
    expect(lastCall.page).toBe(1)
  })
})

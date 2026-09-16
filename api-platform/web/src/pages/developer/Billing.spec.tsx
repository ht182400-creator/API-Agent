/**
 * 账单中心测试（TC-FE-BILL）
 *
 * 回归背景：环境标签原先读 `account.mock_mode`（支付模拟模式），而全局顶栏读
 * `/health` 的 billing_environment —— 两个数据源导致自相矛盾（顶栏「测试环境 · SIMULATION」
 * 而账单中心「生产环境 / 真实账户」，用户实测截图）。修复后标签与顶栏同源（useEnvInfo）。
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor, fireEvent, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import dayjs from 'dayjs'
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
    exportBills: vi.fn(),
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

// ==================== N 轮新增：账单列表 / 分页 / 月度汇总 / 日期筛选 ====================

const bills = [
  { id: 'b1', bill_type: 'recharge', amount: 100, balance_after: 120, description: '会员充值', created_at: '2026-09-16T02:30:00Z' },
  { id: 'b2', bill_type: 'consume', amount: -12.5, balance_after: 107.5, description: '调用天气服务', created_at: '2026-09-16T04:00:00Z' },
  { id: 'b3', bill_type: 'refund', amount: 3, balance_after: 110.5, description: '订单退款退回', created_at: '2026-09-16T05:00:00Z' },
]

const monthlySummary = {
  total_recharge: 500,
  total_consumption: 123.45,
  consumption_count: 42,
  by_repository: [{ repo_id: 'r1', repo_name: '天气服务', total: 123.45, count: 42 }],
}

/** antd Select：打开下拉（必须 mouseDown）→ 在弹层里点 option */
function pick(selector: HTMLElement, optionText: string): void {
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

function comboOf(visibleText: string): HTMLElement {
  const el = screen.getByText(visibleText).closest('.ant-select')
  const selector = el?.querySelector('.ant-select-selector')
  if (!selector) throw new Error(`未找到 Select：${visibleText}`)
  return selector as HTMLElement
}

/** 按「描述」列文本定位账单行 */
function rowOf(description: string): HTMLElement {
  const row = screen.getByText(description).closest('tr')
  if (!row) throw new Error(`未找到账单行：${description}`)
  return row as HTMLElement
}

describe('账单明细与月度汇总（TC-FE-BILLING）', () => {
  beforeEach(() => {
    stubHealth('simulation', false)
    vi.mocked(billingApi.getAccount).mockResolvedValue({ balance: 110.5, mock_mode: false } as never)
    vi.mocked(billingApi.getMonthlySummary).mockResolvedValue(monthlySummary as never)
    vi.mocked(billingApi.getBalanceHistory).mockResolvedValue([] as never)
    vi.mocked(billingApi.getBills).mockResolvedValue({
      items: bills,
      pagination: { page: 1, page_size: 20, total: 3, total_pages: 1 },
    } as never)
    useAuthStore.setState({
      user: { id: 'u1', email: 'dev@example.com', user_type: 'developer', role: 'developer', permissions: [] },
      accessToken: 't',
      refreshToken: 'r',
      isAuthenticated: true,
    } as never)
  })

  it('TC-FE-BILLING-001: 账单列表派生文案（类型/正负金额/余额/时间）且首屏只请求一次', async () => {
    renderWithProviders(<Billing />, { route: '/developer/billing' })

    // ① 默认分页参数
    await waitFor(() =>
      expect(billingApi.getBills).toHaveBeenCalledWith({ page: 1, page_size: 20 })
    )

    // ② 类型 → Tag 文案（recharge/consume/refund；后端也可能给 consumption 别名）。
    // ⚠️ 必须**在行内**断言：「充值」同时是顶部的充值按钮文案（首跑就是全局 getByText 报了多元素）。
    await screen.findByText('会员充值')
    expect(within(rowOf('会员充值')).getByText('充值')).toBeInTheDocument()
    expect(within(rowOf('调用天气服务')).getByText('消费')).toBeInTheDocument()
    expect(within(rowOf('订单退款退回')).getByText('退款')).toBeInTheDocument()

    // ③ 金额：正数带 `+`、负数带 `-`，都用 toFixed(2)（+¥100.00 / -¥12.50 / +¥3.00）
    expect(screen.getByText('+¥100.00')).toBeInTheDocument()
    expect(screen.getByText('-¥12.50')).toBeInTheDocument()
    expect(screen.getByText('+¥3.00')).toBeInTheDocument()

    // ④ 变动后余额
    expect(screen.getByText('¥120.00')).toBeInTheDocument()
    expect(screen.getByText('¥107.50')).toBeInTheDocument()

    // ⑤ 时间格式化到秒
    expect(
      screen.getByText(dayjs(bills[0].created_at).format('YYYY-MM-DD HH:mm:ss'))
    ).toBeInTheDocument()
    // ⑥ 描述原文展示（不做脱敏/截断以外处理）
    expect(screen.getByText('调用天气服务')).toBeInTheDocument()

    // ⑦ 两处合计文案：卡片头「共 3 条记录」与分页「共 3 条」
    expect(screen.getByText('共 3 条记录')).toBeInTheDocument()
    expect(screen.getByText('共 3 条')).toBeInTheDocument()

    // ⑧ 首屏**只应拉一次账单**。
    //   ⚠️ 本页有两个 effect 都会拉账单：`fetchData()`（内含 fetchBills）与
    //      `useEffect(fetchBills, [page,pageSize,dateRange])` —— 挂载时两者都触发，
    //      会重复请求（本用例首跑即暴露，见轮次 N 日志）。
    expect(billingApi.getBills).toHaveBeenCalledTimes(1)
  })

  it('TC-FE-BILLING-002: 切换每页条数后带新 page_size 重新查询', async () => {
    renderWithProviders(<Billing />, { route: '/developer/billing' })
    await waitFor(() => expect(billingApi.getBills).toHaveBeenCalled())

    pick(comboOf('20 条/页'), '10 条/页')

    await waitFor(() =>
      expect(billingApi.getBills).toHaveBeenLastCalledWith({ page: 1, page_size: 10 })
    )
  })

  it('TC-FE-BILLING-003: 月度汇总卡片与当前月份回显', async () => {
    const { container } = renderWithProviders(<Billing />, { route: '/developer/billing' })

    expect(await screen.findByText('本月充值')).toBeInTheDocument()
    expect(screen.getByText('本月消费')).toBeInTheDocument()
    expect(screen.getByText('本月调用')).toBeInTheDocument()
    expect(screen.getByText('账户余额')).toBeInTheDocument()

    // 汇总数值（antd Statistic 把整数与小数拆成多个节点 → 用 textContent 断言）
    await waitFor(() => expect(container.textContent).toContain('500.00'))
    expect(container.textContent).toContain('123.45')
    expect(container.textContent).toContain('42')

    // 月度周期回显：当月文案（YYYY年MM月）；带筛选条件时也须如此
    expect(screen.getByText(dayjs().format('YYYY年MM月'))).toBeInTheDocument()

    // 无余额变化记录 → 空态与引导
    expect(screen.getByText('暂无余额变化记录')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /立即充值/ })).toBeInTheDocument()
  })

  it('TC-FE-BILLING-004: 日期筛选带参重查，且「导出」沿用同一区间', async () => {
    renderWithProviders(<Billing />, { route: '/developer/billing' })
    await waitFor(() => expect(billingApi.getBills).toHaveBeenCalled())

    // ⚠️ RangePicker 必须用**真实键盘输入**（userEvent.type + Enter）：
    //    fireEvent.change 只改 DOM value，rc-picker 的内部选择态不会更新 → 不触发 onChange（首跑实测）。
    const [startInput, endInput] = screen.getAllByPlaceholderText(/开始日期|结束日期/)
    const user = userEvent.setup()
    await user.click(startInput)
    await user.type(startInput, '2026-09-01')
    await user.keyboard('{Enter}')
    await user.type(endInput, '2026-09-30')
    await user.keyboard('{Enter}')

    // 日期变化 → 带 start_date/end_date 重新查询
    await waitFor(() =>
      expect(billingApi.getBills).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 20,
        start_date: '2026-09-01',
        end_date: '2026-09-30',
      })
    )

    // 导出必须沿用当前区间（否则导出的不是用户正在看的账单）
    fireEvent.click(screen.getByRole('button', { name: /导出/ }))
    await waitFor(() =>
      expect(billingApi.exportBills).toHaveBeenCalledWith({
        start_date: '2026-09-01',
        end_date: '2026-09-30',
      })
    )
  })
})

// ==================== C 轮新增：普通用户引导 + 消费分布两分支（TC-FE-BILLING-005/006）====================
// 为什么补：上面 4 条用例**全部以 developer 身份**渲染，于是两个真实分支从未跑到 ——
//   ① `isNormalUser`（user_type === 'user'）的升级引导；
//   ② 「消费分布」的 `distributionData.length > 0` 两分支（空态 / 渲染图表）。

describe('账单中心 · 未覆盖分支（TC-FE-BILLING-005/006）', () => {
  beforeEach(() => {
    stubHealth('simulation', false)
    vi.mocked(billingApi.getAccount).mockResolvedValue({ balance: 110.5, mock_mode: false } as never)
    vi.mocked(billingApi.getMonthlySummary).mockResolvedValue(monthlySummary as never)
    vi.mocked(billingApi.getBalanceHistory).mockResolvedValue([] as never)
    vi.mocked(billingApi.getBills).mockResolvedValue({
      items: bills,
      pagination: { page: 1, page_size: 20, total: 3, total_pages: 1 },
    } as never)
    // ⚠️ 登录态必须显式重置（store 是模块级单例，上一个用例把 user_type 改成 'user' 后会**泄漏**到下一个用例
    //    → 006 会莫名渲染出升级引导条）
    useAuthStore.setState({
      user: { id: 'u1', email: 'dev@example.com', user_type: 'developer', role: 'developer', permissions: [] },
      accessToken: 't',
      refreshToken: 'r',
      isAuthenticated: true,
    } as never)
  })

  /** 普通用户登录态（developer 之外的另一条身份分支） */
  function loginAsNormalUser(): void {
    useAuthStore.setState({
      user: {
        id: 'u2',
        email: 'plain@example.com',
        user_type: 'user',
        role: 'user',
        permissions: [],
      },
      accessToken: 't',
      refreshToken: 'r',
      isAuthenticated: true,
    } as never)
  }

  it('TC-FE-BILLING-005: 普通用户显示「升级为开发者」引导，点击后跳 /user', async () => {
    loginAsNormalUser()
    const user = userEvent.setup()

    // ⚠️ renderWithProviders 默认不渲染 <Routes>：要断言"点了按钮真的跳走"必须自己给目标路由
    renderWithProviders(
      <Routes>
        <Route path="/developer/billing" element={<Billing />} />
        <Route path="/user" element={<div>USER_UPGRADE_STUB</div>} />
      </Routes>,
      { route: '/developer/billing' }
    )

    // 引导条（message + description 两段文案都在）
    expect(await screen.findByText('升级为开发者，解锁更多功能')).toBeInTheDocument()
    expect(
      screen.getByText('成为开发者后，您可以查看完整的消费统计、充值账户、管理账单等功能。')
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '前往升级' }))
    expect(await screen.findByText('USER_UPGRADE_STUB')).toBeInTheDocument()
  })

  it('TC-FE-BILLING-006: 消费分布按 by_repository 渲染；无数据为空态、有数据则不再显示空态', async () => {
    // ① 无 by_repository（或为空）→ 「暂无消费数据」
    vi.mocked(billingApi.getMonthlySummary).mockResolvedValue({
      total_recharge: 0,
      total_consumption: 0,
      consumption_count: 0,
      by_repository: [],
    } as never)
    const first = renderWithProviders(<Billing />, { route: '/developer/billing' })
    expect(await screen.findByText('暂无消费数据')).toBeInTheDocument()
    // 此时余额图同样是空态（两条空态并存、互不干扰）
    expect(screen.getByText('暂无余额变化记录')).toBeInTheDocument()
    first.unmount()

    // ② 有 by_repository → 渲染图表容器（recharts ResponsiveContainer），空态消失
    //    ⚠️ 必须**重新**给出带 by_repository 的 mock：① 已把实现改成空数据，
    //       mockResolvedValue 会一直生效（首跑漏了这一步 → ② 拿到的仍是空 summary）
    vi.mocked(billingApi.getMonthlySummary).mockResolvedValue(monthlySummary as never)
    const second = renderWithProviders(<Billing />, { route: '/developer/billing' })
    await waitFor(() => expect(screen.queryByText('暂无消费数据')).not.toBeInTheDocument())
    // 余额图为空态（未渲染图表）→ 页面上**恰有 1 个**图表容器，即消费分布那张
    expect(second.container.querySelectorAll('.recharts-responsive-container').length).toBe(1)
  })
})

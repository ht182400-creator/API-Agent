/**
 * 对账管理页（admin/Reconciliation.tsx）测试 —— 用例库 FE-ADMIN-RECON
 *
 * 为什么值得测：对账是**金额与差异必须精确**的场景，且本页有几处"错了就很难发现"的逻辑：
 *   ① 状态是**前端映射**（`STATUS_NAMES`）后再展示，映射错会把"有差异"显示成"已完成"；
 *   ② `getReconciliationResult` 的 **404 被特判为"该日无对账记录"**（不进统一错误弹窗），
 *      只有其它错误码才走 `showError` —— 这条分类逻辑一旦改错，普通"没对过账"会被报成系统故障；
 *   ③ 「执行对账」必须带上**当前查询条件**（日期 + 渠道），否则会拿默认条件去跑真实对账；
 *   ④ 差异记录的**差异金额正负高亮**（正数 `+`/success，负数 danger）与"仅待处理行可操作"。
 *
 * ⚠️ 顺带清掉的三笔"补测才暴露"的债（本页此前零测试渲染）：
 *  - `Card bodyStyle` ×3（antd v5 已废弃）→ `styles={{ body: {...} }}`；
 *  - `import { useAuthStore }` 是**死导入**（全文件无使用；tsconfig 关了 noUnusedLocals 才没暴露）。
 *
 * ⚠️ 本组件用的是 `message.useMessage()`（hook 版）而非静态 `message.success` —— 所以
 *    必须替换 `useMessage` 才能拦到提示（只 mock 静态方法拦不到，这是与其它页的差异点）。
 *
 * 用例编号：TC-FE-RECON-001 ~ TC-FE-RECON-004
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent, within } from '@testing-library/react'
import dayjs from 'dayjs'

const { messageSpies, showErrorSpy } = vi.hoisted(() => ({
  messageSpies: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
  showErrorSpy: vi.fn(),
}))

vi.mock('antd', async (importOriginal) => {
  const actual = await importOriginal<typeof import('antd')>()
  return {
    ...actual,
    // ⚠️ 本页提示走 `message.useMessage()`（hook 版）→ 必须替换 useMessage；
    //    其余 message 能力保留真实实现。
    message: Object.assign({}, actual.message, {
      useMessage: () => [messageSpies, null],
    }),
  }
})

// 统一错误处理：用 spy 替换，才能断言"404 不弹错 / 其它错误才弹"
vi.mock('../../components/ErrorModal', () => ({
  useErrorModal: () => ({ showError: showErrorSpy, ErrorModal: () => null }),
}))

vi.mock('../../api/adminReconciliation', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/adminReconciliation')>()
  return {
    ...actual,
    adminReconciliationApi: {
      getReconciliationResult: vi.fn(),
      executeReconciliation: vi.fn(),
      getDisputes: vi.fn(),
      handleDispute: vi.fn(),
      getHistory: vi.fn(),
      getSchedulerStatus: vi.fn(),
      triggerReconciliation: vi.fn(),
      generateReport: vi.fn(),
      getDownloadUrl: vi.fn(),
      getRechargeRecords: vi.fn(),
      getChannelSummary: vi.fn(),
      getPlatformAccounts: vi.fn(),
      updatePlatformAccount: vi.fn(),
    },
  }
})

import AdminReconciliation from './Reconciliation'
import { adminReconciliationApi } from '../../api/adminReconciliation'
import { renderWithProviders } from '../../test/renderWithProviders'

// ---------------- 测试数据 ----------------

const result = {
  reconciliation_id: 'recon-1',
  reconcile_date: '2026-09-16',
  channel: 'alipay',
  channel_name: '支付宝',
  platform_trade_count: 123,
  platform_trade_amount: 4567.89,
  channel_trade_count: 118,
  channel_trade_amount: 4400,
  match_count: 116,
  match_amount: 4300,
  long_count: 1,
  long_amount: 12.34,
  short_count: 1,
  short_amount: 5,
  amount_diff_count: 3,
  amount_diff_total: 17.34,
  status: 'disputed',
  completed_at: '2026-09-16T01:00:00Z',
}

const disputes = [
  {
    id: 'd1',
    reconciliation_id: 'recon-1',
    dispute_type: 'long',
    dispute_type_name: '长款（平台多）',
    local_order_no: 'LO-1',
    channel_trade_no: 'CH-1',
    local_amount: 100,
    channel_amount: 87.66,
    diff_amount: 12.34,
    reason: '本地多',
    handle_status: 'pending',
    handle_status_name: '待处理',
    created_at: '2026-09-16T01:00:00Z',
  },
  {
    id: 'd2',
    reconciliation_id: 'recon-1',
    dispute_type: 'amount_diff',
    dispute_type_name: '金额差异',
    local_order_no: 'LO-2',
    channel_trade_no: 'CH-2',
    local_amount: 50,
    channel_amount: 55,
    diff_amount: -5,
    reason: '渠道多',
    handle_status: 'resolved',
    handle_status_name: '已解决',
    created_at: '2026-09-16T01:00:00Z',
  },
]

function renderPage() {
  return renderWithProviders(<AdminReconciliation />, { route: '/admin/reconciliation' })
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

/**
 * 按可见文本定位 Select 的 selector。
 * ⚠️ 用 getAllByText 而非 getByText：渠道文案（如「支付宝」）在**结果卡片里也会出现**
 *    （来自后端 channel_name），必须挑出其中真正属于 `.ant-select` 的那个。
 */
function comboOf(visibleText: string): HTMLElement {
  for (const el of screen.getAllByText(visibleText)) {
    const sel = el.closest('.ant-select')
    const selector = sel?.querySelector('.ant-select-selector')
    if (selector) return selector as HTMLElement
  }
  throw new Error(`未找到 Select：${visibleText}`)
}

beforeEach(() => {
  vi.mocked(adminReconciliationApi.getReconciliationResult).mockResolvedValue(result as never)
  vi.mocked(adminReconciliationApi.executeReconciliation).mockResolvedValue({ status: 'completed' } as never)
  vi.mocked(adminReconciliationApi.getDisputes).mockResolvedValue({
    items: disputes,
    pagination: { page: 1, page_size: 10, total: 2, total_pages: 1 },
  } as never)
})

describe('对账结果查询与渲染（TC-FE-RECON-001）', () => {
  it('TC-FE-RECON-001: 首屏按「日期+渠道」查询，状态经前端映射，差异>0 时告警', async () => {
    renderPage()

    // ① 首屏用默认查询条件（今天 + 支付宝）
    await waitFor(() =>
      expect(adminReconciliationApi.getReconciliationResult).toHaveBeenCalledWith({
        date: dayjs().format('YYYY-MM-DD'),
        channel: 'alipay',
      })
    )

    // ② 结果卡片：日期 / 渠道 / 状态（disputed → 「有差异」，而不是后端原样输出）
    // ⚠️ 「支付宝」在页面上出现**两次**：顶栏查询条件的 Select 回显 + 结果卡片里的
    //    channel_name。故必须先定位到卡片再断言（首跑就是直接 getByText 报了 multiple）。
    expect(await screen.findByText('对账结果')).toBeInTheDocument()
    const resultCard = screen.getByText('对账结果').closest('.ant-card')
    expect(resultCard).not.toBeNull()
    expect(within(resultCard as HTMLElement).getByText('2026-09-16')).toBeInTheDocument()
    expect(within(resultCard as HTMLElement).getByText('支付宝')).toBeInTheDocument()
    expect(within(resultCard as HTMLElement).getByText('有差异')).toBeInTheDocument()

    // ③ 四项统计（平台/渠道/匹配/差异）
    expect(screen.getByText('123')).toBeInTheDocument()
    expect(screen.getByText('118')).toBeInTheDocument()
    expect(screen.getByText('116')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()

    // ④ 差异 > 0 → 告警并引导到「差异记录」
    expect(
      screen.getByText('共有 3 笔订单存在金额差异，请前往"差异记录"页面处理。')
    ).toBeInTheDocument()
  })
})

describe('无数据与错误分类（TC-FE-RECON-002）', () => {
  it('TC-FE-RECON-002: 404 视为「该日无对账记录」（不进统一错误弹窗），其它错误才交统一处理', async () => {
    // ① 404 → "暂无数据"引导，且**不**触发统一错误处理
    vi.mocked(adminReconciliationApi.getReconciliationResult).mockRejectedValue(
      Object.assign(new Error('未找到'), { response: { status: 404 } })
    )
    const { unmount } = renderPage()
    expect(await screen.findByText('暂无对账数据')).toBeInTheDocument()
    expect(screen.queryByText('对账结果')).not.toBeInTheDocument()
    expect(showErrorSpy).not.toHaveBeenCalled()
    unmount()

    // ② 非 404（如 500）→ 交给统一错误处理，同时页面仍不白屏
    vi.mocked(adminReconciliationApi.getReconciliationResult).mockRejectedValue(
      Object.assign(new Error('服务器错误'), { response: { status: 500 } })
    )
    renderPage()
    await waitFor(() => expect(showErrorSpy).toHaveBeenCalledTimes(1))
    expect(screen.getByText('暂无对账数据')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /执行对账/ })).toBeInTheDocument()
  })
})

describe('执行对账（TC-FE-RECON-003）', () => {
  it('TC-FE-RECON-003: 以当前查询条件提交，成功后提示并重新拉取结果', async () => {
    renderPage()
    await screen.findByText('对账结果')
    const resultCallsBefore = vi.mocked(adminReconciliationApi.getReconciliationResult).mock.calls
      .length

    // 切渠道为「微信支付」—— 执行时必须带上**新条件**（而不是写死 alipay）
    pick(comboOf('支付宝'), '微信支付')
    fireEvent.click(screen.getByRole('button', { name: /执行对账/ }))

    await waitFor(() =>
      expect(adminReconciliationApi.executeReconciliation).toHaveBeenCalledWith({
        date: dayjs().format('YYYY-MM-DD'),
        channel: 'wechat',
      })
    )
    expect(messageSpies.success).toHaveBeenCalledWith('对账执行成功')

    // 执行成功后必须重新拉取结果（否则页面还是旧数据）
    await waitFor(() =>
      expect(vi.mocked(adminReconciliationApi.getReconciliationResult).mock.calls.length).toBe(
        resultCallsBefore + 1
      )
    )
  })
})

describe('差异记录（TC-FE-RECON-004）', () => {
  it('TC-FE-RECON-004: 按 reconciliation_id 查询；差异金额正负高亮；仅待处理行可操作', async () => {
    renderPage()
    await screen.findByText('对账结果')

    fireEvent.click(screen.getByRole('tab', { name: /差异记录/ }))

    // ① 查询参数：带上当前对账单 id + 分页（未选筛选项传 undefined，不是空串）
    await waitFor(() =>
      expect(adminReconciliationApi.getDisputes).toHaveBeenCalledWith({
        reconciliation_id: 'recon-1',
        dispute_type: undefined,
        handle_status: undefined,
        page: 1,
        page_size: 10,
      })
    )

    // ② 明细渲染：差异类型 Tag / 本地金额
    expect(await screen.findByText('长款（平台多）')).toBeInTheDocument()
    expect(screen.getByText('金额差异')).toBeInTheDocument()
    expect(screen.getByText('¥100.00')).toBeInTheDocument()

    // ③ 差异金额正负高亮：正数带 `+`，负数带 `-`（都用绝对值 toFixed(2)）
    expect(screen.getByText('+12.34')).toBeInTheDocument()
    expect(screen.getByText('-5.00')).toBeInTheDocument()

    // ④ 处理状态经 STATUS_NAMES 映射
    expect(screen.getByText('待处理')).toBeInTheDocument()
    expect(screen.getByText('已解决')).toBeInTheDocument()

    // ⑤ 只有 pending 行给「处理」按钮（resolved 行不给）
    expect(screen.getAllByRole('button', { name: /处\s*理/ })).toHaveLength(1)

    // ⑥ 分页合计
    expect(screen.getByText('共 2 条')).toBeInTheDocument()
  })
})

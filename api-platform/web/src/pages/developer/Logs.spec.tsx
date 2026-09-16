/**
 * 调用日志页（developer/Logs.tsx）测试 —— 用例库 FE-DEV-LOGS
 *
 * 为什么值得测：本页是**排障入口**，三处换算/映射错了会让人看错结论：
 *   ① 状态码 → 颜色与文案（2xx 成功 / 4xx 客户端错误 / 5xx 服务端错误 / 缺省未知）；
 *   ② 响应耗时 → 颜色分档（>2000 / >1000 / >500）；
 *   ③ 筛选参数：**「全部 Keys」必须转成 `undefined`**（不能把字符串 `'all'` 传给后端），
 *      且任一筛选变化都要**重置到第 1 页**（否则会停留在越界页码上看到空列表）。
 *
 * ⚠️ 顺带清掉移动端卡片的 `Card bodyStyle`（antd v5 废弃）。
 *
 * 用例编号：TC-FE-DEVLOGS-001 ~ TC-FE-DEVLOGS-004
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import dayjs from 'dayjs'

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
      getLogs: vi.fn(),
      getKeys: vi.fn(),
      getQuota: vi.fn(),
      getUsageHistory: vi.fn(),
      getTopRepos: vi.fn(),
      createKey: vi.fn(),
      updateKey: vi.fn(),
      deleteKey: vi.fn(),
      disableKey: vi.fn(),
      enableKey: vi.fn(),
      revealKey: vi.fn(),
      getKey: vi.fn(),
      getQuotaOverview: vi.fn(),
      setQuota: vi.fn(),
      getConsumptionTrend: vi.fn(),
    },
  }
})

import DeveloperLogs from './Logs'
import { quotaApi } from '../../api/quota'
import { renderWithProviders } from '../../test/renderWithProviders'

// ---------------- 测试数据 ----------------

const LONG_ENDPOINT = '/v1/very/long/endpoint/that/needs/truncation'
const LONG_REQUEST_ID = 'req-abcdefghijklmnopqrstu'

const logs = [
  {
    id: 'l1',
    request_id: LONG_REQUEST_ID,
    api_key_id: 'k1',
    repo_id: 'r1',
    repo_name: '天气服务',
    endpoint: '/v1/chat/completions',
    method: 'POST',
    response_status: 200,
    response_time: 320,
    ip_address: '10.0.0.1',
    created_at: '2026-09-16T02:30:00Z',
  },
  {
    id: 'l2',
    request_id: null, // 无 request_id → 请求ID 列降级显示记录 id
    api_key_id: 'k1',
    repo_id: 'r2',
    repo_name: '', // 空仓库名 → 显示「未知」
    endpoint: LONG_ENDPOINT, // 超 30 字符 → 截断
    method: 'GET',
    response_status: 404,
    response_time: 1500,
    ip_address: '',
    created_at: '2026-09-16T03:00:00Z',
  },
]

const keys = [
  { id: 'k1', key_name: '生产应用', key_prefix: 'sk-live-abc', status: 'active', auth_type: 'api_key', rate_limit_rpm: 1, rate_limit_rph: 1, daily_quota: null, monthly_quota: null, api_key: '', created_at: '2026-09-10T00:00:00Z' },
]

const logResponse = (items: unknown[], total = items.length) => ({
  items,
  pagination: { page: 1, page_size: 20, total, total_pages: 1 },
})

function renderPage() {
  return renderWithProviders(<DeveloperLogs />, { route: '/developer/logs' })
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
 * 按可见文本定位 Select。
 * ⚠️ 必须用 getAllByText：选中后**下拉弹层仍在 DOM 里**，选项文本与选中值同名（如「生产应用」），
 *    getByText 会报多元素 —— 只挑真正属于 `.ant-select` 的那个。
 */
function comboOf(visibleText: string): HTMLElement {
  for (const el of screen.getAllByText(visibleText)) {
    const selector = el.closest('.ant-select')?.querySelector('.ant-select-selector')
    if (selector) return selector as HTMLElement
  }
  throw new Error(`未找到 Select：${visibleText}`)
}

/** 去掉所有空白后的 body 文本（用于断言被拆成多个文本节点的组合文案） */
function flatText(): string {
  return (document.body.textContent || '').replace(/\s/g, '')
}

beforeEach(() => {
  vi.mocked(quotaApi.getLogs).mockResolvedValue(logResponse(logs) as never)
  vi.mocked(quotaApi.getKeys).mockResolvedValue({
    items: keys,
    pagination: { page: 1, page_size: 100, total: 1, total_pages: 1 },
  } as never)
})

describe('默认查询与列表派生文案（TC-FE-DEVLOGS-001）', () => {
  it('TC-FE-DEVLOGS-001: 默认分页参数正确；列表字段按规则渲染（含截断与降级）', async () => {
    renderPage()

    // ① 默认查询：page 1 / page_size 20，其余筛选为空
    await waitFor(() =>
      expect(quotaApi.getLogs).toHaveBeenCalledWith({
        page: 1,
        page_size: 20,
        key_id: undefined,
        repo_id: undefined,
        start_date: undefined,
        end_date: undefined,
      })
    )

    // ② 仓库：空值降级为「未知」
    expect(await screen.findByText('天气服务')).toBeInTheDocument()
    expect(screen.getByText('未知')).toBeInTheDocument()

    // ③ 接口：超 30 字符才截断加省略号
    expect(screen.getByText('/v1/chat/completions')).toBeInTheDocument()
    expect(screen.getByText(LONG_ENDPOINT.substring(0, 30) + '...')).toBeInTheDocument()

    // ④ 方法 Tag 原样展示
    expect(screen.getByText('POST')).toBeInTheDocument()
    expect(screen.getByText('GET')).toBeInTheDocument()

    // ⑤ 状态/耗时文案
    expect(screen.getByText('200 成功')).toBeInTheDocument()
    expect(screen.getByText('404 客户端错误')).toBeInTheDocument()
    expect(screen.getByText('320ms')).toBeInTheDocument()

    // ⑥ IP 空值降级为 '-'
    expect(screen.getByText('10.0.0.1')).toBeInTheDocument()
    expect(screen.getAllByText('-').length).toBeGreaterThan(0)

    // ⑦ 请求ID：有则截断 16 位；无则降级用记录 id
    expect(screen.getByText(LONG_REQUEST_ID.substring(0, 16) + '...')).toBeInTheDocument()
    expect(screen.getByText('l2...')).toBeInTheDocument()

    // ⑧ 时间列（MM-DD HH:mm:ss）
    expect(
      screen.getByText(dayjs(logs[0].created_at).format('MM-DD HH:mm:ss'))
    ).toBeInTheDocument()

    // ⑨ 合计文案（被拆成多个节点 → 用去空白后的全文断言）
    expect(flatText()).toContain('共2条记录')
    expect(screen.getByText('共 2 条')).toBeInTheDocument()
  })
})

describe('状态码与响应耗时分档（TC-FE-DEVLOGS-002）', () => {
  const rows = [
    { status: 201, time: 100, statusText: '201 成功', timeText: '100ms' },
    { status: 403, time: 600, statusText: '403 客户端错误', timeText: '600ms' },
    { status: 503, time: 1200, statusText: '503 服务端错误', timeText: '1200ms' },
    { status: 500, time: 2500, statusText: '500 服务端错误', timeText: '2500ms' },
    { status: 0, time: 0, statusText: '未知', timeText: '-' }, // falsy → 视为缺省
  ]

  it('TC-FE-DEVLOGS-002: 2xx/4xx/5xx 与缺省各有对应文案；耗时按 0.5s/1s/2s 分档', async () => {
    vi.mocked(quotaApi.getLogs).mockResolvedValue(
      logResponse(
        rows.map((r, i) => ({
          id: `s${i}`,
          request_id: `req-${i}`,
          api_key_id: 'k1',
          repo_id: 'r1',
          repo_name: '天气服务',
          endpoint: '/v1/models',
          method: 'GET',
          response_status: r.status,
          response_time: r.time,
          ip_address: '10.0.0.1',
          created_at: '2026-09-16T02:30:00Z',
        }))
      ) as never
    )
    renderPage()

    await waitFor(() => expect(quotaApi.getLogs).toHaveBeenCalled())
    for (const r of rows) {
      expect(await screen.findByText(r.statusText), `状态 ${r.status} 的文案`).toBeInTheDocument()
      expect(screen.getByText(r.timeText), `耗时 ${r.time} 的文案`).toBeInTheDocument()
    }
  })
})

describe('筛选参数传递（TC-FE-DEVLOGS-003）', () => {
  it('TC-FE-DEVLOGS-003: 选 Key 传 key_id；「全部 Keys」传 undefined；日期传区间；清除筛选复原', async () => {
    renderPage()
    await waitFor(() => expect(quotaApi.getLogs).toHaveBeenCalled())

    // ① 选定某个 Key → 以 key_id 查询
    pick(comboOf('选择API Key'), '生产应用')
    await waitFor(() =>
      expect(quotaApi.getLogs).toHaveBeenLastCalledWith(
        expect.objectContaining({ key_id: 'k1', page: 1 })
      )
    )

    // ② 选「全部 Keys」→ 必须传 undefined（**不能**把字符串 'all' 发给后端）
    pick(comboOf('生产应用'), '全部 Keys')
    await waitFor(() =>
      expect(quotaApi.getLogs).toHaveBeenLastCalledWith(
        expect.objectContaining({ key_id: undefined, page: 1 })
      )
    )

    // ③ 日期区间 → start_date / end_date（RangePicker 需真实键盘输入）
    const [startInput, endInput] = screen.getAllByPlaceholderText(/开始日期|结束日期/)
    const user = userEvent.setup()
    await user.click(startInput)
    await user.type(startInput, '2026-09-01')
    await user.keyboard('{Enter}')
    await user.type(endInput, '2026-09-30')
    await user.keyboard('{Enter}')

    await waitFor(() =>
      expect(quotaApi.getLogs).toHaveBeenLastCalledWith(
        expect.objectContaining({
          start_date: '2026-09-01',
          end_date: '2026-09-30',
          page: 1,
        })
      )
    )

    // ④ 清除筛选 → 全部复原为 undefined
    fireEvent.click(screen.getByRole('button', { name: /清除筛选/ }))
    await waitFor(() =>
      expect(quotaApi.getLogs).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 20,
        key_id: undefined,
        repo_id: undefined,
        start_date: undefined,
        end_date: undefined,
      })
    )
  })
})

describe('分页与空态（TC-FE-DEVLOGS-004）', () => {
  it('TC-FE-DEVLOGS-004: 切换每页条数带新 page_size 重查；无数据时给引导文案', async () => {
    // ① 分页切换
    const { unmount } = renderPage()
    await waitFor(() => expect(quotaApi.getLogs).toHaveBeenCalled())
    pick(comboOf('20 条/页'), '50 条/页')
    await waitFor(() =>
      expect(quotaApi.getLogs).toHaveBeenLastCalledWith(
        expect.objectContaining({ page: 1, page_size: 50 })
      )
    )
    unmount()

    // ② 空态（total=0）
    vi.mocked(quotaApi.getLogs).mockResolvedValue(logResponse([], 0) as never)
    renderPage()
    expect(await screen.findByText('暂无调用日志')).toBeInTheDocument()
    expect(screen.getByText('开始使用API后将自动记录调用日志')).toBeInTheDocument()
  })
})

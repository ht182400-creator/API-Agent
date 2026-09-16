/**
 * 仓库详情页（developer/RepoDetail.tsx）测试 —— 用例库 FE-DEV-REPODETAIL
 *
 * 为什么值得测：本页是**接入方看的第一手资料**（限流、价格、端点、调用示例），
 * 展示错了会直接导致接入方按错误的价格/限制调用：
 *   ① 统计与限流配置在 `limits` 缺失时**回退 1000 / 10000 / 100000**；
 *   ② 定价的**计费模式映射**与**精度**（每次调用 4 位小数、每 Token 6 位小数）；
 *   ③ 端点表的空值降级（描述/分类为空显示 `-`）与「无端点」空态；
 *   ④ 单端点时调用指南**自动展开**（`defaultActiveKey`），多端点时折叠；
 *   ⑤ 仓库不存在（后端返回空 / 请求失败）都要给**友好提示**而不是白屏。
 *
 * ⚠️ 本页用 `useParams`，测试必须挂到带 `:slug` 的 Route 上（renderWithProviders 默认不渲染 Routes）。
 *
 * 用例编号：TC-FE-REPODETAIL-001 ~ TC-FE-REPODETAIL-005
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'

vi.mock('../../api/repo', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/repo')>()
  return { ...actual, repoApi: { ...actual.repoApi, get: vi.fn() } }
})

import RepoDetail from './RepoDetail'
import { repoApi } from '../../api/repo'
import { renderWithProviders } from '../../test/renderWithProviders'

// ---------------- 测试数据 ----------------

const repo = {
  id: 'r1',
  name: 'weather-api',
  slug: 'weather-api',
  display_name: '天气查询API',
  description: '提供天气查询与预报服务',
  type: 'ai',
  protocol: 'http',
  status: 'online',
  logo_url: null,
  docs_url: 'https://docs.example.com',
  limits: {
    rpm: 500,
    rph: 5000,
    daily: 50000,
    burst_limit: 20,
    concurrent_limit: 10,
    request_timeout: 30,
  },
  pricing: { type: 'per_call', price_per_call: 0.0234, free_calls: 100 },
  sla: { uptime: '99.9%', latency_p99: 800 },
  endpoints: [
    { method: 'POST', path: '/v1/chat/completions', description: '对话补全', category: 'chat' },
    { method: 'GET', path: '/v1/models', description: '', category: '' },
  ],
  owner: { name: '平台运营' },
  created_at: '2026-09-01T00:00:00Z',
}

function renderPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/developer/repos/:slug" element={<RepoDetail />} />
    </Routes>,
    { route: '/developer/repos/weather-api' }
  )
}

function flatText(): string {
  return (document.body.textContent || '').replace(/\s/g, '')
}

beforeEach(() => {
  vi.mocked(repoApi.get).mockResolvedValue(repo as never)
})

describe('基本信息与 SLA（TC-FE-REPODETAIL-001）', () => {
  it('TC-FE-REPODETAIL-001: 面包屑/标题/状态/协议/文档入口/描述/SLA 均按数据渲染', async () => {
    renderPage()

    // 以 slug 拉取
    await waitFor(() => expect(repoApi.get).toHaveBeenCalledWith('weather-api'))

    // 面包屑 + 标题
    expect(await screen.findByText('仓库市场')).toBeInTheDocument()
    expect(screen.getAllByText('天气查询API').length).toBeGreaterThan(0)
    // 状态与协议（⚠️ 协议在页头与「仓库信息」Descriptions 各出现一次 → 用 getAllByText）
    expect(screen.getByText('已上线')).toBeInTheDocument()
    expect(screen.getAllByText('HTTP').length).toBeGreaterThanOrEqual(1)
    // 文档入口（有 docs_url 才出现）
    const docs = screen.getByRole('link', { name: /查看API文档/ })
    expect(docs).toHaveAttribute('href', 'https://docs.example.com')
    // 描述
    expect(screen.getByText('提供天气查询与预报服务')).toBeInTheDocument()
    // SLA：可用性 + P99
    expect(screen.getByText('可用性 99.9%')).toBeInTheDocument()
    expect(screen.getByText('P99延迟 800ms')).toBeInTheDocument()
  })
})

describe('统计 / 限流 / 定价（TC-FE-REPODETAIL-002）', () => {
  it('TC-FE-REPODETAIL-002: limits 存在时用真实值；缺失时回退 1000/10000/100000', async () => {
    // ① 有 limits → 用真实值 + 出现可选行（突发/并发/超时）
    const first = renderPage()
    await screen.findByText('限流配置')
    expect(screen.getByText('突发限制')).toBeInTheDocument()
    expect(screen.getByText('并发限制')).toBeInTheDocument()
    expect(screen.getByText('请求超时')).toBeInTheDocument()
    expect(flatText()).toContain('50000')
    first.unmount()

    // ② 无 limits → 三处回退到默认值，可选行为不渲染
    vi.mocked(repoApi.get).mockResolvedValue({ ...repo, limits: undefined } as never)
    renderPage()
    await screen.findByText('限流配置')
    const text = flatText()
    expect(text).toContain('1000')
    expect(text).toContain('10000')
    expect(text).toContain('100000')
    expect(screen.queryByText('突发限制')).toBeNull()
    expect(screen.queryByText('并发限制')).toBeNull()
    expect(screen.queryByText('请求超时')).toBeNull()
  })

  it('TC-FE-REPODETAIL-003: 定价计费模式映射与金额精度（每次调用 4 位小数）+ 免费额度', async () => {
    renderPage()
    await screen.findByText('定价信息')

    expect(screen.getByText('按次计费')).toBeInTheDocument()
    // 精度：price_per_call.toFixed(4)
    expect(screen.getByText('¥0.0234')).toBeInTheDocument()
    // 免费额度
    expect(flatText()).toContain('100次')
    // 未提供的字段不渲染
    expect(screen.queryByText('每Token')).toBeNull()
    expect(screen.queryByText('月订阅')).toBeNull()
  })
})

describe('端点列表与调用指南（TC-FE-REPODETAIL-004）', () => {
  it('TC-FE-REPODETAIL-004: 端点表空值降级为 -；无端点给空态；单端点时指南自动展开', async () => {
    // ① 两个端点：描述/分类为空的降级为 '-'
    const first = renderPage()
    await screen.findByText('API端点列表')
    // ⚠️ 端点路径在**端点表格**与**调用指南的折叠标题**各出现一次 → getAllByText
    expect(screen.getAllByText('/v1/chat/completions').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('/v1/models').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('对话补全')).toBeInTheDocument()
    expect(screen.getByText('chat')).toBeInTheDocument()
    // 空描述 + 空分类 → 至少两个 '-'
    expect(screen.getAllByText('-').length).toBeGreaterThanOrEqual(2)
    // 调用指南（多端点 → 折叠，仅标题可见）
    expect(screen.getByText('API调用指南')).toBeInTheDocument()
    first.unmount()

    // ② 单个端点 → defaultActiveKey=['0'] 自动展开，露出调用地址/请求头/两种示例
    vi.mocked(repoApi.get).mockResolvedValue({
      ...repo,
      endpoints: [repo.endpoints[0]],
    } as never)
    const second = renderPage()
    await screen.findByText('API端点列表')
    expect(await screen.findByText('调用地址')).toBeInTheDocument()
    expect(screen.getByText('请求方式')).toBeInTheDocument()
    expect(screen.getByText('请求头 (Headers)')).toBeInTheDocument()
    expect(screen.getByText('Curl 示例')).toBeInTheDocument()
    expect(screen.getByText('JavaScript 示例')).toBeInTheDocument()
    second.unmount()

    // ③ 没有端点 → 空态
    vi.mocked(repoApi.get).mockResolvedValue({ ...repo, endpoints: [] } as never)
    renderPage()
    expect(await screen.findByText('暂无API端点信息')).toBeInTheDocument()
  })
})

describe('仓库不存在（TC-FE-REPODETAIL-005）', () => {
  it('TC-FE-REPODETAIL-005: 后端返回空或请求失败都给友好提示，不白屏', async () => {
    // ① 返回 null
    vi.mocked(repoApi.get).mockResolvedValue(null as never)
    const first = renderPage()
    expect(await screen.findByText('仓库不存在')).toBeInTheDocument()
    expect(screen.getByText('无法找到该仓库，请检查URL是否正确')).toBeInTheDocument()
    first.unmount()

    // ② 请求失败（交统一错误处理后同样落到友好提示）
    vi.mocked(repoApi.get).mockRejectedValue(new Error('网络连接失败'))
    renderPage()
    expect(await screen.findByText('仓库不存在')).toBeInTheDocument()
  })
})

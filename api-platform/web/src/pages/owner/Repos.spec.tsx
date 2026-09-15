/**
 * 仓库管理页（owner/Repos.tsx，1059 行）测试
 *
 * 为什么优先测它（P1，且是 P1-4 的拆分目标之一）：
 *   1. **图标上传的三个分支** —— 类型校验（非图片拒绝）、**大小边界（200KB）**、
 *      FileReader → base64 回填表单。这类"边界判断"写错时页面一切正常，
 *      只是悄悄上传了不该上传的东西或拦下了合法请求。
 *   2. **编辑时的配置加载** —— `loadRepoConfig` 并行取端点与限流；
 *      取失败时会**静默回落到默认限流值**（rpm 1000 等）→ 若回落的默认值比真实值宽松，
 *      保存时会把用户原本更严格的限流"放大"，这是最容易伤到线上的一种回归。
 *   3. 删除走 Popconfirm，点了"删除"但没点"确认"不得发请求。
 *
 * 用例编号：TC-FE-OREPO-001 ~ TC-FE-OREPO-008
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'

const mocks = vi.hoisted(() => ({
  showError: vi.fn(),
  showSuccess: vi.fn(),
}))

vi.mock('../../api/repo', () => ({
  repoApi: {
    getMyRepos: vi.fn(),
    get: vi.fn(),
    delete: vi.fn(),
    activate: vi.fn(),
    deactivate: vi.fn(),
    create: vi.fn(),
    updateConfig: vi.fn(),
    getEndpoints: vi.fn(),
    getLimits: vi.fn(),
    createEndpoint: vi.fn(),
    updateEndpoint: vi.fn(),
    deleteEndpoint: vi.fn(),
    updateLimits: vi.fn(),
  },
}))

// 保留 ErrorContext 的其它导出（Provider 等），只替换 useError 便于断言
vi.mock('../../contexts/ErrorContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../contexts/ErrorContext')>()
  return {
    ...actual,
    useError: () => ({ showError: mocks.showError, showSuccess: mocks.showSuccess }),
  }
})

import OwnerRepos from './Repos'
import { repoApi } from '../../api/repo'
import { useAuthStore } from '../../stores/auth'
import { renderWithProviders } from '../../test/renderWithProviders'

const repoList = [
  {
    id: 'r1',
    name: 'weather-api',
    display_name: '天气 API',
    slug: 'weather-api',
    status: 'online',
    description: '天气查询',
    created_at: '2026-09-01T00:00:00Z',
    // ⚠️ 补全 method/path：此前只有 id，导致详情抽屉的 rowKey 退化成 "undefined-undefined"（重复 key 告警）
    endpoints: [
      { id: 'e1', method: 'GET', path: '/current' },
      { id: 'e2', method: 'POST', path: '/forecast' },
    ],
  },
  {
    id: 'r2',
    name: 'trans-api',
    display_name: '翻译 API',
    slug: 'trans-api',
    status: 'pending',
    description: '多语言翻译',
    created_at: '2026-09-02T00:00:00Z',
    endpoints: [],
  },
]

/** 打开「创建/编辑」弹窗（含图标上传控件） */
function openCreateModal(): void {
  fireEvent.click(screen.getByRole('button', { name: /创建仓库/ }))
}

/** 取弹窗里 file input（antd Upload 内部渲染） */
function getFileInput(): HTMLInputElement {
  const input = document.querySelector('input[type="file"]')
  if (!input) throw new Error('未找到 Upload 的 file input')
  return input as HTMLInputElement
}

beforeEach(() => {
  vi.mocked(repoApi.getMyRepos).mockResolvedValue({
    items: repoList,
    pagination: { page: 1, page_size: 10, total: 2, total_pages: 1 },
  } as never)
  vi.mocked(repoApi.get).mockResolvedValue(repoList[0] as never)
  vi.mocked(repoApi.delete).mockResolvedValue({} as never)
  vi.mocked(repoApi.activate).mockResolvedValue({} as never)
  vi.mocked(repoApi.deactivate).mockResolvedValue({} as never)
  vi.mocked(repoApi.getEndpoints).mockResolvedValue([{ id: 'e1', method: 'GET', path: '/a' }] as never)
  vi.mocked(repoApi.getLimits).mockResolvedValue({
    rpm: 50,
    rph: 500,
    rpd: 5000,
    burst_limit: 10,
    concurrent_limit: 3,
    request_timeout: 15,
    connect_timeout: 5,
  } as never)

  useAuthStore.setState({
    user: {
      id: 'u1',
      email: 'owner@example.com',
      user_type: 'developer',
      role: 'developer',
      permissions: [],
      user_status: 'active',
      email_verified: true,
      vip_level: 0,
      created_at: '2026-01-01T00:00:00Z',
    },
    accessToken: 'tok',
    refreshToken: 'rt',
    isAuthenticated: true,
  })
})

describe('列表与统计', () => {
  it('TC-FE-OREPO-001: 首屏按分页参数加载我的仓库并渲染统计', async () => {
    renderWithProviders(<OwnerRepos />, { route: '/developer/repos' })

    await waitFor(() =>
      expect(repoApi.getMyRepos).toHaveBeenCalledWith({ page: 1, page_size: 10 })
    )

    expect(await screen.findByText('天气 API')).toBeInTheDocument()
    expect(screen.getByText('仓库管理')).toBeInTheDocument()
    // 统计卡片
    expect(screen.getByText('我的仓库')).toBeInTheDocument()
    expect(screen.getByText('已上线仓库')).toBeInTheDocument()
    expect(screen.getByText('API端点总数')).toBeInTheDocument()
  })

  it('TC-FE-OREPO-008: 列表加载失败时不白屏（走 showError 而非崩溃）', async () => {
    vi.mocked(repoApi.getMyRepos).mockRejectedValue(new Error('网络错误'))

    renderWithProviders(<OwnerRepos />, { route: '/developer/repos' })

    await waitFor(() => expect(mocks.showError).toHaveBeenCalled())
    // 页面骨架仍在
    expect(screen.getByText('仓库管理')).toBeInTheDocument()
    expect(screen.getByText('管理您的API仓库，配置端点和限流策略')).toBeInTheDocument()
  })
})

describe('仓库操作', () => {
  it('TC-FE-OREPO-002: 删除需经 Popconfirm 确认，确认后调用 delete 并刷新', async () => {
    renderWithProviders(<OwnerRepos />, { route: '/developer/repos' })
    await screen.findByText('天气 API')

    const listCallsBefore = vi.mocked(repoApi.getMyRepos).mock.calls.length

    // 点第一个「删除」→ 只弹出确认框，此时不应发请求
    fireEvent.click(screen.getAllByRole('button', { name: /删除/ })[0])
    expect(await screen.findByText('确认删除？')).toBeInTheDocument()
    expect(repoApi.delete).not.toHaveBeenCalled()

    // 确认
    // ⚠️ Popconfirm 的确认按钮文案由 antd locale 决定（本页桌面版未传 okText，
    //    项目也未全局配置中文 locale → 实测是 "OK"）→ 不写死文本，直接取弹层内的主按钮。
    const confirmBtn = document.querySelector('.ant-popconfirm-buttons .ant-btn-primary')
    if (!confirmBtn) throw new Error('未找到 Popconfirm 确认按钮')
    fireEvent.click(confirmBtn)

    await waitFor(() => expect(repoApi.delete).toHaveBeenCalledWith('r1'))
    await waitFor(() =>
      expect(vi.mocked(repoApi.getMyRepos).mock.calls.length).toBeGreaterThan(listCallsBefore)
    )
  })

  it('TC-FE-OREPO-003: 编辑时并行加载端点与限流配置', async () => {
    renderWithProviders(<OwnerRepos />, { route: '/developer/repos' })
    await screen.findByText('天气 API')

    fireEvent.click(screen.getAllByRole('button', { name: /编辑/ })[0])

    await waitFor(() => expect(repoApi.getEndpoints).toHaveBeenCalledWith('r1'))
    expect(repoApi.getLimits).toHaveBeenCalledWith('r1')
    // 弹窗打开（标题）；注意真实文案是「编辑仓库配置」
    expect(await screen.findByText('编辑仓库配置')).toBeInTheDocument()
  })

  /**
   * 详情抽屉的限流展示（此前**完全没有用例覆盖**）。
   *
   * ⚠️ 字段名很容易搞错，务必以**后端真实响应**为准：
   *    - 详情（读）：字段名是 **`daily`** —— 见后端
   *      `src/api/v1/repositories/catalog.py` / `config.py`：`daily=limits_data.rpd or 100000`
   *      即后端把存储的 `rpd` **映射成**响应里的 `daily`。
   *    - 保存（写）：字段名是 **`rpd`**（`UpdateLimitsRequest`）。
   *
   * 也就是说：**读写字段不对称**（前端这里读 `daily` 是对的）。
   * 我曾一度按 `rpd` 造 mock，结果抽屉显示兜底值 100000 —— 是 mock 与真实响应不符，
   * 不是前端缺陷。本用例用**真实形态**（daily=5000）锁住"显示真实限额而非兜底值"。
   */
  it('TC-FE-OREPO-009: 详情抽屉「每日请求 (RPD)」显示真实限额，而非兜底值', async () => {
    // 按后端真实响应形态：daily=5000（rph 另设以免与 rpd 数值混淆）
    vi.mocked(repoApi.get).mockResolvedValue({
      ...repoList[0],
      limits: { rpm: 500, rph: 6000, daily: 5000, burst_limit: 20, concurrent_limit: 5 },
    } as never)

    renderWithProviders(<OwnerRepos />, { route: '/developer/repos' })
    await screen.findByText('天气 API')

    fireEvent.click(screen.getAllByRole('button', { name: /详情/ })[0])
    await waitFor(() => expect(repoApi.get).toHaveBeenCalled())

    // 抽屉打开后：应能看到真实值 5000
    expect(await screen.findByText('每日请求 (RPD)')).toBeInTheDocument()
    expect(screen.getByText('5000')).toBeInTheDocument()
    // 且**不得**退化成兜底值 100000
    expect(screen.queryByText('100000')).not.toBeInTheDocument()
  })

  it('TC-FE-OREPO-004: 详情用 slug 拉取仓库详情', async () => {
    renderWithProviders(<OwnerRepos />, { route: '/developer/repos' })
    await screen.findByText('天气 API')

    fireEvent.click(screen.getAllByRole('button', { name: /详情/ })[0])

    // ⚠️ 注意传的是 slug（weather-api），不是 id（r1）—— 这是本页的真实行为，
    //    后端按 slug 取仓库；若误改成 id 会拿到 404。
    await waitFor(() => expect(repoApi.get).toHaveBeenCalledWith('weather-api'))
  })
})

describe('图标上传的三种分支', () => {
  it('TC-FE-OREPO-005: 非图片文件被拒绝（不进入预览态）', async () => {
    renderWithProviders(<OwnerRepos />, { route: '/developer/repos' })
    await screen.findByText('天气 API')
    openCreateModal()

    const input = getFileInput()
    const txt = new File(['hello'], 'a.txt', { type: 'text/plain' })
    fireEvent.change(input, { target: { files: [txt] } })

    // 仍处于"未上传"态（显示默认提示），且未进入"可重新上传"态
    await waitFor(() =>
      expect(screen.getByText('建议 64x64 像素，不超过 200KB')).toBeInTheDocument()
    )
    expect(screen.queryByText('点击删除按钮可重新上传')).not.toBeInTheDocument()
  })

  it('TC-FE-OREPO-006: 超过 200KB 的图片被拒绝（边界判定）', async () => {
    renderWithProviders(<OwnerRepos />, { route: '/developer/repos' })
    await screen.findByText('天气 API')
    openCreateModal()

    const input = getFileInput()
    // 代码判定为 `size / 1024 < 200` → 恰好 200KB 即被拒绝
    const big = new File([new Uint8Array(200 * 1024)], 'big.png', { type: 'image/png' })
    fireEvent.change(input, { target: { files: [big] } })

    await waitFor(() =>
      expect(screen.getByText('建议 64x64 像素，不超过 200KB')).toBeInTheDocument()
    )
    expect(screen.queryByText('点击删除按钮可重新上传')).not.toBeInTheDocument()
  })

  it('TC-FE-OREPO-007: 合法图片经 FileReader 转 base64 后进入预览态', async () => {
    renderWithProviders(<OwnerRepos />, { route: '/developer/repos' })
    await screen.findByText('天气 API')
    openCreateModal()

    const input = getFileInput()
    const img = new File(['content'], 'logo.png', { type: 'image/png' })
    fireEvent.change(input, { target: { files: [img] } })

    // FileReader.onload 是异步的 → 等待预览态切换
    await waitFor(() =>
      expect(screen.getByText('点击删除按钮可重新上传')).toBeInTheDocument()
    )
  })
})

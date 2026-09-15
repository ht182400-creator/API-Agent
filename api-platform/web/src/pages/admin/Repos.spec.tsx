/**
 * 管理员仓库管理页（admin/Repos.tsx）测试
 *
 * 为什么优先测它（P1）：
 *   这是**审核与上下线**的操作台 —— 通过/拒绝/上线/下线直接决定一个仓库能否对外提供服务，
 *   点错一次影响的是别人的业务。而这类缺陷"不白屏、不报错"，只是把状态改错了，
 *   页面测试是拦住它的第一道防线。
 *
 * 实现特点（决定测试手法）：
 *   - 列表来自 `repoApi.adminList`；"我的仓库"另走 `getMyRepos` + 逐仓库 `getStats`；
 *   - ⚠️ `loadStats()` 会**循环 5 个状态**各发一次 `adminList({page_size: 1})`，
 *     而每次操作成功后又会 `loadRepos() + loadStats()` → 一次操作触发 6 个请求。
 *     测试里用 `page_size === 1` 区分"统计探测"与"列表查询"，避免相互污染。
 *
 * 用例编号：TC-FE-AREPO-001 ~ TC-FE-AREPO-008
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'

vi.mock('../../api/repo', () => ({
  repoApi: {
    adminList: vi.fn(),
    getMyRepos: vi.fn(),
    getStats: vi.fn(),
    adminApprove: vi.fn(),
    adminReject: vi.fn(),
    adminOnline: vi.fn(),
    adminOffline: vi.fn(),
    delete: vi.fn(),
  },
}))

import AdminRepos from './Repos'
import { repoApi } from '../../api/repo'
import { useAuthStore } from '../../stores/auth'
import { renderWithProviders } from '../../test/renderWithProviders'

/**
 * 点击表格行内的操作按钮。
 *
 * ⚠️ 不能用 `getByRole('button', { name: /^通过$/ })`：antd 带图标的 Button 会把图标
 *    的 `aria-label`（如 "check-circle"）并入**可访问名**，锚定正则匹配不到（实测踩过）。
 *    改为"按可见文本定位，再取其最近的 button"，语义更贴近用户操作。
 */
function clickRowButton(text: string): void {
  const btn = screen.getByText(text).closest('button')
  if (!btn) throw new Error(`未找到按钮：${text}`)
  fireEvent.click(btn)
}

/** 两条不同状态的仓库：pending 可「通过/拒绝」，approved 可「上线」 */
const repoList = [
  {
    id: 'r1',
    name: '天气服务',
    display_name: '天气服务',
    slug: 'weather',
    status: 'pending',
    description: '天气查询',
    created_at: '2026-09-01T00:00:00Z',
  },
  {
    id: 'r2',
    name: '翻译服务',
    display_name: '翻译服务',
    slug: 'translate',
    status: 'approved',
    description: '多语言翻译',
    created_at: '2026-09-02T00:00:00Z',
  },
]

beforeEach(() => {
  vi.mocked(repoApi.adminList).mockImplementation((async (params: { page_size?: number; status?: string }) => {
    // `page_size: 1` 是 loadStats 的"探测"调用（只关心 total）
    if (params?.page_size === 1) {
      const totals: Record<string, number> = { pending: 1, approved: 1, online: 0, offline: 0, rejected: 4 }
      return {
        items: [],
        pagination: { page: 1, page_size: 1, total: totals[params.status || ''] ?? 0, total_pages: 1 },
      }
    }
    return {
      items: repoList,
      pagination: { page: 1, page_size: 20, total: repoList.length, total_pages: 1 },
    }
  }) as never)

  vi.mocked(repoApi.getMyRepos).mockResolvedValue({
    items: [],
    pagination: { page: 1, page_size: 10, total: 0, total_pages: 0 },
  } as never)
  vi.mocked(repoApi.getStats).mockResolvedValue({ total_calls: 0, total_cost: 0 } as never)
  vi.mocked(repoApi.adminApprove).mockResolvedValue({} as never)
  vi.mocked(repoApi.adminReject).mockResolvedValue({} as never)
  vi.mocked(repoApi.adminOnline).mockResolvedValue({} as never)
  vi.mocked(repoApi.adminOffline).mockResolvedValue({} as never)
  vi.mocked(repoApi.delete).mockResolvedValue({} as never)

  useAuthStore.setState({
    user: {
      id: 'admin1',
      email: 'admin@example.com',
      user_type: 'admin',
      role: 'admin',
      permissions: ['*'],
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

describe('列表加载与渲染', () => {
  it('TC-FE-AREPO-001: 首屏加载列表与各状态统计，渲染页面骨架', async () => {
    renderWithProviders(<AdminRepos />, { route: '/admin/repos' })

    await waitFor(() => expect(repoApi.adminList).toHaveBeenCalled())

    // 列表查询（非统计探测）
    expect(repoApi.adminList).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1, page_size: 20 })
    )
    // 统计探测：5 个状态各一次
    const statCalls = vi.mocked(repoApi.adminList).mock.calls.filter((c) => c[0]?.page_size === 1)
    await waitFor(() => expect(statCalls.length).toBe(5))

    expect(screen.getByText('仓库管理')).toBeInTheDocument()
    expect(screen.getByText('所有仓库')).toBeInTheDocument()
  })

  it('TC-FE-AREPO-002: 渲染仓库行与状态标签', async () => {
    renderWithProviders(<AdminRepos />, { route: '/admin/repos' })

    expect(await screen.findAllByText('天气服务')).not.toHaveLength(0)
    expect(screen.getAllByText('翻译服务').length).toBeGreaterThan(0)
    // 状态标签（pending → 待审核）
    expect(screen.getAllByText('待审核').length).toBeGreaterThan(0)
  })

  it('TC-FE-AREPO-003: 点击状态筛选按钮后带 status 重新查询', async () => {
    renderWithProviders(<AdminRepos />, { route: '/admin/repos' })
    await waitFor(() => expect(repoApi.adminList).toHaveBeenCalled())

    // 筛选按钮文本形如「待审核 (1)」，用正则匹配
    fireEvent.click(screen.getByRole('button', { name: /待审核/ }))

    await waitFor(() => {
      const listCalls = vi.mocked(repoApi.adminList).mock.calls.filter(
        (c) => c[0]?.page_size !== 1
      )
      expect(listCalls.some((c) => c[0]?.status === 'pending')).toBe(true)
    })
  })

  it('TC-FE-AREPO-008: 列表加载失败时不白屏（骨架仍在）', async () => {
    vi.mocked(repoApi.adminList).mockRejectedValue(new Error('后端不可用'))

    renderWithProviders(<AdminRepos />, { route: '/admin/repos' })

    await waitFor(() => expect(repoApi.adminList).toHaveBeenCalled())
    expect(screen.getByText('仓库管理')).toBeInTheDocument()
    expect(screen.getByText('所有仓库')).toBeInTheDocument()
  })
})

describe('审核操作', () => {
  it('TC-FE-AREPO-004: 通过审核 —— 弹窗确认后调用 adminApprove 并带备注', async () => {
    renderWithProviders(<AdminRepos />, { route: '/admin/repos' })
    await screen.findAllByText('天气服务')

    clickRowButton('通过')

    // 弹窗出现
    expect(await screen.findByText('审核通过')).toBeInTheDocument()
    fireEvent.change(screen.getByPlaceholderText('输入审核备注...'), {
      target: { value: '资质齐全，准予上线' },
    })
    fireEvent.click(screen.getByRole('button', { name: '确认通过' }))

    await waitFor(() =>
      expect(repoApi.adminApprove).toHaveBeenCalledWith('r1', { comment: '资质齐全，准予上线' })
    )
  })

  it('TC-FE-AREPO-005: 拒绝审核 —— 弹窗确认后调用 adminReject 并把备注作为原因', async () => {
    renderWithProviders(<AdminRepos />, { route: '/admin/repos' })
    await screen.findAllByText('天气服务')

    clickRowButton('拒绝')

    expect(await screen.findByText('审核拒绝')).toBeInTheDocument()
    fireEvent.change(screen.getByPlaceholderText('输入拒绝原因，以便仓库所有者了解情况...'), {
      target: { value: '接口文档缺失' },
    })
    fireEvent.click(screen.getByRole('button', { name: '确认拒绝' }))

    await waitFor(() =>
      expect(repoApi.adminReject).toHaveBeenCalledWith('r1', { reason: '接口文档缺失' })
    )
  })

  it('TC-FE-AREPO-006: 上线 —— Modal.confirm 确认后调用 adminOnline', async () => {
    renderWithProviders(<AdminRepos />, { route: '/admin/repos' })
    await screen.findAllByText('翻译服务')

    // approved 状态的行才有「上线」按钮
    // ⚠️ 用 getByText（完整匹配）而非 /上线/：否则会命中筛选按钮「已上线 (0)」
    clickRowButton('上线')

    // antd Modal.confirm 的确认按钮文本由代码指定
    fireEvent.click(await screen.findByRole('button', { name: '确认上线' }))

    await waitFor(() => expect(repoApi.adminOnline).toHaveBeenCalledWith('r2'))
  })

  it('TC-FE-AREPO-007: 操作成功后自动刷新列表与统计', async () => {
    renderWithProviders(<AdminRepos />, { route: '/admin/repos' })
    await screen.findAllByText('天气服务')
    await waitFor(() => expect(repoApi.adminList).toHaveBeenCalled())

    const callsBefore = vi.mocked(repoApi.adminList).mock.calls.length

    clickRowButton('通过')
    await screen.findByText('审核通过')
    fireEvent.click(screen.getByRole('button', { name: '确认通过' }))

    await waitFor(() => expect(repoApi.adminApprove).toHaveBeenCalled())
    // 已审核 → 刷新（列表 1 次 + 统计 5 次）
    await waitFor(() =>
      expect(vi.mocked(repoApi.adminList).mock.calls.length).toBeGreaterThan(callsBefore)
    )
  })
})

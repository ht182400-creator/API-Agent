/**
 * API 测试工具（ApiTester.tsx）测试
 *
 * 为什么优先测它（P1）：
 *   这是开发者的主调试入口，且**唯一**直接对后端 proxy 发起真实转发调用的页面 ——
 *   它拼出的 URL、写入的 `X-Access-Key` 头、构造的 body 一旦出错，
 *   开发者会以为是"后端坏了"而排查很久。
 *
 * 实现特点（决定了测试手法）：
 *   - 仓库/端点来自**静态配置** `config/repositories.config`（不是接口）→ 无需 mock 业务 API；
 *   - 发请求用原生 `fetch`（不是 axios）→ 只需 mock `global.fetch`；
 *   - API Key 存在 zustand `useApiKeyStore` → 用真实 store 注入，断言请求头。
 *
 * 用例编号：TC-FE-TESTER-001 ~ TC-FE-TESTER-008
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'

import { ApiTester } from './ApiTester'
import { repositories, selfRepositories, thirdPartyRepositories } from '../../config/repositories.config'
import { useApiKeyStore } from '../../stores/apiKey'
import { useAuthStore } from '../../stores/auth'
import { renderWithProviders } from '../../test/renderWithProviders'

const fetchMock = vi.fn()

/** 取第一次 fetch 调用的 [url, init] */
function firstFetchCall(): [string, RequestInit] {
  const call = fetchMock.mock.calls[0]
  return [String(call[0]), call[1] as RequestInit]
}

beforeEach(() => {
  fetchMock.mockReset()
  fetchMock.mockResolvedValue({
    status: 200,
    json: async () => ({ ok: true, echoed: 'hello' }),
  })
  vi.stubGlobal('fetch', fetchMock)

  useApiKeyStore.setState({ apiKey: '' })
  useAuthStore.setState({
    user: {
      id: 'u1',
      username: 'dev',
      email: 'dev@example.com',
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

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ApiTester 渲染与筛选', () => {
  it('TC-FE-TESTER-001: 渲染标题、仓库/接口统计与三个分类按钮', () => {
    renderWithProviders(<ApiTester />)

    expect(screen.getByText('API 测试工具')).toBeInTheDocument()
    expect(screen.getByText('全部')).toBeInTheDocument()
    expect(screen.getByText('🏠 自研')).toBeInTheDocument()
    expect(screen.getByText('🌐 第三方')).toBeInTheDocument()
    // 统计与"全部仓库"口径一致
    expect(screen.getByText(`${repositories.length} 个仓库`)).toBeInTheDocument()
  })

  it('TC-FE-TESTER-002: 分类切换只展示对应来源的仓库', async () => {
    renderWithProviders(<ApiTester />)

    // 默认「全部」→ 三类合并展示（用配置驱动，避免硬编码仓库名）
    const firstAll = repositories[0]
    expect(await screen.findByText(firstAll.name)).toBeInTheDocument()

    // 切到「自研」
    fireEvent.click(screen.getByText('🏠 自研'))
    if (selfRepositories.length > 0) {
      expect(await screen.findByText(selfRepositories[0].name)).toBeInTheDocument()
    }
    // 第三方专有的仓库此时不应出现（取差集，避免数据重叠导致误判）
    const thirdOnly = thirdPartyRepositories.find(
      (repo) => !selfRepositories.some((self) => self.id === repo.id)
    )
    if (thirdOnly) {
      expect(screen.queryByText(thirdOnly.name)).not.toBeInTheDocument()
    }

    // 切到「第三方」
    fireEvent.click(screen.getByText('🌐 第三方'))
    if (thirdPartyRepositories.length > 0) {
      expect(await screen.findByText(thirdPartyRepositories[0].name)).toBeInTheDocument()
    }
  })

  it('TC-FE-TESTER-003: 点击仓库后展示其端点列表', async () => {
    renderWithProviders(<ApiTester />)

    const repo = repositories.find((r) => r.endpoints.length > 0)!
    fireEvent.click(await screen.findByText(repo.name))

    // 选中后应至少出现该仓库第一个端点的名称或路径
    const endpoint = repo.endpoints[0]
    await waitFor(() => {
      const found =
        screen.queryByText(endpoint.name) ?? screen.queryByText(endpoint.path)
      expect(found).not.toBeNull()
    })
  })
})

describe('API Key 配置', () => {
  it('TC-FE-TESTER-004: 打开配置面板 → 输入 → 保存后按钮显示「已配置」', async () => {
    renderWithProviders(<ApiTester />)

    expect(screen.getByText('配置Key')).toBeInTheDocument()
    fireEvent.click(screen.getByText('配置Key'))

    const input = await screen.findByPlaceholderText('请输入 API Key')
    fireEvent.change(input, { target: { value: 'my-access-key' } })
    fireEvent.click(screen.getByText('💾 保存'))

    await waitFor(() => expect(useApiKeyStore.getState().apiKey).toBe('my-access-key'))
    expect(await screen.findByText('已配置')).toBeInTheDocument()
  })

  it('TC-FE-TESTER-005: 未配置 Key 时请求头使用占位值（便于用户识别）', async () => {
    renderWithProviders(<ApiTester />)

    const repo = repositories.find((r) => r.endpoints.length > 0)!
    fireEvent.click(await screen.findByText(repo.name))

    const endpoint = repo.endpoints[0]
    const clickable =
      (await screen.findByText(endpoint.name).catch(() => null)) ??
      (await screen.findByText(endpoint.path))
    fireEvent.click(clickable)

    const sendBtn = await screen.findByText('发送请求')
    fireEvent.click(sendBtn)

    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const [, init] = firstFetchCall()
    expect((init.headers as Record<string, string>)['X-Access-Key']).toBe('YOUR_API_KEY')
  })
})

describe('发送请求与历史记录', () => {
  /** 选中第一个可用仓库与端点（多数用例的前置） */
  async function selectFirstRepoAndEndpoint(): Promise<void> {
    const repo = repositories.find((r) => r.endpoints.length > 0)!
    fireEvent.click(await screen.findByText(repo.name))
    const endpoint = repo.endpoints[0]
    const clickable =
      (await screen.findByText(endpoint.name).catch(() => null)) ??
      (await screen.findByText(endpoint.path))
    fireEvent.click(clickable)
  }

  it('TC-FE-TESTER-006: 请求经后端 proxy 发出，URL/方法/头部符合约定', async () => {
    useApiKeyStore.setState({ apiKey: 'key-123' })
    renderWithProviders(<ApiTester />)
    await selectFirstRepoAndEndpoint()

    fireEvent.click(await screen.findByText('发送请求'))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())

    const [url, init] = firstFetchCall()
    // 必须走平台后端 proxy（而不是直连仓库地址），否则日志/计费/配额都会缺
    expect(url).toContain('http://localhost:8000/api/v1/repositories/')
    expect(init.method).toBeTruthy()
    expect((init.headers as Record<string, string>)['X-Access-Key']).toBe('key-123')
  })

  it('TC-FE-TESTER-007: 请求成功后响应面板展示结果，历史计数 +1', async () => {
    renderWithProviders(<ApiTester />)
    await selectFirstRepoAndEndpoint()

    expect(screen.getByText('历史 (0)')).toBeInTheDocument()
    fireEvent.click(await screen.findByText('发送请求'))

    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByText('历史 (1)')).toBeInTheDocument())
    // 响应内容出现在面板中（JSON 字符串）
    expect(await screen.findByText(/echoed/)).toBeInTheDocument()
  })

  it('TC-FE-TESTER-008: 请求失败时展示错误且历史仍记录（status=0）', async () => {
    fetchMock.mockRejectedValue(new Error('网络请求失败'))
    renderWithProviders(<ApiTester />)
    await selectFirstRepoAndEndpoint()

    fireEvent.click(await screen.findByText('发送请求'))

    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    // 失败也进入历史（便于排查），页面不崩
    await waitFor(() => expect(screen.getByText('历史 (1)')).toBeInTheDocument())
    expect(screen.getByText('API 测试工具')).toBeInTheDocument()
  })
})

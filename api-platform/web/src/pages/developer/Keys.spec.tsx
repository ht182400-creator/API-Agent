/**
 * API Keys 管理页（developer/Keys.tsx）测试 —— 用例库 FE-DEV-KEYS
 *
 * 为什么值得测：本页承载**凭据安全语义**与**不可逆操作**，两条都是"错了就出事"：
 *   ① 明文 Key **默认不展示**（列表只给 `前缀...****`），完整值只在两个时机出现：
 *      创建成功的一次性弹窗、用户主动点「查看」（revealKey）；且创建弹窗关闭后**不得残留**；
 *   ② 删除**不可恢复** → 必须二次确认；未确认就发请求等于"点一下没了一条凭据"；
 *   ③ 禁用/启用按当前状态给出**对应**操作（active 行给"禁用"、非 active 行给"启用"），
 *      错了会造成"点禁用反而启用"。
 *
 * ⚠️ 顺带清掉：移动端卡片的 `Card bodyStyle`（antd v5 废弃）→ `styles={{ body }}`。
 *    （该分支在 jsdom 下不渲染，所以它不会进警告预算 —— 但一旦真机/窄屏渲染就会刷警告。）
 *
 * ⚠️ 与 Reconciliation 页的差异：**本页用的是静态 `message.success`**（不是 `message.useMessage()`），
 *    所以这里只 mock 静态方法即可拦到提示。
 *
 * 用例编号：TC-FE-KEYS-001 ~ TC-FE-KEYS-005
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
  return { ...actual, message: messageSpies }
})

// 统一错误处理用 spy 替换（本页所有失败分支都走它）
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
      getKeys: vi.fn(),
      createKey: vi.fn(),
      getKey: vi.fn(),
      updateKey: vi.fn(),
      disableKey: vi.fn(),
      enableKey: vi.fn(),
      deleteKey: vi.fn(),
      revealKey: vi.fn(),
      getQuota: vi.fn(),
      getQuotaOverview: vi.fn(),
      setQuota: vi.fn(),
      getLogs: vi.fn(),
      getUsageHistory: vi.fn(),
      getTopRepos: vi.fn(),
      getConsumptionTrend: vi.fn(),
    },
  }
})

import DeveloperKeys from './Keys'
import { quotaApi } from '../../api/quota'
import type { APIKey } from '../../api/quota'
import { useAuthStore } from '../../stores/auth'
import { renderWithProviders } from '../../test/renderWithProviders'

// ---------------- 测试数据 ----------------
// ⚠️ 列表项里**故意带上完整的 `api_key`** —— 用来证明"即使后端把明文带回来了，
//    列表 UI 也绝不渲染它"（真实后端其实只在创建/reveal 时返回）。

const activeKey: APIKey = {
  id: 'k1',
  key_name: '生产应用',
  key_prefix: 'sk-live-abc',
  api_key: 'sk-live-abc-FULL-SECRET-IN-LIST',
  status: 'active',
  auth_type: 'api_key',
  rate_limit_rpm: 1000,
  rate_limit_rph: 10000,
  daily_quota: 5000,
  monthly_quota: null,
  created_at: '2026-09-10T08:30:00Z',
}

const disabledKey: APIKey = {
  id: 'k2',
  key_name: '测试Key',
  key_prefix: 'sk-test-xyz',
  api_key: 'sk-test-xyz-FULL-SECRET-IN-LIST',
  status: 'disabled',
  auth_type: 'hmac',
  rate_limit_rpm: 60,
  rate_limit_rph: 600,
  daily_quota: null,
  monthly_quota: 100000,
  created_at: '2026-09-11T02:00:00Z',
}

const createdKey: APIKey = {
  id: 'k3',
  key_name: '我的应用',
  key_prefix: 'sk-new-abc',
  api_key: 'sk-new-FULL-SECRET-ONE-TIME',
  status: 'active',
  auth_type: 'api_key',
  rate_limit_rpm: 1000,
  rate_limit_rph: 10000,
  daily_quota: null,
  monthly_quota: null,
  created_at: '2026-09-17T00:00:00Z',
}

const listResponse = {
  items: [activeKey, disabledKey],
  pagination: { page: 1, page_size: 10, total: 2, total_pages: 1 },
}

function renderPage() {
  return renderWithProviders(<DeveloperKeys />, { route: '/developer/keys' })
}

/** 按标题定位弹窗（用 `.ant-modal-title`，避免与同名按钮文本冲突） */
function modalOf(title: string): HTMLElement {
  const titleEl = [...document.querySelectorAll('.ant-modal-title')].find(
    (t) => t.textContent === title
  )
  if (!titleEl) throw new Error(`未找到弹窗：${title}`)
  const modal = titleEl.closest('.ant-modal')
  if (!modal) throw new Error(`弹窗缺少 .ant-modal 容器：${title}`)
  return modal as HTMLElement
}

/** 取某一行的 <tr>（按 Key 名称定位） */
function rowOf(keyName: string): HTMLElement {
  const cell = screen.getByText(keyName).closest('tr')
  if (!cell) throw new Error(`未找到行：${keyName}`)
  return cell as HTMLElement
}

beforeEach(() => {
  // 默认非普通用户（能建 Key）；TC-005 会单独改成普通用户
  useAuthStore.setState({ user: null })
  vi.mocked(quotaApi.getKeys).mockResolvedValue(listResponse as never)
  vi.mocked(quotaApi.createKey).mockResolvedValue(createdKey as never)
  vi.mocked(quotaApi.disableKey).mockResolvedValue({} as never)
  vi.mocked(quotaApi.enableKey).mockResolvedValue({} as never)
  vi.mocked(quotaApi.deleteKey).mockResolvedValue({} as never)
})

describe('列表默认不展示明文 Key（TC-FE-KEYS-001）', () => {
  it('TC-FE-KEYS-001: 只显示前缀与派生文案；完整 Key 不出现在页面上', async () => {
    renderPage()

    await waitFor(() =>
      expect(quotaApi.getKeys).toHaveBeenCalledWith({ page: 1, page_size: 10 })
    )
    expect(await screen.findByText('生产应用')).toBeInTheDocument()

    // 🔐 核心安全语义：完整 Key（即便后端带回列表里）**一个字符都不渲染**
    expect(document.body.textContent).not.toContain('FULL-SECRET')

    // 只展示「前缀...****」
    expect(screen.getByText('sk-live-abc...****')).toBeInTheDocument()
    expect(screen.getByText('sk-test-xyz...****')).toBeInTheDocument()

    // 派生文案
    expect(screen.getByText('API Key')).toBeInTheDocument()
    expect(screen.getByText('HMAC')).toBeInTheDocument()
    expect(screen.getByText('1000次/分钟')).toBeInTheDocument()
    expect(screen.getByText('10000次/小时')).toBeInTheDocument()
    expect(screen.getByText('5000次')).toBeInTheDocument()
    expect(screen.getByText('100000次')).toBeInTheDocument()
    // 未设配额 → 「无限制」（两行共 2 处：k1 的月配额、k2 的日配额）
    expect(screen.getAllByText('无限制')).toHaveLength(2)
    // 创建时间按本地时区格式化
    expect(
      screen.getByText(dayjs(activeKey.created_at).format('YYYY-MM-DD HH:mm'))
    ).toBeInTheDocument()

    // 状态：正常（active）；「禁用」文本同时是 active 行的按钮文案 → 用行作用域断言 Tag
    expect(screen.getByText('正常')).toBeInTheDocument()
    expect(within(rowOf('测试Key')).getByText('禁用')).toBeInTheDocument()

    // 状态 → 操作映射：active 行给「禁用」，disabled 行给「启用」
    expect(within(rowOf('生产应用')).getByRole('button', { name: /禁用/ })).toBeInTheDocument()
    expect(within(rowOf('测试Key')).getByRole('button', { name: /启用/ })).toBeInTheDocument()

    expect(screen.getByText('共 2 条')).toBeInTheDocument()
  })
})

describe('创建 Key：一次性展示（TC-FE-KEYS-002）', () => {
  it('TC-FE-KEYS-002: 创建后展示完整 Key 并提示妥善保管；关闭后不再残留；列表重新拉取', async () => {
    renderPage()
    await screen.findByText('生产应用')
    const callsBefore = vi.mocked(quotaApi.getKeys).mock.calls.length

    fireEvent.click(screen.getByRole('button', { name: /创建API Key/ }))
    const modal = modalOf('创建API Key')

    fireEvent.change(within(modal).getByLabelText('Key名称'), {
      target: { value: '我的应用' },
    })
    fireEvent.click(within(modal).getByRole('button', { name: /创\s*建/ }))

    await waitFor(() => expect(quotaApi.createKey).toHaveBeenCalledTimes(1))
    const payload = vi.mocked(quotaApi.createKey).mock.calls[0][0]
    expect(payload).toEqual(
      expect.objectContaining({ name: '我的应用', auth_type: 'api_key' })
    )
    // 未改动的默认值必须原样提交（否则会把用户限流从 1000 改成后端默认）
    expect(String(payload.rate_limit_rpm)).toBe('1000')
    expect(String(payload.rate_limit_rph)).toBe('10000')
    expect(payload.monthly_quota).toBeUndefined()

    expect(messageSpies.success).toHaveBeenCalledWith('API Key创建成功')

    // ① 一次性展示：完整 Key + 明确提示
    const successModal = modalOf('API Key创建成功')
    expect(within(successModal).getByText(/请妥善保管以下Key，仅显示一次/)).toBeInTheDocument()
    expect(within(successModal).getByText('sk-new-FULL-SECRET-ONE-TIME')).toBeInTheDocument()

    // ② 关闭（我已保存）→ 完整 Key 不再出现在页面上
    fireEvent.click(within(successModal).getByRole('button', { name: /我已保存/ }))
    await waitFor(() =>
      expect(document.body.textContent).not.toContain('FULL-SECRET-ONE-TIME')
    )

    // ③ 创建后重新拉取列表
    await waitFor(() =>
      expect(vi.mocked(quotaApi.getKeys).mock.calls.length).toBe(callsBefore + 1)
    )
  })
})

describe('删除需二次确认（TC-FE-KEYS-003）', () => {
  it('TC-FE-KEYS-003: 取消不发请求；确认后才删除并重新拉取', async () => {
    // ① 弹出确认后点「取消」→ 绝不发请求
    const { unmount } = renderPage()
    await screen.findByText('生产应用')
    fireEvent.click(within(rowOf('生产应用')).getByRole('button', { name: /删除/ }))
    expect(await screen.findByText('确认删除？')).toBeInTheDocument()
    expect(quotaApi.deleteKey).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /取\s*消/ }))
    expect(quotaApi.deleteKey).not.toHaveBeenCalled()
    unmount()

    // ② 点「确认」→ 才真正删除，并重新拉取列表
    renderPage()
    await screen.findByText('生产应用')
    const callsBefore = vi.mocked(quotaApi.getKeys).mock.calls.length

    fireEvent.click(within(rowOf('生产应用')).getByRole('button', { name: /删除/ }))
    fireEvent.click(await screen.findByRole('button', { name: /确\s*认/ }))

    await waitFor(() => expect(quotaApi.deleteKey).toHaveBeenCalledWith('k1'))
    expect(messageSpies.success).toHaveBeenCalledWith('API Key已删除')
    await waitFor(() =>
      expect(vi.mocked(quotaApi.getKeys).mock.calls.length).toBe(callsBefore + 1)
    )
  })
})

describe('禁用 / 启用按状态给出对应操作（TC-FE-KEYS-004）', () => {
  it('TC-FE-KEYS-004: active 行禁用、非 active 行启用，成功后提示并重新拉取', async () => {
    renderPage()
    await screen.findByText('生产应用')
    const callsBefore = vi.mocked(quotaApi.getKeys).mock.calls.length

    fireEvent.click(within(rowOf('生产应用')).getByRole('button', { name: /禁用/ }))
    await waitFor(() => expect(quotaApi.disableKey).toHaveBeenCalledWith('k1'))
    expect(messageSpies.success).toHaveBeenCalledWith('API Key已禁用')

    fireEvent.click(within(rowOf('测试Key')).getByRole('button', { name: /启用/ }))
    await waitFor(() => expect(quotaApi.enableKey).toHaveBeenCalledWith('k2'))
    expect(messageSpies.success).toHaveBeenCalledWith('API Key已启用')

    // 两次操作各重新拉取一次
    await waitFor(() =>
      expect(vi.mocked(quotaApi.getKeys).mock.calls.length).toBe(callsBefore + 2)
    )
  })
})

describe('普通用户的升级引导（TC-FE-KEYS-005）', () => {
  it('TC-FE-KEYS-005: 普通用户看不到创建入口，只看到升级引导（列表仍只读可见）', async () => {
    useAuthStore.setState({
      user: {
        id: 'u-1',
        email: 'user@example.com',
        user_type: 'user',
        user_status: 'active',
        role: 'user',
        permissions: [],
        email_verified: true,
        vip_level: 0,
        created_at: '2026-01-01T00:00:00Z',
      },
    })
    renderPage()

    // 引导文案出现
    expect(await screen.findByText('升级为开发者，获取API Keys')).toBeInTheDocument()
    // 创建入口被隐藏（普通用户不允许自助建 Key）
    expect(screen.queryByRole('button', { name: /创建API Key/ })).toBeNull()
    // 既有列表仍可见（只读）
    expect(screen.getByText('生产应用')).toBeInTheDocument()
  })
})

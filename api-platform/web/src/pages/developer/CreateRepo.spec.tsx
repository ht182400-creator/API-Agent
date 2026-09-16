/**
 * 创建仓库页（developer/CreateRepo.tsx）测试 —— 用例库 FE-DEV-CREATEREPO
 *
 * 为什么值得测：本页是**仓库入口**，且带一条真实的业务分叉：
 *   ① 校验（名称 3-50 且只允许字母数字下划线连字符 / 显示名 / 描述必填 / 端点须是合法 URL）
 *      —— 错了会把脏数据写进仓库主表（名称还**不可修改**）；
 *   ② 管理员与非管理员的**提示与按钮文案不同**（创建并上线 vs 提交审核），
 *      提交后**跳转目标也不同**（/admin/repos vs /developer/repos）—— 走错会把管理员
 *      的仓库丢进"待审核"流量里，或把普通用户的仓库直接当已上线；
 *   ③ 图标上传的两道硬限制（仅图片 / ≤200KB）—— 超限必须当场拒绝。
 *
 * 用例编号：TC-FE-CREATEREPO-001 ~ TC-FE-CREATEREPO-005
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'

const { messageSpies } = vi.hoisted(() => ({
  messageSpies: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

vi.mock('antd', async (importOriginal) => {
  const actual = await importOriginal<typeof import('antd')>()
  return { ...actual, message: messageSpies }
})

vi.mock('../../api/repo', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/repo')>()
  return { ...actual, repoApi: { ...actual.repoApi, create: vi.fn() } }
})

import CreateRepo from './CreateRepo'
import { repoApi } from '../../api/repo'
import { useAuthStore } from '../../stores/auth'
import { renderWithProviders } from '../../test/renderWithProviders'

const developerUser = {
  id: 'u1',
  email: 'dev@example.com',
  user_type: 'developer' as const,
  role: 'developer',
  permissions: [],
}
const adminUser = { ...developerUser, id: 'u2', user_type: 'admin' as const, role: 'admin' }

function renderPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/developer/create-repo" element={<CreateRepo />} />
      <Route path="/developer/repos" element={<div>DEV_REPOS_STUB</div>} />
      <Route path="/admin/repos" element={<div>ADMIN_REPOS_STUB</div>} />
    </Routes>,
    { route: '/developer/create-repo' }
  )
}

function submit(): void {
  // 两个按钮文案不同（提交审核 / 创建并上线）；用正则同时匹配
  fireEvent.click(screen.getByRole('button', { name: /提交审核|创建并上线/ }))
}

function fillValidForm(): void {
  fireEvent.change(screen.getByPlaceholderText('例如：weather-api'), {
    target: { value: 'weather-api' },
  })
  fireEvent.change(screen.getByPlaceholderText('例如：天气查询API'), {
    target: { value: '天气查询API' },
  })
  fireEvent.change(
    screen.getByPlaceholderText(
      '详细描述您的API服务功能、使用场景、调用方式等...'
    ),
    { target: { value: '提供天气查询服务' } }
  )
}

beforeEach(() => {
  useAuthStore.setState({ user: developerUser as never })
  vi.mocked(repoApi.create).mockResolvedValue({ id: 'r1', status: 'pending' } as never)
})

describe('必填与格式校验（TC-FE-CREATEREPO-001）', () => {
  it('TC-FE-CREATEREPO-001: 空提交被三条必填拦截；名称规则与端点 URL 格式各自拦截', async () => {
    renderPage()

    // ① 空表单提交 → 三条必填错误，且不发请求
    submit()
    expect(await screen.findByText('请输入仓库名称')).toBeInTheDocument()
    expect(screen.getByText('请输入显示名称')).toBeInTheDocument()
    expect(screen.getByText('请输入仓库描述')).toBeInTheDocument()
    expect(repoApi.create).not.toHaveBeenCalled()

    // ② 名称过短 → 长度规则
    fireEvent.change(screen.getByPlaceholderText('例如：weather-api'), { target: { value: 'ab' } })
    submit()
    expect(await screen.findByText('名称长度在3-50个字符之间')).toBeInTheDocument()

    // ③ 名称含非法字符 → 正则规则
    fireEvent.change(screen.getByPlaceholderText('例如：weather-api'), {
      target: { value: 'bad name!' },
    })
    submit()
    expect(await screen.findByText('只允许字母、数字、下划线和连字符')).toBeInTheDocument()

    // ④ 端点非合法 URL → URL 规则（该字段非必填，但填了就得合法）
    fillValidForm()
    fireEvent.change(screen.getByPlaceholderText('例如：https://api.example.com/v1'), {
      target: { value: 'not-a-url' },
    })
    submit()
    expect(await screen.findByText('请输入有效的URL地址')).toBeInTheDocument()

    expect(repoApi.create).not.toHaveBeenCalled()
  })
})

describe('非管理员提交（TC-FE-CREATEREPO-002）', () => {
  it('TC-FE-CREATEREPO-002: 提示需审核、按钮为「提交审核」；成功后跳开发者仓库页', async () => {
    renderPage()

    // 非管理员：审核须知 + 提交审核按钮
    expect(screen.getByText('审核须知')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /提交审核/ })).toBeInTheDocument()
    expect(screen.queryByText('管理员操作')).toBeNull()

    fillValidForm()
    submit()

    await waitFor(() => expect(repoApi.create).toHaveBeenCalledTimes(1))
    expect(repoApi.create).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'weather-api',
        display_name: '天气查询API',
        description: '提供天气查询服务',
        // 未改动的 initialValues 必须原样提交
        repo_type: 'custom',
        protocol: 'http',
      })
    )
    expect(messageSpies.success).toHaveBeenCalledWith('仓库创建成功')
    // 待审核 → 回开发者仓库页
    expect(await screen.findByText('DEV_REPOS_STUB')).toBeInTheDocument()
  })
})

describe('管理员提交（TC-FE-CREATEREPO-003）', () => {
  it('TC-FE-CREATEREPO-003: 提示直上线、按钮为「创建并上线」；成功后跳管理员仓库页', async () => {
    useAuthStore.setState({ user: adminUser as never })
    vi.mocked(repoApi.create).mockResolvedValue({ id: 'r2', status: 'online' } as never)
    renderPage()

    expect(screen.getByText('管理员操作')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /创建并上线/ })).toBeInTheDocument()
    expect(screen.queryByText('审核须知')).toBeNull()

    fillValidForm()
    submit()

    await waitFor(() => expect(repoApi.create).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('ADMIN_REPOS_STUB')).toBeInTheDocument()
  })
})

describe('创建失败提示（TC-FE-CREATEREPO-004）', () => {
  it('TC-FE-CREATEREPO-004: 后端 detail 优先展示，且停留在本页可重试', async () => {
    vi.mocked(repoApi.create).mockRejectedValue({ detail: '仓库名称已存在' })
    renderPage()

    fillValidForm()
    submit()

    await waitFor(() => expect(messageSpies.error).toHaveBeenCalledWith('仓库名称已存在'))
    // 不跳转、页面仍在
    expect(screen.queryByText('DEV_REPOS_STUB')).toBeNull()
    expect(screen.getByText('创建仓库')).toBeInTheDocument()
  })
})

describe('图标上传限制（TC-FE-CREATEREPO-005）', () => {
  it('TC-FE-CREATEREPO-005: 非图片与超 200KB 都被当场拒绝', async () => {
    // ① 非图片类型
    // ⚠️ 两个场景必须**分开渲染**：同一个 <input type=file> 上连续两次 change，
    //    第二次不会触发 beforeUpload（rc-upload 内部状态所致，实测 Number of calls: 1）。
    const first = renderPage()
    const firstInput = first.container.querySelector('input[type="file"]') as HTMLInputElement
    expect(firstInput).not.toBeNull()
    fireEvent.change(firstInput, {
      target: { files: [new File(['x'], 'a.txt', { type: 'text/plain' })] },
    })
    await waitFor(() => expect(messageSpies.error).toHaveBeenCalledWith('只能上传图片文件！'))
    expect(repoApi.create).not.toHaveBeenCalled()
    first.unmount()

    // ② 图片但超过 200KB（250KB > 200KB 上限）
    const second = renderPage()
    const secondInput = second.container.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(secondInput, {
      target: {
        files: [new File(['x'.repeat(250 * 1024)], 'big.png', { type: 'image/png' })],
      },
    })
    await waitFor(() =>
      expect(messageSpies.error).toHaveBeenCalledWith('图标大小不能超过 200KB！')
    )
    expect(repoApi.create).not.toHaveBeenCalled()
  })
})

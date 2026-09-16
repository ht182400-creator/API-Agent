/**
 * 注册页（Register.tsx）测试 —— 用例库 FE-AUTH-REGISTER（P0）
 *
 * 为什么是 P0：注册与登录并列，是全站仅有的两个"未登录可达"入口。它一旦坏了，
 * 新用户**无法进入系统**；而它内部有三类"错了就致命"的逻辑：
 *   ① 账号类型只允许 `user` / `developer` —— 页面**不得**出现 owner/admin/super_admin
 *      入口（服务端已由 `UserCreate.SELF_REGISTER_ROLES` 白名单封堵自我提权，
 *      提交 9ce24fb4；前端这一层是"不给入口 + 不带越权类型"的第二道防线）；
 *   ② 表单校验（用户名 3-50 且仅字母数字下划线 / 邮箱格式 / 密码 ≥8 / 两次一致）
 *      错了会把脏数据放进注册链路，或让用户"填完才被后端拒绝"；
 *   ③ 成功后必须 **跳 /login**（注册不发 token，不能直接进站）。
 *
 * ⚠️ 拦截分**两层**（本次实测确认）：`confirmPassword` 的 antd 校验器
 *    （dependencies: ['password']）比 `onFinish` 里那句手写
 *    `password !== confirmPassword` **更早**生效 —— 所以"两次密码不一致"表现为
 *    **字段级错误**（红色提示），而不是 `message.error`。那句手写判断只是
 *    校验器失效时的第二道防线，正常路径走不到（首跑用例就是断言错了这一层才失败）。
 *
 * ⚠️ 被测组件有一个"对抗浏览器自动填充"的副作用：挂载后 300/1000/2000ms 会
 *    **无条件清空所有密码输入框**。因此本文件统一用同步的 `fireEvent.change` 填写
 *    并**立即提交**（与 Login.spec 同策略），避免被定时器清空造成假失败；
 *    用例体保持短小，unmount 时组件的 effect cleanup 会清掉这些定时器。
 *
 * ⚠️ 只局部 mock `antd` 的 `message`（见下方注释），其余组件保持真实 ——
 *    这是为了①精确断言提示文案；②规避 antd v5 静态 message 在 jsdom 里打印的
 *    "Static function can not consume context…" 警告（基线外的新种类会让
 *    `npm run test:budget` 直接失败）。
 *
 * 用例编号：TC-FE-REG-001 ~ TC-FE-REG-004
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'

// tip：用 vi.hoisted 让 spy 能在 vi.mock 工厂（被提升到文件顶部）里引用，
//      同时保证断言处拿到的是同一个对象。
const { messageSpies } = vi.hoisted(() => ({
  messageSpies: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

vi.mock('antd', async (importOriginal) => {
  const actual = await importOriginal<typeof import('antd')>()
  return { ...actual, message: messageSpies }
})

// 组件唯一的外部数据源
vi.mock('../../api/auth', () => ({
  authApi: {
    register: vi.fn(),
    login: vi.fn(),
    me: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
  },
}))

import Register from './Register'
import { authApi } from '../../api/auth'
import { renderWithProviders } from '../../test/renderWithProviders'

const registeredUser = {
  id: 'u-new',
  username: 'newuser01',
  email: 'new@example.com',
  user_type: 'developer' as const,
  user_status: 'active',
  role: 'developer',
  permissions: [],
  email_verified: false,
  vip_level: 0,
  created_at: '2026-09-16T00:00:00Z',
}

/**
 * 渲染「注册页 + 一个登录页占位路由」——
 * 后者用于断言注册成功后的跳转（renderWithProviders 默认不渲染 <Routes>）。
 */
function renderRegister() {
  return renderWithProviders(
    <Routes>
      <Route path="/register" element={<Register />} />
      <Route path="/login" element={<div>LOGIN_PAGE_STUB</div>} />
    </Routes>,
    { route: '/register' }
  )
}

/** 同步填写注册表单（避开组件的自动清空定时器） */
function fillRegisterForm(
  overrides: Partial<{
    username: string
    email: string
    password: string
    confirmPassword: string
  }> = {}
): void {
  const {
    username = 'newuser01',
    email = 'new@example.com',
    password = 'secret123',
    confirmPassword = password,
  } = overrides

  fireEvent.change(screen.getByPlaceholderText('用户名（用于登录）'), { target: { value: username } })
  fireEvent.change(screen.getByPlaceholderText('邮箱'), { target: { value: email } })
  fireEvent.change(screen.getByPlaceholderText('密码（至少8位）'), { target: { value: password } })
  fireEvent.change(screen.getByPlaceholderText('确认密码'), { target: { value: confirmPassword } })
}

/** antd Button 会在两个中文字符间插空格 → 可访问名是「注 册」 */
function submit(): void {
  fireEvent.click(screen.getByRole('button', { name: '注 册' }))
}

beforeEach(() => {
  vi.mocked(authApi.register).mockResolvedValue(registeredUser as never)
})

describe('注册页渲染（TC-FE-REG-001）', () => {
  it('TC-FE-REG-001: 渲染关键字段；账号类型只有 user/developer 且随选择切换提示', async () => {
    renderRegister()

    expect(screen.getByText('注册账号')).toBeInTheDocument()
    expect(screen.getByText('加入API Platform')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('用户名（用于登录）')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('邮箱')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('密码（至少8位）')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('确认密码')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '注 册' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '立即登录' })).toBeInTheDocument()

    // 🔐 越权防线之一：只暴露 user / developer 两种角色（owner 已按 V4.0 语义
    //    与 developer 合并；admin / super_admin 绝不可自助注册）
    const radios = screen.getAllByRole('radio') as HTMLInputElement[]
    expect(radios).toHaveLength(2)
    expect(radios.map((r) => r.value).sort()).toEqual(['developer', 'user'])

    // 默认 developer（initialValues）→ 展示其用途提示
    expect(screen.getByText('开发者可使用API服务、创建仓库并获得收益分成')).toBeInTheDocument()

    // 切到普通用户 → 提示文案随之切换（getUserTypeHint 的分支）
    fireEvent.click(screen.getByRole('radio', { name: '普通用户' }))
    expect(await screen.findByText('普通用户可领取试用金额，升级后成为开发者')).toBeInTheDocument()
  })
})

describe('表单校验拦截（TC-FE-REG-002）', () => {
  it('TC-FE-REG-002: 密码不一致 / 长度不足 / 用户名非法均被拦截，不发请求', async () => {
    // ① 两次密码不一致 → 被 confirmPassword 的 antd 校验器（dependencies:['password']）拦下。
    //    ⚠️ 实测：它比组件 onFinish 里那句手写判断**更早**生效 —— 所以体现为**字段级错误**，
    //    而不是 message.error（那行是校验器失效时的第二道防线，正常路径走不到）。
    const { unmount } = renderRegister()
    fillRegisterForm({ password: 'secret123', confirmPassword: 'secret124' })
    submit()

    expect(await screen.findByText('两次输入的密码不一致')).toBeInTheDocument()
    expect(authApi.register).not.toHaveBeenCalled()
    expect(messageSpies.error).not.toHaveBeenCalled()
    unmount()

    // ② 密码不足 8 位 → antd 规则拦截（连 onFinish 都不会进入）
    renderRegister()
    fillRegisterForm({ password: 'short12' })
    submit()

    expect(await screen.findByText('密码至少8位')).toBeInTheDocument()
    expect(authApi.register).not.toHaveBeenCalled()
    expect(messageSpies.error).not.toHaveBeenCalled()

    // ③ 用户名含非法字符（仅允许字母/数字/下划线）→ 规则拦截
    fillRegisterForm({ username: 'bad name!' })
    submit()

    expect(await screen.findByText('只能是字母、数字、下划线')).toBeInTheDocument()
    expect(authApi.register).not.toHaveBeenCalled()
  })
})

describe('注册成功（TC-FE-REG-003）', () => {
  it('TC-FE-REG-003: 以所选类型提交并跳到登录页（注册不直接登录）', async () => {
    renderRegister()

    fillRegisterForm()
    // 选「普通用户」，确认提交的 user_type 跟随选择（而不是写死 developer）
    fireEvent.click(screen.getByRole('radio', { name: '普通用户' }))
    submit()

    await waitFor(() => expect(authApi.register).toHaveBeenCalledTimes(1))
    expect(authApi.register).toHaveBeenCalledWith({
      username: 'newuser01',
      email: 'new@example.com',
      password: 'secret123',
      user_type: 'user',
    })
    expect(messageSpies.success).toHaveBeenCalledWith('注册成功，请登录')

    // 跳转 /login（而不是 / 或直接进站）
    expect(await screen.findByText('LOGIN_PAGE_STUB')).toBeInTheDocument()
  })
})

describe('注册失败（TC-FE-REG-004）', () => {
  it('TC-FE-REG-004: 后端错误原样提示、留在注册页且可重试', async () => {
    vi.mocked(authApi.register).mockRejectedValueOnce(new Error('用户名已存在'))
    renderRegister()

    fillRegisterForm()
    submit()

    // 后端 message 经 client 拦截器写入 error.message → 组件 message.error 呈现
    await waitFor(() => expect(messageSpies.error).toHaveBeenCalledWith('用户名已存在'))

    // 不跳转、页面不白屏（表单仍在，用户可改后重试）
    expect(screen.queryByText('LOGIN_PAGE_STUB')).not.toBeInTheDocument()
    expect(screen.getByText('注册账号')).toBeInTheDocument()

    // 重试成功 → 正常放行（loading 已复位，按钮可再次点击）
    vi.mocked(authApi.register).mockResolvedValue(registeredUser as never)
    submit()
    await waitFor(() => expect(authApi.register).toHaveBeenCalledTimes(2))
    expect(await screen.findByText('LOGIN_PAGE_STUB')).toBeInTheDocument()
  })
})

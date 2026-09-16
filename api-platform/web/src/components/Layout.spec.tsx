/**
 * 主布局（Layout.tsx）测试 —— 菜单可见性
 *
 * 为什么优先测它（P0）：
 *   Layout 决定「用户能看到哪些菜单入口」，这是**越权可见性**的展示层防线。
 *   菜单配错既不会报错也不会白屏 —— 只会让无权用户看到不该有的入口（或反之），
 *   靠人工点很难覆盖全部角色组合。其核心 `getMenuItems(userType)` 是纯函数，最适合单测。
 *
 * ✅ 相关死代码已清理（用例库 FE-BUG-LAYOUT-DEAD-MENU）：`developerWithoutReposMenu`
 *   （已无引用）与 `getMenuItems` 的 `userHasRepos` 参数（不再影响任何分支）均已移除，
 *   连带删除只为该参数服务的 `hasRepos` 状态与 `/user/has-repos` 请求（少一次无谓请求）。
 *
 * 用例编号：TC-FE-LAYOUT-001 ~ TC-FE-LAYOUT-006
 * （组件级渲染/登出用例见用例库 planned：TC-FE-LAYOUT-007~008）
 */
import { describe, it, expect, vi, afterEach } from 'vitest'

// ⚠️ mock 路径必须与 Layout.tsx 的 import 路径解析到同一模块（'../api/auth'）。
//    原先写成 '../../api/auth' 从本文件解析到不存在的位置 → mock 从未生效
//    （001~006 只测纯函数所以没暴露；007/008 一旦渲染组件立即炸出真模块）。
vi.mock('../api/auth', () => ({
  authApi: { logout: vi.fn(), me: vi.fn() },
}))
vi.mock('../api/notification', () => ({
  notificationApi: {
    // ⚠️ 形状必须与 src/api/notification.ts 对齐（C 轮修正）：Layout 实际调用的是
    //    getUnreadCount / getRecent / markAsRead / markAllAsRead。
    //    原先只给了 `getUnreadCount: () => 0`（裸数字，而组件读 `data.unread_count`）
    //    + 一个 Layout 根本不用的 getList，且**缺 getRecent** ——
    //    于是每次渲染都会走进 Layout 的 catch 打一条 console.error，
    //    未读数恒为 undefined，徽标分支永远测不到。
    getUnreadCount: vi.fn().mockResolvedValue({ unread_count: 0 }),
    getRecent: vi.fn().mockResolvedValue([]),
    markAsRead: vi.fn().mockResolvedValue(undefined),
    markAllAsRead: vi.fn().mockResolvedValue(undefined),
    getList: vi.fn().mockResolvedValue({ items: [] }),
  },
}))

/**
 * 设备判定必须**可切换**：Layout 的两套骨架（桌面 Sider / 移动端抽屉）完全由 useDevice 决定，
 * 而 useDevice 读 window.innerWidth（jsdom 默认 1024 → desktop）—— 不 mock 就永远只能测到桌面形态。
 * 用 `vi.hoisted` 暴露一个可变对象，让用例按需改写（比改 window.innerWidth 副作用小得多：
 * 后者会连带影响 antd 的响应式栅格与 Row/Col 断点）。
 */
const { deviceRef } = vi.hoisted(() => ({
  deviceRef: {
    current: { isMobile: false, isTablet: false, isDesktop: true, isLargeDesktop: false },
  },
}))
vi.mock('../hooks/useDevice', () => ({ useDevice: () => deviceRef.current }))

import { getMenuItems } from './Layout'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach } from 'vitest'
import { ErrorProvider } from '../contexts/ErrorContext'
import { useAuthStore } from '../stores/auth'
import Layout from './Layout'
import { authApi } from '../api/auth'
import { notificationApi } from '../api/notification'

/**
 * ⚠️ 通知 mock 的**实现必须在 beforeEach 里给**，不能只写在 `vi.mock` 工厂里：
 *    `vitest.config.ts` 开了 `restoreMocks: true` —— 它在每个用例前对 mock 调 `mockRestore()`，
 *    `vi.fn()` 的默认实现会被清空 → 函数返回 `undefined`。
 *    后果分两种（都曾在旧的工厂写法下静默发生）：
 *      - `getUnreadCount()` → undefined → 读 `.unread_count` 抛错（被 Layout 的 catch 吞掉）；
 *      - `getRecent()` → undefined → `setRecentNotifications(undefined)` →
 *        打开通知面板时 `recentNotifications.length` **直接抛错**（LAYOUT-008 首跑即现）。
 */
beforeEach(() => {
  vi.mocked(notificationApi.getUnreadCount).mockResolvedValue({ unread_count: 0 } as never)
  vi.mocked(notificationApi.getRecent).mockResolvedValue([] as never)
})

/**
 * 把 antd 菜单树拍平成 key 列表。
 * 说明：菜单是嵌套结构（含 `type: 'divider'` 这类无 key 项），断言"有哪些入口"前必须先拍平。
 */
function flatKeys(items: unknown): string[] {
  const out: string[] = []
  const walk = (list: unknown): void => {
    if (!Array.isArray(list)) return
    list.forEach((item) => {
      if (!item || typeof item !== 'object') return
      const node = item as { key?: unknown; children?: unknown }
      if (typeof node.key === 'string') out.push(node.key)
      if (node.children) walk(node.children)
    })
  }
  walk(items)
  return out
}

describe('getMenuItems（用户类型 → 菜单可见性）', () => {
  it('TC-FE-LAYOUT-001: super_admin 只看到超级管理入口', () => {
    const keys = flatKeys(getMenuItems('super_admin'))

    expect(keys).toContain('/superadmin')
    expect(keys).toContain('/superadmin/audit')
    // 不得出现 admin / developer / owner 的入口
    expect(keys.filter((k) => k.startsWith('/admin'))).toEqual([])
    expect(keys.filter((k) => k.startsWith('/developer'))).toEqual([])
    expect(keys).not.toContain('/owner/repos')
  })

  it('TC-FE-LAYOUT-002: admin 含财务对账与计费配置子菜单，且无超管入口', () => {
    const keys = flatKeys(getMenuItems('admin'))

    expect(keys).toContain('/admin/reconciliation')
    expect(keys).toContain('/admin/recharge-records')
    expect(keys).toContain('/admin/pricing-config')
    expect(keys).toContain('/admin/monthly-bills')
    // 越权可见性：管理员不应看到超级管理员专属入口
    expect(keys.filter((k) => k.startsWith('/superadmin'))).toEqual([])
  })

  it('TC-FE-LAYOUT-003: developer 含仓库市场与仓库管理，且无 admin/superadmin 入口', () => {
    const keys = flatKeys(getMenuItems('developer'))

    expect(keys).toContain('/developer/repos') // 仓库市场（可预览所有仓库）
    expect(keys).toContain('/owner/repos') // 仓库管理（仅自己的）
    expect(keys).toContain('/developer/keys')
    expect(keys.filter((k) => k.startsWith('/admin'))).toEqual([])
    expect(keys.filter((k) => k.startsWith('/superadmin'))).toEqual([])
  })

  it('TC-FE-LAYOUT-004: 普通用户只能看到 /user/*，且绝不出现 API Keys 入口', () => {
    const keys = flatKeys(getMenuItems('user'))

    expect(keys).toContain('/user/repos')
    expect(keys.length).toBeGreaterThan(0)
    // 全部入口都在 /user 命名空间下（普通用户只读，不能建 Key / 调 API）
    expect(keys.every((k) => k.startsWith('/user'))).toBe(true)
    expect(keys).not.toContain('/developer/keys')
  })

  it('TC-FE-LAYOUT-005: owner 含 owner 专属的数据分析与收益结算', () => {
    const keys = flatKeys(getMenuItems('owner'))

    expect(keys).toContain('/owner/analytics')
    expect(keys).toContain('/owner/settlement')
    expect(keys).toContain('/owner/repos')
  })

  it('TC-FE-LAYOUT-006: 未知 userType 兜底为普通用户菜单（不泄露任何管理入口）', () => {
    const keys = flatKeys(getMenuItems('ghost-type'))

    expect(keys.every((k) => k.startsWith('/user'))).toBe(true)
    expect(keys).not.toContain('/admin')
    expect(keys).not.toContain('/developer/keys')
    // 缺省参数路径同样安全
    expect(flatKeys(getMenuItems(''))).toEqual(keys)
  })
})

// ==================== 组件级渲染与登出（TC-FE-LAYOUT-007/008）====================
// 与 001~006 的差异：那组测「给定角色应有哪些菜单」的纯函数；
// 这组测「登录用户真的打开页面后，菜单/用户区渲染出来、登出链路真的清空登录态」。

const mockUser = {
  id: 'u1',
  username: 'devadmin',
  email: 'dev@example.com',
  user_type: 'developer',
  role: 'developer',
  permissions: [],
}

function renderLayout() {
  return render(
    <MemoryRouter
      initialEntries={['/developer/dashboard']}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <ErrorProvider>
        <Layout />
      </ErrorProvider>
    </MemoryRouter>
  )
}

describe('Layout 组件渲染与登出', () => {
  beforeEach(() => {
    // forceRefreshUser 内部会调 authApi.me；即便形状不符也会被 Layout 的 try/catch 吞掉
    vi.mocked(authApi.me).mockResolvedValue({ code: 0, data: mockUser } as never)
    useAuthStore.setState({
      user: mockUser,
      accessToken: 'tok',
      refreshToken: 'r',
    } as never)
  })

  it('TC-FE-LAYOUT-007: 登录用户进入布局后渲染出菜单入口与用户信息', async () => {
    renderLayout()

    // 顶栏用户名（username 优先于 email 前缀）
    expect(await screen.findByText('devadmin')).toBeInTheDocument()
    // 菜单已渲染且含可点击项
    expect(screen.getAllByRole('menuitem').length).toBeGreaterThan(0)
    // 越权可见性呼应 001~006：developer 的 DOM 中不得出现超管入口
    expect(screen.queryByText(/超级管理/)).not.toBeInTheDocument()
  })

  it('TC-FE-LAYOUT-008: 「退出登录」调用后端登出并清空本地登录态', async () => {
    const user = userEvent.setup()
    renderLayout()
    await screen.findByText('devadmin')

    // 打开用户下拉（antd Dropdown 可能是 hover 或 click 触发，两种都兼容）
    const trigger = screen.getByText('devadmin')
    await user.click(trigger)
    let logoutItem = screen.queryByText('退出登录')
    if (!logoutItem) {
      await user.hover(trigger)
      logoutItem = await screen.findByText('退出登录')
    }
    await user.click(logoutItem)

    // 后端登出被调用；本地登录态（store.user）被清空
    await waitFor(() => expect(vi.mocked(authApi.logout)).toHaveBeenCalled())
    await waitFor(() => expect(useAuthStore.getState().user).toBeNull())
  })
})

// ==================== C 轮新增：响应式骨架与通知中心（TC-FE-LAYOUT-009~011）====================
// 为什么补：001~008 全部在**桌面形态**下渲染，两条真实分支从未跑到 ——
//   ① 移动端骨架（源码：移动端**完全不渲染 Sider**，改用抽屉 Drawer + 汉堡按钮）；
//   ② 通知未读数落到铃铛徽标、「全部已读」链路。

/** 带路由的布局渲染：菜单点击后的跳转必须由真实 <Routes> 才能断言 */
function renderLayoutRoutes() {
  return render(
    <MemoryRouter
      initialEntries={['/']}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <ErrorProvider>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<div>DASHBOARD_STUB</div>} />
          </Route>
          <Route path="/developer/billing" element={<div>BILLING_STUB</div>} />
          <Route path="/notifications" element={<div>NOTIFICATIONS_STUB</div>} />
        </Routes>
      </ErrorProvider>
    </MemoryRouter>
  )
}

describe('Layout 响应式骨架与通知中心', () => {
  beforeEach(() => {
    vi.mocked(authApi.me).mockResolvedValue({ code: 0, data: mockUser } as never)
    // 每个用例都从"桌面 + 无未读"这一干净状态出发（011 会临时改写成有未读）
    deviceRef.current = { isMobile: false, isTablet: false, isDesktop: true, isLargeDesktop: false }
    vi.mocked(notificationApi.getUnreadCount).mockResolvedValue({ unread_count: 0 } as never)
    vi.mocked(notificationApi.getRecent).mockResolvedValue([] as never)
    useAuthStore.setState({
      user: mockUser,
      accessToken: 'tok',
      refreshToken: 'r',
    } as never)
  })

  afterEach(() => {
    deviceRef.current = { isMobile: false, isTablet: false, isDesktop: true, isLargeDesktop: false }
  })

  it('TC-FE-LAYOUT-009: 移动端改用抽屉：汉堡按钮打开、点菜单项跳转并自动关闭抽屉', async () => {
    deviceRef.current = { isMobile: true, isTablet: false, isDesktop: false, isLargeDesktop: false }
    const user = userEvent.setup()
    const { container } = renderLayoutRoutes()

    // 移动端**不渲染 Sider**（源码注释：避免 CSS 隐藏失效）→ 菜单只会出现在抽屉里
    expect(container.querySelector('.ant-layout-sider')).toBeNull()
    // ⚠️ `MenuOutlined` 渲染出的 class 是 `anticon-menu`（图标名就是 'menu'，**不带** outlined
    //    后缀）；带后缀的是折叠/展开那对（`anticon-menu-fold` / `anticon-menu-unfold`）。
    //    首跑按 `.anticon-menu-outlined` 查不到元素。
    const trigger = container.querySelector('.anticon-menu')
    expect(trigger, '移动端应显示汉堡菜单按钮').toBeTruthy()
    // 抽屉未打开前，菜单项不在 DOM（antd Drawer 首次打开才挂载 children）
    expect(screen.queryByText('账单中心')).not.toBeInTheDocument()

    await user.click(trigger as Element)
    await user.click(await screen.findByText('账单中心'))

    // ① 跳转到菜单 key 对应的路由
    expect(await screen.findByText('BILLING_STUB')).toBeInTheDocument()
    // ② 抽屉自动关闭（源码 onClick 里 setDrawerVisible(false)）。
    //    ⚠️ 抽屉挂在 document 的 portal 上，不在 container 里，必须查 document
    await waitFor(() => expect(document.querySelector('.ant-drawer-open')).toBeNull())
  })

  it('TC-FE-LAYOUT-010: 桌面端侧边栏折叠/展开（折叠时隐藏 logo 文案与类型标签）', async () => {
    const user = userEvent.setup()
    const { container } = renderLayoutRoutes()
    await screen.findByText('devadmin')

    // 展开态：logo 文案「Platform」可见
    expect(screen.getByText('Platform')).toBeInTheDocument()

    await user.click(container.querySelector('.anticon-menu-fold') as Element)
    await waitFor(() => expect(screen.queryByText('Platform')).not.toBeInTheDocument())
    // 折叠态给的是「展开」按钮
    expect(container.querySelector('.anticon-menu-unfold')).toBeTruthy()

    await user.click(container.querySelector('.anticon-menu-unfold') as Element)
    expect(await screen.findByText('Platform')).toBeInTheDocument()
  })

  it('TC-FE-LAYOUT-011: 未读数落到铃铛徽标；「全部已读」调后端并刷新未读数', async () => {
    let unread = 3
    vi.mocked(notificationApi.getUnreadCount).mockImplementation(
      async () => ({ unread_count: unread }) as never
    )
    vi.mocked(notificationApi.getRecent).mockResolvedValue([
      {
        id: 'n1',
        title: '账户余额不足',
        content: '请及时充值以免影响调用',
        created_at: new Date().toISOString(),
      },
    ] as never)

    const user = userEvent.setup()
    const { container } = renderLayoutRoutes()

    // ① 未读数 → 铃铛徽标
    await waitFor(() =>
      expect(container.querySelector('.ant-badge-count')?.textContent).toContain('3')
    )

    // ② 打开通知面板：未读条数与最近通知
    await user.click(container.querySelector('.anticon-bell') as Element)
    expect(await screen.findByText('通知中心')).toBeInTheDocument()
    expect(screen.getByText('3 条未读')).toBeInTheDocument()
    expect(screen.getByText('账户余额不足')).toBeInTheDocument()

    // ③ 全部已读 → 调后端；随后重新拉未读数（mock 改为 0）→ 面板转为「暂无未读」
    unread = 0
    await user.click(screen.getByText('全部已读'))
    await waitFor(() => expect(vi.mocked(notificationApi.markAllAsRead)).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(screen.getByText('暂无未读')).toBeInTheDocument())
  })

  it('TC-FE-LAYOUT-012: 点击通知项标记该条已读并跳转通知页', async () => {
    vi.mocked(notificationApi.getUnreadCount).mockResolvedValue({ unread_count: 1 } as never)
    vi.mocked(notificationApi.getRecent).mockResolvedValue([
      {
        id: 'n1',
        title: '账户余额不足',
        content: '请及时充值以免影响调用',
        created_at: new Date().toISOString(),
      },
    ] as never)

    const user = userEvent.setup()
    const { container } = renderLayoutRoutes()
    await waitFor(() =>
      expect(container.querySelector('.ant-badge-count')?.textContent).toContain('1')
    )

    await user.click(container.querySelector('.anticon-bell') as Element)
    await user.click(await screen.findByText('账户余额不足'))

    // ① 按 id 标记该条已读
    await waitFor(() => expect(vi.mocked(notificationApi.markAsRead)).toHaveBeenCalledWith('n1'))
    // ② 跳通知详情页（developer 的 basePath 为空 → /notifications）
    expect(await screen.findByText('NOTIFICATIONS_STUB')).toBeInTheDocument()
  })
})

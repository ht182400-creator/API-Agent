/**
 * P2/P3 页面「首屏成功渲染」测试（TC-FE-ADMINMISC-001 / 003、TC-FE-DEVMISC-001）
 *
 * 与同目录 `MiscPages.spec.tsx` 的分工：
 *   - `MiscPages.spec.tsx`：**接口全挂**时页面不白屏、骨架仍在（错误分支）；
 *   - 本文件：**接口全部成功返回**时首屏能渲染出内容，且确实调用了数据源（成功分支）。
 *
 * 手法：对每个 api 模块用「**把对象上的所有函数自动替换成成功返回的 mock**」
 * （`resolveAll`）——不需要枚举方法名，也不用 Proxy（vitest 对 Proxy mock 的导出校验会挂死）。
 * 同时登记这些 mock，用 `anyCalled()` 断言"这一页真的去拉数据了"（而不是渲染了个空壳）。
 *
 * ⚠️ 本层只保证「不崩 + 有内容 + 调了数据源」，**不做字段级断言** ——
 *    逐页字段正确性由各自的专属 spec（Keys / Quota / Billing / PricingConfig / Reconciliation …）承担。
 *
 * ⚠️ `restoreMocks: true` 会在每个用例前把 vi.fn() 的实现清掉 → 必须用
 *    `beforeEach(reapply)` 把「成功返回」重新装回去（本文件实测踩过）。
 */
import type { ReactElement } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { waitFor } from '@testing-library/react'

const H = vi.hoisted(() => {
  /**
   * 通用「空成功」载荷。
   *
   * ⚠️ 必须**同时**满足两种接口形态 —— 各页面的接口不统一：
   *   - 有的返回分页对象：`{ items, total, pagination }`；`members` / `channels` …
   *   - 有的**直接返回数组**：页面会立刻 `.map()` / `.reduce()` / `.some()`
   * 若只给对象，后者会在渲染期抛 `xxx.reduce is not a function` → React 卸载整棵树 →
   * 页面变空白（首跑实测：owner/Analytics、superadmin/Roles 就是被这个坑到）。
   * 因此这里返回「**带数组方法的空对象**」：取字段有值、调数组方法返回空结果。
   */
  const payload = () => ({
    // —— 常见字段 ——
    items: [],
    total: 0,
    users: [],
    roles: [],
    configs: [],
    accounts: [],
    channels: [],
    repos: [],
    files: [],
    backups: [],
    lines: [],
    notifications: [],
    logs: [],
    members: [],
    tasks: [],
    pagination: { page: 1, page_size: 10, total: 0, total_pages: 0 },
    generated_at: '2026-09-17T00:00:00.000Z',
    length: 0,
    // 备份配置的最小合法形状（admin/Settings 首屏要读它）
    config: {
      enabled: true,
      max_file_size_mb: 50,
      max_backup_files: 200,
      auto_cleanup: true,
      cleanup_threshold: 75,
    },
    // —— 数组方法（一律返回空结果，保证链式调用不炸）——
    map: () => [],
    filter: () => [],
    slice: () => [],
    concat: () => [],
    flat: () => [],
    flatMap: () => [],
    sort: () => [],
    reverse: () => [],
    join: () => '',
    some: () => false,
    every: () => true,
    find: () => undefined,
    findIndex: () => -1,
    indexOf: () => -1,
    includes: () => false,
    forEach: () => {},
    reduce: (_fn: unknown, init?: unknown) => (init === undefined ? 0 : init),
    reduceRight: (_fn: unknown, init?: unknown) => (init === undefined ? 0 : init),
  })

  const registry: Array<Record<string, unknown>> = []

  /**
   * 把对象上的所有函数替换为「成功返回」的 mock，并登记（供 anyCalled / reapply 使用）。
   * 既可传真实的 api 对象，也可传"只有方法名的占位对象"来构造具名函数导出模块。
   */
  const resolveAll = (obj?: Record<string, unknown>) => {
    if (!obj || typeof obj !== 'object') return obj
    const out: Record<string, unknown> = { ...obj }
    for (const key of Object.keys(out)) {
      if (typeof out[key] === 'function') out[key] = vi.fn().mockResolvedValue(payload())
    }
    registry.push(out)
    return out
  }

  /** 是否至少有一个被登记的 api 方法被调用过 */
  const anyCalled = () =>
    registry.some((o) =>
      Object.values(o).some((f) => ((f as { mock?: { calls: unknown[] } })?.mock?.calls.length ?? 0) > 0)
    )

  /** 重新装回「成功返回」（restoreMocks 会清掉实现） */
  const reapply = () => {
    for (const o of registry) {
      for (const f of Object.values(o)) {
        const fn = f as { mockResolvedValue?: (v: unknown) => void }
        fn?.mockResolvedValue?.(payload())
      }
    }
  }

  return { resolveAll, anyCalled, reapply }
})

const { messageSpies } = vi.hoisted(() => ({
  messageSpies: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

vi.mock('antd', async (importOriginal) => {
  const actual = await importOriginal<typeof import('antd')>()
  return {
    ...actual,
    // ⚠️ 必须同时提供 `useMessage`：有的页用 hook 版提示（`message.useMessage()`），
    //    只给静态方法会报 "message.useMessage is not a function"（首跑实测）。
    message: { ...messageSpies, useMessage: () => [messageSpies, null] },
  }
})

// ---- api 模块：保留纯数据导出（userTypeLabels 等），只把方法换成「成功返回」----
vi.mock('../../api/superadmin', async (io) => {
  const actual = await io<typeof import('../../api/superadmin')>()
  return {
    ...actual,
    dashboardApi: H.resolveAll(actual.dashboardApi as never),
    userApi: H.resolveAll(actual.userApi as never),
    roleApi: H.resolveAll(actual.roleApi as never),
    configApi: H.resolveAll(actual.configApi as never),
  }
})
vi.mock('../../api/admin', async (io) => {
  const actual = await io<typeof import('../../api/admin')>()
  return {
    ...actual,
    adminUserApi: H.resolveAll(actual.adminUserApi as never),
    adminApi: H.resolveAll(actual.adminApi as never),
  }
})
vi.mock('../../api/adminLogs', async (io) => {
  const actual = await io<typeof import('../../api/adminLogs')>()
  // ⚠️ 该模块是**具名函数导出** → 用占位对象交给 resolveAll，逐个换成成功返回的 mock，
  //    并登记进 registry（否则 admin/Settings 这类"只调 getBackupConfig"的页会被误判为没调数据源）。
  const mocked = H.resolveAll({
    getLogFiles: () => {},
    getLogContent: () => {},
    getLogStats: () => {},
    getBackups: () => {},
    getBackupConfig: () => {},
    updateBackupConfig: () => {},
    deleteBackup: () => {},
    cleanupBackups: () => {},
    manualBackup: () => {},
    getBackupContent: () => {},
  }) as Record<string, unknown>
  return { ...actual, ...mocked }
})
vi.mock('../../api/adminReconciliation', async (io) => {
  const actual = await io<typeof import('../../api/adminReconciliation')>()
  return { ...actual, adminReconciliationApi: H.resolveAll(actual.adminReconciliationApi as never) }
})
vi.mock('../../api/billing', async (io) => {
  const actual = await io<typeof import('../../api/billing')>()
  return { ...actual, billingApi: H.resolveAll(actual.billingApi as never) }
})
vi.mock('../../api/repo', async (io) => {
  const actual = await io<typeof import('../../api/repo')>()
  return { ...actual, repoApi: H.resolveAll(actual.repoApi as never) }
})
vi.mock('../../api/user', async (io) => {
  const actual = await io<typeof import('../../api/user')>()
  return { ...actual, userApi: H.resolveAll(actual.userApi as never) }
})
vi.mock('../../api/notification', async (io) => {
  const actual = await io<typeof import('../../api/notification')>()
  return { ...actual, notificationApi: H.resolveAll(actual.notificationApi as never) }
})
vi.mock('../../api/analytics', async (io) => {
  const actual = await io<typeof import('../../api/analytics')>()
  return { ...actual, analyticsApi: H.resolveAll(actual.analyticsApi as never) }
})
vi.mock('../../api/quota', async (io) => {
  const actual = await io<typeof import('../../api/quota')>()
  return { ...actual, quotaApi: H.resolveAll(actual.quotaApi as never) }
})

import AdminUsers from '../admin/Users'
import AdminSettings from '../admin/Settings'
import AdminRechargeRecords from '../admin/RechargeRecords'
import AdminPlatformAccounts from '../admin/PlatformAccounts'
import AdminDashboard from '../admin/Dashboard'
import AdminChannelSummary from '../admin/ChannelSummary'
import AdminMonthlyBills from '../admin/AdminMonthlyBills'
import DevTools from '../admin/DevTools'
import DeveloperDashboard from '../developer/Dashboard'
import DeveloperUsage from '../developer/Usage'
import DeveloperRepos from '../developer/Repos'
import UserDashboard from '../user/UserDashboard'
import Notifications from '../notifications/Notifications'
import OwnerDashboard from '../owner/Dashboard'
import OwnerAnalytics from '../owner/Analytics'
import OwnerSettlement from '../owner/Settlement'
import PaymentSuccess from '../PaymentSuccess'
import SuperAdminDashboard from '../superadmin/SuperAdminDashboard'
import SuperAdminUsers from '../superadmin/SuperAdminUsers'
import SuperAdminRoles from '../superadmin/SuperAdminRoles'
import SuperAdminSystem from '../superadmin/SuperAdminSystem'
import { renderWithProviders } from '../../test/renderWithProviders'

interface PageCase {
  name: string
  el: ReactElement
  route: string
  /** 该页是否会去拉数据（DevTools 是纯前端工具页，不拉） */
  hasApi: boolean
}

const ADMIN_PAGES: PageCase[] = [
  { name: 'admin/Users', el: <AdminUsers />, route: '/admin/users', hasApi: true },
  { name: 'admin/Settings', el: <AdminSettings />, route: '/admin/settings', hasApi: true },
  { name: 'admin/RechargeRecords', el: <AdminRechargeRecords />, route: '/admin/recharge-records', hasApi: true },
  { name: 'admin/PlatformAccounts', el: <AdminPlatformAccounts />, route: '/admin/platform-accounts', hasApi: true },
  { name: 'admin/Dashboard', el: <AdminDashboard />, route: '/admin', hasApi: true },
  { name: 'admin/ChannelSummary', el: <AdminChannelSummary />, route: '/admin/channel-summary', hasApi: true },
  { name: 'admin/AdminMonthlyBills', el: <AdminMonthlyBills />, route: '/admin/monthly-bills', hasApi: true },
  { name: 'admin/DevTools（纯前端工具页）', el: <DevTools />, route: '/admin/devtools', hasApi: false },
]

const DEV_PAGES: PageCase[] = [
  { name: 'developer/Dashboard', el: <DeveloperDashboard />, route: '/developer', hasApi: true },
  { name: 'developer/Usage', el: <DeveloperUsage />, route: '/developer/usage', hasApi: true },
  { name: 'developer/Repos', el: <DeveloperRepos />, route: '/developer/repos', hasApi: true },
  { name: 'user/UserDashboard', el: <UserDashboard />, route: '/user', hasApi: true },
  { name: 'notifications/Notifications', el: <Notifications />, route: '/notifications', hasApi: true },
  { name: 'owner/Dashboard', el: <OwnerDashboard />, route: '/owner', hasApi: true },
  { name: 'owner/Analytics', el: <OwnerAnalytics />, route: '/owner/analytics', hasApi: true },
  { name: 'owner/Settlement', el: <OwnerSettlement />, route: '/owner/settlement', hasApi: true },
  { name: 'PaymentSuccess', el: <PaymentSuccess />, route: '/payment-success', hasApi: false },
  { name: 'superadmin/SuperAdminDashboard', el: <SuperAdminDashboard />, route: '/superadmin', hasApi: true },
  { name: 'superadmin/SuperAdminUsers', el: <SuperAdminUsers />, route: '/superadmin/users', hasApi: true },
  { name: 'superadmin/SuperAdminRoles', el: <SuperAdminRoles />, route: '/superadmin/roles', hasApi: true },
  { name: 'superadmin/SuperAdminSystem', el: <SuperAdminSystem />, route: '/superadmin/system', hasApi: true },
]

beforeEach(() => {
  H.reapply() // ⚠️ restoreMocks 会清掉实现，必须重装
})

describe('接口全部成功返回时的首屏渲染（TC-FE-ADMINMISC-001 / TC-FE-DEVMISC-001）', () => {
  it.each(ADMIN_PAGES)('$name：渲染出内容', async ({ el, route }) => {
    const { container } = renderWithProviders(el, { route })
    await waitFor(() =>
      expect((container.textContent || '').replace(/\s/g, '').length).toBeGreaterThan(20)
    )
  })

  it.each(DEV_PAGES)('$name：渲染出内容', async ({ el, route }) => {
    const { container } = renderWithProviders(el, { route })
    await waitFor(() =>
      expect((container.textContent || '').replace(/\s/g, '').length).toBeGreaterThan(20)
    )
  })
})

describe('关键操作会调用预期数据源（TC-FE-ADMINMISC-003）', () => {
  it.each([...ADMIN_PAGES, ...DEV_PAGES].filter((p) => p.hasApi))(
    '$name：至少调用了一个数据源接口',
    async ({ el, route }) => {
      renderWithProviders(el, { route })
      await waitFor(() => expect(H.anyCalled()).toBe(true))
    }
  )
})

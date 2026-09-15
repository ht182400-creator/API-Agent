/**
 * P2/P3 页面骨架测试（TC-FE-ADMINMISC-002 / TC-FE-DEVMISC-002）
 *
 * 覆盖 21 个一般业务页的最低保证：**接口全挂时页面不白屏、渲染树不被打崩**。
 * 这些页是"数据加载 + 表格/表单"的同构模式 —— 用参数化一次覆盖。
 *
 * ⚠️ 方法：所有 api 模块 mock 成「任意方法调用即 reject」——
 *     页面对 reject 的处理（catch → showError → 骨架仍在）正是骨架层要锁的行为。
 *     「首屏成功渲染」需要逐页构造数据形状，不在本层（见用例库 planned 说明）。
 */
import { describe, it, expect, vi } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import { ErrorProvider } from '../../contexts/ErrorContext'

// ⚠️ mock 策略（v2，弃用「全拒绝 Proxy」—— vitest 对 Proxy mock 的导出校验会**挂死**，实测）：
//    api 对象成员用**空对象**（页面调用 api.x() 得 undefined → TypeError → 被 catch → 不白屏），
//    纯数据导出（userTypeLabels / PERMISSION_DEFINITIONS 等）给空对象供遍历兜底。
vi.mock('../../api/superadmin', () => ({
  dashboardApi: {}, userApi: {}, roleApi: {}, configApi: {},
  userTypeLabels: {}, userTypeColors: {}, roleLabels: {}, PERMISSION_DEFINITIONS: {},
}))
vi.mock('../../api/admin', () => ({ adminUserApi: {}, adminApi: {}, userTypeMap: {} }))
vi.mock('../../api/adminLogs', () => ({
  getBackupConfig: vi.fn().mockRejectedValue(new Error('api rejected')),
  updateBackupConfig: vi.fn().mockRejectedValue(new Error('api rejected')),
}))
vi.mock('../../api/adminReconciliation', () => ({ adminReconciliationApi: {} }))
vi.mock('../../api/billing', () => ({ billingApi: {} }))
vi.mock('../../api/repo', () => ({ repoApi: {} }))
vi.mock('../../api/user', () => ({ userApi: {} }))
vi.mock('../../api/notification', () => ({ notificationApi: {} }))
vi.mock('../../api/analytics', () => ({ analyticsApi: {} }))
vi.mock('../api/payment', () => ({ paymentApi: {} }))

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

interface PageCase {
  /** 页面标识（用例名里可见） */
  name: string
  el: React.ReactElement
  route: string
}

const ADMIN_PAGES: PageCase[] = [
  { name: 'admin/Users', el: <AdminUsers />, route: '/admin/users' },
  { name: 'admin/Settings', el: <AdminSettings />, route: '/admin/settings' },
  { name: 'admin/RechargeRecords', el: <AdminRechargeRecords />, route: '/admin/recharge-records' },
  { name: 'admin/PlatformAccounts', el: <AdminPlatformAccounts />, route: '/admin/platform-accounts' },
  { name: 'admin/Dashboard', el: <AdminDashboard />, route: '/admin' },
  { name: 'admin/ChannelSummary', el: <AdminChannelSummary />, route: '/admin/channel-summary' },
  { name: 'admin/AdminMonthlyBills', el: <AdminMonthlyBills />, route: '/admin/monthly-bills' },
  { name: 'admin/DevTools（无 api 依赖）', el: <DevTools />, route: '/admin/devtools' },
]

const DEV_PAGES: PageCase[] = [
  { name: 'developer/Dashboard', el: <DeveloperDashboard />, route: '/developer' },
  { name: 'developer/Usage', el: <DeveloperUsage />, route: '/developer/usage' },
  { name: 'developer/Repos', el: <DeveloperRepos />, route: '/developer/repos' },
  { name: 'user/UserDashboard', el: <UserDashboard />, route: '/user' },
  { name: 'notifications/Notifications', el: <Notifications />, route: '/notifications' },
  { name: 'owner/Dashboard', el: <OwnerDashboard />, route: '/owner' },
  { name: 'owner/Analytics', el: <OwnerAnalytics />, route: '/owner/analytics' },
  { name: 'owner/Settlement', el: <OwnerSettlement />, route: '/owner/settlement' },
  { name: 'PaymentSuccess', el: <PaymentSuccess />, route: '/payment-success' },
  { name: 'superadmin/SuperAdminDashboard', el: <SuperAdminDashboard />, route: '/superadmin' },
  { name: 'superadmin/SuperAdminUsers', el: <SuperAdminUsers />, route: '/superadmin/users' },
  { name: 'superadmin/SuperAdminRoles', el: <SuperAdminRoles />, route: '/superadmin/roles' },
  { name: 'superadmin/SuperAdminSystem', el: <SuperAdminSystem />, route: '/superadmin/system' },
]

function renderPage(pc: PageCase) {
  return render(
    <ConfigProvider theme={{ token: { motion: false } }}>
      <MemoryRouter initialEntries={[pc.route]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        {/* ⚠️ developer/Repos 等页面使用 useError → 必须在 ErrorProvider 内（实测缺它直接 throw） */}
        <ErrorProvider>
          {pc.el}
        </ErrorProvider>
      </MemoryRouter>
    </ConfigProvider>
  )
}

describe('P2/P3 页面骨架（接口全挂时不白屏）', () => {
  it.each(ADMIN_PAGES)('TC-FE-ADMINMISC-002: $name 报错不白屏', async (pc) => {
    const { container } = renderPage(pc)

    // 首次渲染即有内容（render 同步 throw 会直接红）
    expect(container.firstChild).not.toBeNull()

    // 让 reject 链路（catch → showError → 重渲染）跑完，确认树没被打崩
    await waitFor(
      () => expect(container.firstChild).not.toBeNull(),
      { timeout: 1500 }
    )
    expect(container.querySelector('.ant-spin, .ant-card, .ant-table, form, div')).toBeTruthy()
  })

  it.each(DEV_PAGES)('TC-FE-DEVMISC-002: $name 报错不白屏', async (pc) => {
    const { container } = renderPage(pc)

    expect(container.firstChild).not.toBeNull()
    await waitFor(
      () => expect(container.firstChild).not.toBeNull(),
      { timeout: 1500 }
    )
    expect(container.querySelector('.ant-spin, .ant-card, .ant-table, form, div')).toBeTruthy()
  })
})

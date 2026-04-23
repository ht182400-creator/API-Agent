import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/auth'
import { ErrorProvider } from './contexts/ErrorContext'
import Layout from './components/Layout'
import Login from './pages/auth/Login'
import Register from './pages/auth/Register'
import DeveloperDashboard from './pages/developer/Dashboard'
import DeveloperKeys from './pages/developer/Keys'
import DeveloperQuota from './pages/developer/Quota'
import DeveloperLogs from './pages/developer/Logs'
import DeveloperBilling from './pages/developer/Billing'
import DeveloperRecharge from './pages/developer/Recharge'
import DeveloperRepos from './pages/developer/Repos'
import DeveloperUsage from './pages/developer/Usage'
import DeveloperConsumptionDetails from './pages/developer/ConsumptionDetails'
import DeveloperRepoDetail from './pages/developer/RepoDetail'
import OwnerDashboard from './pages/owner/Dashboard'
import OwnerRepos from './pages/owner/Repos'
import OwnerAnalytics from './pages/owner/Analytics'
import OwnerSettlement from './pages/owner/Settlement'
import AdminDashboard from './pages/admin/Dashboard'
import AdminUsers from './pages/admin/Users'
import AdminRepos from './pages/admin/Repos'
import AdminSettings from './pages/admin/Settings'
import AdminLogs from './pages/admin/AdminLogs'
import AdminRechargeRecords from './pages/admin/RechargeRecords'
import AdminChannelSummary from './pages/admin/ChannelSummary'
import AdminPlatformAccounts from './pages/admin/PlatformAccounts'
import AdminReconciliation from './pages/admin/Reconciliation'
import AdminPricingConfig from './pages/admin/PricingConfig'
import AdminMonthlyBills from './pages/admin/AdminMonthlyBills'
import DevTools from './pages/admin/DevTools'
import ApiTester from './pages/developer/ApiTester'
import SuperAdminDashboard from './pages/superadmin/SuperAdminDashboard'
import SuperAdminUsers from './pages/superadmin/SuperAdminUsers'
import SuperAdminRoles from './pages/superadmin/SuperAdminRoles'
import SuperAdminSystem from './pages/superadmin/SuperAdminSystem'
import Notifications from './pages/notifications/Notifications'
import UserDashboard from './pages/user/UserDashboard'

// 用户类型
type UserType = 'super_admin' | 'admin' | 'owner' | 'developer' | 'user'

// 路由守卫 - 只检查登录状态，不限制用户类型
// 用户类型限制通过页面内的组件实现（升级引导等）
const ProtectedRoute = ({ 
  children, 
}: { 
  children: React.ReactNode
}) => {
  const { isAuthenticated } = useAuthStore()
  
  // 只检查是否登录，不限制用户类型
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return <>{children}</>
}

// 根据用户类型获取默认重定向路径
const getDefaultPath = (userType: string): string => {
  switch (userType) {
    case 'super_admin':
      return '/superadmin'
    case 'admin':
      return '/admin'
    case 'owner':
      return '/owner'
    case 'user':
      return '/user'  // 普通用户跳转到 /user
    case 'developer':
    default:
      return '/'  // 开发者跳转到 /
  }
}

function App() {
  const { user, isAuthenticated } = useAuthStore()
  
  // 获取默认重定向路径
  const defaultPath = user ? getDefaultPath(user.user_type) : '/login'
  
  return (
    <ErrorProvider>
    <Routes>
      {/* 公共路由 */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      
      {/* 超级管理员路由 */}
      <Route path="/superadmin" element={
        <ProtectedRoute allowedUserTypes={['super_admin']}>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<SuperAdminDashboard />} />
        <Route path="users" element={<SuperAdminUsers />} />
        <Route path="roles" element={<SuperAdminRoles />} />
        <Route path="system" element={<SuperAdminSystem />} />
        <Route path="audit" element={<SuperAdminDashboard />} />
        <Route path="notifications" element={<Notifications />} />
      </Route>
      
      {/* 管理员路由 */}
      <Route path="/admin" element={
        <ProtectedRoute allowedUserTypes={['admin']}>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<AdminDashboard />} />
        <Route path="users" element={<AdminUsers />} />
        <Route path="repos" element={<AdminRepos />} />
        <Route path="repos/:slug" element={<DeveloperRepoDetail />} />
        <Route path="logs" element={<AdminLogs />} />
        <Route path="settings" element={<AdminSettings />} />
        <Route path="devtools" element={<DevTools />} />
        {/* V2.6 新增：对账相关页面 */}
        <Route path="recharge-records" element={<AdminRechargeRecords />} />
        <Route path="channel-summary" element={<AdminChannelSummary />} />
        <Route path="platform-accounts" element={<AdminPlatformAccounts />} />
        {/* V2.6 新增：对账核心管理 */}
        <Route path="reconciliation" element={<AdminReconciliation />} />
        <Route path="pricing-config" element={<AdminPricingConfig />} />
        <Route path="monthly-bills" element={<AdminMonthlyBills />} />
        <Route path="notifications" element={<Notifications />} />
      </Route>
      
      {/* 【V4.0 重构】仓库所有者路由 */}
      {/* owner 和 developer 使用相同的菜单，但 owner 可以访问更多功能 */}
      <Route path="/owner" element={
        <ProtectedRoute allowedUserTypes={['owner', 'developer']}>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<OwnerDashboard />} />
        <Route path="repos" element={<OwnerRepos />} />
        <Route path="analytics" element={<OwnerAnalytics />} />
        <Route path="settlement" element={<OwnerSettlement />} />
        <Route path="notifications" element={<Notifications />} />
      </Route>
      
      {/* 普通用户路由 - 引导页 */}
      <Route path="/user" element={
        <ProtectedRoute allowedUserTypes={['user']}>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<UserDashboard />} />
        <Route path="repos" element={<DeveloperRepos />} />
        <Route path="quota" element={<DeveloperQuota />} />
        <Route path="billing" element={<DeveloperBilling />} />
        <Route path="recharge" element={<DeveloperRecharge />} />
        <Route path="notifications" element={<Notifications />} />
      </Route>
      
      {/* 【V4.0 重构】开发者路由 - owner 也可以访问 */}
      <Route path="/" element={
        <ProtectedRoute allowedUserTypes={['developer', 'owner']}>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<DeveloperDashboard />} />
        <Route path="developer">
          <Route index element={<DeveloperDashboard />} />
          {/* API Keys 页面 - 普通用户会看到升级引导 */}
          <Route path="keys" element={<DeveloperKeys />} />
          <Route path="quota" element={<DeveloperQuota />} />
          <Route path="logs" element={<DeveloperLogs />} />
          <Route path="billing" element={<DeveloperBilling />} />
          <Route path="usage" element={<DeveloperUsage />} />
          <Route path="consumption-details" element={<DeveloperConsumptionDetails />} />
          <Route path="recharge" element={<DeveloperRecharge />} />
          <Route path="repos" element={<DeveloperRepos />} />
          <Route path="repos/:slug" element={<DeveloperRepoDetail />} />
          <Route path="api-tester" element={<ApiTester />} />
        </Route>
        <Route path="notifications" element={<Notifications />} />
      </Route>
      
      {/* 默认重定向 - 根据用户类型重定向 */}
      <Route path="*" element={<Navigate to={defaultPath} replace />} />
    </Routes>
    </ErrorProvider>
  )
}

export default App

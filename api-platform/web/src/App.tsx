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
import OwnerDashboard from './pages/owner/Dashboard'
import OwnerRepos from './pages/owner/Repos'
import OwnerAnalytics from './pages/owner/Analytics'
import OwnerSettlement from './pages/owner/Settlement'
import AdminDashboard from './pages/admin/Dashboard'
import AdminUsers from './pages/admin/Users'
import AdminRepos from './pages/admin/Repos'
import AdminSettings from './pages/admin/Settings'
import AdminLogs from './pages/admin/AdminLogs'
import DevTools from './pages/admin/DevTools'
import SuperAdminDashboard from './pages/superadmin/SuperAdminDashboard'
import SuperAdminUsers from './pages/superadmin/SuperAdminUsers'
import SuperAdminRoles from './pages/superadmin/SuperAdminRoles'
import SuperAdminSystem from './pages/superadmin/SuperAdminSystem'
import Notifications from './pages/notifications/Notifications'

// 用户类型
type UserType = 'super_admin' | 'admin' | 'owner' | 'developer' | 'user'

// 路由守卫
const ProtectedRoute = ({ 
  children, 
  allowedUserTypes 
}: { 
  children: React.ReactNode
  allowedUserTypes?: UserType[] 
}) => {
  const { isAuthenticated, user } = useAuthStore()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  // 如果指定了允许的用户类型，检查用户类型
  if (allowedUserTypes && user && !allowedUserTypes.includes(user.user_type as UserType)) {
    // 根据用户类型重定向到对应页面
    const userType = user.user_type as UserType
    switch (userType) {
      case 'super_admin':
        return <Navigate to="/superadmin" replace />
      case 'admin':
        return <Navigate to="/admin" replace />
      case 'owner':
        return <Navigate to="/owner" replace />
      case 'developer':
      case 'user':
      default:
        return <Navigate to="/" replace />
    }
  }
  
  return <>{children}</>
}

// 开发者专属路由守卫（仅允许 developer 类型）
const DeveloperOnlyRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, user } = useAuthStore()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  // 仅 developer 类型可以访问
  if (user && user.user_type !== 'developer') {
    return <Navigate to="/" replace />
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
    case 'developer':
    case 'user':
    default:
      return '/'
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
        <Route path="logs" element={<AdminLogs />} />
        <Route path="settings" element={<AdminSettings />} />
        <Route path="devtools" element={<DevTools />} />
        <Route path="notifications" element={<Notifications />} />
      </Route>
      
      {/* 仓库所有者路由 */}
      <Route path="/owner" element={
        <ProtectedRoute allowedUserTypes={['owner']}>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<OwnerDashboard />} />
        <Route path="repos" element={<OwnerRepos />} />
        <Route path="analytics" element={<OwnerAnalytics />} />
        <Route path="settlement" element={<OwnerSettlement />} />
        <Route path="notifications" element={<Notifications />} />
      </Route>
      
      {/* 开发者/普通用户路由 */}
      <Route path="/" element={
        <ProtectedRoute allowedUserTypes={['developer', 'user']}>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<DeveloperDashboard />} />
        <Route path="developer">
          <Route index element={<DeveloperDashboard />} />
          {/* API Keys 仅开发者类型可访问 */}
          <Route path="keys" element={
            <DeveloperOnlyRoute>
              <DeveloperKeys />
            </DeveloperOnlyRoute>
          } />
          <Route path="quota" element={<DeveloperQuota />} />
          <Route path="logs" element={<DeveloperLogs />} />
          <Route path="billing" element={<DeveloperBilling />} />
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

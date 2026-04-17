import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/auth'
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

// 路由守卫
const ProtectedRoute = ({ 
  children, 
  allowedRoles 
}: { 
  children: React.ReactNode
  allowedRoles?: string[] 
}) => {
  const { isAuthenticated, user } = useAuthStore()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  if (allowedRoles && user && !allowedRoles.includes(user.user_type)) {
    return <Navigate to="/" replace />
  }
  
  return <>{children}</>
}

function App() {
  return (
    <Routes>
      {/* 公共路由 */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      
      {/* 开发者控制台 */}
      <Route path="/" element={
        <ProtectedRoute>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<DeveloperDashboard />} />
        
        {/* 开发者路由 */}
        <Route path="developer">
          <Route index element={<DeveloperDashboard />} />
          <Route path="keys" element={<DeveloperKeys />} />
          <Route path="quota" element={<DeveloperQuota />} />
          <Route path="logs" element={<DeveloperLogs />} />
          <Route path="billing" element={<DeveloperBilling />} />
        </Route>
        
        {/* 仓库所有者路由 */}
        <Route path="owner">
          <Route index element={<OwnerDashboard />} />
          <Route path="repos" element={<OwnerRepos />} />
          <Route path="analytics" element={<OwnerAnalytics />} />
          <Route path="settlement" element={<OwnerSettlement />} />
        </Route>
        
        {/* 管理员路由 */}
        <Route path="admin">
          <Route index element={<AdminDashboard />} />
          <Route path="users" element={<AdminUsers />} />
          <Route path="repos" element={<AdminRepos />} />
          <Route path="logs" element={<AdminLogs />} />
          <Route path="settings" element={<AdminSettings />} />
        </Route>
      </Route>
      
      {/* 默认重定向 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App

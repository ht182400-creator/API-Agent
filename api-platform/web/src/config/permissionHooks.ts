/**
 * 权限守卫 Hook
 * 提供基于用户类型和权限的访问控制
 */

import { useMemo } from 'react'
import { useAuthStore } from '../stores/auth'
import { Permission, RolePermissions, hasPermission, hasRole, RoutePermissions, PermissionKey, Role, UserType } from './permissions'

// Hook: 获取用户所有权限
export function usePermissions(): PermissionKey[] {
  const { user } = useAuthStore()
  
  return useMemo(() => {
    if (!user) return []
    
    // 如果用户有自定义权限，使用自定义权限
    if (user.permissions && user.permissions.length > 0) {
      return user.permissions as PermissionKey[]
    }
    
    // 否则使用角色默认权限
    const role = user.role as Role || 'user'
    return RolePermissions[role] || RolePermissions.user
  }, [user?.role, user?.permissions])
}

// Hook: 检查是否有指定权限
export function useHasPermission(required: PermissionKey | PermissionKey[]): boolean {
  const permissions = usePermissions()
  return hasPermission(permissions, required)
}

// Hook: 检查用户角色
export function useHasRole(requiredRole: Role | Role[]): boolean {
  const { user } = useAuthStore()
  if (!user) return false
  return hasRole(user.role as Role, requiredRole)
}

// Hook: 检查是否为超级管理员
export function useIsSuperAdmin(): boolean {
  return useHasRole('super_admin')
}

// Hook: 检查是否为管理员
export function useIsAdmin(): boolean {
  return useHasRole(['super_admin', 'admin'])
}

// Hook: 检查是否为仓库所有者
export function useIsOwner(): boolean {
  const { user } = useAuthStore()
  return user?.user_type === 'owner'
}

// Hook: 检查用户类型
export function useUserType(): UserType | null {
  const { user } = useAuthStore()
  return (user?.user_type as UserType) || null
}

// Hook: 检查是否可以访问指定路由
export function useCanAccessRoute(path: string): boolean {
  const { user } = useAuthStore()
  const permissions = usePermissions()
  
  return useMemo(() => {
    if (!user) return false
    
    // 查找路由配置
    const route = RoutePermissions.find(r => path.startsWith(r.path))
    if (!route) return true // 未配置的路由默认允许
    
    // 检查用户类型
    if (!route.userTypes.includes(user.user_type as UserType)) {
      return false
    }
    
    // 检查权限
    if (route.requiredPermissions) {
      return hasPermission(permissions, route.requiredPermissions)
    }
    
    return true
  }, [user?.user_type, user?.role, user?.permissions, path, permissions])
}

// 权限检查组件 Props
interface RequirePermissionProps {
  permission?: PermissionKey | PermissionKey[]
  role?: Role | Role[]
  userType?: UserType | UserType[]
  children: React.ReactNode
  fallback?: React.ReactNode
}

// 组件: 权限控制
export function RequirePermission({ 
  permission, 
  role, 
  userType, 
  children, 
  fallback = null 
}: RequirePermissionProps) {
  const hasPermissionAccess = useHasPermission(permission || ['*'])
  const hasRoleAccess = useHasRole(role || 'user')
  const { user } = useAuthStore()
  
  const hasUserTypeAccess = useMemo(() => {
    if (!userType) return true
    const types = Array.isArray(userType) ? userType : [userType]
    return types.includes(user?.user_type as UserType)
  }, [user?.user_type, userType])
  
  if (hasPermissionAccess && hasRoleAccess && hasUserTypeAccess) {
    return <>{children}</>
  }
  
  return <>{fallback}</>
}

// 导出常量供其他模块使用
export { Permission, hasPermission, hasRole }

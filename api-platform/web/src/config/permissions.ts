/**
 * 权限配置 - 角色与权限定义
 * 
 * 用户类型 (user_type) 与角色 (role) 区别：
 * - user_type: 标识用户在平台中的业务角色（决定功能入口）
 * - role: 标识用户在系统中的权限级别
 * 
 * 权限格式: "resource:action"
 * - resource: 模块名称 (user, api, repo, billing, system, log)
 * - action: 操作类型 (read, write, manage, delete)
 */

// 角色定义
export type Role = 'super_admin' | 'admin' | 'developer' | 'user'

// 用户类型定义
export type UserType = 'super_admin' | 'admin' | 'owner' | 'developer' | 'user'

// 权限定义
export const Permission = {
  // 用户相关
  USER_READ: 'user:read',
  USER_WRITE: 'user:write',
  USER_DELETE: 'user:delete',
  USER_MANAGE: 'user:manage',        // 管理所有用户
  USER_ROLE_ASSIGN: 'user:role',     // 分配用户角色
  
  // API Key相关
  API_READ: 'api:read',
  API_WRITE: 'api:write',
  API_DELETE: 'api:delete',
  API_MANAGE: 'api:manage',          // 管理所有API Keys
  
  // 仓库相关
  REPO_READ: 'repo:read',
  REPO_WRITE: 'repo:write',
  REPO_DELETE: 'repo:delete',
  REPO_APPROVE: 'repo:approve',      // 审核仓库
  REPO_MANAGE: 'repo:manage',        // 管理所有仓库
  
  // 账单相关
  BILLING_READ: 'billing:read',
  BILLING_WRITE: 'billing:write',
  BILLING_MANAGE: 'billing:manage',  // 管理所有账单
  BILLING_RECHARGE: 'billing:recharge', // 充值
  
  // 日志相关
  LOG_READ: 'log:read',              // 查看自己的日志
  LOG_ALL: 'log:all',                // 查看所有日志
  
  // 系统相关
  SYSTEM_SETTINGS: 'system:settings', // 系统设置
  SYSTEM_LOGS: 'system:logs',        // 系统日志
  
  // 开发者特有
  DEV_API_KEYS: 'dev:apikeys',       // 管理自己的API Keys
  DEV_QUOTA: 'dev:quota',            // 查看配额
  DEV_BILLING: 'dev:billing',        // 个人账单
  
  // 仓库所有者特有
  OWNER_REPO: 'owner:repo',          // 管理自己的仓库
  OWNER_ANALYTICS: 'owner:analytics', // 数据分析
  OWNER_SETTLEMENT: 'owner:settlement', // 收益结算
} as const

export type PermissionKey = typeof Permission[keyof typeof Permission]

// 各用户类型的默认权限
export const RolePermissions: Record<Role, PermissionKey[]> = {
  // 超级管理员 - 拥有所有权限
  super_admin: ['*'],
  
  // 管理员 - 系统管理和用户管理
  admin: [
    Permission.USER_READ,
    Permission.USER_WRITE,
    Permission.USER_DELETE,
    Permission.USER_MANAGE,
    Permission.API_READ,
    Permission.API_MANAGE,
    Permission.REPO_READ,
    Permission.REPO_APPROVE,
    Permission.REPO_MANAGE,
    Permission.BILLING_READ,
    Permission.BILLING_MANAGE,
    Permission.LOG_ALL,
    Permission.SYSTEM_SETTINGS,
    Permission.SYSTEM_LOGS,
  ],
  
  // 开发者 - 基本使用权限
  developer: [
    Permission.DEV_API_KEYS,
    Permission.DEV_QUOTA,
    Permission.DEV_BILLING,
    Permission.LOG_READ,
    Permission.BILLING_READ,
    Permission.REPO_READ,
  ],
  
  // 普通用户 - 受限权限
  user: [
    Permission.DEV_QUOTA,
    Permission.BILLING_READ,
    Permission.REPO_READ,
  ],
}

// 各用户类型的默认角色
export const UserTypeDefaultRole: Record<UserType, Role> = {
  super_admin: 'super_admin',
  admin: 'admin',
  owner: 'developer',  // 仓库所有者使用developer角色权限
  developer: 'user',
  user: 'user',
}

// 权限检查函数
export function hasPermission(userPermissions: PermissionKey[], required: PermissionKey | PermissionKey[]): boolean {
  // 超级管理员 (*表示所有权限)
  if (userPermissions.includes('*' as PermissionKey)) {
    return true
  }
  
  const requiredPerms = Array.isArray(required) ? required : [required]
  return requiredPerms.every(perm => userPermissions.includes(perm))
}

// 角色检查函数
export function hasRole(userRole: Role, requiredRole: Role | Role[]): boolean {
  const roleHierarchy: Record<Role, number> = {
    super_admin: 4,
    admin: 3,
    developer: 2,
    user: 1,
  }
  
  const requiredRoles = Array.isArray(requiredRole) ? requiredRole : [requiredRole]
  const userLevel = roleHierarchy[userRole] || 0
  
  return requiredRoles.some(role => userLevel >= roleHierarchy[role])
}

// 路由权限映射
export interface RoutePermission {
  path: string
  userTypes: UserType[]
  requiredPermissions?: PermissionKey[]
}

export const RoutePermissions: RoutePermission[] = [
  // 首页/开发者仪表板
  { path: '/', userTypes: ['developer', 'user'] },
  
  // 开发者路由
  { path: '/developer/keys', userTypes: ['developer'], requiredPermissions: [Permission.DEV_API_KEYS] },
  // 【V5.0新增】仓库市场 - 开发者可以预览所有在线仓库
  { path: '/developer/repos', userTypes: ['developer', 'owner'] },
  { path: '/developer/quota', userTypes: ['developer'], requiredPermissions: [Permission.DEV_QUOTA] },
  { path: '/developer/logs', userTypes: ['developer'], requiredPermissions: [Permission.LOG_READ] },
  { path: '/developer/billing', userTypes: ['developer'], requiredPermissions: [Permission.DEV_BILLING] },
  
  // 仓库所有者路由 (开发者也可访问)
  { path: '/owner', userTypes: ['owner', 'developer'] },
  { path: '/owner/repos', userTypes: ['owner', 'developer'], requiredPermissions: [Permission.OWNER_REPO] },
  { path: '/owner/analytics', userTypes: ['owner', 'developer'], requiredPermissions: [Permission.OWNER_ANALYTICS] },
  { path: '/owner/settlement', userTypes: ['owner', 'developer'], requiredPermissions: [Permission.OWNER_SETTLEMENT] },
  
  // 管理员路由
  { path: '/admin', userTypes: ['admin'] },
  { path: '/admin/users', userTypes: ['admin'], requiredPermissions: [Permission.USER_MANAGE] },
  { path: '/admin/repos', userTypes: ['admin'], requiredPermissions: [Permission.REPO_MANAGE] },
  { path: '/admin/logs', userTypes: ['admin'], requiredPermissions: [Permission.LOG_ALL] },
  { path: '/admin/settings', userTypes: ['admin'], requiredPermissions: [Permission.SYSTEM_SETTINGS] },
  { path: '/admin/devtools', userTypes: ['admin'], requiredPermissions: [Permission.SYSTEM_SETTINGS] },
  
  // 超级管理员路由
  { path: '/superadmin', userTypes: ['super_admin'] },
  { path: '/superadmin/users', userTypes: ['super_admin'], requiredPermissions: [Permission.USER_MANAGE] },
  { path: '/superadmin/roles', userTypes: ['super_admin'], requiredPermissions: [Permission.USER_ROLE_ASSIGN] },
  { path: '/superadmin/system', userTypes: ['super_admin'], requiredPermissions: [Permission.SYSTEM_SETTINGS] },
  { path: '/superadmin/audit', userTypes: ['super_admin'], requiredPermissions: [Permission.LOG_ALL] },
]

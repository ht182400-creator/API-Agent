/**
 * 超级管理员 API
 */

// 用户类型映射
export const userTypeLabels: Record<string, string> = {
  super_admin: '超级管理员',
  admin: '管理员',
  owner: '仓库所有者',
  developer: '开发者',
  user: '普通用户',
}

export const userTypeColors: Record<string, string> = {
  super_admin: 'red',
  admin: 'orange',
  owner: 'blue',
  developer: 'green',
  user: 'default',
}

// 角色标签映射
export const roleLabels: Record<string, string> = {
  super_admin: '超级管理员',
  admin: '管理员',
  developer: '开发者',
  user: '普通用户',
}

// 用户列表项
export interface UserListItem {
  id: string
  username: string
  email: string
  phone?: string
  user_type: string
  role: string
  user_status: string
  vip_level: number
  permissions: string[]
  created_at: string
  last_login_at?: string
}

// 仪表板统计数据
export interface DashboardStats {
  total_users: number
  active_users: number
  total_repos: number
  total_api_keys: number
  total_revenue: number
  user_type_stats: { type: string; count: number }[]
}

// 最近活动
export interface RecentActivity {
  id: string
  action: string
  username: string
  resource_type: string
  resource_id?: string
  description?: string
  ip_address?: string
  status: string
  created_at: string
}

// 角色项
export interface RoleItem {
  id: string
  name: string
  display_name: string
  description?: string
  permissions: string[]
  is_system: boolean
  is_active: boolean
  priority: number
  user_count: number
  created_at: string
}

// 审计日志项
export interface AuditLogItem {
  id: string
  user_id?: string
  username?: string
  user_type?: string
  action: string
  resource_type: string
  resource_id?: string
  description?: string
  ip_address?: string
  status: string
  error_message?: string
  created_at: string
}

// 系统配置项
export interface ConfigItem {
  id: string
  category: string
  key: string
  value?: string
  value_type: string
  label?: string
  description?: string
  options: string[]
  is_system: boolean
  is_visible: boolean
  is_editable: boolean
  updated_at?: string
}

// 分页参数
export interface PaginationParams {
  page?: number
  page_size?: number
  keyword?: string
  user_type?: string
  user_status?: string
  action?: string
  resource_type?: string
}

// 导入 api 方法
import { api } from './client'

// 仪表板 API
export const dashboardApi = {
  // 获取仪表板统计
  getStats: () => api.get<DashboardStats>('/superadmin/dashboard/stats'),
  
  // 获取最近活动
  getRecentActivity: (limit = 10) => 
    api.get<RecentActivity[]>('/superadmin/dashboard/recent-activity', { limit }),
}

// 用户管理 API
export const userApi = {
  // 获取用户列表
  list: (params?: PaginationParams) => 
    api.get<{ items: UserListItem[]; total: number; page: number; page_size: number }>(
      '/superadmin/users', 
      params
    ),
  
  // 更新用户
  update: (userId: string, data: {
    user_type?: string
    role?: string
    user_status?: string
    vip_level?: number
    permissions?: string[]
  }) => api.put<UserListItem>(`/superadmin/users/${userId}`, data),
  
  // 删除用户
  delete: (userId: string) => api.delete<void>(`/superadmin/users/${userId}`),
}

// 审计日志 API
export const auditApi = {
  // 获取审计日志列表
  list: (params?: PaginationParams & { start_date?: string; end_date?: string }) => 
    api.get<{ items: AuditLogItem[]; total: number; page: number; page_size: number }>(
      '/superadmin/audit-logs',
      params
    ),
}

// 角色权限 API
export const roleApi = {
  // 获取角色列表
  list: () => api.get<RoleItem[]>('/superadmin/roles'),
  
  // 获取权限定义
  getPermissions: () => api.get<Record<string, { name: string; group: string }>>('/superadmin/permissions'),
}

// 系统配置 API
export const configApi = {
  // 获取配置列表
  list: (category?: string) => 
    api.get<ConfigItem[]>('/superadmin/configs', { category }),
  
  // 更新配置
  update: (configId: string, value: string) => 
    api.put<ConfigItem>(`/superadmin/configs/${configId}`, { value }),
  
  // 初始化配置
  initialize: () => api.post<{ message: string }>('/superadmin/configs/initialize'),
}

// 权限定义
export const PERMISSION_DEFINITIONS: Record<string, { name: string; group: string }> = {
  // 用户管理
  'user:read': { name: '查看用户', group: '用户管理' },
  'user:write': { name: '创建/编辑用户', group: '用户管理' },
  'user:delete': { name: '删除用户', group: '用户管理' },
  'user:manage': { name: '管理用户', group: '用户管理' },
  'user:role': { name: '分配角色', group: '用户管理' },
  
  // API Keys
  'api:read': { name: '查看API Keys', group: 'API Keys' },
  'api:write': { name: '创建API Keys', group: 'API Keys' },
  'api:delete': { name: '删除API Keys', group: 'API Keys' },
  'api:manage': { name: '管理API Keys', group: 'API Keys' },
  
  // 仓库管理
  'repo:read': { name: '查看仓库', group: '仓库管理' },
  'repo:write': { name: '创建仓库', group: '仓库管理' },
  'repo:delete': { name: '删除仓库', group: '仓库管理' },
  'repo:approve': { name: '审核仓库', group: '仓库管理' },
  'repo:manage': { name: '管理仓库', group: '仓库管理' },
  
  // 账单管理
  'billing:read': { name: '查看账单', group: '账单管理' },
  'billing:write': { name: '创建账单', group: '账单管理' },
  'billing:manage': { name: '管理账单', group: '账单管理' },
  'billing:recharge': { name: '账户充值', group: '账单管理' },
  
  // 日志查看
  'log:read': { name: '查看日志', group: '日志查看' },
  'log:all': { name: '查看所有日志', group: '日志查看' },
  
  // 系统管理
  'system:settings': { name: '系统设置', group: '系统管理' },
  'system:logs': { name: '系统日志', group: '系统管理' },
  
  // 开发者功能
  'dev:apikeys': { name: 'API Keys', group: '开发者功能' },
  'dev:quota': { name: '配额管理', group: '开发者功能' },
  'dev:billing': { name: '账单管理', group: '开发者功能' },
  
  // 仓库所有者
  'owner:repo': { name: '我的仓库', group: '仓库所有者' },
  'owner:analytics': { name: '数据分析', group: '仓库所有者' },
  'owner:settlement': { name: '收益结算', group: '仓库所有者' },
}

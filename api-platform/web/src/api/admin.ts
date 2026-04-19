/**
 * 管理员 API
 */

// 管理员仪表板统计数据
export interface AdminDashboardStats {
  total_users: number
  active_users: number
  total_repos: number
  today_new_users: number
  total_api_keys: number
  total_revenue: number
  today_calls: number
}

// 导入 api 方法
import { api } from './client'

// 管理员仪表板 API
export const adminApi = {
  // 获取仪表板统计
  getStats: () => api.get<AdminDashboardStats>('/admin/dashboard/stats'),
  
  // 获取用户列表
  listUsers: (params?: { page?: number; page_size?: number; keyword?: string; user_type?: string }) => 
    api.get<{ items: any[]; total: number; page: number; page_size: number }>('/admin/users', params),
}

// 别名，用于兼容 Users.tsx
export const adminUserApi = {
  ...adminApi,
  list: adminApi.listUsers,
}

// 用户类型映射
export const userTypeLabels: Record<string, string> = {
  admin: '管理员',
  owner: '仓库所有者',
  developer: '开发者',
  user: '普通用户',
}

export const userTypeColors: Record<string, string> = {
  admin: 'orange',
  owner: 'blue',
  developer: 'green',
  user: 'default',
}

// 兼容旧代码的 userTypeMap
export const userTypeMap: Record<string, { label: string; color: string }> = {
  admin: { label: '管理员', color: 'orange' },
  owner: { label: '仓库所有者', color: 'blue' },
  developer: { label: '开发者', color: 'green' },
  user: { label: '普通用户', color: 'default' },
}

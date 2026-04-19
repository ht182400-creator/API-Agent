/**
 * 仓库API类型定义
 * 更新: V2.4 - 端点和限流配置从数据库读取
 */

// 仓库端点
export interface RepositoryEndpoint {
  path: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  description?: string
  category?: string
  rpm_limit?: number
  rph_limit?: number
}

// 仓库限流配置
export interface RepositoryLimits {
  rpm: number
  rph: number
  daily: number
  burst_limit?: number
  concurrent_limit?: number
  request_timeout?: number
  connect_timeout?: number
}

// 仓库定价配置
export interface RepositoryPricing {
  type: 'per_call' | 'token' | 'flow' | 'subscription' | 'free'
  price_per_call?: number
  price_per_token?: number
  price_per_mb?: number
  monthly_price?: number
  yearly_price?: number
  free_calls?: number
  free_tokens?: number
  free_quota_days?: number
}

// 仓库SLA信息
export interface RepositorySLA {
  uptime?: number | string
  latency_p99?: number
}

// 仓库所有者信息
export interface RepositoryOwner {
  id: string
  name: string
  type?: 'internal' | 'external'
}

// 仓库响应结构 (V2.4)
export interface Repository {
  id: string
  name: string
  slug: string
  display_name?: string
  description?: string
  type: string
  protocol: string
  status: 'online' | 'offline' | 'pending' | 'approved' | 'rejected'
  owner?: RepositoryOwner
  pricing?: RepositoryPricing
  limits?: RepositoryLimits
  endpoints?: RepositoryEndpoint[]
  docs_url?: string
  sla?: RepositorySLA
  // 兼容旧字段
  category?: string
  endpoint?: string
  adapter_type?: 'http' | 'grpc' | 'websocket'
  auth_type?: string
  rate_limit?: { rpm: number; rph: number }
  call_count?: number
  created_at: string
  updated_at?: string
  online_at?: string
}

// 仓库统计信息
export interface RepoStats {
  repo_id: string
  today_calls: number
  week_calls: number
  total_calls: number
  today_cost: number
  week_cost: number
  total_cost: number
}

// 创建仓库请求
export interface CreateRepoRequest {
  name: string
  display_name?: string
  description?: string
  repo_type: 'psychology' | 'stock' | 'ai' | 'translation' | 'vision' | 'custom'
  protocol?: 'http' | 'grpc' | 'websocket'
  endpoint_url?: string
  api_docs_url?: string
}

// 更新仓库请求
export interface UpdateRepoRequest {
  display_name?: string
  description?: string
  endpoint_url?: string
  api_docs_url?: string
  status?: string
}

// 仓库筛选参数
export interface RepositoryFilters {
  page?: number
  page_size?: number
  type?: string
  protocol?: string
  search?: string
  owner_id?: string
  status?: string  // 管理员可按状态筛选
}

// 管理员审核请求
export interface AdminApproveRequest {
  comment?: string
}

export interface AdminRejectRequest {
  reason?: string
}

// ============================================
// API 调用函数
// ============================================

import { api, PaginatedResponse } from './client'

// 仓库API
export const repoApi = {
  // 获取仓库列表
  list: (params?: {
    page?: number
    page_size?: number
    type?: string
    protocol?: string
    search?: string
  }) => {
    return api.get<PaginatedResponse<Repository>>('/repositories', params)
  },

  // 获取仓库详情
  get: (repo_id: string) => {
    return api.get<Repository>(`/repositories/${repo_id}`)
  },

  // 获取仓库统计
  getStats: (repo_id: string) => {
    return api.get<RepoStats>(`/repositories/${repo_id}/stats`)
  },

  // 创建仓库
  create: (data: CreateRepoRequest) => {
    return api.post<Repository>('/repositories', data)
  },

  // 更新仓库
  update: (repo_id: string, data: Partial<CreateRepoRequest>) => {
    return api.put<Repository>(`/repositories/${repo_id}`, data)
  },

  // 删除仓库
  delete: (repo_id: string) => {
    return api.delete(`/repositories/${repo_id}`)
  },

  // 上线仓库
  activate: (repo_id: string) => {
    return api.put<Repository>(`/repositories/${repo_id}`, { status: 'online' })
  },

  // 下线仓库
  deactivate: (repo_id: string) => {
    return api.put<Repository>(`/repositories/${repo_id}`, { status: 'offline' })
  },

  // 获取仓库分类
  getCategories: () => {
    return api.get<string[]>('/repositories/categories')
  },

  // 获取我创建的仓库
  getMyRepos: (params?: { page?: number; page_size?: number }) => {
    return api.get<PaginatedResponse<Repository>>('/repositories/my', params)
  },

  // ==================== 管理员 API ====================

  // 获取所有仓库（管理员）
  adminList: (params?: {
    status?: string
    page?: number
    page_size?: number
  }) => {
    return api.get<PaginatedResponse<Repository>>('/repositories/admin/all', params)
  },

  // 审核通过仓库（管理员）
  adminApprove: (repo_id: string, data?: { comment?: string }) => {
    return api.post<Repository>(`/repositories/${repo_id}/approve`, data || {})
  },

  // 审核拒绝仓库（管理员）
  adminReject: (repo_id: string, data?: { reason?: string }) => {
    return api.post<Repository>(`/repositories/${repo_id}/reject`, data || {})
  },

  // 上线仓库（管理员）
  adminOnline: (repo_id: string) => {
    return api.post<Repository>(`/repositories/${repo_id}/online`, {})
  },

  // 下线仓库（管理员）
  adminOffline: (repo_id: string) => {
    return api.post<Repository>(`/repositories/${repo_id}/offline`, {})
  },
}

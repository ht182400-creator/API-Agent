/**
 * 仓库API
 */

import { api, PaginatedResponse } from './client'

// 仓库类型
export interface Repository {
  id: string
  name: string
  display_name: string
  description: string
  category: string
  owner_id: string
  owner_name?: string
  adapter_type: 'http' | 'grpc' | 'websocket'
  endpoint: string
  auth_type: string
  pricing: PricingConfig
  rate_limit: RateLimitConfig
  status: 'active' | 'inactive' | 'maintenance'
  is_public: boolean
  call_count: number
  created_at: string
  updated_at: string
}

// 定价配置
export interface PricingConfig {
  type: 'per_call' | 'per_token' | 'per_volume' | 'free'
  price?: number
  price_per_token?: number
  price_per_mb?: number
}

// 速率限制配置
export interface RateLimitConfig {
  rpm: number
  rph: number
}

// 创建仓库请求
export interface CreateRepoRequest {
  name: string
  description: string
  category: string
  adapter_type: 'http' | 'grpc' | 'websocket'
  endpoint: string
  auth_type: string
  pricing?: PricingConfig
  rate_limit?: RateLimitConfig
  is_public?: boolean
}

// 仓库统计
export interface RepoStats {
  repo_id: string
  today_calls: number
  week_calls: number
  total_calls: number
  today_cost: number
  week_cost: number
  total_cost: number
}

// 仓库API
export const repoApi = {
  // 获取仓库列表
  list: (params?: {
    page?: number
    page_size?: number
    category?: string
    search?: string
    is_public?: boolean
    owner_id?: string
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
}

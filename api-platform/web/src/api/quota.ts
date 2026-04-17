/**
 * 配额API
 */

import { api, PaginatedResponse } from './client'

// API Key类型
export interface APIKey {
  id: string
  key_name: string
  key_prefix: string
  api_key: string  // 仅创建时返回完整key
  status: 'active' | 'disabled' | 'expired'
  auth_type: 'api_key' | 'hmac' | 'jwt'
  rate_limit_rpm: number
  rate_limit_rph: number
  daily_quota: number | null
  monthly_quota: number | null
  last_used_at?: string
  created_at: string
  expires_at?: string
}

// 配额信息
export interface QuotaInfo {
  api_key_id: string
  daily: {
    used: number
    limit: number | null
    remaining: number | null
  }
  monthly: {
    used: number
    limit: number | null
    remaining: number | null
  }
}

// 调用日志
export interface APICallLog {
  id: string
  api_key_id: string
  repo_id: string
  repo_name: string
  endpoint: string
  method: string
  request_params?: object
  response_status: number
  response_time: number
  ip_address?: string
  created_at: string
}

// 创建API Key请求
export interface CreateKeyRequest {
  name: string
  auth_type?: 'api_key' | 'hmac' | 'jwt'
  rate_limit_rpm?: number
  rate_limit_rph?: number
  daily_quota?: number
  monthly_quota?: number
  allowed_repos?: string[]
  denied_repos?: string[]
}

// 配额API
export const quotaApi = {
  // 获取API Key列表
  getKeys: (params?: { page?: number; page_size?: number }) => {
    return api.get<{ data: PaginatedResponse<APIKey> }>('/quota/keys', params)
  },
  
  // 创建API Key
  createKey: (data: CreateKeyRequest) => {
    return api.post<{ data: APIKey }>('/quota/keys', data)
  },
  
  // 获取API Key详情
  getKey: (key_id: string) => {
    return api.get<{ data: APIKey }>(`/quota/keys/${key_id}`)
  },
  
  // 更新API Key
  updateKey: (key_id: string, data: Partial<CreateKeyRequest>) => {
    return api.put<{ data: APIKey }>(`/quota/keys/${key_id}`, data)
  },
  
  // 禁用API Key
  disableKey: (key_id: string) => {
    return api.post(`/quota/keys/${key_id}/disable`)
  },
  
  // 启用API Key
  enableKey: (key_id: string) => {
    return api.post(`/quota/keys/${key_id}/enable`)
  },
  
  // 删除API Key
  deleteKey: (key_id: string) => {
    return api.delete(`/quota/keys/${key_id}`)
  },
  
  // 获取配额信息
  getQuota: (key_id: string) => {
    return api.get<{ data: QuotaInfo }>(`/quota/info/${key_id}`)
  },
  
  // 获取所有API Key的配额概览
  getQuotaOverview: () => {
    return api.get<{ data: QuotaInfo[] }>('/quota/overview')
  },
  
  // 设置配额限制
  setQuota: (key_id: string, daily_quota?: number, monthly_quota?: number) => {
    return api.post(`/quota/keys/${key_id}/set-quota`, { daily_quota, monthly_quota })
  },
  
  // 获取调用日志
  getLogs: (params?: {
    page?: number
    page_size?: number
    key_id?: string
    repo_id?: string
    start_date?: string
    end_date?: string
  }) => {
    return api.get<{ data: PaginatedResponse<APICallLog> }>('/quota/logs', params)
  },
  
  // 获取配额使用历史
  getUsageHistory: (key_id: string, period_type?: 'daily' | 'monthly', days?: number) => {
    return api.get<{ data: { date: string; total_amount: number; call_count: number }[] }>(
      `/quota/usage-history/${key_id}`,
      { period_type, days }
    )
  },
  
  // 获取使用量最高的仓库
  getTopRepos: (key_id: string, limit?: number, days?: number) => {
    return api.get<{ data: { repo_id: string; repo_name: string; total_amount: number; call_count: number }[] }>(
      `/quota/top-repos/${key_id}`,
      { limit, days }
    )
  },
}

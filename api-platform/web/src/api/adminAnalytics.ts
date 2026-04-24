/**
 * Admin Analytics API - 管理员分析报表API
 * V1.0 - 管理员视角的全局数据统计和趋势分析
 */

import { api } from './client'

// ==================== 类型定义 ====================

/**
 * 概览统计数据
 */
export interface AdminOverview {
  repos: {
    total: number
    online: number
    pending: number
  }
  calls: {
    today: number
    week: number
    month: number
    total: number
    today_success: number
    today_failed: number
  }
  revenue: {
    today: number
    week: number
    month: number
    total: number
  }
  active_users: number
  generated_at: string
}

/**
 * 趋势数据
 */
export interface TrendData {
  labels: string[]
  series: {
    calls: number[]
    revenue: number[]
  }
  period: 'hour' | 'day' | 'week'
  days: number
  repo_id: string | null
  generated_at: string
}

/**
 * 仓库明细项
 */
export interface RepoDetailItem {
  repo_id: string
  name: string
  slug: string
  status: string
  owner_id: string
  total_calls: number
  success_calls: number
  failed_calls: number
  success_rate: number
  total_cost: number
  created_at: string
}

/**
 * 仓库明细响应
 */
export interface RepoDetailsResponse {
  items: RepoDetailItem[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
  generated_at: string
}

/**
 * 仓库趋势数据
 */
export interface RepoTrendData {
  repo_id: string
  repo_name: string
  labels: string[]
  series: {
    calls: number[]
    revenue: number[]
    avg_latency: number[]
  }
  days: number
  generated_at: string
}

/**
 * 排行榜项（用户）
 */
export interface UserRankingItem {
  rank: number
  user_id: string
  user_name: string
  user_email: string
  total_calls: number
  total_cost: number
}

/**
 * 排行榜项（仓库）
 */
export interface RepoRankingItem {
  rank: number
  repo_id: string
  repo_name: string
  repo_slug: string
  status: string
  total_calls: number
  total_cost: number
}

/**
 * 分页参数
 */
export interface PaginationParams {
  page?: number
  page_size?: number
}

// ==================== API 方法 ====================

export const adminAnalyticsApi = {
  /**
   * 获取分析概览统计
   */
  getOverview: async (): Promise<AdminOverview> => {
    return await api.get<AdminOverview>('/analytics/overview')
  },

  /**
   * 获取调用和收入趋势
   * @param period 统计周期: hour(按小时), day(按天)
   * @param days 查询天数(按天时有效)
   * @param repo_id 可选的仓库ID过滤
   */
  getTrend: async (params: {
    period?: 'hour' | 'day'
    days?: number
    repo_id?: string
  } = {}): Promise<TrendData> => {
    return await api.get<TrendData>('/analytics/trend', { params })
  },

  /**
   * 获取仓库明细列表
   */
  getRepoDetails: async (params: {
    page?: number
    page_size?: number
    status?: string
    sort_by?: 'total_calls' | 'total_cost' | 'name'
    sort_order?: 'asc' | 'desc'
  } = {}): Promise<RepoDetailsResponse> => {
    return await api.get<RepoDetailsResponse>('/analytics/repo-details', { params })
  },

  /**
   * 获取指定仓库的趋势数据
   */
  getRepoTrend: async (repoId: string, days: number = 7): Promise<RepoTrendData> => {
    return await api.get<RepoTrendData>(`/analytics/repo/${repoId}/trend`, {
      params: { days }
    })
  },

  /**
   * 获取用户调用量排行榜
   * @param period 统计周期: today, week, month, all
   * @param limit 返回数量
   */
  getUserRanking: async (params: {
    period?: 'today' | 'week' | 'month' | 'all'
    limit?: number
  } = {}): Promise<{ items: UserRankingItem[]; period: string; generated_at: string }> => {
    return await api.get('/analytics/user-ranking', { params })
  },

  /**
   * 获取仓库调用量排行榜
   * @param period 统计周期: today, week, month, all
   * @param limit 返回数量
   */
  getRepoRanking: async (params: {
    period?: 'today' | 'week' | 'month' | 'all'
    limit?: number
  } = {}): Promise<{ items: RepoRankingItem[]; period: string; generated_at: string }> => {
    return await api.get('/analytics/repo-ranking', { params })
  }
}

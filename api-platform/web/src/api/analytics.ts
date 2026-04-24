/**
 * Analytics API - 仓库所有者数据分析
 */

import { api } from './client'

export interface WeeklyStats {
  date: string
  calls: number
  revenue: number
}

export interface HourlyStats {
  hour: string
  calls: number
}

export interface SourceStats {
  name: string
  value: number
  percentage: number
}

export interface OverviewStats {
  total_calls: number
  month_calls: number
  total_repos: number
  total_revenue: number
  growth_rate: number
}

/**
 * 转换后端概览数据为前端格式
 */
function transformOverview(data: any): OverviewStats {
  return {
    total_calls: data.calls?.total || 0,
    month_calls: data.calls?.month || 0,
    total_repos: data.repos?.total || 0,
    total_revenue: data.revenue?.total || 0,
    growth_rate: 0  // 后端未提供，可后续添加
  }
}

/**
 * 转换后端趋势数据为周统计数据
 */
function transformWeeklyStats(data: any): WeeklyStats[] {
  if (!data.labels || !data.series) return []
  return data.labels.map((label: string, index: number) => ({
    date: label,
    calls: data.series.calls?.[index] || 0,
    revenue: data.series.revenue?.[index] || 0
  }))
}

/**
 * 转换后端趋势数据为小时统计数据
 */
function transformHourlyStats(data: any): HourlyStats[] {
  if (!data.labels || !data.series) return []
  return data.labels.map((label: string, index: number) => ({
    hour: label,
    calls: data.series.calls?.[index] || 0
  }))
}

/**
 * 转换后端排行榜数据为来源统计数据
 */
function transformSourceStats(data: any): SourceStats[] {
  if (!data.items || data.items.length === 0) return []
  const total = data.items.reduce((sum: number, item: any) => sum + item.total_calls, 0)
  return data.items.map((item: any) => ({
    name: item.repo_name || 'Unknown',
    value: item.total_calls,
    percentage: total > 0 ? Math.round((item.total_calls / total) * 100) : 0
  }))
}

export const analyticsApi = {
  /**
   * 获取总览统计
   */
  getOverview: async (): Promise<OverviewStats> => {
    const response = await api.get<any>('/analytics/overview')
    return transformOverview(response)
  },

  /**
   * 获取每周统计
   */
  getWeeklyStats: async (weeks: number = 1): Promise<WeeklyStats[]> => {
    const response = await api.get<any>('/analytics/trend', {
      params: { period: 'day', days: weeks * 7 }
    })
    return transformWeeklyStats(response)
  },

  /**
   * 获取24小时分布
   */
  getHourlyStats: async (): Promise<HourlyStats[]> => {
    const response = await api.get<any>('/analytics/trend', {
      params: { period: 'hour' }
    })
    return transformHourlyStats(response)
  },

  /**
   * 获取调用来源分布
   */
  getSourceStats: async (): Promise<SourceStats[]> => {
    const response = await api.get<any>('/analytics/repo-ranking', {
      params: { period: 'week', limit: 10 }
    })
    return transformSourceStats(response)
  }
}

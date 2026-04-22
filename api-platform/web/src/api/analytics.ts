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

export const analyticsApi = {
  /**
   * 获取总览统计
   */
  getOverview: async (): Promise<OverviewStats> => {
    // api.get() 已由 client.ts 拦截器自动提取 data 字段
    return await api.get<OverviewStats>('/owner/overview')
  },

  /**
   * 获取每周统计
   */
  getWeeklyStats: async (weeks: number = 1): Promise<WeeklyStats[]> => {
    return await api.get<WeeklyStats[]>('/owner/weekly', { params: { weeks } })
  },

  /**
   * 获取24小时分布
   */
  getHourlyStats: async (): Promise<HourlyStats[]> => {
    return await api.get<HourlyStats[]>('/owner/hourly')
  },

  /**
   * 获取调用来源分布
   */
  getSourceStats: async (): Promise<SourceStats[]> => {
    return await api.get<SourceStats[]>('/owner/sources')
  }
}

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
    const response = await api.get('/owner/overview')
    return response.data
  },

  /**
   * 获取每周统计
   */
  getWeeklyStats: async (weeks: number = 1): Promise<WeeklyStats[]> => {
    const response = await api.get('/owner/weekly', { params: { weeks } })
    return response.data
  },

  /**
   * 获取24小时分布
   */
  getHourlyStats: async (): Promise<HourlyStats[]> => {
    const response = await api.get('/owner/hourly')
    return response.data
  },

  /**
   * 获取调用来源分布
   */
  getSourceStats: async (): Promise<SourceStats[]> => {
    const response = await api.get('/owner/sources')
    return response.data
  }
}

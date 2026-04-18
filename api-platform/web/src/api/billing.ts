/**
 * 计费API
 */

import { api, PaginatedResponse } from './client'

// 账户信息
export interface Account {
  id: string
  user_id: string
  balance: number
  frozen_balance: number
  total_recharge: number
  total_consumption: number
  created_at: string
}

// 账单类型
export type BillType = 'recharge' | 'consumption' | 'refund' | 'freeze' | 'unfreeze' | 'settlement'

// 账单记录
export interface Bill {
  id: string
  account_id: string
  bill_type: BillType
  amount: number
  balance_after: number
  payment_method?: string
  payment_id?: string
  api_key_id?: string
  repo_id?: string
  repo_name?: string
  description: string
  created_at: string
}

// 月度汇总
export interface MonthlySummary {
  year: number
  month: number
  total_recharge: number
  total_consumption: number
  consumption_count: number
  net_change: number
  by_repository: {
    repo_id: string
    repo_name: string
    total: number
    count: number
  }[]
}

// 充值请求
export interface RechargeRequest {
  amount: number
  payment_method: 'alipay' | 'wechat' | 'bank' | 'manual'
}

// 计费API
export const billingApi = {
  // 获取账户信息
  getAccount: () => {
    return api.get<Account>('/billing/account')
  },
  
  // 充值
  recharge: (data: RechargeRequest) => {
    return api.post<{ order_id: string; pay_url: string }>('/billing/recharge', data)
  },
  
  // 获取账单列表
  getBills: (params?: {
    page?: number
    page_size?: number
    bill_type?: BillType
    start_date?: string
    end_date?: string
  }) => {
    return api.get<PaginatedResponse<Bill>>('/billing/bills', params)
  },
  
  // 获取月度汇总
  getMonthlySummary: (year?: number, month?: number) => {
    return api.get<MonthlySummary>('/billing/monthly-summary', { year, month })
  },
  
  // 获取余额历史
  getBalanceHistory: (days?: number) => {
    return api.get<{ date: string; daily_change: number; balance: number }[]>(
      '/billing/balance-history',
      { days }
    )
  },
  
  // 获取消费趋势
  getConsumptionTrend: (days?: number) => {
    return api.get<{ date: string; amount: number }[]>('/billing/consumption-trend', { days })
  },
}

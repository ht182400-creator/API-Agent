import { api } from './client'
import { useAuthStore } from '../stores/auth'

// ============ Billing API (Developer) ============

export interface UserUsage {
  call_count: number
  total_tokens: number
  total_cost: number
  by_repository: {
    repo_id: string
    repo_name: string
    call_count: number
    total_tokens: number
    total_cost: number
  }[]
}

export interface ConsumptionDetail {
  id: number
  repo_id: string | null
  repo_name: string
  endpoint: string
  request_params?: string  // 请求参数 (JSON字符串)
  tester?: string           // 测试人员
  tokens_used: number
  cost: number
  created_at: string
}

export interface ConsumptionDetailsResponse {
  items: ConsumptionDetail[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}

export interface UserAccount {
  id: string
  user_id: string
  balance: number
  frozen_balance: number
  total_recharge: number
  total_consumption: number
  total_revenue: number  // API 调用总收益
  created_at: string
  mock_mode: boolean
  environment: string
}

// Monthly Bill types
export interface MonthlyBill {
  id: string
  year: number
  month: number
  total_recharge: number
  total_consumption: number
  net_change: number
  beginning_balance: number
  ending_balance: number
  total_calls: number
  total_tokens: number
  status: 'pending' | 'generated' | 'reviewed' | 'published'
  generated_at?: string
  published_at?: string
}

export interface MonthlyBillDetail extends MonthlyBill {
  details: {
    by_repository?: {
      repo_id: string
      repo_name: string
      call_count: number
      total_tokens: number
      total_cost: number
    }[]
    generated_at?: string
    period?: string
  }
  review_comment?: string
  reviewed_at?: string
}

// Monthly Summary types
export interface MonthlySummary {
  year?: number
  month?: number
  total_recharge: number
  total_consumption: number
  consumption_count: number
  net_change?: number
  by_repository: {
    repo_id: string | null
    repo_name: string
    call_count: number
    total: number
  }[]
  environment?: string
  mock_mode?: boolean
}

export interface MonthlySummaryResponse {
  environment: string
  current_period: {
    start: string
    end: string
  }
  summary: MonthlySummary
}

// Bill types
export interface Bill {
  id: number
  bill_type: string
  amount: number
  balance_before: number
  balance_after: number
  description: string
  repo_id?: string
  repo_name?: string
  created_at: string
}

export interface PaginatedBills {
  items: Bill[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}

export interface BalanceHistoryItem {
  date: string
  balance: number
}

export interface PaginatedMonthlyBills {
  items: MonthlyBill[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
  environment: string
}

// Admin Billing API types
export interface AdminMonthlyBill {
  id: string
  user_id: string
  username: string
  email: string
  year: number
  month: number
  environment: string
  total_recharge: number
  total_consumption: number
  net_change: number
  beginning_balance: number
  ending_balance: number
  total_calls: number
  total_tokens: number
  status: string
  reviewed_at?: string
  reviewed_by?: string
  generated_at?: string
  published_at?: string
  created_at?: string
}

export interface PaginatedAdminMonthlyBills {
  items: AdminMonthlyBill[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
  environment: string
}

export const billingApi = {
  // Get user account info
  getAccount: () => {
    return api.get<UserAccount>('/billing/account')
  },

  // Get monthly summary
  getMonthlySummary: () => {
    return api.get<MonthlySummary>('/billing/monthly-summary')
  },

  // Get balance history
  getBalanceHistory: (days: number = 30) => {
    return api.get<BalanceHistoryItem[]>('/billing/balance-history', { days })
  },

  // Get consumption trend
  getConsumptionTrend: (days: number = 7) => {
    return api.get<{ date: string; amount: number }[]>('/billing/consumption-trend', { days })
  },

  // Get bills list
  getBills: (params?: {
    page?: number
    page_size?: number
    bill_type?: string
    start_date?: string
    end_date?: string
  }) => {
    return api.get<PaginatedBills>('/billing/bills', params)
  },

  // Export bills as CSV
  exportBills: async (params?: {
    bill_type?: string
    start_date?: string
    end_date?: string
  }): Promise<void> => {
    try {
      // 构建查询参数
      const queryParams = new URLSearchParams()
      if (params?.bill_type) queryParams.append('bill_type', params.bill_type)
      if (params?.start_date) queryParams.append('start_date', params.start_date)
      if (params?.end_date) queryParams.append('end_date', params.end_date)
      
      const queryString = queryParams.toString() ? `?${queryParams.toString()}` : ''
      const baseUrl = import.meta.env.VITE_API_URL || '/api/v1'
      const token = useAuthStore.getState().accessToken
      
      // 使用 fetch 发送带认证的请求
      const response = await fetch(`${baseUrl}/billing/bills/export${queryString}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      
      // 检查响应状态
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `导出失败 (${response.status})`)
      }
      
      // 获取文件名
      const contentDisposition = response.headers.get('content-disposition')
      let filename = 'bills_export.csv'
      if (contentDisposition) {
        const match = contentDisposition.match(/filename\*?=(?:UTF-8'')?"?([^"]+)"?/)
        if (match) {
          filename = decodeURIComponent(match[1])
        }
      }
      
      // 下载文件
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      // 记录详细错误日志
      console.error('[导出账单] 失败:', error)
      // 向用户显示友好错误信息
      throw new Error('导出失败，请稍后重试')
    }
  },

  // Get user usage statistics
  getUsage: () => {
    return api.get<UserUsage>('/billing/usage')
  },

  // Get consumption details
  getConsumptionDetails: (params?: {
    page?: number
    page_size?: number
    repo_id?: string
    start_date?: string
    end_date?: string
  }) => {
    return api.get<ConsumptionDetailsResponse>('/billing/consumption-details', params)
  },

  // ============ Monthly Bill APIs (Developer) ============

  // Get user's monthly bills
  getMonthlyBills: (params?: {
    page?: number
    page_size?: number
    year?: number
    month?: number
    status?: string
  }) => {
    return api.get<PaginatedMonthlyBills>('/billing/monthly-bills', params)
  },

  // Get user's monthly bill detail
  getMonthlyBillDetail: (billId: string) => {
    return api.get<MonthlyBillDetail>(`/billing/monthly-bills/${billId}`)
  },

  // Get available periods for user's monthly bills
  getAvailablePeriods: () => {
    return api.get<{ year: number; month: number }[]>('/billing/monthly-bills/available-periods')
  },

  // ============ Admin Monthly Bill APIs ============

  // Get all generated monthly bills (Admin)
  getAdminMonthlyBills: (params?: {
    page?: number
    page_size?: number
    year?: number
    month?: number
    user_id?: string
    status?: string
    environment?: string
  }) => {
    return api.get<PaginatedAdminMonthlyBills>('/admin/billing/monthly-bills/generated', params)
  },

  // Get monthly bill detail (Admin)
  getAdminMonthlyBillDetail: (billId: string) => {
    return api.get<MonthlyBillDetail>(`/admin/billing/monthly-bills/${billId}`)
  },

  // Generate monthly bills (Admin)
  generateMonthlyBills: (params: {
    year: number
    month: number
    user_id?: string
    environment?: string
  }) => {
    return api.post<{
      year: number
      month: number
      environment: string
      generated_count: number
      skipped_count: number
      total_count: number
      errors?: { user_id: string; error: string }[]
    }>('/admin/billing/monthly-bills/generate', null, { params })
  },

  // Review monthly bill (Admin)
  reviewMonthlyBill: (billId: string, params: {
    action: 'approve' | 'reject'
    comment?: string
  }) => {
    return api.put<{
      id: string
      status: string
      reviewed_by: string
      reviewed_at: string
      review_comment?: string
    }>(`/admin/billing/monthly-bills/${billId}/review`, null, { params })
  },

  // Publish monthly bill (Admin)
  publishMonthlyBill: (billId: string) => {
    return api.put<{
      id: string
      status: string
      published_at: string
    }>(`/admin/billing/monthly-bills/${billId}/publish`)
  },

  // Get available periods for admin monthly bills
  getAdminAvailablePeriods: (environment?: string) => {
    return api.get<{ year: number; month: number }[]>('/admin/billing/monthly-bills/years-months', { environment })
  },
}

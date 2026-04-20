import { api } from './client'

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

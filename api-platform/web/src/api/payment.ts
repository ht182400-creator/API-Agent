/**
 * 支付API
 * 更新: V2.5 - 新增支付和充值功能
 */

import { api, PaginatedResponse } from './client'

// 充值套餐
export interface RechargePackage {
  id: string
  name: string
  price: number
  bonus_amount: number
  bonus_ratio?: number
  min_amount?: number
  max_amount?: number
  description?: string
  is_active: boolean
  is_featured: boolean
  is_custom: boolean
  sort_order: number
  created_at: string
}

// 充值配置
export interface RechargeConfig {
  min_amount: number
  max_amount: number
  default_bonus_ratio: number
  mock_mode: boolean  // 是否为模拟模式
}

// 支付订单
export interface Payment {
  id: string
  payment_no: string
  order_no: string
  user_id: string
  amount: number
  bonus_amount: number
  total_amount: number
  payment_method: string
  status: 'pending' | 'paid' | 'cancelled' | 'failed' | 'refunded'
  transaction_id?: string
  pay_time?: string
  created_at: string
  package_info?: RechargePackage
}

// 创建支付请求
export interface CreatePaymentRequest {
  package_id: string
  payment_method?: 'wechat' | 'alipay' | 'bankcard'
}

// 支付状态响应
export interface PaymentStatus {
  payment_no: string
  status: string
  amount: number
  pay_url?: string
  qr_code?: string
}

// 支付记录筛选
export interface PaymentFilters {
  page?: number
  page_size?: number
  status?: string
  payment_method?: string
  start_date?: string
  end_date?: string
}

// ============================================
// API 调用函数
// ============================================

export const paymentApi = {
  // 获取充值配置
  getConfig: () => {
    return api.get<RechargeConfig>('/payments/config')
  },

  // 获取充值套餐列表
  getPackages: () => {
    return api.get<RechargePackage[]>('/payments/packages')
  },

  // 获取套餐详情
  getPackage: (package_id: string) => {
    return api.get<RechargePackage>(`/payments/packages/${package_id}`)
  },

  // 创建套餐支付订单
  createPayment: (data: CreatePaymentRequest) => {
    return api.post<Payment>('/payments/create', data)
  },

  // 自定义金额充值
  createCustomRecharge: (amount: number, paymentMethod: string = 'alipay') => {
    return api.post<Payment>('/payments/custom', {
      amount,
      payment_method: paymentMethod,
    })
  },

  // 查询支付状态
  getPaymentStatus: (payment_no: string) => {
    return api.get<PaymentStatus>(`/payments/status/${payment_no}`)
  },

  // 取消订单
  cancelPayment: (payment_no: string) => {
    return api.post(`/payments/cancel/${payment_no}`)
  },

  // 获取支付记录
  getPaymentRecords: (params?: PaymentFilters) => {
    return api.get<PaginatedResponse<Payment>>('/payments/records', params)
  },

  // 刷新支付状态（轮询）
  pollPaymentStatus: async (payment_no: string, maxAttempts = 10, interval = 2000): Promise<PaymentStatus> => {
    for (let i = 0; i < maxAttempts; i++) {
      const status = await paymentApi.getPaymentStatus(payment_no)
      if (status.status === 'paid') {
        return status
      }
      if (status.status === 'cancelled' || status.status === 'failed') {
        return status
      }
      await new Promise(resolve => setTimeout(resolve, interval))
    }
    return paymentApi.getPaymentStatus(payment_no)
  },

  // 模拟支付成功回调（开发测试用）
  mockPaymentCallback: (payment_no: string) => {
    return api.post('/payments/callback', {
      payment_no,
      transaction_id: `MOCK_${Date.now()}`,
      status: 'success',
      payer_info: { mock: true },
    })
  },
}

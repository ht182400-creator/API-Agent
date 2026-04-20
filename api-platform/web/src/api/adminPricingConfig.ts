import { api } from './client'

// ============ 计费配置 API ============

export interface PricingConfig {
  id: string
  repo_id: string | null
  pricing_type: 'call' | 'token' | 'package'
  price_per_call?: number
  free_calls?: number
  price_per_1k_input_tokens?: number
  price_per_1k_output_tokens?: number
  free_input_tokens?: number
  free_output_tokens?: number
  packages?: PackageItem[]
  default_package_id?: string
  pricing_tiers?: PricingTier[]
  vip_discounts?: Record<string, number>
  priority: number
  status: 'active' | 'inactive'
  description?: string
  created_at: string
  updated_at: string
}

export interface PackageItem {
  id: string
  name: string
  calls: number
  price: number
  period_days?: number
}

export interface PricingTier {
  min_calls: number
  max_calls?: number
  discount: number
}

export interface PricingConfigListResponse {
  items: PricingConfig[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface CreatePricingConfigRequest {
  repo_id?: string
  pricing_type: 'call' | 'token' | 'package'
  price_per_call?: number
  free_calls?: number
  price_per_1k_input_tokens?: number
  price_per_1k_output_tokens?: number
  free_input_tokens?: number
  free_output_tokens?: number
  packages?: PackageItem[]
  default_package_id?: string
  pricing_tiers?: PricingTier[]
  vip_discounts?: Record<string, number>
  priority?: number
  description?: string
}

export interface CostPreviewRequest {
  pricing_type: 'call' | 'token' | 'package'
  config_id?: string
  call_count?: number
  input_tokens?: number
  output_tokens?: number
  vip_level?: number
  price_per_call?: number
  price_per_1k_input_tokens?: number
  price_per_1k_output_tokens?: number
  free_calls?: number
  free_input_tokens?: number
  free_output_tokens?: number
}

export interface CostPreviewResponse {
  config_id?: string
  pricing_type: string
  input: {
    call_count: number
    input_tokens: number
    output_tokens: number
    vip_level: number
  }
  cost: number
  details: {
    base_cost: number
    tier_discount: number
    vip_discount: number
    free_deduction: number
  }
}

// API methods
export const adminPricingConfigApi = {
  // 获取配置列表
  getConfigs: (params?: { page?: number; page_size?: number; pricing_type?: string; status?: string }) => {
    return api.get<PricingConfigListResponse>('/admin/pricing-configs', params)
  },

  // 获取单个配置
  getConfig: (configId: string) => {
    return api.get<PricingConfig>(`/admin/pricing-configs/${configId}`)
  },

  // 获取全局配置
  getGlobalConfigs: () => {
    return api.get<PricingConfig[]>('/admin/pricing-configs/global')
  },

  // 按仓库获取配置
  getConfigByRepo: (repoId: string) => {
    return api.get<PricingConfig[]>(`/admin/pricing-configs/by-repo/${repoId}`)
  },

  // 创建配置
  createConfig: (data: CreatePricingConfigRequest) => {
    return api.post<PricingConfig>('/admin/pricing-configs', data)
  },

  // 更新配置
  updateConfig: (configId: string, data: CreatePricingConfigRequest) => {
    return api.put<PricingConfig>(`/admin/pricing-configs/${configId}`, data)
  },

  // 删除配置
  deleteConfig: (configId: string) => {
    return api.delete<void>(`/admin/pricing-configs/${configId}`)
  },

  // 启用配置
  enableConfig: (configId: string) => {
    return api.post<PricingConfig>(`/admin/pricing-configs/${configId}/enable`)
  },

  // 禁用配置
  disableConfig: (configId: string) => {
    return api.post<PricingConfig>(`/admin/pricing-configs/${configId}/disable`)
  },

  // 费用预览（后端使用Query参数）
  calculateCost: (data: CostPreviewRequest) => {
    const params: Record<string, any> = {
      pricing_type: data.pricing_type,
      call_count: data.call_count || 1,
      input_tokens: data.input_tokens || 0,
      output_tokens: data.output_tokens || 0,
      vip_level: data.vip_level || 0,
    }
    // 只有有效值才添加 config_id
    if (data.config_id) {
      params.config_id = data.config_id
    }
    return api.get<CostPreviewResponse>('/admin/pricing-configs/calculate-cost', params)
  },
}

// 导出常量
export const PRICING_TYPE_OPTIONS = [
  { label: '按调用计费', value: 'call' },
  { label: '按Token计费', value: 'token' },
  { label: '套餐包计费', value: 'package' },
]

export const STATUS_OPTIONS = [
  { label: '全部', value: '' },
  { label: '启用', value: 'active' },
  { label: '禁用', value: 'inactive' },
]

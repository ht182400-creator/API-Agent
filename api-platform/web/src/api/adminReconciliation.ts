/**
 * 管理员对账 API
 */

import { api, PaginatedResponse } from './client'

// 充值记录项
export interface RechargeRecordItem {
  id: string
  payment_no: string
  user_id: string
  user_phone?: string
  user_email?: string
  amount: number
  bonus_amount: number
  total_amount: number
  payment_method: string
  payment_method_name: string
  status: string
  transaction_id?: string
  environment: string
  balance_after?: number
  created_at: string
  pay_time?: string
}

// 充值汇总
export interface RechargeSummary {
  total_count: number
  success_count: number
  failed_count: number
  pending_count: number
  total_amount: number
  total_bonus: number
  total_receivable: number
}

// 充值记录响应
export interface RechargeRecordsResponse {
  items: RechargeRecordItem[]
  summary: RechargeSummary
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}

// 渠道汇总项
export interface ChannelSummary {
  channel: string
  channel_name: string
  channel_icon: string
  trade_count: number
  trade_amount: number
  success_count: number
  pending_count: number
  failed_count: number
}

// 总汇总
export interface TotalSummary {
  trade_count: number
  trade_amount: number
  success_count: number
  pending_count: number
  failed_count: number
}

// 渠道汇总响应
export interface ChannelSummaryResponse {
  date: string
  channels: ChannelSummary[]
  total: TotalSummary
}

// 平台账户项
export interface PlatformAccountItem {
  id: string
  channel: string
  channel_name: string
  channel_icon: string
  account_no?: string
  account_name?: string
  balance: number
  frozen_balance: number
  available_balance: number
  currency: string
  status: string
  remark?: string
}

// 平台账户响应
export interface PlatformAccountsResponse {
  accounts: PlatformAccountItem[]
  total_available: number
  total_frozen: number
  total_balance: number
}

// 充值记录查询参数
export interface RechargeRecordsParams {
  date?: string
  channel?: string
  status?: string
  page?: number
  page_size?: number
}

// ==================== 对账核心API类型 ====================

// 对账结果项
export interface ReconciliationResultItem {
  reconciliation_id: string
  reconcile_date: string
  channel: string
  channel_name: string
  platform_trade_count: number
  platform_trade_amount: number
  channel_trade_count: number
  channel_trade_amount: number
  match_count: number
  match_amount: number
  long_count: number
  long_amount: number
  short_count: number
  short_amount: number
  amount_diff_count: number
  amount_diff_total: number
  status: string
  completed_at?: string
}

// 执行对账请求
export interface ExecuteReconciliationRequest {
  date: string
  channel: string
}

// 执行对账响应
export interface ExecuteReconciliationResponse {
  reconciliation_id: string
  platform_trade_count: number
  platform_trade_amount: number
  channel_trade_count: number
  channel_trade_amount: number
  match_count: number
  long_count: number
  short_count: number
  dispute_count: number
  status: string
}

// 差异记录项
export interface DisputeItem {
  id: string
  reconciliation_id: string
  dispute_type: string
  dispute_type_name: string
  local_order_no: string
  channel_trade_no: string
  local_amount: number
  channel_amount: number
  diff_amount: number
  reason: string
  handle_status: string
  handle_status_name: string
  handle_remark?: string
  handler_id?: string
  handler_name?: string
  handled_at?: string
  created_at: string
}

// 差异记录列表响应
export interface DisputeListResponse {
  items: DisputeItem[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}

// 处理差异请求
export interface HandleDisputeRequest {
  handle_status: string
  handle_remark?: string
}

// 历史对账记录项
export interface ReconciliationHistoryItem {
  id: string
  reconcile_date: string
  channel: string
  channel_name: string
  platform_trade_count: number
  platform_trade_amount: number
  channel_trade_count: number
  channel_trade_amount: number
  match_count: number
  long_count: number
  short_count: number
  amount_diff_count: number
  status: string
  status_name: string
  completed_at?: string
  created_at: string
}

// 历史对账记录响应
export interface ReconciliationHistoryResponse {
  items: ReconciliationHistoryItem[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}

// 对账查询参数
export interface ReconciliationQueryParams {
  date?: string
  channel?: string
  reconciliation_id?: string
  dispute_type?: string
  handle_status?: string
  status?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

// 渠道选项
export const CHANNEL_OPTIONS = [
  { value: 'alipay', label: '支付宝' },
  { value: 'wechat', label: '微信支付' },
  { value: 'unionpay', label: '银联' },
]

// 差异类型选项
export const DISPUTE_TYPE_OPTIONS = [
  { value: 'long', label: '长款（平台多）' },
  { value: 'short', label: '短款（渠道多）' },
  { value: 'amount_diff', label: '金额差异' },
]

// 处理状态选项
export const HANDLE_STATUS_OPTIONS = [
  { value: 'pending', label: '待处理' },
  { value: 'resolved', label: '已解决' },
  { value: 'ignored', label: '已忽略' },
]

// 对账状态选项
export const RECONCILIATION_STATUS_OPTIONS = [
  { value: 'pending', label: '待对账' },
  { value: 'processing', label: '对账中' },
  { value: 'completed', label: '已完成' },
  { value: 'disputed', label: '有差异' },
]

export const adminReconciliationApi = {
  // 获取充值记录明细
  getRechargeRecords: (params?: RechargeRecordsParams) => {
    return api.get<RechargeRecordsResponse>('/admin/recharge/records', params)
  },

  // 获取渠道收款汇总
  getChannelSummary: (date?: string) => {
    const params = date ? { date_str: date } : {}
    return api.get<ChannelSummaryResponse>('/admin/recharge/summary', params)
  },

  // 获取平台账户余额
  getPlatformAccounts: () => {
    return api.get<PlatformAccountsResponse>('/admin/platform/accounts')
  },

  // 更新平台账户
  updatePlatformAccount: (accountId: string, data: Partial<PlatformAccountItem>) => {
    return api.put<PlatformAccountItem>(`/admin/platform/accounts/${accountId}`, data)
  },

  // ==================== 对账核心API ====================

  /**
   * 执行对账
   * POST /admin/reconciliation/execute
   */
  executeReconciliation: (data: ExecuteReconciliationRequest) => {
    return api.post<ExecuteReconciliationResponse>('/admin/reconciliation/execute', data)
  },

  /**
   * 查询对账结果
   * GET /admin/reconciliation/result
   */
  getReconciliationResult: (params: { date: string; channel: string }) => {
    return api.get<ReconciliationResultItem>('/admin/reconciliation/result', params)
  },

  /**
   * 获取差异记录列表
   * GET /admin/reconciliation/disputes
   */
  getDisputes: (params?: ReconciliationQueryParams) => {
    return api.get<DisputeListResponse>('/admin/reconciliation/disputes', params)
  },

  /**
   * 处理差异
   * PUT /admin/reconciliation/disputes/{id}
   */
  handleDispute: (disputeId: string, data: HandleDisputeRequest) => {
    return api.put<DisputeItem>(`/admin/reconciliation/disputes/${disputeId}`, data)
  },

  /**
   * 获取历史对账记录
   * GET /admin/reconciliation/history
   */
  getHistory: (params?: ReconciliationQueryParams) => {
    return api.get<ReconciliationHistoryResponse>('/admin/reconciliation/history', params)
  },

  // ==================== 阶段三：定时对账与报表导出 ====================

  /**
   * 获取调度器状态
   * GET /admin/reconciliation/scheduler/status
   */
  getSchedulerStatus: () => {
    return api.get<SchedulerStatusResponse>('/admin/reconciliation/scheduler/status')
  },

  /**
   * 手动触发对账任务
   * POST /admin/reconciliation/scheduler/trigger
   */
  triggerReconciliation: (data: TriggerReconciliationRequest) => {
    return api.post<TriggerReconciliationResponse>('/admin/reconciliation/scheduler/trigger', data)
  },

  /**
   * 生成对账报表
   * POST /admin/reconciliation/report
   */
  generateReport: (data: ReportRequest) => {
    return api.post<ReportResponse>('/admin/reconciliation/report', data)
  },

  /**
   * 下载对账报表
   * GET /admin/reconciliation/report/download
   */
  getDownloadUrl: (params: ReportDownloadParams) => {
    const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'
    const query = new URLSearchParams({
      start_date: params.start_date,
      end_date: params.end_date,
      ...(params.channel && { channel: params.channel }),
      format: params.format || 'csv',
    })
    return `${BASE_URL}/admin/reconciliation/report/download?${query.toString()}`
  },
}

// ==================== 阶段三新增类型 ====================

// 调度器状态
export interface SchedulerStatus {
  is_running: boolean
  last_run_time?: string
  task_count: number
  tasks: SchedulerTask[]
}

export interface SchedulerTask {
  id: number
  date: string
  status: string
  executed_at: string
  channels: string[]
}

export interface SchedulerStatusResponse {
  is_running: boolean
  last_run_time?: string
  task_count: number
  tasks: SchedulerTask[]
}

// 手动触发对账请求
export interface TriggerReconciliationRequest {
  date?: string
  channels?: string[]
}

// 手动触发对账响应
export interface TriggerReconciliationResponse {
  status: string
  date: string
  channels: Record<string, any>
  total: {
    platform_trade_count: number
    platform_trade_amount: number
    channel_trade_count: number
    channel_trade_amount: number
    match_count: number
    long_count: number
    short_count: number
    amount_diff_count: number
  }
  executed_at: string
}

// 报表请求
export interface ReportRequest {
  start_date: string
  end_date: string
  channel?: string
  format?: 'csv' | 'excel'
}

// 报表项
export interface ReportItem {
  reconcile_date: string
  channel: string
  channel_name: string
  platform_trade_count: number
  platform_trade_amount: number
  channel_trade_count: number
  channel_trade_amount: number
  match_count: number
  match_rate: number
  long_count: number
  long_amount: number
  short_count: number
  short_amount: number
  amount_diff_count: number
  amount_diff_total: number
  pending_dispute_count: number
  status: string
}

// 报表响应
export interface ReportResponse {
  items: ReportItem[]
  summary: {
    total_count: number
    total_platform_amount: number
    total_channel_amount: number
    total_match_count: number
    total_long_count: number
    total_short_count: number
    total_amount_diff: number
    total_pending: number
  }
  generated_at: string
  date_range: {
    start_date: string
    end_date: string
  }
}

// 报表下载参数
export interface ReportDownloadParams {
  start_date: string
  end_date: string
  channel?: string
  format?: 'csv' | 'excel'
}

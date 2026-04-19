/**
 * 通知 API 服务
 */

import { api } from './client'

// 通知类型
export type NotificationType = 'system' | 'billing' | 'api' | 'security'

// 通知优先级
export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent'

// 通知状态
export type NotificationStatus = 'unread' | 'read' | 'deleted'

// 通知项接口
export interface Notification {
  id: string
  title: string
  content: string
  notification_type: NotificationType
  priority: NotificationPriority
  status: NotificationStatus
  extra_data: Record<string, any>
  created_at: string
  read_at: string | null
}

// 通知列表响应
export interface NotificationListResponse {
  total: number
  page: number
  page_size: number
  notifications: Notification[]
}

// 未读数量响应
export interface UnreadCountResponse {
  unread_count: number
}

// 通知偏好设置
export interface NotificationPreference {
  email_enabled: boolean
  in_app_enabled: boolean
  push_enabled: boolean
  preferences: {
    system: boolean
    billing: boolean
    api: boolean
    security: boolean
  }
}

// 通知 API
export const notificationApi = {
  /**
   * 获取通知列表
   */
  getList: (params?: {
    status?: string
    notification_type?: string
    page?: number
    page_size?: number
  }) => {
    return api.get<NotificationListResponse>('/notifications', params)
  },

  /**
   * 获取未读通知数量
   */
  getUnreadCount: () => {
    return api.get<UnreadCountResponse>('/notifications/unread-count')
  },

  /**
   * 获取最近未读通知（用于下拉面板）
   */
  getRecent: (limit: number = 5) => {
    return api.get<Notification[]>('/notifications/recent', { limit })
  },

  /**
   * 标记单条通知为已读
   */
  markAsRead: (notificationId: string) => {
    return api.post(`/notifications/${notificationId}/read`)
  },

  /**
   * 标记所有通知为已读
   */
  markAllAsRead: () => {
    return api.post('/notifications/read-all')
  },

  /**
   * 删除通知
   */
  delete: (notificationId: string) => {
    return api.delete(`/notifications/${notificationId}`)
  },

  /**
   * 删除所有已读通知
   */
  deleteAllRead: () => {
    return api.delete('/notifications/read/delete-all')
  },

  /**
   * 获取通知偏好设置
   */
  getPreference: () => {
    return api.get<NotificationPreference>('/notifications/preferences')
  },

  /**
   * 更新通知偏好设置
   */
  updatePreference: (data: Partial<NotificationPreference>) => {
    return api.put<NotificationPreference>('/notifications/preferences', data)
  },
}

export default notificationApi

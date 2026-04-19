/**
 * 认证API
 */

import { api } from './client'

// 用户类型
export type UserType = 'super_admin' | 'admin' | 'owner' | 'developer' | 'user'

// 用户接口
export interface User {
  id: string
  username?: string      // 用户名
  email: string
  phone?: string
  user_type: UserType
  user_status: string
  role: string          // 角色: super_admin, admin, developer, user
  permissions: string[] // 权限列表
  email_verified: boolean
  vip_level: number
  created_at: string
  last_login_at?: string
  avatar_url?: string
}

// 登录请求（支持用户名或邮箱）
export interface LoginRequest {
  username?: string  // 用户名登录
  email?: string    // 邮箱登录
  password: string
}

// 注册请求
export interface RegisterRequest {
  username: string
  email: string
  password: string
  user_type?: 'user' | 'developer' | 'owner'
}

// Token响应
export interface TokenResponse {
  access_token: string
  refresh_token: string
  expires_in: number
}

// 认证API
export const authApi = {
  // 用户登录 - client.ts 已自动提取 data 字段，直接返回 TokenResponse
  login: (data: LoginRequest) => {
    return api.post<TokenResponse>('/auth/login', data)
  },
  
  // 用户注册 - client.ts 已自动提取 data 字段
  register: (data: RegisterRequest) => {
    return api.post<User>('/auth/register', data)
  },
  
  // 刷新Token - client.ts 已自动提取 data 字段
  refresh: (refresh_token: string) => {
    return api.post<TokenResponse>('/auth/refresh', { refresh_token })
  },
  
  // 获取当前用户信息 - client.ts 已自动提取 data 字段
  me: () => {
    return api.get<User>('/auth/me')
  },
  
  // 登出
  logout: () => {
    return api.post<{ message: string }>('/auth/logout')
  },
  
  // 修改密码
  changePassword: (old_password: string, new_password: string) => {
    return api.post('/auth/change-password', { old_password, new_password })
  },
  
  // 发送验证码
  sendVerifyCode: (email: string, type: 'register' | 'reset') => {
    return api.post('/auth/send-code', { email, type })
  },
  
  // 重置密码
  resetPassword: (email: string, code: string, new_password: string) => {
    return api.post('/auth/reset-password', { email, code, new_password })
  },
}

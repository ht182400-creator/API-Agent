/**
 * 认证API
 */

import { api, ApiResponse } from './client'

// 用户类型
export interface User {
  id: string
  email: string
  phone?: string
  user_type: 'developer' | 'owner' | 'admin'
  user_status: string
  email_verified: boolean
  vip_level: number
  created_at: string
  last_login_at?: string
}

// 登录请求
export interface LoginRequest {
  email: string
  password: string
}

// 注册请求
export interface RegisterRequest {
  email: string
  password: string
  user_type?: 'developer' | 'owner'
}

// Token响应
export interface TokenResponse {
  access_token: string
  refresh_token: string
  expires_in: number
}

// 认证API
export const authApi = {
  // 用户登录
  login: (data: LoginRequest) => {
    return api.post<ApiResponse<TokenResponse>>('/auth/login', data)
  },
  
  // 用户注册
  register: (data: RegisterRequest) => {
    return api.post<ApiResponse<User>>('/auth/register', data)
  },
  
  // 刷新Token
  refresh: (refresh_token: string) => {
    return api.post<ApiResponse<TokenResponse>>('/auth/refresh', { refresh_token })
  },
  
  // 获取当前用户信息
  me: () => {
    return api.get<ApiResponse<User>>('/auth/me')
  },
  
  // 登出
  logout: () => {
    return api.post<ApiResponse<{ message: string }>>('/auth/logout')
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

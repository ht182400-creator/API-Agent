/**
 * API客户端 - 统一HTTP请求封装
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { useAuthStore } from '../stores/auth'
import { logger } from '../utils/logger'

// API基础URL
const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

// 创建axios实例
const client: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
client.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    logger.debug(`[API Request] ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    logger.error('[API Request Error]', error.message)
    return Promise.reject(error)
  }
)

// 响应拦截器
client.interceptors.response.use(
  (response: AxiosResponse) => {
    const res = response.data
    
    logger.debug(`[API Response] ${response.config.url} - ${response.status}`, res)
    
    // 统一处理错误码
    if (res.code !== 0 && res.code !== undefined) {
      const error = new Error(res.message || '请求失败')
      ;(error as any).code = res.code
      ;(error as any).request_id = res.request_id
      logger.warn(`[API Error] ${response.config.url} - code:${res.code} ${res.message}`)
      return Promise.reject(error)
    }
    
    return res
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      
      logger.error(`[API Error] ${error.config?.url || 'unknown'} - ${status}`, {
        message: data?.message || data?.detail,
        code: data?.code,
        request_id: data?.request_id
      })
      
      // 从响应中提取错误消息
      let errorMessage = data?.message || data?.detail || ''
      
      switch (status) {
        case 401:
          // 401可能是Token过期或认证失败，保留错误消息用于显示
          errorMessage = errorMessage || '登录已过期，请重新登录'
          // 清除登录状态（仅在其他页面清除，登录页不跳转）
          if (!window.location.pathname.includes('/login')) {
            useAuthStore.getState().logout()
          }
          break
        case 403:
          errorMessage = errorMessage || '无权限访问'
          break
        case 404:
          errorMessage = errorMessage || '资源不存在'
          break
        case 429:
          errorMessage = errorMessage || '请求过于频繁，请稍后再试'
          break
        case 500:
          errorMessage = errorMessage || '服务器错误，请稍后再试'
          break
        default:
          errorMessage = errorMessage || '请求失败'
      }
      
      error.message = errorMessage
    } else if (error.request) {
      error.message = '网络连接失败，请检查网络'
      logger.error(`[API Network Error]`, error.message)
    }
    
    return Promise.reject(error)
  }
)

// API响应类型
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
  request_id?: string
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// 请求方法封装
export const api = {
  get<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<T> {
    return client.get(url, { params, ...config }).then((res) => res.data)
  },
  
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return client.post(url, data, config).then((res) => res.data)
  },
  
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return client.put(url, data, config).then((res) => res.data)
  },
  
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return client.delete(url, config).then((res) => res.data)
  },
}

export default client

/**
 * API客户端 - 统一HTTP请求封装
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { useAuthStore } from '../stores/auth'

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
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
client.interceptors.response.use(
  (response: AxiosResponse) => {
    const res = response.data
    
    // 统一处理错误码
    if (res.code !== 0 && res.code !== undefined) {
      const error = new Error(res.message || '请求失败')
      ;(error as any).code = res.code
      ;(error as any).request_id = res.request_id
      return Promise.reject(error)
    }
    
    return res
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case 401:
          // Token过期，清除登录状态
          useAuthStore.getState().logout()
          window.location.href = '/login'
          break
        case 403:
          error.message = data.message || '无权限访问'
          break
        case 404:
          error.message = data.message || '资源不存在'
          break
        case 429:
          error.message = data.message || '请求过于频繁'
          break
        case 500:
          error.message = data.message || '服务器错误'
          break
        default:
          error.message = data.message || '网络错误'
      }
    } else if (error.request) {
      error.message = '网络连接失败'
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

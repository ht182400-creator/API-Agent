/**
 * API客户端 - 统一HTTP请求封装
 * 
 * 特性:
 * - 自动添加认证 Token
 * - 统一错误处理
 * - 详细日志记录
 * - 请求/响应拦截器
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
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
    
    // 记录请求日志
    logger.logRequest(
      config.method?.toUpperCase() || 'GET',
      config.url || '',
      {
        params: config.params,
        data: config.data,
      }
    )
    
    return config
  },
  (error) => {
    logger.error('[Request Interceptor Error]', {
      message: error.message,
      code: error.code,
      url: error.config?.url,
    })
    return Promise.reject(error)
  }
)

// 响应拦截器
client.interceptors.response.use(
  (response: AxiosResponse) => {
    const { config, status, data } = response
    
    // 记录响应日志（记录原始响应）
    logger.logResponse(
      config.method?.toUpperCase() || 'GET',
      config.url || '',
      status,
      data
    )
    
    // 统一处理业务错误码
    if (data.code !== undefined && data.code !== 0) {
      const error = new Error(data.message || '请求失败') as AxiosError & { 
        code?: number
        request_id?: string
        userMessage?: string
      }
      error.code = data.code
      error.request_id = data.request_id
      error.userMessage = data.message  // 添加用户友好的错误消息
      
      logger.warn('[API Business Error]', {
        url: config.url,
        code: data.code,
        message: data.message,
        request_id: data.request_id,
      })
      
      return Promise.reject(error)
    }
    
    // 自动提取 data 字段（统一响应格式）
    // 后端返回: { code: 0, message: "success", data: {...} }
    // 前端直接获取: {...}
    const extractedData = data?.data !== undefined ? data.data : data
    
    // 返回提取后的数据，让 API 方法直接使用业务数据
    return {
      ...response,
      data: extractedData,
    } as AxiosResponse
  },
  (error: AxiosError & { userMessage?: string }) => {
    const { config, response, request } = error
    
    // 提取错误信息
    let errorMessage = ''
    let userMessage = ''  // 用户友好的错误消息
    
    if (response) {
      // 服务器响应了但有错误
      const data = response.data as any
      
      // 优先使用后端返回的 message
      if (data?.message) {
        errorMessage = typeof data.message === 'string' ? data.message : JSON.stringify(data.message)
        userMessage = errorMessage
      } else if (data?.detail) {
        errorMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
        userMessage = errorMessage
      }
      
      // 根据状态码设置默认消息
      if (!errorMessage) {
        switch (response.status) {
          case 400:
            errorMessage = '请求参数错误'
            userMessage = '数据验证失败，请检查输入'
            break
          case 401:
            errorMessage = '登录已过期'
            userMessage = '登录已过期，请重新登录'
            break
          case 403:
            errorMessage = '无权限访问'
            userMessage = '您没有权限执行此操作'
            break
          case 404:
            errorMessage = '资源不存在'
            userMessage = '请求的资源不存在'
            break
          case 422:
            errorMessage = '数据验证失败'
            userMessage = '数据格式不正确'
            break
          case 429:
            errorMessage = '请求过于频繁'
            userMessage = '请求过于频繁，请稍后再试'
            break
          case 500:
            errorMessage = '服务器错误'
            userMessage = '服务器开小差了，请稍后重试'
            break
          case 502:
          case 503:
          case 504:
            errorMessage = '服务暂时不可用'
            userMessage = '服务暂时不可用，请稍后重试'
            break
          default:
            errorMessage = `请求失败 (${response.status})`
            userMessage = `操作失败 (${response.status})`
        }
      }
      
      // 记录错误日志
      logger.logApiError(
        config?.method?.toUpperCase() || 'GET',
        config?.url || '',
        error
      )
      
      // 设置用户友好的错误消息
      error.userMessage = userMessage
      error.message = errorMessage
      error.code = data?.code
      ;(error as any).request_id = data?.request_id
      ;(error as any).responseData = data
      
      // 处理 401 - 自动登出
      if (response.status === 401 && !config?.url?.includes('/auth/')) {
        const currentPath = window.location.pathname
        // 避免在登录页触发
        if (!currentPath.includes('/login')) {
          logger.warn('[Auth] Token expired, logging out...')
          useAuthStore.getState().logout()
        }
      }
      
    } else if (request) {
      // 请求发出但没有收到响应
      errorMessage = '网络连接失败'
      userMessage = '网络连接失败，请检查网络'
      
      logger.error('[Network Error]', {
        message: 'No response received',
        url: config?.url,
        timeout: error.config?.timeout,
      })
      
      error.message = errorMessage
      error.userMessage = userMessage
      
    } else {
      // 请求配置出错
      errorMessage = '请求配置错误'
      userMessage = '请求配置错误'
      
      logger.error('[Config Error]', {
        message: error.message,
      })
      
      error.message = errorMessage
      error.userMessage = userMessage
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

// 分页响应 - 与后端 PaginatedResponse 对齐
export interface Pagination {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface PaginatedResponse<T> {
  items: T[]
  pagination: Pagination
}

// 请求方法封装
export const api = {
  get<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<T> {
    return client.get(url, { params, ...config }).then((res) => (res as any).data)
  },
  
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return client.post(url, data, config).then((res) => (res as any).data)
  },
  
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return client.put(url, data, config).then((res) => (res as any).data)
  },
  
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return client.delete(url, config).then((res) => (res as any).data)
  },
  
  patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return client.patch(url, data, config).then((res) => (res as any).data)
  },
}

export default client

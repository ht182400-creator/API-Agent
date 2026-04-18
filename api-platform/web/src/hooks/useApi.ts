/**
 * API 请求 Hook
 * 提供统一的错误处理和日志记录
 */

import { useCallback } from 'react'
import { useError } from '../contexts/ErrorContext'
import { logger } from '../utils/logger'

/**
 * API 请求封装 Hook
 * 
 * 使用方式:
 * ```tsx
 * const { request, isLoading } = useApi()
 * 
 * // 在函数中使用
 * const fetchData = async () => {
 *   const data = await request(() => api.getData())
 * }
 * ```
 */
export function useApi() {
  const { showError } = useError()

  /**
   * 执行 API 请求，自动处理错误
   */
  const request = useCallback(async <T>(
    apiFn: () => Promise<T>,
    options?: {
      onSuccess?: (data: T) => void
      onError?: (error: any) => void
      context?: string  // 用于日志记录的上下文
    }
  ): Promise<T | undefined> => {
    const { onSuccess, onError, context } = options || {}
    
    try {
      if (context) {
        logger.debug(`[${context}] Request started`)
      }
      
      const data = await apiFn()
      
      if (context) {
        logger.debug(`[${context}] Request succeeded`, data)
      }
      
      if (onSuccess) {
        onSuccess(data)
      }
      
      return data
    } catch (error: any) {
      // 记录错误日志
      if (context) {
        logger.error(`[${context}] Request failed`, {
          message: error.message,
          userMessage: error.userMessage,
          code: error.code,
        })
      }
      
      // 显示错误弹窗
      showError(error)
      
      if (onError) {
        onError(error)
      }
      
      return undefined
    }
  }, [showError])

  /**
   * 执行带重试的 API 请求
   */
  const requestWithRetry = useCallback(async <T>(
    apiFn: () => Promise<T>,
    maxRetries: number = 3,
    delay: number = 1000,
    context?: string
  ): Promise<T | undefined> => {
    let lastError: any
    
    for (let i = 0; i < maxRetries; i++) {
      try {
        if (context) {
          logger.debug(`[${context}] Attempt ${i + 1}/${maxRetries}`)
        }
        
        const data = await apiFn()
        
        if (context && i > 0) {
          logger.info(`[${context}] Succeeded on attempt ${i + 1}`)
        }
        
        return data
      } catch (error: any) {
        lastError = error
        
        if (context) {
          logger.warn(`[${context}] Attempt ${i + 1} failed`, {
            message: error.message,
            willRetry: i < maxRetries - 1,
          })
        }
        
        // 如果还有重试次数，等待后重试
        if (i < maxRetries - 1) {
          await new Promise(resolve => setTimeout(resolve, delay * (i + 1)))
        }
      }
    }
    
    // 所有重试都失败了
    if (context) {
      logger.error(`[${context}] All ${maxRetries} attempts failed`)
    }
    
    showError(lastError)
    return undefined
  }, [showError])

  return {
    request,
    requestWithRetry,
  }
}

/**
 * 页面加载时自动获取数据的 Hook
 */
export function useAsyncData<T>(
  fetchFn: () => Promise<T>,
  deps: any[] = [],
  options?: {
    immediate?: boolean
    context?: string
  }
) {
  const { request } = useApi()
  
  const load = useCallback(async () => {
    return request(fetchFn, { context: options?.context })
  }, [request, fetchFn, options?.context])

  return {
    load,
  }
}

export default useApi

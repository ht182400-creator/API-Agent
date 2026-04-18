/**
 * 全局错误处理 Context
 * 提供统一的错误处理和日志记录功能
 */

import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react'
import { Modal, Result, Button, Typography, Space, Collapse, message, Alert } from 'antd'
import { 
  ExclamationCircleOutlined, 
  CloseCircleOutlined, 
  WarningOutlined, 
  InfoCircleOutlined,
  BugOutlined,
  LogoutOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/auth'
import { logger, LogLevel } from '../utils/logger'

const { Text, Paragraph } = Typography
const { Panel } = Collapse

// 错误类型枚举
export enum ErrorType {
  AUTH = 'auth',               // 认证错误（登录过期、无权限等）
  VALIDATION = 'validation',    // 验证错误（参数错误等）
  NETWORK = 'network',          // 网络错误（连接失败、超时等）
  SERVER = 'server',           // 服务器错误（500等）
  NOT_FOUND = 'not_found',     // 资源不存在（404等）
  BUSINESS = 'business',       // 业务错误（余额不足、配额用完等）
  UNKNOWN = 'unknown',         // 未知错误
}

// 错误配置
interface ErrorConfig {
  icon: React.ReactNode
  title: string
  subTitle: string
  showLogout?: boolean
}

// 认证错误码对应的标题和副标题
const authErrorConfigByCode: Record<number, { title: string; subTitle: string }> = {
  40101: { title: '登录失败', subTitle: '用户名/邮箱或密码错误，请检查后重试' },
  40102: { title: '登录已过期', subTitle: '请重新登录后继续操作' },
  40103: { title: 'API Key已禁用', subTitle: '请联系管理员启用您的API Key' },
  40104: { title: 'API Key已过期', subTitle: '请联系管理员续期您的API Key' },
  40105: { title: 'API Key无效', subTitle: '请检查您的API Key是否正确' },
}

// 获取认证错误的配置（根据错误码）
function getAuthErrorConfig(error: any): ErrorConfig {
  const code = error?.response?.data?.code || error?.code
  const customConfig = authErrorConfigByCode[code]
  
  if (customConfig) {
    return {
      icon: <LogoutOutlined style={{ color: '#faad14', fontSize: 48 }} />,
      title: customConfig.title,
      subTitle: customConfig.subTitle,
      showLogout: true,
    }
  }
  
  // 默认配置
  return {
    icon: <LogoutOutlined style={{ color: '#faad14', fontSize: 48 }} />,
    title: '登录已过期',
    subTitle: '请重新登录后继续操作',
    showLogout: true,
  }
}

const errorConfigs: Record<ErrorType, ErrorConfig> = {
  [ErrorType.AUTH]: {
    icon: <LogoutOutlined style={{ color: '#faad14', fontSize: 48 }} />,
    title: '登录已过期',
    subTitle: '请重新登录后继续操作',
    showLogout: true,
  },
  [ErrorType.VALIDATION]: {
    icon: <WarningOutlined style={{ color: '#fa8c16', fontSize: 48 }} />,
    title: '数据验证失败',
    subTitle: '请检查输入的数据格式',
  },
  [ErrorType.NETWORK]: {
    icon: <InfoCircleOutlined style={{ color: '#1890ff', fontSize: 48 }} />,
    title: '网络连接失败',
    subTitle: '请检查网络连接后重试',
  },
  [ErrorType.SERVER]: {
    icon: <BugOutlined style={{ color: '#ff4d4f', fontSize: 48 }} />,
    title: '服务器开小差了',
    subTitle: '工程师已收到通知，正在处理中',
  },
  [ErrorType.NOT_FOUND]: {
    icon: <InfoCircleOutlined style={{ color: '#8c8c8c', fontSize: 48 }} />,
    title: '资源不存在',
    subTitle: '请求的资源已被删除或不存在',
  },
  [ErrorType.BUSINESS]: {
    icon: <ExclamationCircleOutlined style={{ color: '#52c41a', fontSize: 48 }} />,
    title: '业务限制',
    subTitle: '无法完成操作，请检查账户状态',
  },
  [ErrorType.UNKNOWN]: {
    icon: <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 48 }} />,
    title: '操作失败',
    subTitle: '发生未知错误，请稍后重试',
  }
}

// 错误上下文类型
interface ErrorContextType {
  // 显示错误弹窗
  showError: (error: any, retry?: () => void) => void
  // 关闭错误弹窗
  closeError: () => void
  // 显示成功提示
  showSuccess: (msg: string) => void
  // 显示警告提示
  showWarning: (msg: string) => void
  // 显示信息提示
  showInfo: (msg: string) => void
}

// 创建上下文
const ErrorContext = createContext<ErrorContextType | null>(null)

// 解析错误类型
function parseErrorType(error: any): ErrorType {
  if (!error) return ErrorType.UNKNOWN

  const status = error.response?.status || error.status
  const data = error.response?.data
  const message = (error.message || '').toLowerCase()

  // 根据状态码判断
  switch (status) {
    case 401:
      return ErrorType.AUTH
    case 403:
      return ErrorType.AUTH  // 权限不足也归类为认证问题
    case 404:
    case 410:
      return ErrorType.NOT_FOUND
    case 422:
      return ErrorType.VALIDATION
    case 400:
      // 检查是否是业务错误
      if (data?.code >= 40000 && data?.code < 50000) {
        return ErrorType.BUSINESS
      }
      return ErrorType.VALIDATION
    case 429:
      return ErrorType.BUSINESS  // 限流也算业务限制
    case 500:
    case 502:
    case 503:
    case 504:
      return ErrorType.SERVER
    case 0:
    case 'ECONNABORTED':
    case 'Network Error':
      return ErrorType.NETWORK
    default:
      // 根据错误消息关键词判断
      if (message.includes('network') || message.includes('fetch') || message.includes('连接') || message.includes('网络')) {
        return ErrorType.NETWORK
      }
      if (message.includes('auth') || message.includes('login') || message.includes('登录') || message.includes('认证') || message.includes('token')) {
        return ErrorType.AUTH
      }
      if (message.includes('quota') || message.includes('balance') || message.includes('余额') || message.includes('配额')) {
        return ErrorType.BUSINESS
      }
      return ErrorType.UNKNOWN
  }
}

// 提取友好的错误消息
function extractErrorMessage(error: any): string {
  if (!error) return '未知错误'

  // 优先使用后端返回的 message
  const data = error.response?.data
  if (data?.message) {
    const msg = typeof data.message === 'string' ? data.message : JSON.stringify(data.message)
    return msg.length > 200 ? msg.substring(0, 200) + '...' : msg
  }

  if (data?.detail) {
    const detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
    return detail.length > 200 ? detail.substring(0, 200) + '...' : detail
  }

  // 使用 error.message
  let msg = error.message || ''
  
  // 移除 traceback 等调试信息
  if (msg.includes('Traceback') || msg.includes('stack') || msg.includes('\\n')) {
    msg = msg.split(/\\n|\n/)[0] || msg
  }

  if (msg.length > 200) {
    msg = msg.substring(0, 200) + '...'
  }

  return msg || '操作失败'
}

// 记录错误到日志
function logError(error: any, context?: string): void {
  const errorInfo = {
    message: error?.message || 'Unknown error',
    status: error?.response?.status,
    code: error?.response?.data?.code,
    url: error?.config?.url,
    method: error?.config?.method,
    stack: error?.stack,
  }
  
  if (context) {
    logger.error(`[${context}]`, errorInfo)
  } else {
    logger.error('[Error]', errorInfo)
  }
}

// 错误提供者组件
interface ErrorProviderProps {
  children: ReactNode
}

export function ErrorProvider({ children }: ErrorProviderProps) {
  const [errorModal, setErrorModal] = useState<{
    visible: boolean
    error: any
    retry?: () => void
    details?: any
  }>({
    visible: false,
    error: null,
  })

  const navigate = useNavigate()
  const { logout, isAuthenticated } = useAuthStore()

  // 显示错误
  const showError = useCallback((error: any, retry?: () => void) => {
    // 记录错误日志
    logError(error)

    setErrorModal({
      visible: true,
      error,
      retry,
      details: {
        timestamp: new Date().toISOString(),
        url: error?.config?.url,
        method: error?.config?.method,
        status: error?.response?.status,
        code: error?.response?.data?.code,
        requestId: error?.response?.data?.request_id,
      }
    })
  }, [])

  // 关闭错误
  const closeError = useCallback(() => {
    setErrorModal(prev => ({ ...prev, visible: false }))
  }, [])

  // 重新登录
  const handleRelogin = useCallback(() => {
    closeError()
    logout()
    navigate('/login')
  }, [logout, navigate, closeError])

  // 重试操作
  const handleRetry = useCallback(() => {
    closeError()
    if (errorModal.retry) {
      setTimeout(() => errorModal.retry!(), 100)
    }
  }, [closeError, errorModal.retry])

  // 快捷提示方法
  const showSuccess = useCallback((msg: string) => {
    message.success(msg)
    logger.info('[Success]', msg)
  }, [])

  const showWarning = useCallback((msg: string) => {
    message.warning(msg)
    logger.warn('[Warning]', msg)
  }, [])

  const showInfo = useCallback((msg: string) => {
    message.info(msg)
    logger.info('[Info]', msg)
  }, [])

  const errorType = errorModal.error ? parseErrorType(errorModal.error) : ErrorType.UNKNOWN
  // 认证错误根据错误码动态获取配置
  const config = errorType === ErrorType.AUTH 
    ? getAuthErrorConfig(errorModal.error) 
    : errorConfigs[errorType]
  const errorMessage = errorModal.error ? extractErrorMessage(errorModal.error) : ''

  return (
    <ErrorContext.Provider value={{ showError, closeError, showSuccess, showWarning, showInfo }}>
      {children}
      
      {/* 统一错误提示弹窗 */}
      <Modal
        open={errorModal.visible}
        onCancel={closeError}
        footer={null}
        width={520}
        centered
        closable={true}
        maskClosable={true}
        title={null}
      >
        <Result
          icon={config.icon}
          title={config.title}
          subTitle={config.subTitle}
          style={{ padding: '20px 0 0' }}
          extra={
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {/* 错误消息 - 后端返回的具体错误信息 */}
              <Alert 
                message={errorMessage}
                type={errorType === ErrorType.AUTH ? "warning" : "error"}
                showIcon
                style={{ maxWidth: 400, margin: '0 auto' }}
              />

              {/* 详细信息（可折叠） */}
              {import.meta.env.DEV && errorModal.details && (
                <Collapse ghost size="small">
                  <Panel header="详细信息（开发模式）" key="details">
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        时间: {errorModal.details.timestamp}
                      </Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        URL: {errorModal.details.method?.toUpperCase()} {errorModal.details.url}
                      </Text>
                      {errorModal.details.status && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          状态码: {errorModal.details.status}
                        </Text>
                      )}
                      {errorModal.details.code && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          错误码: {errorModal.details.code}
                        </Text>
                      )}
                      {errorModal.details.requestId && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          请求ID: {errorModal.details.requestId}
                        </Text>
                      )}
                    </Space>
                  </Panel>
                </Collapse>
              )}

              {/* 操作按钮 */}
              <Space style={{ marginTop: 8 }}>
                {errorModal.retry && (
                  <Button type="primary" onClick={handleRetry}>
                    重试
                  </Button>
                )}
                {config.showLogout && isAuthenticated && (
                  <Button onClick={handleRelogin}>
                    重新登录
                  </Button>
                )}
                <Button onClick={closeError}>
                  关闭
                </Button>
              </Space>
            </Space>
          }
        />
      </Modal>
    </ErrorContext.Provider>
  )
}

// Hook 用于访问错误上下文
export function useError() {
  const context = useContext(ErrorContext)
  if (!context) {
    throw new Error('useError must be used within ErrorProvider')
  }
  return context
}

export default ErrorProvider

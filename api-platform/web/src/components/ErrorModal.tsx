/**
 * 统一错误提示组件 - 使用 Ant Design Modal 显示友好的错误提示
 */

import { Modal, Result, Button, Typography, Space } from 'antd'
import { ExclamationCircleOutlined, CloseCircleOutlined, WarningOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { useState, useCallback } from 'react'

const { Text, Paragraph } = Typography

// 错误类型枚举
export enum ErrorType {
  AUTH = 'auth',           // 认证错误
  VALIDATION = 'validation', // 验证错误
  NETWORK = 'network',     // 网络错误
  SERVER = 'server',       // 服务器错误
  NOT_FOUND = 'not_found', // 资源不存在
  PERMISSION = 'permission', // 权限错误
  UNKNOWN = 'unknown',     // 未知错误
}

// 错误配置
interface ErrorConfig {
  icon: React.ReactNode
  title: string
  subTitle: string
  type: ErrorType
}

const errorConfigs: Record<ErrorType, ErrorConfig> = {
  [ErrorType.AUTH]: {
    icon: <ExclamationCircleOutlined style={{ color: '#faad14', fontSize: 48 }} />,
    title: '认证失败',
    subTitle: '请检查登录状态后重试',
    type: ErrorType.AUTH
  },
  [ErrorType.VALIDATION]: {
    icon: <WarningOutlined style={{ color: '#fa8c16', fontSize: 48 }} />,
    title: '数据验证失败',
    subTitle: '请检查输入的数据格式',
    type: ErrorType.VALIDATION
  },
  [ErrorType.NETWORK]: {
    icon: <InfoCircleOutlined style={{ color: '#1890ff', fontSize: 48 }} />,
    title: '网络错误',
    subTitle: '请检查网络连接后重试',
    type: ErrorType.NETWORK
  },
  [ErrorType.SERVER]: {
    icon: <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 48 }} />,
    title: '服务器错误',
    subTitle: '服务器处理请求时发生错误',
    type: ErrorType.SERVER
  },
  [ErrorType.NOT_FOUND]: {
    icon: <InfoCircleOutlined style={{ color: '#8c8c8c', fontSize: 48 }} />,
    title: '资源不存在',
    subTitle: '请求的资源已被删除或不存在',
    type: ErrorType.NOT_FOUND
  },
  [ErrorType.PERMISSION]: {
    icon: <ExclamationCircleOutlined style={{ color: '#f5222d', fontSize: 48 }} />,
    title: '权限不足',
    subTitle: '您没有权限执行此操作',
    type: ErrorType.PERMISSION
  },
  [ErrorType.UNKNOWN]: {
    icon: <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 48 }} />,
    title: '操作失败',
    subTitle: '发生未知错误，请稍后重试',
    type: ErrorType.UNKNOWN
  }
}

// 解析错误类型
export function parseErrorType(error: any): ErrorType {
  if (!error) return ErrorType.UNKNOWN

  // 从 HTTP 状态码判断
  const status = error.response?.status || error.status
  switch (status) {
    case 401:
      return ErrorType.AUTH
    case 403:
      return ErrorType.PERMISSION
    case 404:
      return ErrorType.NOT_FOUND
    case 422:
    case 400:
      return ErrorType.VALIDATION
    case 500:
    case 502:
    case 503:
    case 504:
      return ErrorType.SERVER
    case 0:
    case 'ECONNABORTED':
      return ErrorType.NETWORK
    default:
      // 从错误消息判断
      const message = (error.message || '').toLowerCase()
      if (message.includes('network') || message.includes('fetch') || message.includes('连接')) {
        return ErrorType.NETWORK
      }
      if (message.includes('auth') || message.includes('login') || message.includes('登录') || message.includes('认证')) {
        return ErrorType.AUTH
      }
      if (message.includes('permission') || message.includes('权限') || message.includes('禁止')) {
        return ErrorType.PERMISSION
      }
      return ErrorType.UNKNOWN
  }
}

// 提取友好的错误消息
export function extractErrorMessage(error: any): string {
  if (!error) return '未知错误'

  // 优先使用 userMessage
  if (error.userMessage) return error.userMessage

  // 从 axios 响应提取
  const data = error.response?.data
  if (data?.message) return data.message
  if (data?.detail) return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)

  // 使用 error.message
  let message = error.message || ''

  // 移除 traceback 等调试信息
  if (message.includes('Traceback') || message.includes('stack') || message.includes('\\n')) {
    // 只取第一行有用的信息
    message = message.split('\\n')[0] || message.split('\n')[0] || '操作失败'
  }

  // 如果消息过长，截断
  if (message.length > 200) {
    message = message.substring(0, 200) + '...'
  }

  return message || '操作失败'
}

// 错误提示 Modal 的 props
interface ErrorModalProps {
  open: boolean
  error: any
  onClose: () => void
  onRetry?: () => void
  showDetails?: boolean
}

// 错误提示 Modal 组件
export function ErrorModal({ open, error, onClose, onRetry, showDetails = false }: ErrorModalProps) {
  const errorType = parseErrorType(error)
  const config = errorConfigs[errorType]
  const errorMessage = extractErrorMessage(error)

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={500}
      centered
      closable={true}
      maskClosable={true}
    >
      <Result
        icon={config.icon}
        title={config.title}
        subTitle={config.subTitle}
        extra={
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {/* 错误消息 */}
            <div style={{ 
              background: '#f5f5f5', 
              padding: '12px 16px', 
              borderRadius: 8,
              textAlign: 'center'
            }}>
              <Text type="secondary">{errorMessage}</Text>
            </div>

            {/* 详细错误信息（可选） */}
            {showDetails && error?.response?.data?.traceback && (
              <div style={{ 
                background: '#fff1f0', 
                padding: 12, 
                borderRadius: 8,
                maxHeight: 200,
                overflow: 'auto'
              }}>
                <Paragraph type="secondary" style={{ fontSize: 12, margin: 0 }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                    {error.response.data.traceback}
                  </pre>
                </Paragraph>
              </div>
            )}

            {/* 操作按钮 */}
            <Space style={{ marginTop: 16 }}>
              {onRetry && (
                <Button type="primary" onClick={onRetry}>
                  重试
                </Button>
              )}
              <Button onClick={onClose}>
                关闭
              </Button>
            </Space>
          </Space>
        }
      />
    </Modal>
  )
}

// Hook 用于管理错误状态
export function useErrorModal() {
  const [errorModalState, setErrorModalState] = useState<{
    open: boolean
    error: any
    onRetry?: () => void
  }>({
    open: false,
    error: null
  })

  const showError = useCallback((error: any, onRetry?: () => void) => {
    setErrorModalState({
      open: true,
      error,
      onRetry
    })
  }, [])

  const closeError = useCallback(() => {
    setErrorModalState(prev => ({ ...prev, open: false }))
  }, [])

  const ErrorModalComponent = useCallback(() => (
    <ErrorModal
      open={errorModalState.open}
      error={errorModalState.error}
      onClose={closeError}
      onRetry={errorModalState.onRetry}
    />
  ), [errorModalState, closeError])

  return {
    showError,
    closeError,
    ErrorModal: ErrorModalComponent
  }
}

export default ErrorModal

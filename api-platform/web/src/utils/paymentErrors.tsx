/**
 * 支付错误处理工具
 * V2.5 新增 - 统一的支付相关错误处理
 */

import { Result, Button, Space, Typography, Alert } from 'antd'
import { 
  CloudSyncOutlined, 
  ExclamationCircleOutlined, 
  ClockCircleOutlined,
  LinkOutlined,
  ReloadOutlined
} from '@ant-design/icons'

const { Text, Paragraph } = Typography

// 支付错误类型
export enum PaymentErrorType {
  // 支付通道/网关错误
  PAYMENT_GATEWAY_ERROR = 'payment_gateway_error',    // AE0310600325 等网关错误
  PAYMENT_TIMEOUT = 'payment_timeout',                // 支付超时
  PAYMENT_NETWORK_ERROR = 'payment_network_error',   // 网络问题
  
  // 订单相关错误
  ORDER_NOT_FOUND = 'order_not_found',                // 订单不存在
  ORDER_EXPIRED = 'order_expired',                     // 订单已过期
  ORDER_CANCELLED = 'order_cancelled',                 // 订单已取消
  ORDER_ALREADY_PAID = 'order_already_paid',           // 订单已支付
  ORDER_AMOUNT_MISMATCH = 'order_amount_mismatch',     // 金额不一致
  
  // 支付方式错误
  PAYMENT_METHOD_UNAVAILABLE = 'payment_method_unavailable', // 支付方式不可用
  
  // 沙箱环境错误
  SANDBOX_ERROR = 'sandbox_error',                    // 沙箱环境错误
  
  // 通用错误
  PAYMENT_FAILED = 'payment_failed',                  // 支付失败
  PAYMENT_CANCELLED = 'payment_cancelled',             // 用户取消支付
  UNKNOWN = 'unknown',                                 // 未知错误
}

// 支付错误配置
export interface PaymentErrorConfig {
  type: PaymentErrorType
  title: string
  subTitle: string
  icon: React.ReactNode
  retryable: boolean  // 是否可以重试
  showContactSupport?: boolean  // 是否显示联系客服
  showOrderDetails?: boolean   // 是否显示订单详情
  customTips?: string          // 自定义提示
}

// 支付宝/微信错误码映射
const paymentErrorMappings: Record<string, PaymentErrorType> = {
  // 支付宝错误码
  'AE0310600325': PaymentErrorType.PAYMENT_GATEWAY_ERROR,
  'AE0310600311': PaymentErrorType.PAYMENT_GATEWAY_ERROR,
  'ACQ.TRADE_NOT_EXIST': PaymentErrorType.ORDER_NOT_FOUND,
  'ACQ.TRADE_STATUS_ERROR': PaymentErrorType.ORDER_ALREADY_PAID,
  'ACQ.BuyerBalanceNotEnough': PaymentErrorType.PAYMENT_GATEWAY_ERROR,
  'ACQ.SystemError': PaymentErrorType.PAYMENT_GATEWAY_ERROR,
  'ACQ.InvalidParameter': PaymentErrorType.PAYMENT_GATEWAY_ERROR,
  'ACQ.AccessDenied': PaymentErrorType.PAYMENT_METHOD_UNAVAILABLE,
  
  // 通用错误码
  'timeout': PaymentErrorType.PAYMENT_TIMEOUT,
  'TIMEOUT': PaymentErrorType.PAYMENT_TIMEOUT,
  'network': PaymentErrorType.PAYMENT_NETWORK_ERROR,
  'NETWORK_ERROR': PaymentErrorType.PAYMENT_NETWORK_ERROR,
  'ERR_NETWORK': PaymentErrorType.PAYMENT_NETWORK_ERROR,
  
  // 订单状态
  'ORDER_EXPIRED': PaymentErrorType.ORDER_EXPIRED,
  'ORDER_CANCELLED': PaymentErrorType.ORDER_CANCELLED,
  'ORDER_PAID': PaymentErrorType.ORDER_ALREADY_PAID,
  
  // 沙箱
  'SANDBOX': PaymentErrorType.SANDBOX_ERROR,
  'sandbox': PaymentErrorType.SANDBOX_ERROR,
}

// 错误码对应的友好配置
const errorConfigs: Record<PaymentErrorType, PaymentErrorConfig> = {
  [PaymentErrorType.PAYMENT_GATEWAY_ERROR]: {
    type: PaymentErrorType.PAYMENT_GATEWAY_ERROR,
    title: '支付通道繁忙',
    subTitle: '支付通道暂时繁忙，请稍后重试',
    icon: <CloudSyncOutlined style={{ color: '#fa8c16', fontSize: 48 }} />,
    retryable: true,
    showContactSupport: true,
    customTips: '如急需充值，可选择稍后重试或联系客服处理'
  },
  [PaymentErrorType.PAYMENT_TIMEOUT]: {
    type: PaymentErrorType.PAYMENT_TIMEOUT,
    title: '支付超时',
    subTitle: '支付已超时，订单已关闭',
    icon: <ClockCircleOutlined style={{ color: '#1890ff', fontSize: 48 }} />,
    retryable: true,
    showOrderDetails: true,
    customTips: '请重新发起支付，订单有效期为10分钟'
  },
  [PaymentErrorType.PAYMENT_NETWORK_ERROR]: {
    type: PaymentErrorType.PAYMENT_NETWORK_ERROR,
    title: '网络连接失败',
    subTitle: '网络连接失败，请检查网络后重试',
    icon: <ExclamationCircleOutlined style={{ color: '#ff4d4f', fontSize: 48 }} />,
    retryable: true,
    customTips: '请确保网络连接稳定后重试支付'
  },
  [PaymentErrorType.ORDER_NOT_FOUND]: {
    type: PaymentErrorType.ORDER_NOT_FOUND,
    title: '订单不存在',
    subTitle: '订单信息有误，请刷新页面重试',
    icon: <ExclamationCircleOutlined style={{ color: '#8c8c8c', fontSize: 48 }} />,
    retryable: true,
    showOrderDetails: true,
  },
  [PaymentErrorType.ORDER_EXPIRED]: {
    type: PaymentErrorType.ORDER_EXPIRED,
    title: '订单已过期',
    subTitle: '订单已过期，请重新下单',
    icon: <ClockCircleOutlined style={{ color: '#ff4d4f', fontSize: 48 }} />,
    retryable: true,
    showOrderDetails: true,
    customTips: '订单有效期为10分钟，超过后将自动关闭'
  },
  [PaymentErrorType.ORDER_CANCELLED]: {
    type: PaymentErrorType.ORDER_CANCELLED,
    title: '订单已取消',
    subTitle: '该订单已被取消',
    icon: <ExclamationCircleOutlined style={{ color: '#8c8c8c', fontSize: 48 }} />,
    retryable: true,
    showOrderDetails: true,
    customTips: '如需继续充值，请重新下单'
  },
  [PaymentErrorType.ORDER_ALREADY_PAID]: {
    type: PaymentErrorType.ORDER_ALREADY_PAID,
    title: '订单已支付',
    subTitle: '该订单已完成支付',
    icon: <ExclamationCircleOutlined style={{ color: '#52c41a', fontSize: 48 }} />,
    retryable: false,
    customTips: '如未到账，请联系客服处理'
  },
  [PaymentErrorType.ORDER_AMOUNT_MISMATCH]: {
    type: PaymentErrorType.ORDER_AMOUNT_MISMATCH,
    title: '支付金额不一致',
    subTitle: '实际支付金额与订单金额不一致',
    icon: <ExclamationCircleOutlined style={{ color: '#faad14', fontSize: 48 }} />,
    retryable: false,
    showContactSupport: true,
    customTips: '请核实支付金额，或联系客服处理'
  },
  [PaymentErrorType.PAYMENT_METHOD_UNAVAILABLE]: {
    type: PaymentErrorType.PAYMENT_METHOD_UNAVAILABLE,
    title: '支付方式不可用',
    subTitle: '当前支付方式暂时不可用',
    icon: <ExclamationCircleOutlined style={{ color: '#fa8c16', fontSize: 48 }} />,
    retryable: true,
    customTips: '请尝试其他支付方式'
  },
  [PaymentErrorType.SANDBOX_ERROR]: {
    type: PaymentErrorType.SANDBOX_ERROR,
    title: '沙箱环境错误',
    subTitle: '支付测试环境暂时异常',
    icon: <CloudSyncOutlined style={{ color: '#722ED1', fontSize: 48 }} />,
    retryable: true,
    customTips: '沙箱环境可能不稳定，建议稍后重试或切换到生产环境测试'
  },
  [PaymentErrorType.PAYMENT_FAILED]: {
    type: PaymentErrorType.PAYMENT_FAILED,
    title: '支付失败',
    subTitle: '支付遇到问题，请稍后重试',
    icon: <ExclamationCircleOutlined style={{ color: '#ff4d4f', fontSize: 48 }} />,
    retryable: true,
    showContactSupport: true,
  },
  [PaymentErrorType.PAYMENT_CANCELLED]: {
    type: PaymentErrorType.PAYMENT_CANCELLED,
    title: '支付已取消',
    subTitle: '您已取消支付',
    icon: <ExclamationCircleOutlined style={{ color: '#8c8c8c', fontSize: 48 }} />,
    retryable: true,
    customTips: '如需继续充值，请重新发起支付'
  },
  [PaymentErrorType.UNKNOWN]: {
    type: PaymentErrorType.UNKNOWN,
    title: '支付异常',
    subTitle: '支付遇到问题，请稍后重试',
    icon: <ExclamationCircleOutlined style={{ color: '#ff4d4f', fontSize: 48 }} />,
    retryable: true,
    showContactSupport: true,
  },
}

/**
 * 解析错误类型
 */
export function parsePaymentErrorType(error: any): PaymentErrorType {
  if (!error) return PaymentErrorType.UNKNOWN

  // 1. 从错误码提取
  const errorCode = error.code || error.error_code || error.errorCode
  if (errorCode && paymentErrorMappings[errorCode]) {
    return paymentErrorMappings[errorCode]
  }

  // 2. 从错误消息提取
  const errorMessage = (error.message || error.msg || '').toLowerCase()
  
  // 检查特定的错误消息模式
  if (errorMessage.includes('ae03106') || errorMessage.includes('系统有点儿忙')) {
    return PaymentErrorType.PAYMENT_GATEWAY_ERROR
  }
  if (errorMessage.includes('timeout') || errorMessage.includes('超时')) {
    return PaymentErrorType.PAYMENT_TIMEOUT
  }
  if (errorMessage.includes('network') || errorMessage.includes('网络') || errorMessage.includes('连接')) {
    return PaymentErrorType.PAYMENT_NETWORK_ERROR
  }
  if (errorMessage.includes('not exist') || errorMessage.includes('不存在') || errorMessage.includes('TRADE_NOT_EXIST')) {
    return PaymentErrorType.ORDER_NOT_FOUND
  }
  if (errorMessage.includes('expired') || errorMessage.includes('已过期') || errorMessage.includes('超时')) {
    return PaymentErrorType.ORDER_EXPIRED
  }
  if (errorMessage.includes('cancel') || errorMessage.includes('取消')) {
    return PaymentErrorType.PAYMENT_CANCELLED
  }
  if (errorMessage.includes('already paid') || errorMessage.includes('已支付') || errorMessage.includes('TRADE_STATUS_ERROR')) {
    return PaymentErrorType.ORDER_ALREADY_PAID
  }
  if (errorMessage.includes('sandbox') || errorMessage.includes('沙箱')) {
    return PaymentErrorType.SANDBOX_ERROR
  }

  // 3. 从 HTTP 状态码判断
  const status = error.response?.status || error.status
  if (status === 404) {
    return PaymentErrorType.ORDER_NOT_FOUND
  }
  if (status === 0 || status === 'ECONNABORTED') {
    return PaymentErrorType.PAYMENT_NETWORK_ERROR
  }

  return PaymentErrorType.UNKNOWN
}

/**
 * 提取错误详情
 */
export function extractPaymentErrorDetails(error: any): {
  code?: string
  message: string
  orderNo?: string
} {
  if (!error) return { message: '未知错误' }

  // 错误码
  const code = error.code || error.error_code || error.errorCode || 
               error.response?.data?.code || error.response?.data?.error_code

  // 错误消息
  let message = error.userMessage || error.message || error.msg || ''
  
  // 从 axios 响应提取
  if (!message && error.response?.data) {
    const data = error.response.data
    message = data.message || data.msg || data.error || data.error_message || ''
  }

  // 清理消息
  if (message.includes('Traceback') || message.includes('stack')) {
    message = message.split('\n')[0] || '操作失败'
  }
  if (message.length > 200) {
    message = message.substring(0, 200) + '...'
  }

  // 订单号
  const orderNo = error.order_no || error.orderNo || 
                  error.response?.data?.order_no ||
                  error.response?.data?.payment_no

  return {
    code: code as string | undefined,
    message: message || '未知错误',
    orderNo: orderNo as string | undefined
  }
}

/**
 * 获取支付错误配置
 */
export function getPaymentErrorConfig(error: any): PaymentErrorConfig {
  const errorType = parsePaymentErrorType(error)
  return errorConfigs[errorType] || errorConfigs[PaymentErrorType.UNKNOWN]
}

/**
 * 渲染支付错误结果组件
 */
export interface PaymentErrorResultProps {
  error: any
  onRetry?: () => void
  onContactSupport?: () => void
  onClose?: () => void
  showOrderDetails?: boolean
  orderNo?: string
  amount?: number
}

export function PaymentErrorResult({ 
  error, 
  onRetry, 
  onContactSupport,
  onClose,
  showOrderDetails: forceShowDetails = false,
  orderNo,
  amount
}: PaymentErrorResultProps) {
  const config = getPaymentErrorConfig(error)
  const details = extractPaymentErrorDetails(error)
  
  // 如果没有强制显示订单详情，使用配置决定
  const showOrderDetails = forceShowDetails || config.showOrderDetails || false
  
  // 确定要显示的订单号
  const displayOrderNo = orderNo || details.orderNo

  return (
    <Result
      icon={config.icon}
      title={config.title}
      subTitle={config.subTitle}
      extra={
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* 错误详情 */}
          <div style={{ 
            background: '#f5f5f5', 
            padding: '12px 16px', 
            borderRadius: 8,
            textAlign: 'center'
          }}>
            {details.code && (
              <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>
                错误码：{details.code}
              </Text>
            )}
            <Text type="secondary">{details.message}</Text>
          </div>

          {/* 订单详情（可选） */}
          {showOrderDetails && displayOrderNo && (
            <div style={{ 
              background: '#fffbe6', 
              padding: 12, 
              borderRadius: 8,
              border: '1px solid #ffe58f'
            }}>
              <Space direction="vertical" size={4}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  订单号：{displayOrderNo}
                </Text>
                {amount && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    订单金额：¥{amount.toFixed(2)}
                  </Text>
                )}
              </Space>
            </div>
          )}

          {/* 自定义提示 */}
          {config.customTips && (
            <Alert
              type="warning"
              message={config.customTips}
              showIcon
              icon={<ExclamationCircleOutlined />}
            />
          )}

          {/* 操作按钮 */}
          <Space style={{ marginTop: 16 }}>
            {config.retryable && onRetry && (
              <Button type="primary" icon={<ReloadOutlined />} onClick={onRetry}>
                重新支付
              </Button>
            )}
            {config.showContactSupport && onContactSupport && (
              <Button icon={<LinkOutlined />} onClick={onContactSupport}>
                联系客服
              </Button>
            )}
            {onClose && (
              <Button onClick={onClose}>
                关闭
              </Button>
            )}
          </Space>
        </Space>
      }
    />
  )
}

/**
 * 显示支付错误的便捷函数（用于 message/notification）
 */
export function getPaymentErrorMessage(error: any): {
  type: 'success' | 'error' | 'warning' | 'info'
  content: string
} {
  const config = getPaymentErrorConfig(error)
  
  if (config.retryable) {
    return {
      type: 'warning',
      content: `${config.title}：${config.subTitle}`
    }
  } else {
    return {
      type: 'error',
      content: `${config.title}：${config.subTitle}`
    }
  }
}

/**
 * 判断是否是支付相关错误
 */
export function isPaymentError(error: any): boolean {
  if (!error) return false
  
  const errorType = parsePaymentErrorType(error)
  return errorType !== PaymentErrorType.UNKNOWN || 
         error.message?.toLowerCase().includes('payment') ||
         error.message?.toLowerCase().includes('pay') ||
         error.message?.includes('支付')
}

export default {
  PaymentErrorType,
  parsePaymentErrorType,
  extractPaymentErrorDetails,
  getPaymentErrorConfig,
  PaymentErrorResult,
  getPaymentErrorMessage,
  isPaymentError,
}

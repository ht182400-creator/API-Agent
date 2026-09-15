/**
 * 支付成功页面
 * 用于支付宝 return_url 跳转，显示支付成功信息并通知原始窗口
 * 
 * 流程：
 * 1. 从 URL 获取 out_trade_no 参数
 * 2. 查询支付状态获取详细信息
 * 3. 通过 postMessage 通知原始窗口（window.opener）
 * 4. 显示支付成功信息，提示用户关闭此页面
 */

import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Card, Result, Descriptions, Button, Spin, Alert, Space, Typography } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { paymentApi, PaymentStatus as ApiPaymentStatus } from '../api/payment'
import { useAuthStore } from '../stores/auth'

const { Title, Text, Paragraph } = Typography

/**
 * 页面内使用的支付状态。
 *
 * 说明：后端 /payments/status 实际返回的字段比 `api/payment.ts` 中声明的更多
 *（如 order_no / balance）。此前本页自行定义了**同名但结构不同**的接口，
 * 导致 API 返回值无法赋给本地 state（TS2345）。现改为**扩展** API 类型。
 */
interface PaymentStatus extends ApiPaymentStatus {
  order_no?: string
  balance?: number
}

export default function PaymentSuccess() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const outTradeNo = searchParams.get('out_trade_no')
  
  const [loading, setLoading] = useState(true)
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notified, setNotified] = useState(false)

  // 判断是否为普通用户
  const isNormalUser = user?.user_type === 'user'

  useEffect(() => {
    // 【新增】页面加载时检查是否已有支付成功结果（从其他标签页跳转过来）
    const checkExistingResult = () => {
      try {
        const resultStr = localStorage.getItem('payment_success_result')
        if (resultStr) {
          const result = JSON.parse(resultStr)
          console.log('[PaymentSuccess] 检测到已有支付结果:', result)
          // 清除，避免重复
          localStorage.removeItem('payment_success_result')
        }
      } catch (e) {
        console.error('[PaymentSuccess] 检查支付结果失败:', e)
      }
    }
    
    checkExistingResult()
    
    const fetchPaymentStatus = async () => {
      if (!outTradeNo) {
        setError('缺少订单号参数')
        setLoading(false)
        return
      }

      try {
        const status = await paymentApi.getPaymentStatus(outTradeNo)
        setPaymentStatus(status)
        
        // 通知原始窗口
        if (window.opener && !notified) {
          // 延迟通知，确保页面已渲染
          setTimeout(() => {
            if (window.opener) {
              window.opener.postMessage({
                type: 'PAYMENT_SUCCESS',
                paymentNo: outTradeNo,
                status: status.status,
                amount: status.amount
              }, '*')
              console.log('[PaymentSuccess] 已通知 opener 窗口', { outTradeNo, status: status.status })
              setNotified(true)
            }
          }, 500)
        }
      } catch (err: any) {
        console.error('[PaymentSuccess] 获取支付状态失败', err)
        setError(err.message || '获取支付状态失败')
      } finally {
        setLoading(false)
      }
    }

    fetchPaymentStatus()
  }, [outTradeNo])

  // 处理关闭窗口
  const handleClose = () => {
    // 【V7.4 修复】使用 localStorage 通知商户页面，解决跨窗口通信问题
    // 当 return_url 在新窗口打开时，window.opener 指向支付宝，无法直接 postMessage
    const paymentResult = {
      outTradeNo: outTradeNo,
      status: paymentStatus?.status || 'paid',
      amount: paymentStatus?.amount,
      timestamp: Date.now(),
      closed: true
    }
    
    console.log('[PaymentSuccess] handleClose 被调用，准备设置 localStorage:', paymentResult)
    
    try {
      // 设置到 localStorage，商户页面的 storage 事件监听器会收到通知
      localStorage.setItem('payment_success_result', JSON.stringify(paymentResult))
      console.log('[PaymentSuccess] localStorage 设置成功')
    } catch (e) {
      console.error('[PaymentSuccess] localStorage 设置失败:', e)
    }
    
    // 同时尝试 postMessage（兼容同一窗口的情况）
    if (window.opener) {
      console.log('[PaymentSuccess] window.opener 存在，尝试 postMessage')
      window.opener.postMessage({
        type: 'PAYMENT_SUCCESS_PAGE_CLOSED',
        paymentNo: outTradeNo,
        paymentStatus: paymentStatus,
        isSuccess: paymentStatus?.status === 'paid' || paymentStatus?.status === 'completed'
      }, '*')
    } else {
      console.log('[PaymentSuccess] window.opener 不存在，跳过 postMessage')
    }
    
    console.log('[PaymentSuccess] 准备关闭窗口')
    window.close()
  }

  // 返回充值页面
  const handleReturn = () => {
    if (window.opener) {
      // 如果有 opener，通知它刷新并关闭
      window.opener.postMessage({
        type: 'RETURN_TO_RECHARGE',
        paymentNo: outTradeNo
      }, '*')
      window.close()
    } else {
      // 没有 opener，跳转到充值页面
      navigate(isNormalUser ? '/user/recharge' : '/developer/recharge')
    }
  }

  // 渲染内容
  const renderContent = () => {
    if (loading) {
      return (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          {/* ⚠️ Spin 的 tip 单独使用不渲染 → 自行渲染文字 */}
          <Spin size="large" />
          <div style={{ marginTop: 12, color: '#666' }}>正在加载支付信息...</div>
        </div>
      )
    }

    if (error) {
      return (
        <Result
          status="error"
          icon={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
          title="获取支付信息失败"
          subTitle={error}
          extra={[
            <Button type="primary" key="return" onClick={handleReturn}>
              返回充值页面
            </Button>,
            <Button key="close" onClick={handleClose}>
              关闭页面
            </Button>
          ]}
        />
      )
    }

    if (!paymentStatus) {
      return (
        <Result
          status="warning"
          title="未找到支付信息"
          extra={[
            <Button type="primary" key="return" onClick={handleReturn}>
              返回充值页面
            </Button>
          ]}
        />
      )
    }

    return (
      <>
        <Result
          status="success"
          icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
          title={isNormalUser ? '升级成功！' : '充值成功！'}
          subTitle={
            isNormalUser 
              ? '恭喜！您已成为开发者，可以开始使用 API 服务了' 
              : `充值金额 ¥${paymentStatus.amount?.toFixed(2)} 已到账`
          }
        />
        
        <Card size="small" style={{ marginBottom: 16 }}>
          <Descriptions column={1} size="small" colon={false}>
            <Descriptions.Item label="订单号">
              <Text copyable={{ text: paymentStatus.payment_no || outTradeNo || '' }}>
                {paymentStatus.payment_no || outTradeNo}
              </Text>
            </Descriptions.Item>
            {paymentStatus.amount && (
              <Descriptions.Item label="充值金额">
                <Text strong style={{ fontSize: 16, color: '#52c41a' }}>
                  ¥{paymentStatus.amount.toFixed(2)}
                </Text>
              </Descriptions.Item>
            )}
            {paymentStatus.balance !== undefined && (
              <Descriptions.Item label="账户余额">
                <Text strong style={{ fontSize: 16 }}>
                  ¥{paymentStatus.balance.toFixed(2)}
                </Text>
              </Descriptions.Item>
            )}
            <Descriptions.Item label="支付状态">
              <Text type="success">
                {paymentStatus.status === 'paid' || paymentStatus.status === 'completed' ? '已支付' : paymentStatus.status}
              </Text>
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Alert 
          type="success" 
          message={isNormalUser 
            ? '恭喜！您已成为开发者' 
            : '充值已完成，余额已更新'
          } 
          description="您现在可以关闭此页面，返回商户平台继续操作"
          style={{ marginBottom: 16 }}
          showIcon
        />

        <Space style={{ width: '100%', justifyContent: 'center' }} direction="vertical">
          <Button type="primary" size="large" block onClick={handleReturn}>
            {isNormalUser ? '开始使用 API 服务' : '返回充值页面'}
          </Button>
          <Button block onClick={handleClose}>
            关闭此页面
          </Button>
        </Space>
      </>
    )
  }

  return (
    <div style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      background: '#f0f2f5',
      padding: 20
    }}>
      <Card 
        style={{ 
          width: 450, 
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          borderRadius: 8
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={4}>支付结果</Title>
        </div>
        {renderContent()}
      </Card>
    </div>
  )
}

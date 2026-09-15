/**
 * 充值中心页面
 * V2.5 新增
 */

import { useState, useEffect, useRef } from 'react'
import '../../styles/cyber-theme.css'
import { Card, Row, Col, Typography, Button, Tag, Empty, Spin, Modal, Radio, Space, message, Descriptions, Divider, Result, InputNumber, Alert } from 'antd'
import { 
  GiftOutlined, 
  CheckCircleOutlined, 
  WechatOutlined, 
  AlipayOutlined, 
  CreditCardOutlined,
  ReloadOutlined,
  ExclamationCircleOutlined,
  EditOutlined,
  RocketOutlined
} from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { paymentApi, RechargePackage, Payment, RechargeConfig } from '../../api/payment'
import { authApi } from '../../api/auth'
import { billingApi } from '../../api/billing'
import { useErrorModal } from '../../components/ErrorModal'
import { PaymentErrorResult, getPaymentErrorMessage, isPaymentError } from '../../utils/paymentErrors.tsx'
import { useAuthStore } from '../../stores/auth'
import styles from './Recharge.module.css'
import '../../styles/payment-methods.css'

const { Title, Text, Paragraph } = Typography

// 计算订单剩余有效期（秒）
// 后端直接计算 expires_in 返回，前端直接使用
const calculateRemainingSeconds = (expiresIn: number | undefined): number => {
  if (expiresIn === undefined || expiresIn === null) {
    console.warn('[倒计时] expires_in 为空，使用默认值 600')
    return 600
  }
  
  console.log('[倒计时] expires_in:', expiresIn)
  return Math.max(0, expiresIn)
}

// 支付方式配置
const PAYMENT_METHODS = [
  { value: 'wechat', label: '微信支付', icon: <WechatOutlined />, color: '#07C160' },
  { value: 'alipay', label: '支付宝', icon: <AlipayOutlined />, color: '#1677FF' },
  { value: 'bankcard', label: '银行卡', icon: <CreditCardOutlined />, color: '#722ED1' },
]

// 【调试日志】支付流程追踪
const paymentLogger = {
  info: (step: string, data?: any) => {
    const logData = { step, timestamp: new Date().toISOString(), ...data }
    console.log(`[PaymentFlow] ${step}`, logData)
    paymentApi.clientLog(step, 'info', logData).catch(() => {})
  },
  error: (step: string, error: any) => {
    const logData = { step, timestamp: new Date().toISOString(), error: String(error) }
    console.error(`[PaymentFlow] ERROR - ${step}`, logData)
    paymentApi.clientLog(step, 'error', logData).catch(() => {})
  },
  warn: (step: string, data?: any) => {
    const logData = { step, timestamp: new Date().toISOString(), ...data }
    console.warn(`[PaymentFlow] WARN - ${step}`, logData)
    paymentApi.clientLog(step, 'warning', logData).catch(() => {})
  }
}

export default function DeveloperRecharge() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [packages, setPackages] = useState<RechargePackage[]>([])
  const [selectedPackage, setSelectedPackage] = useState<RechargePackage | null>(null)
  // payment_method 取值受后端约束（详见 api/payment.ts 的 createPayment 参数类型），故收窄为联合类型
  const [paymentMethod, setPaymentMethod] = useState<'wechat' | 'alipay' | 'bankcard'>('alipay')
  const [paymentType, setPaymentType] = useState<'page' | 'qrcode'>('qrcode')  // 默认扫码支付
  const [payModalVisible, setPayModalVisible] = useState(false)
  const [creatingOrder, setCreatingOrder] = useState(false)
  const [currentPayment, setCurrentPayment] = useState<Payment | null>(null)
  const [paySuccess, setPaySuccess] = useState(false)
  const [countdown, setCountdown] = useState(0)
  
  // 最新账户余额
  const [currentBalance, setCurrentBalance] = useState<number | null>(null)
  
  // 支付错误处理
  const [payError, setPayError] = useState<any>(null)
  const [payErrorVisible, setPayErrorVisible] = useState(false)
  
  // 支付宝同步回调处理
  const [isProcessingCallback, setIsProcessingCallback] = useState(false)
  
  // 自定义金额
  const [showCustomAmount, setShowCustomAmount] = useState(false)
  const [customAmount, setCustomAmount] = useState<number | null>(null)
  const [rechargeConfig, setRechargeConfig] = useState<RechargeConfig | null>(null)
  
  // 扫码支付轮询
  const [qrcodePolling, setQrcodePolling] = useState(false)

  // 刷新二维码状态
  const [refreshingQrCode, setRefreshingQrCode] = useState(false)

  // 支付宝支付窗口引用，用于支付成功后主动关闭
  const payWindowRef = useRef<Window | null>(null)

  // 轮询支付窗口关闭的 interval ID
  const payWindowIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  
  // 【新增】用于跟踪最新的支付状态，避免闭包问题
  const paymentStateRef = useRef<{
    currentPayment: Payment | null
    payModalVisible: boolean
    paySuccess: boolean
  }>({ currentPayment: null, payModalVisible: false, paySuccess: false })
  
  // 同步 state 到 ref
  useEffect(() => {
    paymentStateRef.current = {
      currentPayment,
      payModalVisible,
      paySuccess
    }
  }, [currentPayment, payModalVisible, paySuccess])
  
  // 【新增】轮询定时器 ref，用于检测支付结果
  const paymentPollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  
  // 【新增】启动支付结果轮询
  const startPaymentPoll = () => {
    // 如果已经有轮询在运行，不再启动
    if (paymentPollIntervalRef.current) {
      console.log('[Recharge] 支付结果轮询已在运行，跳过启动')
      return
    }
    
    console.log('[Recharge] 启动支付结果轮询（每3秒一次）')
    paymentPollIntervalRef.current = setInterval(() => {
      const state = paymentStateRef.current
      
      // 【关键修复】只要弹窗打开且未成功，就继续轮询
      // handleRefreshStatus 内部会处理 currentPayment 为空的情况
      // 它会检查 URL 中的 out_trade_no 参数
      if (state.payModalVisible && !state.paySuccess) {
        // 【修复】只有终态才跳过轮询：paid, completed, failed, expired
        // cancelled 可能是因为超时，但用户可能已经支付，所以继续查询
        const terminalStatuses = ['paid', 'completed', 'failed', 'expired']
        if (state.currentPayment && terminalStatuses.includes(state.currentPayment.status)) {
          console.log('[Recharge] 跳过轮询：订单状态已是终态', state.currentPayment.status)
          return
        }
        
        console.log('[Recharge] 轮询查询支付状态...（当前状态:', state.currentPayment?.status || '无订单')
        // 【优化】自动轮询时不显示错误提示，避免干扰用户
        handleRefreshStatus(false)
      } else {
        // 条件不满足，停止轮询
        console.log('[Recharge] 停止支付结果轮询：条件不满足', {
          payModalVisible: state.payModalVisible,
          paySuccess: state.paySuccess
        })
        stopPaymentPoll()
      }
    }, 3000) // 每 3 秒查询一次
  }
  
  // 【新增】停止支付结果轮询
  const stopPaymentPoll = () => {
    if (paymentPollIntervalRef.current) {
      console.log('[Recharge] 停止支付结果轮询')
      clearInterval(paymentPollIntervalRef.current)
      paymentPollIntervalRef.current = null
    }
  }

  const { showError, ErrorModal: ErrorModalComponent } = useErrorModal()
  
  // 判断是否是普通用户
  const isNormalUser = user?.user_type === 'user'

  // 处理支付宝同步回调（带轮询机制，解决异步回调不稳定问题）
  const handleAlipayCallback = async () => {
    // 获取支付宝回调参数
    const outTradeNo = searchParams.get('out_trade_no')
    
    // 只要有 out_trade_no 就查询支付状态（支付宝回跳时可能不带 trade_status）
    if (!outTradeNo) return false
    
    setIsProcessingCallback(true)
    setPayModalVisible(true)
    message.loading({ content: '正在确认支付结果...', key: 'alipayCallback' })
    
    // 【优化轮询策略】前6次快速轮询(500ms)，后6次慢速(1s)，最后3次(2s)
    const pollPaymentStatus = async (): Promise<any> => {
      const intervals = [500, 500, 500, 500, 500, 500, 1000, 1000, 1000, 1000, 1000, 1000, 2000, 2000, 2000]
      
      for (let i = 0; i < intervals.length; i++) {
        try {
          // 【关键】后端会主动查询支付宝，即使异步回调没到也能获取真实状态
          const status = await paymentApi.getPaymentStatus(outTradeNo)
          console.log(`[AlipayCallback] 轮询第 ${i + 1}/${intervals.length} 次:`, status)
          
          if (status.status === 'paid' || status.status === 'completed') {
            return status
          }
        } catch (error) {
          console.error(`[AlipayCallback] 轮询第 ${i + 1} 次失败:`, error)
        }
        
        if (i < intervals.length - 1) {
          await new Promise(resolve => setTimeout(resolve, intervals[i]))
        }
      }
      return null
    }
    
    // 处理支付成功
    const handlePaymentSuccess = async (status: any) => {
      paymentLogger.info('handlePaymentSuccess 开始', { 
        outTradeNo, 
        status: status.status,
        payWindowRef_exists: !!payWindowRef.current,
        payWindowRef_closed: payWindowRef.current?.closed
      })
      
      // 关闭支付宝支付窗口（如果有）
      closePayWindow()
      
      // 更新订单信息
      setCurrentPayment({
        ...status,
        payment_no: outTradeNo,
        status: 'paid',
        amount: status.amount || currentPayment?.amount
      } as Payment)
      
      // 刷新余额
      await fetchBalance()
      
    // 显示成功界面（不关闭弹窗）
    setPaySuccess(true)
    clearPaymentFromSession()
    setIsProcessingCallback(false)
    
    // 5秒后自动刷新（使用 ref 确保正确检测状态）
    setTimeout(() => {
      if (paymentStateRef.current.paySuccess) {
        window.location.reload()
      }
    }, 5000)
  }
    
    // 显示支付超时对话框
    const showTimeoutDialog = () => {
      setCurrentPayment({
        payment_no: outTradeNo,
        status: 'pending'
      } as Payment)
      
      Modal.confirm({
        title: '支付状态确认超时',
        icon: <ExclamationCircleOutlined style={{ color: '#faad14' }} />,
        content: (
          <div>
            <Paragraph>
              支付宝已返回付款成功，但支付结果暂时无法确认。
            </Paragraph>
            <Paragraph type="secondary">
              可能原因：网络延迟或支付宝通道繁忙
            </Paragraph>
            <Alert 
              type="info" 
              message={'您的付款已由支付宝处理，余额将在稍后自动到账。如需立即到账，请点击"刷新状态"按钮。'} 
              style={{ marginTop: 12 }}
            />
          </div>
        ),
        okText: '刷新状态',
        cancelText: '返回充值中心',
        onOk: () => {
          // 重新查询状态
          handleRefreshStatus()
        },
        onCancel: () => {
          // 清除 URL 参数，关闭弹窗
          clearUrlParams()
          setPayModalVisible(false)
        }
      })
    }
    
    try {
      // 【关键优化】立即查询一次，后端会主动查支付宝
      const initialStatus = await paymentApi.getPaymentStatus(outTradeNo)
      console.log('[AlipayCallback] 首次查询状态:', initialStatus)
      
      if (initialStatus.status === 'paid' || initialStatus.status === 'completed') {
        // 状态已经是成功，直接处理
        await handlePaymentSuccess(initialStatus)
      } else {
        // 状态还不是成功，开始轮询
        message.loading({ content: '支付确认中（正在同步支付结果），请稍候...', key: 'alipayCallback' })
        
        const polledStatus = await pollPaymentStatus()
        
        if (polledStatus) {
          await handlePaymentSuccess(polledStatus)
        } else {
          // 轮询超时，显示友好提示
          message.destroy('alipayCallback')
          showTimeoutDialog()
        }
      }
    } catch (error: any) {
      console.error('支付宝回调处理失败', error)
      // 【V7.4 修复】不要使用 outTradeNo 作为 payment_no，因为它们是不同的字段
      // outTradeNo 是 order_no（支付宝商户订单号），不是 payment_no（系统支付单号）
      // 保存 order_no，让 handleRefreshStatus 可以使用它
      setCurrentPayment({
        payment_no: '',  // 暂时为空，等刷新时再查询
        order_no: outTradeNo,  // 保存 order_no
        status: 'pending'
      } as Payment)
      setPayModalVisible(true)
      message.warning({ content: '查询失败，请点击"刷新状态"按钮确认', key: 'alipayCallback' })
    } finally {
      setIsProcessingCallback(false)
    }
    
    return true
  }
  
  // 清除 URL 中的支付宝回调参数
  const clearUrlParams = () => {
    const url = new URL(window.location.href)
    if (url.searchParams.has('out_trade_no') || url.searchParams.has('trade_status')) {
      url.searchParams.delete('out_trade_no')
      url.searchParams.delete('trade_status')
      url.searchParams.delete('trade_no')
      window.history.replaceState({}, '', url.pathname)
    }
  }

  useEffect(() => {
    // 初始化函数
    const init = async () => {
      await Promise.all([
        fetchPackages(),
        fetchConfig(),
        fetchBalance(),  // 获取账户余额
      ])
      
      // 【V7.1】检查是否有从支付宝返回的支付信息
      const outTradeNo = searchParams.get('out_trade_no')
      const tradeStatus = searchParams.get('trade_status')
      
      // 如果有 out_trade_no，直接查询支付状态（支付宝回跳时可能不带 trade_status）
      if (outTradeNo) {
        await handleAlipayCallback()
        return
      }
      
      // 【V7.1】如果没有支付宝回调参数，检查 sessionStorage 是否有待恢复的支付
      if (!outTradeNo) {
        const savedPayment = restorePaymentFromSession()
        if (savedPayment) {
          console.log('[Recharge] 从 sessionStorage 恢复支付信息:', savedPayment)
          // 从后端获取最新的订单信息（包括 created_at_timestamp）
          try {
            const paymentStatus = await paymentApi.getPaymentStatus(savedPayment.payment_no)
            // 后端返回 created_at（ISO 字符串），换算为时间戳；缺失时回退当前时间
            const createdAtTimestamp = paymentStatus.created_at
              ? new Date(paymentStatus.created_at).getTime()
              : Date.now()
            setCurrentPayment({
              payment_no: savedPayment.payment_no,
              order_no: savedPayment.order_no,
              amount: savedPayment.amount,
              pay_url: savedPayment.pay_url,
              status: paymentStatus.status,
              created_at: paymentStatus.created_at || new Date().toISOString(),
              expires_in: paymentStatus.expires_in
            } as Payment)
            setCountdown(calculateRemainingSeconds(paymentStatus.expires_in)) // 使用后端计算的剩余有效期
          } catch {
            // 如果查询失败，设置为默认值
            setCurrentPayment({
              payment_no: savedPayment.payment_no,
              order_no: savedPayment.order_no,
              amount: savedPayment.amount,
              pay_url: savedPayment.pay_url,
              status: 'pending',
              created_at: new Date().toISOString(),
            } as Payment)
            setCountdown(600)
          }
          setPayModalVisible(true)
          message.info('已恢复您的支付订单，请点击"刷新状态"确认支付结果')
        }
      }
    }
    
    init()
  }, [])

  // 倒计时刷新支付状态
  useEffect(() => {
    if (countdown > 0 && currentPayment && currentPayment.status === 'pending') {
      const timer = setTimeout(() => setCountdown(c => c - 1), 1000)
      return () => clearTimeout(timer)
    }
  }, [countdown, currentPayment])

  // 【V7.4 修复】监听来自支付成功页面的通知
  useEffect(() => {
    // 处理 localStorage 变化（跨窗口通信，解决 postMessage 无法触达的问题）
    const handleStorageChange = (event: StorageEvent) => {
      console.log('[Recharge] storage 事件触发:', { key: event.key, newValue: event.newValue, url: window.location.href })
      
      if (event.key === 'payment_success_result' && event.newValue) {
        try {
          const result = JSON.parse(event.newValue)
          console.log('[Recharge] 解析 payment_success_result 成功:', result)
          
          paymentLogger.info('收到支付成功页面关闭通知', {
            outTradeNo: result.outTradeNo,
            status: result.status,
            source: 'localStorage'
          })
          
          // 关闭支付宝支付窗口
          console.log('[Recharge] 调用 closePayWindow()')
          closePayWindow()
          
          // 设置支付成功状态
          if (result.status === 'paid' || result.status === 'completed') {
            // 二维码支付模式：显示小消息并关闭弹窗
            if (currentPayment?.qr_code) {
              console.log('[Recharge] 二维码支付成功，显示小消息')
              setCurrentPayment({
                payment_no: result.outTradeNo,
                status: 'paid',
                amount: result.amount,
              } as Payment)
              clearPaymentFromSession()
              fetchBalance()
              setPayModalVisible(false)
              message.success('充值成功！')
            } else {
              // 跳转支付模式：显示大界面（不关闭弹窗）
              console.log('[Recharge] 跳转支付成功，显示大界面')
              setCurrentPayment({
                payment_no: result.outTradeNo,
                status: 'paid',
                amount: result.amount,
              } as Payment)
              setPaySuccess(true)  // 显示大界面
              clearPaymentFromSession()
              fetchBalance()
            }
          } else {
            console.log('[Recharge] 支付状态不是成功:', result.status)
          }
          
          // 清除 localStorage 中的记录
          console.log('[Recharge] 清除 localStorage')
          localStorage.removeItem('payment_success_result')
        } catch (error) {
          console.error('[Recharge] 解析 payment_success_result 失败:', error)
        }
      }
    }
    
    // 【新增】检查支付结果的函数（仅处理跳转支付的回调）
    // 注意：二维码支付使用轮询机制，不需要也不应该处理 localStorage 中的跳转支付结果
    const checkPaymentResult = () => {
      // 【关键修复】只有在跳转支付模式下（没有二维码）才处理 localStorage 结果
      // 二维码支付有独立的轮询机制（startQrcodePolling），不受此影响
      if (currentPayment?.qr_code) {
        console.log('[Recharge] checkPaymentResult 跳过：二维码支付模式，无需处理 localStorage')
        return
      }
      
      try {
        const resultStr = localStorage.getItem('payment_success_result')
        if (resultStr) {
          const result = JSON.parse(resultStr)
          console.log('[Recharge] checkPaymentResult 检测到支付成功:', result)
          
          paymentLogger.info('checkPaymentResult 检测到支付成功', {
            outTradeNo: result.outTradeNo,
            status: result.status
          })
          
          // 关闭支付宝支付窗口
          closePayWindow()
          
          // 设置支付成功状态
          if (result.status === 'paid' || result.status === 'completed') {
            setCurrentPayment({
              payment_no: result.outTradeNo,
              status: 'paid',
              amount: result.amount,
            } as Payment)
            setPaySuccess(true)
            clearPaymentFromSession()
            fetchBalance()
            setPayModalVisible(false)
            message.success('充值成功！')
          }
          
          // 清除 localStorage
          localStorage.removeItem('payment_success_result')
        }
      } catch (error) {
        console.error('[Recharge] checkPaymentResult 失败:', error)
      }
    }
    
    // 【新增】监听窗口获得焦点事件（支付页面关闭后，当前页面会获得焦点）
    const handleWindowFocus = () => {
      const state = paymentStateRef.current
      console.log('[Recharge] 窗口获得焦点，直接查询支付状态')
      console.log('[Recharge] 当前状态:', { 
        hasPayment: !!state.currentPayment, 
        status: state.currentPayment?.status,
        modalVisible: state.payModalVisible,
        paySuccess: state.paySuccess
      })
      
      // 【关键修复】使用 ref 获取最新状态，避免闭包问题
      // 只在弹窗打开、支付未成功、有支付信息时才查询
      if (state.payModalVisible && !state.paySuccess && state.currentPayment) {
        if (state.currentPayment.status !== 'paid') {
          console.log('[Recharge] 调用 handleRefreshStatus 查询后端支付状态')
          // 【优化】自动刷新时不显示错误提示
          handleRefreshStatus(false)
        } else {
          console.log('[Recharge] 跳过查询：payment 状态已是', state.currentPayment.status)
        }
      } else {
        console.log('[Recharge] 跳过查询：条件不满足', { 
          payModalVisible: state.payModalVisible, 
          paySuccess: state.paySuccess,
          hasPayment: !!state.currentPayment
        })
      }
    }
    
    // 【新增】页面可见性变化时检查（从其他标签页返回时）
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        const state = paymentStateRef.current
        console.log('[Recharge] 页面可见性变为可见，直接查询支付状态')
        
        // 【关键修复】使用 ref 获取最新状态
        if (state.payModalVisible && !state.paySuccess && state.currentPayment) {
          if (state.currentPayment.status !== 'paid') {
            console.log('[Recharge] 调用 handleRefreshStatus 查询后端支付状态')
            // 【优化】自动刷新时不显示错误提示
            handleRefreshStatus(false)
          }
        }
      }
    }
    
    // 处理 postMessage（兼容同一窗口的情况）
    const handleMessage = (event: MessageEvent) => {
      const data = event.data
      if (!data || typeof data !== 'object') return
      
      console.log('[Recharge] 收到 postMessage:', data)
      
      // 处理支付成功页面关闭通知
      if (data.type === 'PAYMENT_SUCCESS_PAGE_CLOSED') {
        paymentLogger.info('收到支付成功页面关闭通知', {
          paymentNo: data.paymentNo,
          isSuccess: data.isSuccess,
          source: 'postMessage'
        })
        
        closePayWindow()
        
        if (data.isSuccess && data.paymentStatus) {
          const state = paymentStateRef.current
          // 二维码支付模式：显示小消息并关闭弹窗
          if (state.currentPayment?.qr_code) {
            console.log('[Recharge] postMessage 二维码支付成功，显示小消息')
            setCurrentPayment({
              payment_no: data.paymentNo,
              status: 'paid',
              amount: data.paymentStatus.amount,
            } as Payment)
            clearPaymentFromSession()
            fetchBalance()
            setPayModalVisible(false)
            message.success('充值成功！')
          } else {
            // 跳转支付模式：显示大界面（不关闭弹窗）
            console.log('[Recharge] postMessage 跳转支付成功，显示大界面')
            setCurrentPayment({
              payment_no: data.paymentNo,
              status: 'paid',
              amount: data.paymentStatus.amount,
            } as Payment)
            setPaySuccess(true)
            clearPaymentFromSession()
            fetchBalance()
          }
        } else {
          setTimeout(() => {
            window.location.reload()
          }, 300)
        }
        return
      }
      
      // 处理支付成功通知（兼容旧版本）
      if (data.type === 'PAYMENT_SUCCESS') {
        paymentLogger.info('收到支付成功通知（兼容模式）', {
          paymentNo: data.paymentNo,
          source: 'postMessage'
        })
        
        closePayWindow()
        const state = paymentStateRef.current
        // 二维码支付模式：显示小消息并关闭弹窗
        if (state.currentPayment?.qr_code) {
          console.log('[Recharge] postMessage PAYMENT_SUCCESS 二维码支付成功，显示小消息')
          setCurrentPayment({
            payment_no: data.paymentNo,
            status: 'paid',
            amount: data.amount,
          } as Payment)
          clearPaymentFromSession()
          fetchBalance()
          setPayModalVisible(false)
          message.success('充值成功！')
        } else {
          // 跳转支付模式：显示大界面（不关闭弹窗）
          console.log('[Recharge] postMessage PAYMENT_SUCCESS 跳转支付成功，显示大界面')
          setCurrentPayment({
            payment_no: data.paymentNo,
            status: 'paid',
            amount: data.amount,
          } as Payment)
          setPaySuccess(true)
          clearPaymentFromSession()
          fetchBalance()
        }
        return
      }
      
      // 处理返回充值页面（兼容旧版本）
      if (data.type === 'RETURN_TO_RECHARGE') {
        paymentLogger.info('收到返回充值页面通知', { paymentNo: data.paymentNo })
        closePayWindow()
        setTimeout(() => {
          window.location.reload()
        }, 300)
      }
    }
    
    // 监听 localStorage 变化
    window.addEventListener('storage', handleStorageChange)
    window.addEventListener('message', handleMessage)
    // 【新增】监听窗口获得焦点
    window.addEventListener('focus', handleWindowFocus)
    // 【新增】监听页面可见性变化
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    return () => {
      window.removeEventListener('storage', handleStorageChange)
      window.removeEventListener('message', handleMessage)
      window.removeEventListener('focus', handleWindowFocus)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [])

  const fetchPackages = async () => {
    setLoading(true)
    try {
      const data = await paymentApi.getPackages()
      setPackages(data.filter(pkg => pkg.is_active))
    } catch (error: any) {
      showError(error, fetchPackages)
    } finally {
      setLoading(false)
    }
  }

  const fetchConfig = async () => {
    try {
      const config = await paymentApi.getConfig()
      setRechargeConfig(config)
    } catch (error) {
      console.error('获取充值配置失败', error)
    }
  }

  // 获取账户余额
  const fetchBalance = async () => {
    try {
      const account = await billingApi.getAccount()
      setCurrentBalance(account.balance)
    } catch (error) {
      console.error('获取账户余额失败', error)
    }
  }

  const handleSelectPackage = (pkg: RechargePackage) => {
    setSelectedPackage(pkg)
    setShowCustomAmount(false)
    setCustomAmount(null)
  }

  const handleCustomAmountSelect = () => {
    setSelectedPackage(null)
    setShowCustomAmount(true)
  }

  const handleCustomAmountChange = (value: number | null) => {
    setCustomAmount(value)
  }

  // ========== 扫码支付轮询函数（必须在 handleCreateOrder 之前定义）==========

  // 扫码支付轮询
  const startQrcodePolling = async (paymentNo: string) => {
    console.log('[DEBUG] startQrcodePolling 函数被调用, paymentNo:', paymentNo)
    setQrcodePolling(true)
    let isPolling = true  // 使用局部变量，避免 React 状态异步问题
    const intervals = [2000, 2000, 2000, 3000, 3000, 5000, 5000, 10000]
    
    for (let i = 0; i < intervals.length; i++) {
      if (!isPolling) break // 用户关闭弹窗时停止轮询
      
      try {
        const status = await paymentApi.getPaymentStatus(paymentNo)
        console.log(`[QRCode Poll] 第 ${i + 1} 次:`, status)
        
        if (status.status === 'paid' || status.status === 'completed') {
          isPolling = false
          setQrcodePolling(false)
          // 支付成功
          handleQrcodePaymentSuccess(status)
          return
        }
      } catch (error) {
        console.error(`[QRCode Poll] 第 ${i + 1} 次失败:`, error)
      }
      
      if (i < intervals.length - 1) {
        await new Promise(resolve => setTimeout(resolve, intervals[i]))
      }
    }
    
    // 轮询结束但未支付成功
    isPolling = false
    setQrcodePolling(false)
    message.warning({ content: '支付状态查询超时，请点击"刷新状态"按钮确认', key: 'qrcodePoll' })
  }

  // 扫码支付成功处理
  const handleQrcodePaymentSuccess = async (status: any) => {
    setQrcodePolling(false)
    closePayWindow() // 关闭支付宝支付窗口（如果有）
    
    // 更新订单信息
    setCurrentPayment({
      ...status,
      payment_no: status.payment_no || currentPayment?.payment_no,
      amount: status.amount || currentPayment?.amount,
    } as Payment)
    
    // 刷新余额
    await fetchBalance()
    
    // 显示成功界面（不关闭弹窗）
    setPaySuccess(true)
    clearPaymentFromSession()
    
    // 5秒后自动刷新（使用 ref 确保正确检测状态）
    setTimeout(() => {
      if (paymentStateRef.current.paySuccess) {
        window.location.reload()
      }
    }, 5000)
  }

  // 停止扫码轮询
  const stopQrcodePolling = () => {
    setQrcodePolling(false)
  }

  // ========== 扫码支付轮询函数结束 ==========

  const handleCreateOrder = async () => {
    // 套餐充值
    if (selectedPackage) {
      setCreatingOrder(true)
      try {
        paymentLogger.info('handleCreateOrder 开始创建订单', {
          package_id: selectedPackage.id,
          paymentMethod,
          paymentType  // 调试：记录 paymentType 值
        })
        const payment = await paymentApi.createPayment({
          package_id: selectedPackage.id,
          payment_method: paymentMethod,
          payment_type: paymentType,  // 添加支付类型
        })
        paymentLogger.info('handleCreateOrder 订单创建成功', {
          payment_no: payment.payment_no,
          qr_code_exists: !!payment.qr_code,
          pay_url_exists: !!payment.pay_url
        })
        setCurrentPayment(payment)
        setPayModalVisible(true)
        setPaySuccess(false)
        setPayError(null) // 清除之前的错误
        setCountdown(calculateRemainingSeconds(payment.expires_in)) // 使用后端计算的剩余有效期
        savePaymentToSession(payment) // 保存到 sessionStorage
        message.success('订单创建成功')
        
        // 如果是扫码支付，自动开始轮询
        if (paymentType === 'qrcode' && payment.qr_code) {
          startQrcodePolling(payment.payment_no)
        } else {
          // 【新增】跳转支付模式：启动支付结果轮询作为后备
          startPaymentPoll()
        }
      } catch (error: any) {
        // 如果是支付相关错误，使用友好的错误提示
        if (isPaymentError(error)) {
          handlePaymentError(error)
        } else {
          showError(error, handleCreateOrder)
        }
      } finally {
        setCreatingOrder(false)
      }
      return
    }

    // 自定义金额充值（暂不支持扫码，调用原有接口）
    if (showCustomAmount && customAmount) {
      if (!rechargeConfig) {
        message.error('充值配置加载失败')
        return
      }
      if (customAmount < rechargeConfig.min_amount) {
        message.error(`最低充值金额为 ${rechargeConfig.min_amount} 元`)
        return
      }
      if (customAmount > rechargeConfig.max_amount) {
        message.error(`最高充值金额为 ${rechargeConfig.max_amount} 元`)
        return
      }

      setCreatingOrder(true)
      try {
        paymentLogger.info('handleCreateCustomOrder 开始创建自定义充值订单', {
          amount: customAmount,
          paymentMethod,
          paymentType
        })
        const payment = await paymentApi.createCustomRecharge({
          amount: customAmount,
          payment_method: paymentMethod,
          payment_type: paymentType,
        })
        paymentLogger.info('handleCreateCustomOrder 订单创建成功', {
          payment_no: payment.payment_no,
          qr_code_exists: !!payment.qr_code,
        })
        setCurrentPayment(payment)
        setPayModalVisible(true)
        setPaySuccess(false)
        setPayError(null) // 清除之前的错误
        setCountdown(calculateRemainingSeconds(payment.expires_in)) // 使用后端计算的剩余有效期
        savePaymentToSession(payment) // 保存到 sessionStorage
        message.success('订单创建成功')
        
        // 如果是扫码支付，自动开始轮询
        console.log('[DEBUG] 准备启动扫码轮询:', { paymentType, hasQrCode: !!payment.qr_code, payment_no: payment.payment_no })
        if (paymentType === 'qrcode' && payment.qr_code) {
          console.log('[DEBUG] 调用 startQrcodePolling:', payment.payment_no)
          startQrcodePolling(payment.payment_no)
        } else {
          // 【新增】跳转支付模式：启动支付结果轮询作为后备
          startPaymentPoll()
        }
      } catch (error: any) {
        // 如果是支付相关错误，使用友好的错误提示
        if (isPaymentError(error)) {
          handlePaymentError(error)
        } else {
          showError(error, handleCreateOrder)
        }
      } finally {
        setCreatingOrder(false)
      }
      return
    }

    message.warning('请选择充值套餐或输入自定义金额')
  }

  // 关闭支付宝支付窗口
  const closePayWindow = () => {
    // 【增强】详细记录调用时的窗口句柄状态
    paymentLogger.info('closePayWindow 被调用')
    
    // 停止轮询
    if (payWindowIntervalRef.current) {
      clearInterval(payWindowIntervalRef.current)
      payWindowIntervalRef.current = null
    }
    
    // 关闭窗口
    if (payWindowRef.current) {
      const windowRef = payWindowRef.current
      paymentLogger.info('closePayWindow 准备关闭支付窗口')
      
      if (!windowRef.closed) {
        try {
          windowRef.close()
        } catch (e) {
          // 跨域时可能失败，忽略
        }
      }
      payWindowRef.current = null
    } else {
      paymentLogger.info('closePayWindow 没有支付窗口引用（可能是return_url跳转模式）')
      
      // 对于 return_url 跳转模式，尝试关闭当前窗口
      try {
        window.close()
      } catch (e) {
        // 忽略
      }
    }
  }

  // 刷新二维码
  const handleRefreshQrCode = async () => {
    if (!currentPayment) return
    
    setRefreshingQrCode(true)
    try {
      const result = await paymentApi.refreshQrCode(currentPayment.payment_no)
      setCurrentPayment({
        ...currentPayment,
        qr_code: result.qr_code
      })
      message.success('二维码已刷新，请重新扫描')
    } catch (error: any) {
      // 使用友好的错误提示
      if (isPaymentError(error)) {
        handlePaymentError(error)
      } else {
        message.error('刷新二维码失败，请稍后重试')
      }
    } finally {
      setRefreshingQrCode(false)
    }
  }

  // 保存支付信息到 sessionStorage，以便从支付宝返回后恢复
  const savePaymentToSession = (payment: Payment) => {
    try {
      sessionStorage.setItem('pending_payment', JSON.stringify({
        payment_no: payment.payment_no,
        amount: payment.amount,
        order_no: payment.order_no,
        pay_url: payment.pay_url,
        savedAt: Date.now()
      }))
    } catch (e) {
      console.error('保存支付信息失败:', e)
    }
  }

  // 从 sessionStorage 恢复支付信息
  const restorePaymentFromSession = (): { payment_no: string; amount: number; order_no: string; pay_url?: string } | null => {
    try {
      const saved = sessionStorage.getItem('pending_payment')
      if (saved) {
        const data = JSON.parse(saved)
        // 检查是否过期（30分钟内）
        if (Date.now() - data.savedAt < 30 * 60 * 1000) {
          return data
        } else {
          sessionStorage.removeItem('pending_payment')
        }
      }
    } catch (e) {
      console.error('恢复支付信息失败:', e)
    }
    return null
  }

  // 清除 sessionStorage 中的支付信息
  const clearPaymentFromSession = () => {
    try {
      sessionStorage.removeItem('pending_payment')
    } catch (e) {
      console.error('清除支付信息失败:', e)
    }
  }

  const handleOpenPay = async () => {
    if (!currentPayment) return
    
    const isMockMode = rechargeConfig?.mock_mode ?? true
    
    if (isMockMode) {
      // 模拟支付模式（开发环境）
      Modal.confirm({
        title: '模拟支付',
        icon: <ExclamationCircleOutlined />,
        content: (
          <div>
            <p>支付金额：<Text strong>¥{currentPayment.amount.toFixed(2)}</Text></p>
            <p>支付方式：{PAYMENT_METHODS.find(m => m.value === paymentMethod)?.label}</p>
            <Paragraph type="secondary">
              （开发环境：点击确认后自动完成支付）
            </Paragraph>
          </div>
        ),
        onOk: async () => {
          // 模拟支付成功 - 调用后端回调接口
          message.loading({ content: '支付处理中...', key: 'pay' })
          try {
            await paymentApi.mockPaymentCallback(currentPayment.payment_no)
            clearPaymentFromSession()
            message.success({ content: '支付成功！', key: 'pay' })
            setPaySuccess(true)
            setCurrentPayment({ ...currentPayment, status: 'paid' })
            fetchBalance()  // 获取最新余额
          } catch (error: any) {
            // 使用友好的支付错误提示
            if (isPaymentError(error)) {
              handlePaymentError(error)
            } else {
              message.error({ content: '支付处理失败', key: 'pay' })
            }
          }
        },
      })
    } else {
      // 真实支付模式（生产环境）
      // 优先使用创建时已生成的支付链接
      if (currentPayment.pay_url) {
        // 检查是否是沙箱环境的错误链接
        if (currentPayment.pay_url.includes('系统繁忙') || 
            currentPayment.pay_url.includes('AE03106') ||
            currentPayment.pay_url.includes('error')) {
          handlePaymentError({
            code: 'AE0310600325',
            message: '支付宝支付通道暂时繁忙，请稍后重试',
            order_no: currentPayment.payment_no
          })
          return
        }
        
        // 【V7.0 修复】在跳转前显示确认提示
        Modal.confirm({
          title: '即将跳转到支付宝支付',
          icon: <AlipayOutlined style={{ color: '#1677FF' }} />,
          content: (
            <div>
              <p>支付金额：<Text strong>¥{currentPayment.amount.toFixed(2)}</Text></p>
              <Paragraph type="secondary">
                将在新窗口打开支付宝支付页面。请在新窗口完成支付。
              </Paragraph>
              <Alert 
                type="info" 
                message={'提示：如果支付宝页面显示错误，请关闭该窗口，然后点击"刷新状态"按钮确认支付结果。'} 
                style={{ marginTop: 8 }}
              />
            </div>
          ),
          okText: '打开支付宝支付',
          cancelText: '取消',
          onOk: async () => {
            paymentLogger.info('handleOpenPay.onOk 开始', { 
              payment_no: currentPayment.payment_no,
              pay_url: currentPayment.pay_url 
            })
            
            // 【关键修复】打开支付窗口前先查询订单状态，避免重复支付
            message.loading({ content: '正在检查订单状态...', key: 'checkStatus' })
            try {
              paymentLogger.info('handleOpenPay 开始查询订单状态', { 
                payment_no: currentPayment.payment_no 
              })
              const status = await paymentApi.getPaymentStatus(currentPayment.payment_no)
              paymentLogger.info('handleOpenPay 订单状态查询结果', { 
                payment_no: currentPayment.payment_no,
                status: status.status,
                pay_url: status.pay_url
              })
              
              // 如果订单已完成或已支付，提示用户并关闭支付弹窗
              if (status.status === 'paid' || status.status === 'completed') {
                paymentLogger.info('handleOpenPay 订单已支付，进入成功流程', { 
                  payment_no: currentPayment.payment_no,
                  status: status.status
                })
                message.destroy('checkStatus')
                setPayModalVisible(false)  // 关闭商户平台弹窗
                closePayWindow()  // 关闭支付宝窗口
                clearPaymentFromSession()
                setPaySuccess(true)
                setCurrentPayment({ ...currentPayment, status: 'paid' })
                await fetchBalance()
                message.success({ content: '该订单已支付成功！正在刷新...', key: 'paySuccess' })
                setTimeout(() => {
                  paymentLogger.info('handleOpenPay 触发页面刷新')
                  window.location.reload()
                }, 1500)
                return
              }
            } catch (error) {
              paymentLogger.error('handleOpenPay 查询订单状态失败', error)
              console.error('[handleOpenPay] 查询订单状态失败:', error)
              // 查询失败不影响后续流程，继续打开支付窗口
            }
            
            message.destroy('checkStatus')
            
            // 【V7.2】在新窗口打开支付宝，避免支付宝出错导致商户页面丢失
            paymentLogger.info('handleOpenPay 准备打开支付窗口', { 
              pay_url: currentPayment.pay_url 
            })
            const payWindow = window.open(currentPayment.pay_url, '_blank', 'width=900,height=700,scrollbars=yes')
            
            // 【新增】详细记录窗口句柄信息
            paymentLogger.info('handleOpenPay 支付窗口已打开', { 
              pay_window_object_type: payWindow ? 'Window' : 'null',
              pay_window_closed: payWindow?.closed,
              pay_window_ref_before: !!payWindowRef.current,
              pay_window_ref_closed_before: payWindowRef.current?.closed
            })
            
            if (payWindow) {
              // 保存支付窗口引用到 ref，用于支付成功后主动关闭
              payWindowRef.current = payWindow
              
              // 【新增】详细记录 ref 保存后的状态
              paymentLogger.info('handleOpenPay 窗口引用已保存到 payWindowRef', {
                pay_window_ref_after: !!payWindowRef.current,
                pay_window_ref_closed_after: payWindowRef.current?.closed,
                pay_window_ref_same: payWindowRef.current === payWindow
              })
              
              // 保存支付信息到 sessionStorage
              savePaymentToSession(currentPayment)
              message.success({ content: '支付页面已在新窗口打开', key: 'payUrl' })
              
              // 监听支付窗口状态
              payWindowIntervalRef.current = setInterval(() => {
                // 只在窗口关闭时记录，避免刷屏
                if (payWindow.closed) {
                  paymentLogger.info('handleOpenPay 检测到支付窗口已关闭，清除轮询')
                  if (payWindowIntervalRef.current) {
                    clearInterval(payWindowIntervalRef.current)
                    payWindowIntervalRef.current = null
                  }
                  // 用户关闭了支付窗口，自动刷新支付状态（不显示错误提示）
                  handleRefreshStatus(false)
                }
              }, 1000)
            } else {
              paymentLogger.warn('handleOpenPay 支付窗口打开失败（可能被阻止）')
              message.warning({
                content: '支付窗口被阻止，请允许弹窗后重试',
                duration: 5
              })
            }
          },
          onCancel: () => {
            // 用户取消，保持在当前页面
          }
        })
      } else {
        // 如果没有，尝试重新获取
        message.loading({ content: '获取支付链接...', key: 'payUrl' })
        try {
          const status = await paymentApi.getPaymentStatus(currentPayment.payment_no)
          if (status.pay_url) {
            // 检查是否错误链接
            if (status.pay_url.includes('系统繁忙') || 
                status.pay_url.includes('AE03106') ||
                status.pay_url.includes('error')) {
              handlePaymentError({
                code: 'AE0310600325',
                message: '支付宝支付通道暂时繁忙，请稍后重试',
                order_no: currentPayment.payment_no
              })
              return
            }
            
            // 保存到 sessionStorage
            savePaymentToSession({ ...currentPayment, pay_url: status.pay_url } as Payment)
            
            Modal.confirm({
              title: '即将跳转到支付宝支付',
              icon: <AlipayOutlined style={{ color: '#1677FF' }} />,
              content: (
                <div>
                  <p>支付金额：<Text strong>¥{currentPayment.amount.toFixed(2)}</Text></p>
                  <Paragraph type="secondary">
                    将在新窗口打开支付宝支付页面。请在新窗口完成支付。
                  </Paragraph>
                  <Alert 
                    type="info" 
                    message={'提示：如果支付宝页面显示错误，请关闭该窗口，然后点击"刷新状态"按钮确认支付结果。'} 
                    style={{ marginTop: 8 }}
                  />
                </div>
              ),
              okText: '打开支付宝支付',
              cancelText: '取消',
              onOk: () => {
                // 在新窗口打开支付宝
                const payWindow = window.open(status.pay_url, '_blank', 'width=900,height=700,scrollbars=yes')
                
                // 【新增】详细记录窗口句柄信息
                paymentLogger.info('handleOpenPay(else分支) 支付窗口已打开', { 
                  pay_window_object_type: payWindow ? 'Window' : 'null',
                  pay_window_closed: payWindow?.closed,
                  pay_window_ref_before: !!payWindowRef.current,
                  pay_window_ref_closed_before: payWindowRef.current?.closed
                })
                
                if (payWindow) {
                  // 保存支付窗口引用到 ref
                  payWindowRef.current = payWindow
                  
                  // 【新增】详细记录 ref 保存后的状态
                  paymentLogger.info('handleOpenPay(else分支) 窗口引用已保存到 payWindowRef', {
                    pay_window_ref_after: !!payWindowRef.current,
                    pay_window_ref_closed_after: payWindowRef.current?.closed,
                    pay_window_ref_same: payWindowRef.current === payWindow
                  })
                  
                  message.success({ content: '支付页面已在新窗口打开', key: 'payUrl' })
                  
                  // 监听支付窗口状态
                  payWindowIntervalRef.current = setInterval(() => {
                    // 只在窗口关闭时记录，避免刷屏
                    if (payWindow.closed) {
                      paymentLogger.info('handleOpenPay(else分支) 检测到窗口关闭，清除轮询')
                      if (payWindowIntervalRef.current) {
                        clearInterval(payWindowIntervalRef.current)
                        payWindowIntervalRef.current = null
                      }
                      // 窗口关闭时自动刷新（不显示错误提示）
                      handleRefreshStatus(false)
                    }
                  }, 1000)
                } else {
                  paymentLogger.warn('handleOpenPay(else分支) 支付窗口打开失败（可能被阻止）')
                  message.warning({
                    content: '支付窗口被阻止，请允许弹窗后重试',
                    duration: 5
                  })
                }
              }
            })
          } else {
            message.error({ content: '支付链接生成失败，请稍后重试', key: 'payUrl' })
          }
        } catch (error: any) {
          // 使用友好的支付错误提示
          if (isPaymentError(error)) {
            handlePaymentError(error)
          } else {
            message.error({ content: '获取支付状态失败', key: 'payUrl' })
          }
        }
      }
    }
  }

  const handlePayModalClose = () => {
    // 【修复】关闭弹窗时停止所有轮询
    stopPaymentPoll() // 停止支付结果轮询
    if (payWindowIntervalRef.current) {
      clearInterval(payWindowIntervalRef.current)
      payWindowIntervalRef.current = null
    }
    stopQrcodePolling() // 停止扫码轮询
    
    setPayModalVisible(false)
    setPayError(null)
    clearUrlParams()
  }

  // 支付错误处理函数
  const handlePaymentError = (error: any) => {
    setPayError(error)
    setPayErrorVisible(true)
  }

  // 关闭支付错误弹窗
  const handlePayErrorClose = () => {
    setPayErrorVisible(false)
    setPayError(null)
  }

  // 重试支付
  const handleRetryPayment = () => {
    handlePayErrorClose()
    handleOpenPay()
  }

  // 联系客服
  const handleContactSupport = () => {
    window.open('mailto:support@example.com?subject=充值问题咨询', '_blank')
  }

  // 【V6.0 重构】监听支付成功状态，使用强制刷新确保用户类型更新
  useEffect(() => {
    if (paySuccess) {
      // 【关键修复】支付成功后已由 handlePaymentSuccess/handleRefreshStatus 触发页面刷新
      // 这里只需要处理用户升级后的特殊跳转逻辑
      const currentUser = useAuthStore.getState().user
      const isUserNormal = currentUser?.user_type === 'user'
      
      if (isUserNormal) {
        // 普通用户升级后，跳转到用户首页
        setTimeout(() => {
          window.location.href = '/user'
        }, 1000)
      }
      // 开发者/所有者续费的情况已经在 handleRefreshStatus 中处理了
    }
  }, [paySuccess])

  // 【V7.4 修复】handleRefreshStatus 支持使用 order_no 查询
  // 【优化】添加 showError 参数，自动轮询时不显示错误提示，避免干扰用户
  const handleRefreshStatus = async (showError: boolean = true) => {
    if (!currentPayment) {
      // 【V7.4 修复】如果 currentPayment 为空，检查 URL 中是否有 out_trade_no
      const urlOutTradeNo = searchParams.get('out_trade_no')
      if (urlOutTradeNo) {
        console.log('[handleRefreshStatus] currentPayment 为空，使用 URL 中的 out_trade_no:', urlOutTradeNo)
        setCurrentPayment({
          payment_no: '',
          order_no: urlOutTradeNo,
          status: 'pending'
        } as Payment)
      } else {
        paymentLogger.warn('handleRefreshStatus 被调用但没有 currentPayment')
        // 【优化】只有明确需要显示错误时才提示
        if (showError) {
          message.error('没有支付信息')
        }
        return
      }
    }
    
    // 【V7.4 修复】优先使用 payment_no，如果为空则使用 order_no
    const queryKey = currentPayment.payment_no || currentPayment.order_no
    if (!queryKey) {
      paymentLogger.warn('handleRefreshStatus 既没有 payment_no 也没有 order_no')
      message.error('缺少查询参数')
      return
    }
    
    paymentLogger.info('handleRefreshStatus 开始', { 
      payment_no: currentPayment.payment_no,
      order_no: currentPayment.order_no,
      current_status: currentPayment.status,
      queryKey: queryKey,
      showError: showError
    })
    try {
      const status = await paymentApi.getPaymentStatus(queryKey)
      paymentLogger.info('handleRefreshStatus 查询结果', { 
        queryKey: queryKey,
        status: status.status
      })
      
      // 【调试】自动轮询时打印更多状态信息
      if (!showError) {
        console.log('[handleRefreshStatus] 自动轮询结果:', {
          queryKey: queryKey,
          status: status.status,
          isPending: status.status === 'pending',
          isSuccess: status.status === 'paid' || status.status === 'completed'
        })
      }
      // 【V7.4 修复】更新 payment_no（如果之前为空）
      const updatedPayment = {
        ...currentPayment,
        payment_no: status.payment_no || currentPayment.payment_no,
        status: status.status as any
      }
      setCurrentPayment(updatedPayment)
      // 同时检查 'paid' 和 'completed' 状态
      if (status.status === 'paid' || status.status === 'completed') {
        paymentLogger.info('handleRefreshStatus 检测到支付成功', {
          payment_no: updatedPayment.payment_no,
          status: status.status,
          isQrcode: !!currentPayment?.qr_code
        })
        closePayWindow()  // 关闭支付宝支付窗口
        stopPaymentPoll()  // 停止支付结果轮询
        clearPaymentFromSession()
        fetchBalance()  // 获取最新余额
        
        // 【跳转支付专用逻辑】显示大界面，不关闭弹窗
        if (!currentPayment?.qr_code) {
          console.log('[handleRefreshStatus] 跳转支付成功，显示大界面')
          setPaySuccess(true)  // 显示大界面
          message.success('支付成功！正在刷新页面...')
          // 5秒后自动刷新
          setTimeout(() => {
            if (paymentStateRef.current.paySuccess) {
              window.location.reload()
            }
          }, 5000)
        } else {
          // 二维码支付走独立逻辑，这里不应该被调用
          // 但以防万一，还是关闭弹窗刷新
          console.log('[handleRefreshStatus] 二维码支付被意外调用，关闭弹窗')
          setPayModalVisible(false)
          setPaySuccess(true)
          message.success('支付成功！正在刷新页面...')
          setTimeout(() => {
            window.location.reload()
          }, 800)
        }
      }
      // 不重置倒计时，让订单有效期自然倒数
    } catch (error: any) {
      // 【调试】记录自动轮询的错误详情
      console.error('[handleRefreshStatus] 查询失败:', {
        queryKey: queryKey,
        showError: showError,
        error: error?.message || error
      })
      paymentLogger.error('handleRefreshStatus 查询失败', { queryKey: queryKey, error })
      // 【优化】只有明确需要显示错误时才提示
      if (showError) {
        message.error('查询失败')
      }
    }
  }

  const renderPackageCard = (pkg: RechargePackage) => {
    const isSelected = selectedPackage?.id === pkg.id
    const hasBonus = pkg.bonus_amount > 0 || pkg.bonus_ratio > 0

    return (
      <Card
        key={pkg.id}
        className={`${styles.packageCard} ${isSelected ? styles.selected : ''} ${pkg.is_featured ? styles.featured : ''}`}
        hoverable
        onClick={() => handleSelectPackage(pkg)}
      >
        {pkg.is_featured && (
          <div className={styles.featuredTag}>
            <GiftOutlined /> 推荐
          </div>
        )}
        
        <div className={styles.packageHeader}>
          <Text strong className={styles.packageName}>{pkg.name}</Text>
          {hasBonus && (
            <Tag color="gold" icon={<GiftOutlined />}>
              {pkg.bonus_ratio > 0 ? `赠送${pkg.bonus_ratio}%` : `+¥${pkg.bonus_amount}`}
            </Tag>
          )}
        </div>

        <div className={styles.priceSection}>
          <span className={styles.currencyIcon}>¥</span>
          <span className={styles.price}>{pkg.price.toFixed(2)}</span>
        </div>

        <div className={styles.packageDetail}>
          <Text type="secondary">
            {hasBonus ? (
              <>实际到账：<Text strong>¥{((pkg.price || 0) + (pkg.bonus_amount || 0) + (pkg.price || 0) * ((pkg.bonus_ratio || 0) / 100)).toFixed(2)}</Text></>
            ) : (
              '无赠送'
            )}
          </Text>
        </div>

        {pkg.description && (
          <Paragraph type="secondary" className={styles.description}>
            {pkg.description}
          </Paragraph>
        )}

        {isSelected && (
          <div className={styles.selectedIndicator}>
            <CheckCircleOutlined /> 已选择
          </div>
        )}
      </Card>
    )
  }

  if (loading) {
    return (
      <div className={styles.loading}>
        <Spin size="large" tip="加载套餐列表..." />
      </div>
    )
  }

  return (
    <div className={`${styles.container} bamboo-bg-pattern`}>
      <ErrorModalComponent />
      
      {/* 普通用户升级引导 - 明确告知充值即升级 */}
      {isNormalUser && (
        <Alert
          type="warning"
          showIcon
          icon={<RocketOutlined />}
          message="充值即可升级为开发者"
          description={
            <div>
              <p style={{ marginBottom: 8 }}>
                <strong>升级说明：</strong>充值成功后，您的账户将自动升级为开发者，可享受：
              </p>
              <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                <li>创建API仓库并获得收益分成</li>
                <li>充值金额将作为账户余额使用</li>
              </ul>
            </div>
          }
          action={
            <Button type="primary" size="small" onClick={() => navigate('/user')}>
              查看升级详情
            </Button>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      <div className={styles.header}>
        <div>
          <Title level={4}>充值中心</Title>
          <Text type="secondary">选择充值套餐，完成支付后立即到账</Text>
        </div>
        <Space>
          {rechargeConfig?.mock_mode && (
            <Tag color="orange">⚠️ 开发环境 - 模拟支付</Tag>
          )}
          {!rechargeConfig?.mock_mode && (
            <Tag color="green">🛡️ 生产环境 - 真实支付</Tag>
          )}
          <Button icon={<ReloadOutlined />} onClick={fetchPackages}>
            刷新套餐
          </Button>
        </Space>
      </div>

      {/* 充值套餐 */}
      <Card title="选择充值套餐" className={styles.packageSection}>
        {packages.length === 0 ? (
          <Empty description="暂无充值套餐" />
        ) : (
          <>
            <Row gutter={[16, 16]}>
              {packages.map(pkg => (
                <Col xs={24} sm={12} lg={8} xl={6} key={pkg.id}>
                  {renderPackageCard(pkg)}
                </Col>
              ))}
            </Row>
            
            {/* 自定义金额选项 */}
            <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
              <Col xs={24} sm={12} lg={8} xl={6}>
                <Card
                  className={`${styles.packageCard} ${showCustomAmount ? styles.selected : ''}`}
                  hoverable
                  onClick={handleCustomAmountSelect}
                >
                  <div className={styles.packageHeader}>
                    <EditOutlined style={{ marginRight: 8 }} />
                    <Text strong>自定义金额</Text>
                  </div>
                  <div className={styles.packageDetail}>
                    <Text type="secondary">
                      {rechargeConfig ? `可充值 ${rechargeConfig.min_amount} - ${rechargeConfig.max_amount} 元` : '输入任意金额'}
                    </Text>
                  </div>
                  {showCustomAmount && (
                    <div className={styles.selectedIndicator}>
                      <CheckCircleOutlined /> 已选择
                    </div>
                  )}
                </Card>
              </Col>
            </Row>
          </>
        )}
      </Card>

      {/* 支付方式 */}
      {(selectedPackage || showCustomAmount) && (
        <Card title="选择支付方式" className={styles.paymentSection}>
          <Radio.Group
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
            className={styles.paymentMethods}
          >
            <Space size="large" wrap>
              {PAYMENT_METHODS.map(method => (
                <Radio.Button key={method.value} value={method.value} className="methodButton">
                  <Space>
                    <span style={{ color: method.color }}>{method.icon}</span>
                    <span>{method.label}</span>
                  </Space>
                </Radio.Button>
              ))}
            </Space>
          </Radio.Group>

          {/* 支付类型：扫码支付 vs 跳转支付 */}
          {paymentMethod === 'alipay' && (
            <>
              <Divider />
              <Radio.Group
                value={paymentType}
                onChange={(e) => setPaymentType(e.target.value)}
              >
                <Space size="large" wrap>
                  <Radio.Button value="qrcode">
                    <Space>
                      <span>📱</span>
                      <span>扫码支付（推荐）</span>
                    </Space>
                  </Radio.Button>
                  <Radio.Button value="page">
                    <Space>
                      <span>💻</span>
                      <span>跳转支付</span>
                    </Space>
                  </Radio.Button>
                </Space>
              </Radio.Group>
              <div style={{ marginTop: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {paymentType === 'qrcode' 
                    ? '• 页面直接显示二维码，无需跳转，推荐使用' 
                    : '• 跳转到支付宝完成支付，适合电脑操作'}
                </Text>
              </div>
            </>
          )}

          <Divider />

          <Descriptions bordered column={2}>
            <Descriptions.Item label="充值方式">
              {selectedPackage ? selectedPackage.name : '自定义金额'}
            </Descriptions.Item>
            {selectedPackage ? (
              <>
                <Descriptions.Item label="赠送金额">
                  {selectedPackage.bonus_amount > 0 && `+¥${selectedPackage.bonus_amount}`}
                  {selectedPackage.bonus_ratio > 0 && ` + ${selectedPackage.bonus_ratio}%`}
                  {!selectedPackage.bonus_amount && !selectedPackage.bonus_ratio && '无'}
                </Descriptions.Item>
                <Descriptions.Item label="支付金额">
                  <Text strong className={styles.payAmount}>¥{selectedPackage.price.toFixed(2)}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="实际到账">
                  <Text type="success">
                    ¥{((selectedPackage.price || 0) + (selectedPackage.bonus_amount || 0) + (selectedPackage.price || 0) * ((selectedPackage.bonus_ratio || 0) / 100)).toFixed(2)}
                  </Text>
                </Descriptions.Item>
              </>
            ) : (
              <>
                <Descriptions.Item label="充值金额">
                  <InputNumber
                    min={rechargeConfig?.min_amount || 1}
                    max={rechargeConfig?.max_amount || 10000}
                    value={customAmount}
                    onChange={handleCustomAmountChange}
                    prefix="¥"
                    style={{ width: 150 }}
                    placeholder={`${rechargeConfig?.min_amount || 1} - ${rechargeConfig?.max_amount || 10000}`}
                  />
                </Descriptions.Item>
                <Descriptions.Item label="赠送金额">
                  {rechargeConfig && rechargeConfig.default_bonus_ratio > 0 ? (
                    <Text type="warning">+{(customAmount || 0) * rechargeConfig.default_bonus_ratio}%</Text>
                  ) : '无'}
                </Descriptions.Item>
                <Descriptions.Item label="实际到账">
                  {rechargeConfig && rechargeConfig.default_bonus_ratio > 0 ? (
                    <Text type="success">
                      ¥{((customAmount || 0) * (1 + rechargeConfig.default_bonus_ratio)).toFixed(2)}
                    </Text>
                  ) : (
                    <Text type="success">¥{(customAmount || 0).toFixed(2)}</Text>
                  )}
                </Descriptions.Item>
              </>
            )}
          </Descriptions>

          <div className={styles.actionSection}>
            {selectedPackage ? (
              <Button 
                type="primary" 
                size="large" 
                onClick={handleCreateOrder}
                loading={creatingOrder}
                disabled={!selectedPackage}
              >
                立即充值 ¥{selectedPackage.price.toFixed(2)}
              </Button>
            ) : (
              <Button 
                type="primary" 
                size="large" 
                onClick={handleCreateOrder}
                loading={creatingOrder}
                disabled={!customAmount}
              >
                立即充值 ¥{customAmount?.toFixed(2) || '0.00'}
              </Button>
            )}
          </div>
        </Card>
      )}

      {/* 支付错误弹窗 */}
      <Modal
        title="支付异常"
        open={payErrorVisible}
        onCancel={handlePayErrorClose}
        footer={null}
        width={500}
        centered
        maskClosable={true}
      >
        <PaymentErrorResult
          error={payError}
          onRetry={handleRetryPayment}
          onContactSupport={handleContactSupport}
          onClose={handlePayErrorClose}
          orderNo={currentPayment?.payment_no}
          amount={currentPayment?.amount}
        />
      </Modal>

      {/* 支付弹窗 */}
      <Modal
        title={isProcessingCallback ? "支付确认中" : (paySuccess ? (isNormalUser ? "升级成功" : "充值成功") : "订单支付")}
        open={payModalVisible}
        onCancel={handlePayModalClose}
        footer={null}
        width={paySuccess ? 480 : 500}
        maskClosable={!isProcessingCallback && !paySuccess}
        closable={!isProcessingCallback && !paySuccess}
      >
        {isProcessingCallback ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin size="large" tip="正在确认支付结果，请稍候..." />
          </div>
        ) : paySuccess ? (
          // 【V8.0 优化】大尺寸成功界面，像支付宝跳转页面一样醒目
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            {/* 成功图标 */}
            <div style={{ 
              width: 80, 
              height: 80, 
              borderRadius: '50%', 
              background: '#f6ffed',
              border: '3px solid #52c41a',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px'
            }}>
              <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
            </div>
            
            {/* 成功标题 */}
            <Title level={3} style={{ color: '#52c41a', marginBottom: 8 }}>
              {isNormalUser ? '升级成功！' : '充值成功！'}
            </Title>
            
            {/* 副标题 */}
            <Text type="secondary" style={{ fontSize: 14 }}>
              {isNormalUser 
                ? '恭喜！您已成为开发者，可以开始使用 API 服务了'
                : `充值金额 ¥${currentPayment?.amount?.toFixed(2)} 已到账`
              }
            </Text>
            
            <Divider style={{ margin: '24px 0' }} />
            
            {/* 详细信息卡片 */}
            <Card 
              size="small" 
              style={{ 
                marginBottom: 20,
                background: '#fafafa',
                borderRadius: 8
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {/* 订单号 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text type="secondary">订单号</Text>
                  <Text copyable={{ text: currentPayment?.payment_no }} style={{ fontFamily: 'monospace' }}>
                    {currentPayment?.payment_no}
                  </Text>
                </div>
                
                {/* 充值金额 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text type="secondary">充值金额</Text>
                  <Text strong style={{ fontSize: 18, color: '#52c41a' }}>
                    ¥{currentPayment?.amount?.toFixed(2) || '0.00'}
                  </Text>
                </div>
                
                {/* 账户余额 */}
                {currentBalance !== null && !isNormalUser && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Text type="secondary">账户余额</Text>
                    <Text strong style={{ fontSize: 18 }}>
                      ¥{currentBalance.toFixed(2)}
                    </Text>
                  </div>
                )}
                
                {/* 支付状态 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text type="secondary">支付状态</Text>
                  <Tag color="success" style={{ margin: 0 }}>已支付</Tag>
                </div>
                
                {/* 支付时间 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text type="secondary">支付时间</Text>
                  <Text>{new Date().toLocaleString('zh-CN')}</Text>
                </div>
              </div>
            </Card>
            
            {/* 倒计时提示 */}
            <Alert 
              type="success" 
              message={
                <span>
                  页面将在 <Text strong style={{ color: '#52c41a' }}>5</Text> 秒后自动刷新
                </span>
              }
              style={{ marginBottom: 20 }}
              showIcon
            />
            
            {/* 操作按钮 */}
            <Space style={{ width: '100%' }} direction="vertical">
              <Button 
                type="primary" 
                size="large" 
                block 
                onClick={() => isNormalUser ? navigate('/user') : window.location.reload()}
              >
                {isNormalUser ? '开始使用 API 服务' : '立即刷新'}
              </Button>
              <Button 
                size="large" 
                block 
                onClick={handlePayModalClose}
              >
                继续充值
              </Button>
            </Space>
          </div>
        ) : (
          <>
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="订单号">{currentPayment?.payment_no}</Descriptions.Item>
              <Descriptions.Item label="充值金额">
                <Text strong>¥{currentPayment?.amount.toFixed(2)}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="支付方式">
                {PAYMENT_METHODS.find(m => m.value === paymentMethod)?.label}
              </Descriptions.Item>
              <Descriptions.Item label="剩余有效期">
                <Text type={countdown < 10 ? 'danger' : 'secondary'}>{countdown} 秒</Text>
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            {/* 扫码支付：显示二维码 */}
            {currentPayment?.qr_code && currentPayment.qr_code.length > 0 ? (
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                <Alert 
                  type="info" 
                  message="请使用支付宝扫码支付" 
                  showIcon 
                  style={{ marginBottom: 16 }}
                />
                <img 
                  src={currentPayment.qr_code} 
                  alt="支付宝扫码支付" 
                  style={{ 
                    width: 200, 
                    height: 200, 
                    border: '1px solid #f0f0f0',
                    borderRadius: 8
                  }} 
                />
                <div style={{ marginTop: 12 }}>
                  <Button 
                    size="small" 
                    icon={<ReloadOutlined />} 
                    onClick={handleRefreshQrCode}
                    loading={refreshingQrCode}
                  >
                    刷新二维码
                  </Button>
                </div>
                {qrcodePolling && (
                  <div style={{ marginTop: 16 }}>
                    <Spin size="small" />
                    <Text type="secondary" style={{ marginLeft: 8 }}>等待支付结果...</Text>
                  </div>
                )}
              </div>
            ) : (
              /* 跳转支付：显示支付按钮 */
              <div className={styles.payActions}>
                <Alert 
                  type="warning" 
                  message="支付完成后，请手动关闭支付宝窗口" 
                  showIcon 
                  style={{ marginBottom: 16 }}
                />
                <Button 
                  type="primary" 
                  size="large" 
                  block 
                  onClick={handleOpenPay}
                  disabled={countdown <= 0}
                >
                  {PAYMENT_METHODS.find(m => m.value === paymentMethod)?.icon} 
                  {countdown <= 0 ? '订单已过期' : '打开支付页面'}
                </Button>
              </div>
            )}

            <div style={{ marginTop: 16, textAlign: 'center' }}>
              <Space>
                <Button onClick={() => handleRefreshStatus()}>
                  <ReloadOutlined /> 刷新状态
                </Button>
                <Button 
                  danger 
                  onClick={async () => {
                    stopQrcodePolling()  // 停止扫码轮询
                    if (currentPayment) {
                      await paymentApi.cancelPayment(currentPayment.payment_no)
                      message.success('订单已取消')
                      setPayModalVisible(false)
                    }
                  }}
                >
                  取消订单
                </Button>
              </Space>
            </div>

            <Text type="secondary" className={styles.hint}>
              {currentPayment?.qr_code && currentPayment.qr_code.length > 0
                ? '提示：支付完成后请耐心等待，系统将自动确认'
                : '提示：支付完成后请点击"刷新状态"确认支付结果'}
            </Text>
          </>
        )}
      </Modal>
    </div>
  )
}

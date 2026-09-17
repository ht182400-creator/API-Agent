/**
 * 充值中心页面
 * V2.5 新增
 */

import { useState, useEffect, useRef } from 'react'
import '../../styles/cyber-theme.css'
import { Card, Row, Col, Typography, Button, Tag, Empty, Spin, Modal, Radio, Space, message, Divider, Result, Alert } from 'antd'
import { 
  CheckCircleOutlined, 
  // ⚠️ AlipayOutlined 仍有本文件内的直接使用（跳转支付 / 二维码弹窗），
  //    不能随 PAYMENT_METHODS 一起迁走；Wechat/CreditCard 才是仅由常量使用的。
  AlipayOutlined,
  ReloadOutlined,
  ExclamationCircleOutlined,
  EditOutlined,
  RocketOutlined
} from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { paymentApi, RechargePackage, Payment } from '../../api/payment'
// 注：authApi 早已是未使用的 dead import；billingApi / RechargeConfig 随 useRechargeData 抽出后不再需要
import { useErrorModal } from '../../components/ErrorModal'
import { PaymentErrorResult, getPaymentErrorMessage, isPaymentError } from '../../utils/paymentErrors.tsx'
import { useAuthStore } from '../../stores/auth'
import styles from './Recharge.module.css'
import '../../styles/payment-methods.css'
// 【P1-4 拆分】纯逻辑层已抽出到 ./recharge/（常量与支付日志）
import { PAYMENT_METHODS, calculateRemainingSeconds } from './recharge/constants'
import { paymentLogger } from './recharge/rechargeLogger'
import { useRechargeData } from './recharge/useRechargeData'
import { useEnvInfo } from '../../hooks/useEnvInfo'
  
import { PackageCard } from './recharge/components/PackageCard'
import { PaymentSummary } from './recharge/components/PaymentSummary'
import { PaymentModal } from './recharge/components/PaymentModal'
import { usePaymentFlow } from './recharge/payment/usePaymentFlow'
import { useQrcodePolling } from './recharge/useQrcodePolling'
import { usePaymentPolling } from './recharge/usePaymentPolling'
import {
  savePaymentToSession,
  restorePaymentFromSession,
  clearPaymentFromSession,
} from './recharge/paymentSession'

const { Title, Text, Paragraph } = Typography

export default function DeveloperRecharge() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user } = useAuthStore()
  // 【P1-4 拆分】loading / packages / rechargeConfig / currentBalance 及其加载函数
  // 已抽到 ./recharge/useRechargeData（在 useErrorModal() 之后调用，见下方）
  const [selectedPackage, setSelectedPackage] = useState<RechargePackage | null>(null)
  // payment_method 取值受后端约束（详见 api/payment.ts 的 createPayment 参数类型），故收窄为联合类型
  const [paymentMethod, setPaymentMethod] = useState<'wechat' | 'alipay' | 'bankcard'>('alipay')
  const [paymentType, setPaymentType] = useState<'page' | 'qrcode'>('qrcode')  // 默认扫码支付
  // 【M2-2 接线】生命周期状态（订单 / 弹窗 / 已支付 / 确认中）收敛进支付流程状态机，
  // 由 usePaymentFlow 提供**只读派生值 + 语义化 action** —— 页面内不再有这些 setState。
  // 方案与逐处映射见 docs/payment-flow-refactor.md。
  const flow = usePaymentFlow()
  const {
    payment: currentPayment,
    isModalOpen: payModalVisible,
    isPaid: paySuccess,
    isConfirming: isProcessingCallback,
  } = flow
  const [creatingOrder, setCreatingOrder] = useState(false)
  const [countdown, setCountdown] = useState(0)
  
  // 最新账户余额  —— 已迁至 ./recharge/useRechargeData
  
  // 支付错误处理
  const [payError, setPayError] = useState<any>(null)
  const [payErrorVisible, setPayErrorVisible] = useState(false)
  
  // 支付宝同步回调处理（isProcessingCallback）→ 现为 flow.isConfirming（见上）
  
  // 自定义金额
  const [showCustomAmount, setShowCustomAmount] = useState(false)
  const [customAmount, setCustomAmount] = useState<number | null>(null)
  // rechargeConfig 已迁至 ./recharge/useRechargeData
  
  // 扫码支付轮询状态 qrcodePolling 已随 ./recharge/useQrcodePolling 抽出（见 closePayWindow 之后）

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
  
  // 【新增】轮询定时器 ref（paymentPollIntervalRef）现由 ./recharge/usePaymentPolling 提供：
  //    下方「组件卸载清理所有定时器」的 effect 仍直接写它的 `.current`（同作用域）。

  // 【P1-4 修复】扫码轮询的"是否继续"标志（`qrcodePollingRef`）现由 ./recharge/useQrcodePolling
  //    提供并从那里解构出来 —— 它必须用 ref 而非局部变量：`stopQrcodePolling` 是由
  //    「取消订单 / 关闭弹窗」从**外部**调用的，局部变量对它不可见。原实现用局部 `isPolling`
  //    + stop 里只 setState，导致**取消订单后轮询仍会跑满 8 次（约 32 秒）**，期间若后端返回
  //    paid，还会把已取消的订单标记成支付成功（"用户关闭弹窗时停止轮询"的注释与实现不符）。
  //    ⚠️ 下方卸载清理 effect 仍直接写它的 `.current`（同作用域，运行时已初始化）。
  
  // 【P1-4 拆分】支付结果轮询（startPaymentPoll / stopPaymentPoll / 定时器 ref）已抽为
  // ./recharge/usePaymentPolling —— 见下方 handleRefreshStatus **定义之后**的调用处。

  // 【P1-4 修复】组件卸载时清理**所有**轮询定时器。
  // ⚠️ 原实现只在「关闭支付窗口 / 关闭弹窗」时清理；若用户开着支付弹窗直接切走页面
  //    （SPA 路由跳转 / 关标签页），这些定时器会继续跑并持续请求后端。
  //    实测：卸载后仍会多发出数次 getPaymentStatus（用例 TC-FE-RECHARGE-014 先失败后通过）。
  useEffect(() => {
    return () => {
      // 直接写 ref（不在卸载后 setState）
      qrcodePollingRef.current = false
      if (paymentPollIntervalRef.current) {
        clearInterval(paymentPollIntervalRef.current)
        paymentPollIntervalRef.current = null
      }
      if (payWindowIntervalRef.current) {
        clearInterval(payWindowIntervalRef.current)
        payWindowIntervalRef.current = null
      }
    }
  }, [])

  const { showError, ErrorModal: ErrorModalComponent } = useErrorModal()

  // 【环境同源】支付通道标签按运行环境区分（/health billing_environment，与顶栏徽标一致）
  const envInfo = useEnvInfo()

  // 【P1-4 拆分】套餐 / 充值配置 / 账户余额的加载与状态。
  // ⚠️ 把 showError 传进去（而非让 hook 自己 useErrorModal）：否则会存在两套独立的
  //    errorModal 状态，hook 里报的错不会显示在页面这个弹窗上。
  const { loading, packages, rechargeConfig, currentBalance, fetchPackages, fetchConfig, fetchBalance } =
    useRechargeData(showError)
  
  // 判断是否是普通用户
  const isNormalUser = user?.user_type === 'user'

  // 处理支付宝同步回调（带轮询机制，解决异步回调不稳定问题）
  const handleAlipayCallback = async () => {
    // 获取支付宝回调参数
    const outTradeNo = searchParams.get('out_trade_no')
    
    // 只要有 out_trade_no 就查询支付状态（支付宝回跳时可能不带 trade_status）
    if (!outTradeNo) return false
    
    // 【M2-2】先落一个"仅知 order_no"的占位订单（原实现在下方 catch 分支也这么做），
    // 再进入"确认中" —— confirming 会挡住重复信号与用户的关闭操作
    flow.restored({ payment_no: '', order_no: outTradeNo, status: 'pending' } as Payment)
    flow.startConfirming()
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
      
      // 【M2-2】结算走状态机唯一入口；这条路径是"跳转支付成功 → 保留弹窗显示大界面"
      flow.settlePaid(
        {
          ...status,
          payment_no: outTradeNo,
          amount: status.amount || currentPayment?.amount,
        } as Partial<Payment>,
        { closeModal: false }
      )
      
      // 刷新余额
      await fetchBalance()
      
    clearPaymentFromSession()
    
    // 5秒后自动刷新（使用 ref 确保正确检测状态）
    setTimeout(() => {
      if (paymentStateRef.current.paySuccess) {
        window.location.reload()
      }
    }, 5000)
  }
    
    // 显示支付超时对话框
    const showTimeoutDialog = () => {
      // 【M2-2】仍是未支付 → 订单补丁
      flow.settlePending({ payment_no: outTradeNo })
      
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
          flow.closeModal()
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
      // 【M2-2】占位订单（orderRestored 内含"开弹窗"）
      flow.restored({
        payment_no: '',  // 暂时为空，等刷新时再查询
        order_no: outTradeNo,  // 保存 order_no
        status: 'pending',
      } as Payment)
      message.warning({ content: '查询失败，请点击"刷新状态"按钮确认', key: 'alipayCallback' })
    } finally {
      // 【M2-2】退出"确认中"：若最终仍未成功，机器退回 awaiting（终态下该事件被忽略）
      flow.settlePending()
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
            // 【M2-2】恢复订单（内含"开弹窗"；过期时间由 expires_in 推算）
            flow.restored({
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
            // 【M2-2】查询失败也要把订单恢复出来（原行为：回落默认值）
            flow.restored({
              payment_no: savedPayment.payment_no,
              order_no: savedPayment.order_no,
              amount: savedPayment.amount,
              pay_url: savedPayment.pay_url,
              status: 'pending',
              created_at: new Date().toISOString(),
            } as Payment)
            setCountdown(600)
          }
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
            // 【M2-2】结算走唯一入口：弹窗去留由状态机**按支付方式推导**（扫码关、跳转留）。
            // 原来这段 if/else 两个分支各写一遍结算 —— 正是"同一规则抄 7 遍"的源头。
            const wasQrcode = !!currentPayment?.qr_code
            flow.settlePaid({
              payment_no: result.outTradeNo,
              amount: result.amount,
            } as Partial<Payment>)
            clearPaymentFromSession()
            fetchBalance()
            if (wasQrcode) message.success('充值成功！')
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
            // 【M2-2】这条路径原实现是"关弹窗 + 提示"（跳转语义但显式关掉）→ closeModal: true
            flow.settlePaid(
              { payment_no: result.outTradeNo, amount: result.amount } as Partial<Payment>,
              { closeModal: true }
            )
            clearPaymentFromSession()
            fetchBalance()
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
          // 【M2-2】合并两分支为一次结算（弹窗去留由状态机按支付方式推导）
          const wasQrcode = !!paymentStateRef.current.currentPayment?.qr_code
          console.log('[Recharge] postMessage 支付成功，结算')
          flow.settlePaid({
            payment_no: data.paymentNo,
            amount: data.paymentStatus.amount,
          } as Partial<Payment>)
          clearPaymentFromSession()
          fetchBalance()
          if (wasQrcode) message.success('充值成功！')
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
        // 【M2-2】同 PAGE_CLOSED：合并两分支为一次结算
        const wasQrcode = !!paymentStateRef.current.currentPayment?.qr_code
        console.log('[Recharge] postMessage PAYMENT_SUCCESS 支付成功，结算')
        flow.settlePaid({ payment_no: data.paymentNo, amount: data.amount } as Partial<Payment>)
        clearPaymentFromSession()
        fetchBalance()
        if (wasQrcode) message.success('充值成功！')
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

  // fetchPackages / fetchConfig / fetchBalance 已迁至 ./recharge/useRechargeData

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

  // ========== 扫码支付轮询函数已抽至 ./recharge/useQrcodePolling
  // （startQrcodePolling / handleQrcodePaymentSuccess / stopQrcodePolling 三者原样搬走；
  //   本文件下方 handleCreateOrder 仍按原名调用它们）==========

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
        // 【M2-2】下单成功 → 状态机进 awaiting（自动推导 mode / 开弹窗 / 算过期时间）
        flow.created(payment)
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
        // 【M2-2】下单成功 → 状态机进 awaiting（自动推导 mode / 开弹窗 / 算过期时间）
        flow.created(payment)
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

  // 【P1-4 拆分】扫码轮询（start / stop / 成功回调 / 是否继续的 ref）已抽为
  // ./recharge/useQrcodePolling。
  // ⚠️ 调用点必须在 closePayWindow **定义之后**：hook 入参在调用时立即求值，
  //    而 closePayWindow 是本组件内的 const —— 放在它前面会触发 TDZ。
  // ⚠️ 这里只解构出 4 个成员，其中 qrcodePollingRef 是给上方卸载清理 effect 用的。
  const { qrcodePolling, qrcodePollingRef, startQrcodePolling, stopQrcodePolling } =
    useQrcodePolling({
      currentPayment,
      // 【M2-2】结算改为状态机 action（hook 内部不再直接 setState）
      onPaid: flow.settlePaid,
      fetchBalance,
      closePayWindow,
      paymentStateRef,
    })

  // 刷新二维码
  const handleRefreshQrCode = async () => {
    if (!currentPayment) return
    
    setRefreshingQrCode(true)
    try {
      const result = await paymentApi.refreshQrCode(currentPayment.payment_no)
      // 【M2-2】订单补丁（二维码变了，订单与探测节奏都不变）
      flow.patchOrder({ qr_code: result.qr_code })
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

  // savePaymentToSession / restorePaymentFromSession / clearPaymentFromSession
  // 已迁至 ./recharge/paymentSession（含 30 分钟过期规则）

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
            // 【M2-2】模拟支付走跳转语义（保留弹窗显示成功大界面）
            flow.settlePaid(undefined, { closeModal: false })
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
                closePayWindow()  // 关闭支付宝窗口
                clearPaymentFromSession()
                // 【M2-2】该订单已支付：显式关弹窗（原实现如此），随后自动刷新页面
                flow.settlePaid(undefined, { closeModal: true })
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
    
    flow.closeModal()
    setPayError(null)
    clearUrlParams()
  }

  /**
   * 取消当前订单
   * （B5 轮随支付弹窗抽出而上移：弹窗组件保持纯展示，动作逻辑留在页面）
   */
  const handleCancelOrder = async () => {
    stopQrcodePolling() // 停止扫码轮询
    if (currentPayment) {
      await paymentApi.cancelPayment(currentPayment.payment_no)
      message.success('订单已取消')
      // 【M2-2】取消 → 状态机进终态 cancelled（弹窗同时关闭；此后任何 STATUS_* 都被忽略）
      flow.cancelOrder()
    }
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
        // 【M2-2】只有 order_no 时先落一张占位订单
        flow.restored({ payment_no: '', order_no: urlOutTradeNo, status: 'pending' } as Payment)
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
      // 【M2-2】订单补丁（更新 payment_no / status，不推进探测节奏）
      flow.patchOrder(updatedPayment)
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
          // 【M2-2】结算走唯一入口（跳转语义：保留弹窗显示大界面）
          flow.settlePaid(undefined, { closeModal: false })
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
          // 【M2-2】意外路径：显式关弹窗
          flow.settlePaid(undefined, { closeModal: true })
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

  // 【P1-4 拆分】支付结果轮询（跳转支付的后备查询）已抽为 ./recharge/usePaymentPolling。
  // ⚠️ 调用点有两个硬约束，缺一即报错：
  //    ① 必须在 handleRefreshStatus **定义之后**：hook 入参在调用时立即求值，
  //       而它是本组件内的 const —— 放前面会抛 TDZ（与 useQrcodePolling 同一约束）；
  //    ② 必须在下方的 `if (loading) return ...` **之前**：那是本组件的早退分支，
  //       挂载首屏 loading=true 会提前 return，hook 若放在其后就会出现
  //       "Rendered fewer hooks than expected"（实测 18 条用例全红）。
  //    ⚠️ 解构出的 paymentPollIntervalRef 是给上方「卸载清理所有定时器」的 effect 用的。
  const { paymentPollIntervalRef, startPaymentPoll, stopPaymentPoll } = usePaymentPolling({
    paymentStateRef,
    refreshStatus: handleRefreshStatus,
  })

  // renderPackageCard 已抽为展示组件 ./recharge/components/PackageCard

  if (loading) {
    return (
      <div className={styles.loading}>
        {/* ⚠️ antd 的 `tip` 只在嵌套/全屏模式生效，单独使用 <Spin tip /> 时文字不会显示
            （antd 会告警且用户看不到任何说明）→ 改为自行渲染文字 */}
        <Spin size="large" />
        <div style={{ marginTop: 12, color: '#666' }}>加载套餐列表...</div>
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
          {/* ⚠️ 按**运行环境**（/health 的 billing_environment）区分支付通道性质，与顶栏徽标同源：
              测试环境 → 测试支付通道；生产环境 → 真实支付通道。
              （不读 rechargeConfig.mock_mode：那是下单流程的行为分支，不是环境标识 ——
               曾因此让「真实支付通道」出现在 SIMULATION 环境，与顶栏矛盾，用户实测两轮反馈。） */}
          {envInfo?.billing_environment === 'production' ? (
            <Tag color="green">🛡️ 真实支付通道</Tag>
          ) : (
            <Tag color="orange">🧪 测试支付通道（模拟）</Tag>
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
                  <PackageCard
                    pkg={pkg}
                    selected={selectedPackage?.id === pkg.id}
                    onSelect={handleSelectPackage}
                  />
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

          <PaymentSummary
            selectedPackage={selectedPackage}
            customAmount={customAmount}
            rechargeConfig={rechargeConfig}
            onCustomAmountChange={handleCustomAmountChange}
          />

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

      {/* 支付弹窗 —— B5 轮已抽为 ./recharge/components/PaymentModal
          （三态：确认中 / 成功大界面 / 下单信息；「取消订单」的动作逻辑见 handleCancelOrder） */}
      <PaymentModal
        open={payModalVisible}
        isProcessingCallback={isProcessingCallback}
        paySuccess={paySuccess}
        isNormalUser={isNormalUser}
        currentPayment={currentPayment}
        currentBalance={currentBalance}
        countdown={countdown}
        paymentMethod={paymentMethod}
        qrcodePolling={qrcodePolling}
        refreshingQrCode={refreshingQrCode}
        onClose={handlePayModalClose}
        onGoToUser={() => navigate('/user')}
        onReload={() => window.location.reload()}
        onRefreshQrCode={handleRefreshQrCode}
        onOpenPay={handleOpenPay}
        onRefreshStatus={() => handleRefreshStatus()}
        onCancelOrder={handleCancelOrder}
      />
    </div>
  )
}

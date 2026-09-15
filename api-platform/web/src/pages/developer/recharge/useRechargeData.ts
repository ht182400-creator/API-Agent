/**
 * 充值页数据加载（套餐 / 充值配置 / 账户余额）—— P1-4 前端拆分第 2 步
 *
 * 从 Recharge.tsx 抽出。这一层只做"取数据 + 存状态"，不含任何支付流程逻辑，
 * 因此可以独立演进、也可被将来的"套餐选择弹窗"等复用。
 */
import { useState } from 'react'
import { paymentApi, RechargeConfig, RechargePackage } from '../../../api/payment'
import { billingApi } from '../../../api/billing'

/** 与 `useErrorModal().showError` 同签名 */
export type ShowError = (error: any, onRetry?: () => void) => void

export interface RechargeData {
  loading: boolean
  packages: RechargePackage[]
  rechargeConfig: RechargeConfig | null
  currentBalance: number | null
  fetchPackages: () => Promise<void>
  fetchConfig: () => Promise<void>
  fetchBalance: () => Promise<void>
}

/**
 * ⚠️ `showError` 由调用方传入（而不是这里自己 `useErrorModal()`）：
 *    否则 hook 与组件会各持一套 errorModal 状态，**hook 里报的错不会显示在页面的弹窗上**。
 */
export function useRechargeData(showError: ShowError): RechargeData {
  const [loading, setLoading] = useState(false)
  const [packages, setPackages] = useState<RechargePackage[]>([])
  const [rechargeConfig, setRechargeConfig] = useState<RechargeConfig | null>(null)
  const [currentBalance, setCurrentBalance] = useState<number | null>(null)

  const fetchPackages = async () => {
    setLoading(true)
    try {
      const data = await paymentApi.getPackages()
      // ⚠️ 只在售的套餐才渲染（后端的 is_active 约定）
      setPackages(data.filter((pkg) => pkg.is_active))
    } catch (error: any) {
      // 重试即再次调用自身（与拆分前行为一致）
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
      // ⚠️ 与拆分前一致：配置获取失败**只记日志**，不弹错（页面会以默认值兜底提示）
      console.error('获取充值配置失败', error)
    }
  }

  const fetchBalance = async () => {
    try {
      const account = await billingApi.getAccount()
      setCurrentBalance(account.balance)
    } catch (error) {
      // 余额失败同样不打断页面
      console.error('获取账户余额失败', error)
    }
  }

  return {
    loading,
    packages,
    rechargeConfig,
    currentBalance,
    fetchPackages,
    fetchConfig,
    fetchBalance,
  }
}

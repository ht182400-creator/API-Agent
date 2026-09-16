/**
 * 运行环境信息 Hook（L5）
 *
 * ⚠️ 为什么抽成 hook：环境标识此前只在 Layout 顶栏使用（读 /health），
 *    而 Billing 页各自用 `account.mock_mode` 判断 —— **支付模拟模式（mock_mode）
 *    与账单环境（billing_environment）是两个概念**（9-15 已解耦）：
 *    simulation 环境下接真实支付网关沙箱时 mock_mode=false，Billing 却把
 *    它显示成「生产环境 / 真实账户」，与顶栏的「测试环境 · SIMULATION」自相矛盾
 *    （用户实测截图）。统一到 /health 的 is_production/billing_environment 一个来源。
 *
 * 环境信息属非关键路径：获取失败返回 null，调用方隐藏徽标即可，不影响主流程。
 */
import { useEffect, useState } from 'react'

export interface EnvInfo {
  environment: string
  billing_environment: string
  is_production: boolean
}

export function useEnvInfo(): EnvInfo | null {
  const [envInfo, setEnvInfo] = useState<EnvInfo | null>(null)

  useEffect(() => {
    let cancelled = false
    const fetchEnvironment = async () => {
      try {
        const resp = await fetch('/health')
        if (!resp.ok) return
        const data = await resp.json()
        if (!cancelled) {
          setEnvInfo({
            environment: data.environment || 'unknown',
            billing_environment: data.billing_environment || 'unknown',
            is_production: Boolean(data.is_production),
          })
        }
      } catch (error) {
        console.warn('[useEnvInfo] 获取环境信息失败（不影响使用）:', error)
      }
    }
    fetchEnvironment()
    return () => {
      cancelled = true
    }
  }, [])

  return envInfo
}

/**
 * 充值页常量与纯函数（从 Recharge.tsx 抽出，P1-4 拆分第 1 步）
 *
 * 放在 `.tsx` 是因为 PAYMENT_METHODS 内含 JSX 图标。
 */
import type { ReactNode } from 'react'
import { WechatOutlined, AlipayOutlined, CreditCardOutlined } from '@ant-design/icons'
import type { RechargePackage } from '../../../api/payment'

export type PaymentMethodValue = 'wechat' | 'alipay' | 'bankcard'

/**
 * 套餐「实际到账」= 价格 + 固定赠送 + 价格 × 比例赠送%。
 *
 * ⚠️ 该式子原先在**两处**各写一遍（套餐卡片、支付摘要区）——
 *    行内重复最危险之处在于"只改了其中一处"。抽到此处作为**唯一实现**。
 */
export const calcArrivedAmount = (pkg: RechargePackage): string =>
  (
    (pkg.price || 0) +
    (pkg.bonus_amount || 0) +
    (pkg.price || 0) * ((pkg.bonus_ratio || 0) / 100)
  ).toFixed(2)

/**
 * 计算订单剩余有效期（秒）。
 *
 * 后端只把 `expires_in` 算好返回，前端直接用；
 * 缺失时回退 600 秒（10 分钟），负数归零。
 */
export const calculateRemainingSeconds = (expiresIn: number | undefined): number => {
  if (expiresIn === undefined || expiresIn === null) {
    console.warn('[倒计时] expires_in 为空，使用默认值 600')
    return 600
  }

  console.log('[倒计时] expires_in:', expiresIn)
  return Math.max(0, expiresIn)
}

export const PAYMENT_METHODS: {
  value: PaymentMethodValue
  label: string
  icon: ReactNode
  color: string
}[] = [
  { value: 'wechat', label: '微信支付', icon: <WechatOutlined />, color: '#07C160' },
  { value: 'alipay', label: '支付宝', icon: <AlipayOutlined />, color: '#1677FF' },
  { value: 'bankcard', label: '银行卡', icon: <CreditCardOutlined />, color: '#722ED1' },
]

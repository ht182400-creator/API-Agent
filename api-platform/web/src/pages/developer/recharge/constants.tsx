/**
 * 充值页常量与纯函数（从 Recharge.tsx 抽出，P1-4 拆分第 1 步）
 *
 * 放在 `.tsx` 是因为 PAYMENT_METHODS 内含 JSX 图标。
 */
import { WechatOutlined, AlipayOutlined, CreditCardOutlined } from '@ant-design/icons'

export type PaymentMethodValue = 'wechat' | 'alipay' | 'bankcard'

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
  icon: React.ReactNode
  color: string
}[] = [
  { value: 'wechat', label: '微信支付', icon: <WechatOutlined />, color: '#07C160' },
  { value: 'alipay', label: '支付宝', icon: <AlipayOutlined />, color: '#1677FF' },
  { value: 'bankcard', label: '银行卡', icon: <CreditCardOutlined />, color: '#722ED1' },
]

/**
 * 待支付订单的本地暂存（sessionStorage）—— P1-4 前端拆分第 3 步（1/2）
 *
 * 用途：用户在**支付宝页面或新窗口**完成支付后回到本站（或刷新页面）时，
 * 仍能凭暂存的单号向后端确认结果 —— 即"不丢单"。
 *
 * ⚠️ 有效期 30 分钟：超过则视为作废并**顺带清理**，避免回跳到很旧的订单上。
 * ⚠️ 所有操作都不抛错（sessionStorage 在隐私模式/额度满时可能不可用）。
 */

export const PENDING_PAYMENT_KEY = 'pending_payment'

/** 暂存有效期：30 分钟 */
export const PENDING_PAYMENT_TTL_MS = 30 * 60 * 1000

export interface StoredPayment {
  payment_no: string
  amount: number
  order_no: string
  pay_url?: string
  /** 写入时刻（用于过期判断） */
  savedAt: number
}

type SavablePayment = {
  payment_no: string
  amount: number
  order_no: string
  pay_url?: string
}

/** 保存待支付订单（供从支付页返回 / 刷新后恢复） */
export const savePaymentToSession = (payment: SavablePayment): void => {
  try {
    sessionStorage.setItem(
      PENDING_PAYMENT_KEY,
      JSON.stringify({
        payment_no: payment.payment_no,
        amount: payment.amount,
        order_no: payment.order_no,
        pay_url: payment.pay_url,
        savedAt: Date.now(),
      })
    )
  } catch (e) {
    console.error('保存支付信息失败:', e)
  }
}

/** 读取待支付订单；超过 30 分钟视为作废并清理，返回 null */
export const restorePaymentFromSession = (): StoredPayment | null => {
  try {
    const saved = sessionStorage.getItem(PENDING_PAYMENT_KEY)
    if (saved) {
      const data = JSON.parse(saved) as StoredPayment
      // 检查是否过期（30 分钟内）
      if (Date.now() - data.savedAt < PENDING_PAYMENT_TTL_MS) {
        return data
      }
      sessionStorage.removeItem(PENDING_PAYMENT_KEY)
    }
  } catch (e) {
    console.error('恢复支付信息失败:', e)
  }
  return null
}

/** 清除暂存（支付成功 / 主动放弃时调用） */
export const clearPaymentFromSession = (): void => {
  try {
    sessionStorage.removeItem(PENDING_PAYMENT_KEY)
  } catch (e) {
    console.error('清除支付信息失败:', e)
  }
}

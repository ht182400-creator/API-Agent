/**
 * 充值/支付流程日志（从 Recharge.tsx 抽出，P1-4 拆分第 1 步）
 *
 * ⚠️ 本模块在**支付主流程中同步调用**（handleCreateOrder / 各轮询回调），
 *    因此它自身**绝不能抛错**。一旦抛错，异常会被上层的 try/catch 当成"下单失败"吞掉，
 *    用户看到的现象是"点了充值按钮没有任何反应"，且只在 console 留一条 TypeError，极难排查。
 *
 *    （实测踩过：clientLog 返回非 Promise 时抛
 *     `Cannot read properties of undefined (reading 'catch')`，后端请求根本没发出。）
 */
import { paymentApi } from '../../../api/payment'

/**
 * 发送支付流程日志 —— **保证不抛错**。
 *
 * 两道防护：
 *   ① try/catch 包住同步调用（防 clientLog 同步抛错）；
 *   ② Promise.resolve(...).catch(() => {})（防返回非 Promise / Promise 拒绝）。
 */
export const sendPaymentLog = (
  step: string,
  level: 'info' | 'warning' | 'error',
  logData: Record<string, unknown>
): void => {
  try {
    Promise.resolve(paymentApi.clientLog(step, level, logData)).catch(() => {})
  } catch {
    /* 日志上报失败不影响业务 */
  }
}

export const paymentLogger = {
  info: (step: string, data?: Record<string, unknown>) => {
    const logData = { step, timestamp: new Date().toISOString(), ...data }
    console.log(`[PaymentFlow] ${step}`, logData)
    sendPaymentLog(step, 'info', logData)
  },
  error: (step: string, error: unknown) => {
    const logData = { step, timestamp: new Date().toISOString(), error: String(error) }
    console.error(`[PaymentFlow] ERROR - ${step}`, logData)
    sendPaymentLog(step, 'error', logData)
  },
  warn: (step: string, data?: Record<string, unknown>) => {
    const logData = { step, timestamp: new Date().toISOString(), ...data }
    console.warn(`[PaymentFlow] WARN - ${step}`, logData)
    sendPaymentLog(step, 'warning', logData)
  },
}

/**
 * 支付错误处理工具（paymentErrors.tsx）测试
 *
 * 为什么优先测它（P1，且是纯逻辑）：
 *   充值/支付是全站最敏感的资金链路，而这套工具决定**用户看到的错误解释与可行动作**
 *   （能否重试、是否显示订单号、是否引导联系客服）。文案或分类错了，用户会做出错误动作
 *   （例如把"订单已过期"当成"网络问题"反复重试）。
 *   它的 5 个导出函数都是纯逻辑，最适合单测；组件 `PaymentErrorResult` 由页面测试覆盖。
 *
 * 用例编号：TC-FE-PAYERR-001 ~ TC-FE-PAYERR-015
 */
import { describe, it, expect } from 'vitest'
import {
  PaymentErrorType,
  extractPaymentErrorDetails,
  getPaymentErrorConfig,
  getPaymentErrorMessage,
  isPaymentError,
  parsePaymentErrorType,
} from './paymentErrors'
import paymentErrorsDefault from './paymentErrors'

describe('parsePaymentErrorType（错误 → 支付错误类型）', () => {
  it('TC-FE-PAYERR-001: 支付宝/网关错误码映射', () => {
    const cases: Array<[string, PaymentErrorType]> = [
      ['AE0310600325', PaymentErrorType.PAYMENT_GATEWAY_ERROR],
      ['AE0310600311', PaymentErrorType.PAYMENT_GATEWAY_ERROR],
      ['ACQ.TRADE_NOT_EXIST', PaymentErrorType.ORDER_NOT_FOUND],
      ['ACQ.TRADE_STATUS_ERROR', PaymentErrorType.ORDER_ALREADY_PAID],
      ['ACQ.AccessDenied', PaymentErrorType.PAYMENT_METHOD_UNAVAILABLE],
      ['ORDER_EXPIRED', PaymentErrorType.ORDER_EXPIRED],
      ['ORDER_CANCELLED', PaymentErrorType.ORDER_CANCELLED],
      ['ORDER_PAID', PaymentErrorType.ORDER_ALREADY_PAID],
      ['SANDBOX', PaymentErrorType.SANDBOX_ERROR],
      ['ERR_NETWORK', PaymentErrorType.PAYMENT_NETWORK_ERROR],
    ]

    cases.forEach(([code, expected]) => {
      expect(parsePaymentErrorType({ code }), `code=${code}`).toBe(expected)
    })
  })

  it('TC-FE-PAYERR-002: 兼容 error_code / errorCode 字段别名', () => {
    expect(parsePaymentErrorType({ error_code: 'ORDER_PAID' })).toBe(PaymentErrorType.ORDER_ALREADY_PAID)
    expect(parsePaymentErrorType({ errorCode: 'ORDER_PAID' })).toBe(PaymentErrorType.ORDER_ALREADY_PAID)
  })

  it('TC-FE-PAYERR-003: 无错误码时按消息关键词分类（中英混合）', () => {
    const cases: Array<[string, PaymentErrorType]> = [
      ['系统有点儿忙，请稍后再试', PaymentErrorType.PAYMENT_GATEWAY_ERROR],
      ['ae0310600325 gateway error', PaymentErrorType.PAYMENT_GATEWAY_ERROR],
      ['request timeout', PaymentErrorType.PAYMENT_TIMEOUT],
      ['网络连接失败', PaymentErrorType.PAYMENT_NETWORK_ERROR],
      ['订单不存在', PaymentErrorType.ORDER_NOT_FOUND],
      ['订单已过期', PaymentErrorType.ORDER_EXPIRED],
      ['用户已取消', PaymentErrorType.PAYMENT_CANCELLED],
      ['订单已支付', PaymentErrorType.ORDER_ALREADY_PAID],
      ['沙箱环境不可用', PaymentErrorType.SANDBOX_ERROR],
    ]

    cases.forEach(([message, expected]) => {
      expect(parsePaymentErrorType({ message }), `message=${message}`).toBe(expected)
    })
  })

  it('TC-FE-PAYERR-004: ⚠️ 消息含「超时」时优先判为支付超时（而非订单过期）', () => {
    // 说明：实现里 `timeout|超时` 的判断排在 `expired|已过期` 之前，因此
    //      "订单已超时" 会被归为 PAYMENT_TIMEOUT。此处**如实记录**该优先级（既有行为），
    //      避免后续误改；若产品语义希望区分，需先调整判断顺序。
    expect(parsePaymentErrorType({ message: '订单已超时' })).toBe(PaymentErrorType.PAYMENT_TIMEOUT)
    expect(parsePaymentErrorType({ message: 'timeout' })).toBe(PaymentErrorType.PAYMENT_TIMEOUT)
  })

  it('TC-FE-PAYERR-005: 兜底走 HTTP 状态码（404 → 订单不存在）', () => {
    expect(parsePaymentErrorType({ response: { status: 404 } })).toBe(PaymentErrorType.ORDER_NOT_FOUND)
    expect(parsePaymentErrorType({ status: 0 })).toBe(PaymentErrorType.PAYMENT_NETWORK_ERROR)
  })

  it('TC-FE-PAYERR-006: 空输入 / 无法识别 → UNKNOWN（不抛错）', () => {
    expect(parsePaymentErrorType(null)).toBe(PaymentErrorType.UNKNOWN)
    expect(parsePaymentErrorType(undefined)).toBe(PaymentErrorType.UNKNOWN)
    expect(parsePaymentErrorType({})).toBe(PaymentErrorType.UNKNOWN)
    expect(parsePaymentErrorType({ message: '莫名其妙' })).toBe(PaymentErrorType.UNKNOWN)
    // ✅ 已修（knownIssues：FE-BUG-PAYERR-ECONNABORTED）：axios 把超时/网络类错误码放在
    //    `error.code` 上，现在会显式识别 —— 下面几条即该修复的回归防线。
    expect(parsePaymentErrorType({ code: 'ECONNABORTED' })).toBe(PaymentErrorType.PAYMENT_TIMEOUT)
    expect(parsePaymentErrorType({ code: 'ETIMEDOUT' })).toBe(PaymentErrorType.PAYMENT_TIMEOUT)
    expect(parsePaymentErrorType({ code: 'ERR_CONNECTION_REFUSED' })).toBe(
      PaymentErrorType.PAYMENT_NETWORK_ERROR
    )
    // 非网络/超时类错误码不受影响
    expect(parsePaymentErrorType({ code: 'ERR_BAD_REQUEST' })).toBe(PaymentErrorType.UNKNOWN)
  })

  it('TC-FE-PAYERR-007: 优先级 —— 错误码 > 消息 > 状态码', () => {
    // 错误码可直接命中时不看消息
    expect(parsePaymentErrorType({ code: 'ORDER_PAID', message: '网络异常' })).toBe(
      PaymentErrorType.ORDER_ALREADY_PAID
    )
    // 消息可命中时不看状态码
    expect(parsePaymentErrorType({ message: '订单已过期', status: 404 })).toBe(
      PaymentErrorType.ORDER_EXPIRED
    )
  })
})

describe('extractPaymentErrorDetails（提取可展示详情）', () => {
  it('TC-FE-PAYERR-008: 从多来源提取 错误码 / 消息 / 订单号', () => {
    const details = extractPaymentErrorDetails({
      code: 'AE0310600325',
      userMessage: '支付失败，请重试',
      order_no: 'ORD-1',
    })
    expect(details).toEqual({ code: 'AE0310600325', message: '支付失败，请重试', orderNo: 'ORD-1' })
  })

  it('TC-FE-PAYERR-009: 回落到 response.data 的字段（message / order_no / payment_no）', () => {
    const fromData = extractPaymentErrorDetails({
      response: { data: { message: '通道异常', order_no: 'ORD-2' } },
    })
    expect(fromData.message).toBe('通道异常')
    expect(fromData.orderNo).toBe('ORD-2')

    const fromPaymentNo = extractPaymentErrorDetails({
      response: { data: { payment_no: 'PAY-9' } },
    })
    expect(fromPaymentNo.orderNo).toBe('PAY-9')
  })

  it('TC-FE-PAYERR-010: 清理堆栈且超长截断为 200 字符', () => {
    const withStack = extractPaymentErrorDetails({ message: 'Error: 失败\nTraceback: xyz' })
    expect(withStack.message).toBe('Error: 失败')

    const long = extractPaymentErrorDetails({ message: 'x'.repeat(500) })
    expect(long.message).toHaveLength(203)
    expect(long.message.endsWith('...')).toBe(true)
  })

  it('TC-FE-PAYERR-011: 无可用信息时给出「未知错误」', () => {
    expect(extractPaymentErrorDetails(null)).toEqual({ message: '未知错误' })
    expect(extractPaymentErrorDetails({})).toEqual({
      code: undefined,
      message: '未知错误',
      orderNo: undefined,
    })
  })
})

describe('getPaymentErrorConfig / getPaymentErrorMessage', () => {
  it('TC-FE-PAYERR-012: 按错误映射到预设配置（含 retryable 与引导项）', () => {
    const gateway = getPaymentErrorConfig({ code: 'AE0310600325' })
    expect(gateway.title).toBe('支付通道繁忙')
    expect(gateway.retryable).toBe(true)
    expect(gateway.showContactSupport).toBe(true)
    expect(gateway.icon).toBeTruthy()

    const notFound = getPaymentErrorConfig({ code: 'ACQ.TRADE_NOT_EXIST' })
    expect(notFound.title).toBe('订单不存在')
    expect(notFound.showOrderDetails).toBe(true)
  })

  it('TC-FE-PAYERR-013: 未知错误回落 UNKNOWN 配置（不返回 undefined）', () => {
    const config = getPaymentErrorConfig({ message: '莫名其妙' })
    expect(config.type).toBe(PaymentErrorType.UNKNOWN)
    expect(config.title).toBeTruthy()
    expect(config.subTitle).toBeTruthy()
    // 连 null 也不能炸
    expect(getPaymentErrorConfig(null).type).toBe(PaymentErrorType.UNKNOWN)
  })

  it('TC-FE-PAYERR-014: 消息级别由配置的 retryable 决定（warning / error）', () => {
    // 映射关系断言（用配置驱动，避免把各类型的 retryable 取值写死在测试里）
    const codes = ['AE0310600325', 'ACQ.TRADE_NOT_EXIST', 'ORDER_EXPIRED', 'SANDBOX', 'ORDER_CANCELLED']

    codes.forEach((code) => {
      const config = getPaymentErrorConfig({ code })
      const msg = getPaymentErrorMessage({ code })
      expect(msg.type, `code=${code} retryable=${config.retryable}`).toBe(
        config.retryable ? 'warning' : 'error'
      )
      expect(msg.content).toBe(`${config.title}：${config.subTitle}`)
    })

    // 明确钉住一条已知可重试的（通道繁忙 → 提示用户可重试）
    const gatewayMsg = getPaymentErrorMessage({ code: 'AE0310600325' })
    expect(gatewayMsg.type).toBe('warning')
    expect(gatewayMsg.content).toBe('支付通道繁忙：支付通道暂时繁忙，请稍后重试')
  })
})

describe('isPaymentError 与默认导出', () => {
  it('TC-FE-PAYERR-015: 识别支付错误（含仅靠 message 含 pay/payment/支付 的情况）', () => {
    expect(isPaymentError(null)).toBe(false)
    expect(isPaymentError({ code: 'AE0310600325' })).toBe(true)
    expect(isPaymentError({ message: 'payment failed' })).toBe(true)
    expect(isPaymentError({ message: '支付失败' })).toBe(true)
    // ✅ 已修（knownIssues：FE-BUG-PAYERR-ISPAYMENT-TYPE）：原先空 message 时整条链短路
    //    返回 undefined（函数声明为 boolean），现统一转字符串判断 → **严格返回 false**。
    expect(isPaymentError({ message: '莫名其妙' })).toBe(false)
    expect(isPaymentError({})).toBe(false)
    // `msg` 字段别名同样生效
    expect(isPaymentError({ msg: 'payment timeout' })).toBe(true)
  })

  it('TC-FE-PAYERR-016: 默认导出包含全部公开 API（供 default import 使用）', () => {
    expect(Object.keys(paymentErrorsDefault).sort()).toEqual(
      [
        'PaymentErrorResult',
        'PaymentErrorType',
        'extractPaymentErrorDetails',
        'getPaymentErrorConfig',
        'getPaymentErrorMessage',
        'isPaymentError',
        'parsePaymentErrorType',
      ].sort()
    )
  })
})

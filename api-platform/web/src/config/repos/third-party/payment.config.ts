/**
 * Payment API 仓库配置
 * @description 第三方仓库 - 支付服务
 */

import { Repository } from '../../../types/api-tester';

export const paymentRepository: Repository = {
  id: 'payment-api',
  slug: 'payment',
  name: '支付服务API',
  description: '提供微信支付、支付宝、银联等多种支付方式（第三方集成）',
  icon: 'credit-card',
  category: 'third_party',
  baseUrl: '/api/v1/payment',
  authType: 'api_key',
  authHeader: 'X-Access-Key',
  enabled: true,
  version: '2.0.0',
  contact: {
    name: 'Payment Provider',
    url: 'https://paymentprovider.com'
  },
  endpoints: [
    {
      id: 'create_order',
      name: '创建支付订单',
      description: '创建支付订单并返回支付二维码或链接',
      path: '/create',
      method: 'POST',
      params: [],
      requestBody: [
        {
          name: 'order_id',
          type: 'string',
          required: true,
          description: '商户订单号',
          placeholder: '商户自定义订单号',
          in: 'body'
        },
        {
          name: 'amount',
          type: 'number',
          required: true,
          description: '订单金额(分)',
          placeholder: '金额，单位：分',
          in: 'body',
          validation: {
            min: 1
          }
        },
        {
          name: 'currency',
          type: 'select',
          required: false,
          description: '货币类型',
          defaultValue: 'CNY',
          options: [
            { label: '人民币', value: 'CNY' },
            { label: '美元', value: 'USD' },
            { label: '港币', value: 'HKD' }
          ],
          in: 'body'
        },
        {
          name: 'channel',
          type: 'select',
          required: true,
          description: '支付渠道',
          options: [
            { label: '微信支付', value: 'wechat' },
            { label: '支付宝', value: 'alipay' },
            { label: '银联', value: 'unionpay' }
          ],
          in: 'body'
        },
        {
          name: 'subject',
          type: 'string',
          required: true,
          description: '订单标题',
          placeholder: '商品描述',
          in: 'body'
        },
        {
          name: 'notify_url',
          type: 'string',
          required: false,
          description: '异步通知地址',
          placeholder: '支付结果回调URL',
          in: 'body'
        }
      ],
      responseExample: {
        code: 0,
        message: 'success',
        data: {
          order_id: 'ORDER_20260422001',
          payment_id: 'PAY_20260422001',
          qr_code: 'weixin://wxpay/bizpayurl?pr=xxx',
          expire_time: '2026-04-22 10:30:00'
        }
      },
      tags: ['支付', '订单']
    },
    {
      id: 'query_order',
      name: '查询订单状态',
      description: '查询支付订单的支付状态',
      path: '/query',
      method: 'GET',
      params: [
        {
          name: 'order_id',
          type: 'string',
          required: true,
          description: '商户订单号',
          placeholder: '商户自定义订单号',
          in: 'query'
        }
      ],
      responseExample: {
        code: 0,
        message: 'success',
        data: {
          order_id: 'ORDER_20260422001',
          status: 'paid',
          paid_time: '2026-04-22 10:15:30',
          amount: 100
        }
      },
      tags: ['支付', '查询']
    },
    {
      id: 'refund',
      name: '申请退款',
      description: '对已支付的订单申请退款',
      path: '/refund',
      method: 'POST',
      params: [],
      requestBody: [
        {
          name: 'order_id',
          type: 'string',
          required: true,
          description: '商户订单号',
          in: 'body'
        },
        {
          name: 'refund_amount',
          type: 'number',
          required: true,
          description: '退款金额(分)',
          in: 'body',
          validation: {
            min: 1
          }
        },
        {
          name: 'reason',
          type: 'string',
          required: false,
          description: '退款原因',
          placeholder: '请输入退款原因',
          in: 'body'
        }
      ],
      responseExample: {
        code: 0,
        message: 'success',
        data: {
          refund_id: 'REFUND_20260422001',
          order_id: 'ORDER_20260422001',
          refund_amount: 100,
          status: 'processing'
        }
      },
      tags: ['支付', '退款']
    }
  ]
};

/**
 * SMS API 仓库配置
 * @description 第三方仓库 - 短信服务
 */

import { Repository } from '../../../types/api-tester';

export const smsRepository: Repository = {
  id: 'sms-api',
  slug: 'sms',
  name: '短信服务API',
  description: '提供短信发送、验证码、通知推送等短信服务（第三方集成）',
  icon: 'message',
  category: 'third_party',
  baseUrl: '/api/v1/sms',
  authType: 'api_key',
  authHeader: 'X-Access-Key',
  enabled: true,
  version: '1.0.0',
  contact: {
    name: 'SMS Provider',
    email: 'support@smsprovider.com',
    url: 'https://smsprovider.com'
  },
  endpoints: [
    {
      id: 'send',
      name: '发送短信',
      description: '向指定手机号发送短信',
      path: '/send',
      method: 'POST',
      params: [],
      requestBody: [
        {
          name: 'phone',
          type: 'string',
          required: true,
          description: '手机号码',
          placeholder: '请输入手机号',
          in: 'body',
          validation: {
            pattern: '^1[3-9]\\d{9}$'
          }
        },
        {
          name: 'template_id',
          type: 'string',
          required: true,
          description: '模板ID',
          placeholder: '如：SMS_123456789',
          in: 'body'
        },
        {
          name: 'params',
          type: 'string',
          required: false,
          description: '模板参数(JSON格式)',
          placeholder: '{"code":"123456"}',
          in: 'body'
        }
      ],
      responseExample: {
        code: 0,
        message: 'success',
        data: {
          message_id: 'MSG_202604220001',
          phone: '138****8888',
          status: 'sent',
          send_time: '2026-04-22 10:00:00'
        }
      },
      tags: ['短信']
    },
    {
      id: 'verify',
      name: '验证码校验',
      description: '校验用户输入的短信验证码',
      path: '/verify',
      method: 'POST',
      params: [],
      requestBody: [
        {
          name: 'phone',
          type: 'string',
          required: true,
          description: '手机号码',
          in: 'body'
        },
        {
          name: 'code',
          type: 'string',
          required: true,
          description: '验证码',
          placeholder: '请输入验证码',
          in: 'body'
        },
        {
          name: 'template_id',
          type: 'string',
          required: true,
          description: '模板ID',
          in: 'body'
        }
      ],
      responseExample: {
        code: 0,
        message: 'success',
        data: {
          valid: true,
          expires_in: 300
        }
      },
      tags: ['短信', '验证']
    },
    {
      id: 'batch_send',
      name: '批量发送',
      description: '向多个手机号发送相同内容的短信',
      path: '/batch-send',
      method: 'POST',
      params: [],
      requestBody: [
        {
          name: 'phones',
          type: 'string',
          required: true,
          description: '手机号列表(JSON数组)',
          placeholder: '["13800001111","13800002222"]',
          in: 'body'
        },
        {
          name: 'content',
          type: 'string',
          required: true,
          description: '短信内容',
          placeholder: '请输入短信内容',
          in: 'body'
        }
      ],
      responseExample: {
        code: 0,
        message: 'success',
        data: {
          total: 2,
          success: 2,
          failed: 0,
          results: [
            { phone: '138****1111', status: 'sent' },
            { phone: '138****2222', status: 'sent' }
          ]
        }
      },
      tags: ['短信', '批量']
    }
  ]
};

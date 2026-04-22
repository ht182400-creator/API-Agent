/**
 * Logistics API 仓库配置
 * @description 自研仓库 - 物流追踪服务
 */

import { Repository } from '../../../types/api-tester';

export const logisticsRepository: Repository = {
  id: 'logistics-api',
  slug: 'logistics',
  name: '物流追踪API',
  description: '提供快递查询、物流追踪、运费计算等物流相关服务',
  icon: 'car',
  category: 'self',
  baseUrl: '/api/v1/logistics',
  authType: 'api_key',
  authHeader: 'X-Access-Key',
  enabled: true,
  version: '1.0.0',
  endpoints: [
    {
      id: 'track',
      name: '物流追踪',
      description: '根据快递单号查询物流状态和轨迹',
      path: '/track',
      method: 'GET',
      params: [
        {
          name: 'tracking_no',
          type: 'string',
          required: true,
          description: '快递单号',
          placeholder: '请输入快递单号',
          in: 'query'
        },
        {
          name: 'carrier',
          type: 'select',
          required: false,
          description: '快递公司',
          options: [
            { label: '自动识别', value: 'auto' },
            { label: '顺丰速运', value: 'sf' },
            { label: '圆通速递', value: 'yt' },
            { label: '中通快递', value: 'zt' },
            { label: '韵达快递', value: 'yd' }
          ],
          defaultValue: 'auto',
          in: 'query'
        }
      ],
      responseExample: {
        code: 0,
        message: 'success',
        data: {
          tracking_no: 'SF1234567890',
          carrier: '顺丰速运',
          status: '运输中',
          current_location: '上海市浦东新区',
          traces: [
            { time: '2026-04-22 08:00', location: '上海市浦东新区', status: '派送中' },
            { time: '2026-04-21 18:00', location: '上海市分拨中心', status: '到达目的城市' }
          ]
        }
      },
      tags: ['物流']
    },
    {
      id: 'freight',
      name: '运费计算',
      description: '计算快递运费',
      path: '/freight',
      method: 'POST',
      params: [],
      requestBody: [
        {
          name: 'from_city',
          type: 'string',
          required: true,
          description: '发货城市',
          placeholder: '如：上海',
          in: 'body'
        },
        {
          name: 'to_city',
          type: 'string',
          required: true,
          description: '收货城市',
          placeholder: '如：北京',
          in: 'body'
        },
        {
          name: 'weight',
          type: 'number',
          required: true,
          description: '重量(kg)',
          placeholder: '请输入重量',
          in: 'body',
          validation: {
            min: 0.1,
            max: 50
          }
        },
        {
          name: 'carrier',
          type: 'select',
          required: false,
          description: '快递公司',
          options: [
            { label: '顺丰速运', value: 'sf' },
            { label: '圆通速递', value: 'yt' },
            { label: '中通快递', value: 'zt' }
          ],
          in: 'body'
        }
      ],
      responseExample: {
        code: 0,
        message: 'success',
        data: {
          from_city: '上海',
          to_city: '北京',
          weight: 1.5,
          carriers: [
            { name: '顺丰速运', freight: 23, estimated_days: 2 },
            { name: '圆通速递', freight: 12, estimated_days: 3 }
          ]
        }
      },
      tags: ['物流', '计算']
    }
  ]
};

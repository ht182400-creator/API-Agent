/**
 * Weather API 仓库配置
 * @description 自研仓库 - 天气API服务
 * @basedOn CallWeatherTest Tool 源码实现
 * @see Developer/CallWeatherTest Tool/
 */

import { Repository } from '../../../types/api-tester';

export const weatherRepository: Repository = {
  id: 'weather-api',
  slug: 'weather-api',
  name: '天气API',
  description: '提供实时天气、天气预报、空气质量、天气预警等全方位天气数据服务',
  icon: 'cloud',
  category: 'self',
  /** API Platform 后端 proxy 接口路径 */
  baseUrl: '/api/v1/repositories/weather-api',
  apiUrl: 'http://localhost:8000',
  authType: 'api_key',
  authHeader: 'X-Access-Key',
  enabled: true,
  version: '1.0.0',
  contact: {
    name: 'Weather Team',
    email: 'weather@example.com'
  },
  endpoints: [
    {
      id: 'current',
      name: '实时天气',
      description: '获取指定城市的实时天气信息，包括温度、湿度、风速、体感温度、能见度、气压等',
      path: '/current',
      method: 'GET',
      params: [
        {
          name: 'city',
          type: 'string',
          required: true,
          description: '城市名称（支持中文或拼音）',
          placeholder: '如：北京、上海、London',
          in: 'query'
        },
        {
          name: 'language',
          type: 'select',
          required: false,
          description: '返回语言',
          defaultValue: 'zh-CN',
          options: [
            { label: '中文', value: 'zh-CN' },
            { label: 'English', value: 'en' }
          ],
          in: 'query'
        },
        {
          name: 'unit',
          type: 'select',
          required: false,
          description: '温度单位',
          defaultValue: 'c',
          options: [
            { label: '摄氏度 (°C)', value: 'c' },
            { label: '华氏度 (°F)', value: 'f' }
          ],
          in: 'query'
        }
      ],
      responseExample: {
        code: 200,
        message: 'success',
        data: {
          city: '北京',
          city_code: '101010100',
          country: '中国',
          weather: '晴',
          weather_code: '0',
          temperature: 25.5,
          temperature_f: 77.9,
          feels_like: 27.0,
          humidity: 60,
          humidity_percent: 60,
          wind_speed: 12.5,
          wind_speed_unit: 'km/h',
          wind_direction: '东南风',
          wind_direction_degree: 135,
          pressure: 1010,
          visibility: 15.0,
          uv_index: 5,
          aqi: 85,
          aqi_level: '良',
          update_time: '2026-04-22 10:00:00',
          sunrise: '05:32',
          sunset: '18:58'
        },
        request_id: 'req_20260422100000',
        timestamp: 1745287200
      },
      tags: ['天气']
    },
    {
      id: 'forecast',
      name: '天气预报',
      description: '获取指定城市未来1-7天的天气预报，包含每日最高/最低温度、天气状况、风力风向等',
      path: '/forecast',
      method: 'GET',
      params: [
        {
          name: 'city',
          type: 'string',
          required: true,
          description: '城市名称（支持中文或拼音）',
          placeholder: '如：北京、上海',
          in: 'query'
        },
        {
          name: 'days',
          type: 'select',
          required: false,
          description: '预报天数（1-7天）',
          defaultValue: 3,
          options: [
            { label: '1天', value: 1 },
            { label: '3天', value: 3 },
            { label: '5天', value: 5 },
            { label: '7天', value: 7 }
          ],
          in: 'query'
        },
        {
          name: 'unit',
          type: 'select',
          required: false,
          description: '温度单位',
          defaultValue: 'c',
          options: [
            { label: '摄氏度 (°C)', value: 'c' },
            { label: '华氏度 (°F)', value: 'f' }
          ],
          in: 'query'
        }
      ],
      responseExample: {
        code: 200,
        message: 'success',
        data: {
          city: '北京',
          city_code: '101010100',
          forecast_days: 3,
          forecasts: [
            {
              date: '2026-04-22',
              weekday: '星期三',
              weather: '多云',
              weather_code: '1',
              weather_icon: 'cloudy',
              temp_high: 28,
              temp_low: 15,
              temp_high_f: 82,
              temp_low_f: 59,
              humidity: 55,
              wind: '东南风 3-4级',
              wind_speed: 15.5,
              uv_index: 5,
              air_quality: { aqi: 85, level: '良' }
            },
            {
              date: '2026-04-23',
              weekday: '星期四',
              weather: '晴',
              weather_code: '0',
              weather_icon: 'sunny',
              temp_high: 30,
              temp_low: 17,
              temp_high_f: 86,
              temp_low_f: 63,
              humidity: 45,
              wind: '南风 2-3级',
              wind_speed: 10.0,
              uv_index: 7,
              air_quality: { aqi: 72, level: '良' }
            }
          ],
          update_time: '2026-04-22 10:00:00'
        },
        request_id: 'req_20260422100001',
        timestamp: 1745287201
      },
      tags: ['天气']
    },
    {
      id: 'aqi',
      name: '空气质量',
      description: '获取指定城市的空气质量指数(AQI)和 PM2.5、PM10、O3、SO2、NO2 等污染物浓度',
      path: '/aqi',
      method: 'GET',
      params: [
        {
          name: 'city',
          type: 'string',
          required: true,
          description: '城市名称（支持中文或拼音）',
          placeholder: '如：北京、上海',
          in: 'query'
        }
      ],
      responseExample: {
        code: 200,
        message: 'success',
        data: {
          city: '北京',
          city_code: '101010100',
          aqi: 85,
          level: '良',
          level_color: '#ffff00',
          primary_pollutant: 'PM2.5',
          health_advice: '空气质量良好，可以正常外出活动',
          pollutants: {
            pm25: { value: 58.0, level: '良', level_color: '#ffff00', unit: 'μg/m³' },
            pm10: { value: 102.0, level: '轻度污染', level_color: '#ff7e00', unit: 'μg/m³' },
            so2: { value: 15.0, level: '优', level_color: '#00e400', unit: 'μg/m³' },
            no2: { value: 45.0, level: '良', level_color: '#ffff00', unit: 'μg/m³' },
            co: { value: 0.8, level: '良', level_color: '#ffff00', unit: 'mg/m³' },
            o3: { value: 120.0, level: '良', level_color: '#ffff00', unit: 'μg/m³' }
          },
          update_time: '2026-04-22 10:00:00'
        },
        request_id: 'req_20260422100002',
        timestamp: 1745287202
      },
      tags: ['环境']
    },
    {
      id: 'alerts',
      name: '天气预警',
      description: '获取指定城市的天气预警信息，包括预警类型、级别、详细描述和防御指南',
      path: '/alerts',
      method: 'GET',
      params: [
        {
          name: 'city',
          type: 'string',
          required: true,
          description: '城市名称（支持中文或拼音）',
          placeholder: '如：北京、上海',
          in: 'query'
        }
      ],
      responseExample: {
        code: 200,
        message: 'success',
        data: {
          city: '北京',
          has_alerts: true,
          alerts_count: 2,
          alerts: [
            {
              id: 'alert_2026042201',
              type: '暴雨',
              type_code: '03',
              level: '黄色',
              level_code: '03',
              title: '暴雨黄色预警',
              description: '预计未来6小时内，全市大部分地区将出现50毫米以上的暴雨天气...',
              possible_effect: '可能出现城市内涝、山洪等次生灾害',
              suggestions: [
                '政府及相关部门按照职责做好防暴雨工作',
                '交通管理部门根据路况在强降雨路段采取交通管制措施',
                '切断低洼地带有危险的室外电源，暂停在空旷地方的户外作业'
              ],
              publish_time: '2026-04-22 08:00:00',
              start_time: '2026-04-22 08:00:00',
              end_time: '2026-04-22 20:00:00',
              source: '北京市气象局'
            }
          ],
          update_time: '2026-04-22 10:00:00'
        },
        request_id: 'req_20260422100003',
        timestamp: 1745287203
      },
      tags: ['预警']
    }
  ]
};

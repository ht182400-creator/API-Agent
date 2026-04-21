# 天气 API 产品 - API 设计文档

## 文档控制

| 项目 | 内容 |
|------|------|
| 文档编号 | API-WEATHER-001 |
| 版本号 | V1.0.0 |
| 创建日期 | 2026-04-21 |

---

## 1. API 概览

### 1.1 基本信息

| 项目 | 内容 |
|------|------|
| API 名称 | Weather API |
| 版本 | v1 |
| Base URL | `/api/v1/weather` |
| 协议 | HTTPS |
| 数据格式 | JSON |
| 编码 | UTF-8 |

### 1.2 认证方式

所有接口需要通过 API Key 进行认证：

```
Authorization: Bearer {API_KEY}
```

或在请求头中包含：

```
X-API-Key: {API_KEY}
```

---

## 2. 接口详情

### 2.1 实时天气查询

**接口地址**: `GET /api/v1/weather/current`

**请求示例**:

```bash
curl -X GET "https://api.platform.com/api/v1/weather/current?city=北京" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**请求参数**:

| 参数名 | 位置 | 类型 | 必填 | 说明 | 默认值 |
|--------|------|------|------|------|--------|
| city | query | string | 是 | 城市名称（支持中文/拼音） | - |
| language | query | string | 否 | 返回语言 | zh-CN |
| unit | query | string | 否 | 温度单位: c=摄氏度, f=华氏度 | c |

**成功响应 (200)**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "city": "北京",
    "city_code": "101010100",
    "country": "中国",
    "weather": "晴",
    "weather_code": "00",
    "temperature": 25,
    "temperature_f": 77,
    "feels_like": 27,
    "humidity": 45,
    "humidity_percent": 45,
    "wind_speed": 12,
    "wind_speed_unit": "km/h",
    "wind_direction": "南风",
    "wind_direction_degree": 180,
    "pressure": 1013,
    "visibility": 10,
    "uv_index": 6,
    "aqi": 58,
    "aqi_level": "良",
    "update_time": "2026-04-21 13:00:00",
    "sunrise": "05:42",
    "sunset": "18:56"
  },
  "request_id": "req_abc123def456",
  "timestamp": 1745210400
}
```

**错误响应**:

```json
{
  "code": 404,
  "message": "城市未找到",
  "error": {
    "code": "CITY_NOT_FOUND",
    "details": "请检查城市名称是否正确"
  },
  "request_id": "req_abc123def456"
}
```

### 2.2 天气预报查询

**接口地址**: `GET /api/v1/weather/forecast`

**请求示例**:

```bash
curl -X GET "https://api.platform.com/api/v1/weather/forecast?city=北京&days=3" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**请求参数**:

| 参数名 | 位置 | 类型 | 必填 | 说明 | 默认值 |
|--------|------|------|------|------|--------|
| city | query | string | 是 | 城市名称 | - |
| days | query | int | 否 | 预报天数(1-7) | 3 |
| unit | query | string | 否 | 温度单位 | c |

**成功响应 (200)**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "city": "北京",
    "city_code": "101010100",
    "forecast_days": 3,
    "forecasts": [
      {
        "date": "2026-04-21",
        "weekday": "星期二",
        "weather": "晴",
        "weather_code": "00",
        "weather_icon": "☀️",
        "temp_high": 28,
        "temp_low": 16,
        "temp_high_f": 82,
        "temp_low_f": 61,
        "humidity": 45,
        "wind": "南风3-4级",
        "wind_speed": 12,
        "uv_index": 6,
        "air_quality": {
          "aqi": 58,
          "level": "良"
        }
      },
      {
        "date": "2026-04-22",
        "weekday": "星期三",
        "weather": "多云",
        "weather_code": "01",
        "weather_icon": "⛅",
        "temp_high": 26,
        "temp_low": 15,
        "humidity": 50,
        "wind": "东南风2-3级",
        "wind_speed": 8,
        "uv_index": 4,
        "air_quality": {
          "aqi": 65,
          "level": "良"
        }
      }
    ],
    "update_time": "2026-04-21 13:00:00"
  },
  "request_id": "req_abc123def456",
  "timestamp": 1745210400
}
```

### 2.3 空气质量查询

**接口地址**: `GET /api/v1/weather/aqi`

**请求示例**:

```bash
curl -X GET "https://api.platform.com/api/v1/weather/aqi?city=北京" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**请求参数**:

| 参数名 | 位置 | 类型 | 必填 | 说明 | 默认值 |
|--------|------|------|------|------|--------|
| city | query | string | 是 | 城市名称 | - |

**成功响应 (200)**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "city": "北京",
    "city_code": "101010100",
    "aqi": 58,
    "level": "良",
    "level_color": "#90EE90",
    "primary_pollutant": "PM2.5",
    "health_advice": "空气质量良好，可以正常进行户外活动",
    "pollutants": {
      "pm25": {
        "value": 35,
        "level": "良",
        "level_color": "#90EE90"
      },
      "pm10": {
        "value": 68,
        "level": "良",
        "level_color": "#90EE90"
      },
      "so2": {
        "value": 10,
        "level": "优",
        "level_color": "#00FF00"
      },
      "no2": {
        "value": 45,
        "level": "良",
        "level_color": "#90EE90"
      },
      "co": {
        "value": 0.8,
        "unit": "mg/m³"
      },
      "o3": {
        "value": 120,
        "unit": "μg/m³"
      }
    },
    "update_time": "2026-04-21 13:00:00"
  },
  "request_id": "req_abc123def456",
  "timestamp": 1745210400
}
```

### 2.4 天气预警查询

**接口地址**: `GET /api/v1/weather/alerts`

**请求示例**:

```bash
curl -X GET "https://api.platform.com/api/v1/weather/alerts?city=北京" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**成功响应 (200)**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "city": "北京",
    "has_alerts": true,
    "alerts_count": 1,
    "alerts": [
      {
        "id": "alert_001",
        "type": "台风",
        "type_code": "TY",
        "level": "橙色",
        "level_code": "ORANGE",
        "title": "台风橙色预警",
        "description": "今年第3号台风正向北偏西方向移动...",
        "possible_effect": "请注意防范大风和强降雨天气",
        "suggestions": [
          "停止室内外大型集会和高空等户外危险作业",
          "加固或者拆除易被风吹动的搭建物",
          "相关地区应当注意防范强降水可能引发的山洪"
        ],
        "publish_time": "2026-04-21 10:00:00",
        "start_time": "2026-04-21 10:00:00",
        "end_time": "2026-04-22 10:00:00",
        "source": "中央气象台"
      }
    ],
    "update_time": "2026-04-21 13:00:00"
  },
  "request_id": "req_abc123def456",
  "timestamp": 1745210400
}
```

---

## 3. 错误码定义

### 3.1 业务错误码

| 错误码 | HTTP状态码 | 错误信息 | 说明 |
|--------|------------|----------|------|
| 200 | 200 | success | 请求成功 |
| 400 | 400 | INVALID_PARAMETER | 参数错误 |
| 401 | 401 | UNAUTHORIZED | 未授权 |
| 403 | 403 | FORBIDDEN | 权限不足 |
| 404 | 404 | CITY_NOT_FOUND | 城市未找到 |
| 429 | 429 | RATE_LIMIT_EXCEEDED | 请求过于频繁 |
| 500 | 500 | INTERNAL_ERROR | 服务器内部错误 |
| 503 | 503 | SERVICE_UNAVAILABLE | 服务不可用 |

### 3.2 AQI 等级说明

| AQI 范围 | 等级 | 颜色 | 健康建议 |
|----------|------|------|----------|
| 0-50 | 优 | #00FF00 | 空气质量令人满意，基本无空气污染 |
| 51-100 | 良 | #90EE90 | 空气质量可接受，某些污染物对极少数人有轻微影响 |
| 101-150 | 轻度污染 | #FFFF00 | 易感人群症状有轻度加剧，健康人群出现刺激症状 |
| 151-200 | 中度污染 | #FFA500 | 进一步加剧易感人群症状，可能对心脏、呼吸系统有影响 |
| 201-300 | 重度污染 | #FF4500 | 心脏病和肺病患者症状显著加剧，运动耐受力降低 |
| >300 | 严重污染 | #990066 | 健康人群运动耐受力降低，有明显强烈症状 |

---

## 4. 调用限制

### 4.1 频次限制

| 套餐类型 | 每分钟限制 | 每月限制 | 说明 |
|----------|------------|----------|------|
| 免费版 | 10 | 1,000 | 基础功能 |
| 专业版 | 100 | 100,000 | 商业应用 |
| 企业版 | 1000 | 无限制 | 大规模应用 |

### 4.2 超限处理

当调用频率超过限制时，返回 429 错误：

```json
{
  "code": 429,
  "message": "请求过于频繁，请稍后再试",
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "retry_after": 60,
    "limit_type": "minute",
    "current_usage": 11,
    "limit": 10
  },
  "request_id": "req_abc123def456"
}
```

---

## 5. SDK 示例

### 5.1 Python SDK

```python
from weather_sdk import WeatherClient

# 初始化客户端
client = WeatherClient(api_key="YOUR_API_KEY")

# 获取实时天气
weather = client.get_current(city="北京")
print(f"北京天气: {weather['data']['weather']}, 温度: {weather['data']['temperature']}°C")

# 获取天气预报
forecast = client.get_forecast(city="北京", days=3)
for day in forecast['data']['forecasts']:
    print(f"{day['date']}: {day['weather']}, {day['temp_low']}-{day['temp_high']}°C")
```

### 5.2 JavaScript/Node.js SDK

```javascript
import { WeatherClient } from '@platform/weather-sdk';

// 初始化客户端
const client = new WeatherClient({ apiKey: 'YOUR_API_KEY' });

// 获取实时天气
const weather = await client.getCurrent({ city: '北京' });
console.log(`北京天气: ${weather.data.weather}, 温度: ${weather.data.temperature}°C`);

// 获取天气预报
const forecast = await client.getForecast({ city: '北京', days: 3 });
forecast.data.forecasts.forEach(day => {
  console.log(`${day.date}: ${day.weather}, ${day.tempLow}-${day.tempHigh}°C`);
});
```

---

**文档结束**

# Developer 在 API 平台的操作指南

## 目录

1. [概述](#1-概述)
2. [前提条件](#2-前提条件)
3. [获取 API Key](#3-获取-api-key)
4. [使用测试工具](#4-使用测试工具)
5. [常见问题](#5-常见问题)

---

## 1. 概述

本文档为 Developer 介绍如何在 API 平台使用 Weather API 服务，包括获取 API Key、调用接口和常见问题处理。

### 1.1 平台地址

| 环境 | 地址 |
|------|------|
| 前端控制台 | http://localhost:3000 |
| API 服务 | http://localhost:9000 |

### 1.2 角色说明

**Developer** 是 API 平台的核心用户角色，拥有以下权限：

- 浏览和搜索 API 仓库
- 订阅 API 服务
- 创建和管理 API Key
- 查看使用量和账单

---

## 2. 前提条件

### 2.1 账号准备

1. 拥有 API 平台的 Developer 账号
2. 账号已完成邮箱验证
3. 账户有足够的余额或配额

### 2.2 环境要求

| 软件 | 版本要求 |
|------|----------|
| 浏览器 | Chrome 90+ / Firefox 88+ / Safari 14+ / Edge 90+ |
| 网络 | 可访问 API 平台服务器 |

---

## 3. 获取 API Key

### 3.1 登录 Developer Portal

1. 打开浏览器，访问 `http://localhost:3000`
2. 点击右上角「登录」按钮
3. 输入邮箱和密码
4. 点击「确认登录」

### 3.2 进入 API 市场

1. 登录成功后，进入控制台首页
2. 点击左侧菜单「API 市场」
3. 在搜索框输入「天气 API」或「weather」
4. 点击进入天气 API 详情页

### 3.3 订阅 API

1. 在 API 详情页，点击「订阅」按钮
2. 选择订阅方案（免费/付费）
3. 阅读并同意服务条款
4. 点击「确认订阅」

### 3.4 创建 API Key

1. 订阅成功后，进入「API Key 管理」页面
2. 点击「创建 Key」按钮
3. 填写 Key 名称（如：测试Key）
4. 选择权限范围（建议勾选所有权限）
5. 点击「创建」
6. **重要**：复制并妥善保存生成的 Key

```
⚠️ 注意事项：
- API Key 只显示一次，刷新页面后将无法查看完整内容
- 请勿将 Key 泄露给他人
- 建议定期更换 Key
```

### 3.5 Key 管理

| 操作 | 位置 | 说明 |
|------|------|------|
| 查看 | Key 列表 | 点击 Key 名称展开查看 |
| 复制 | Key 列表 | 点击复制图标 |
| 编辑 | Key 详情 | 修改 Key 名称和权限 |
| 删除 | Key 列表 | 删除后无法恢复 |

---

## 4. 使用测试工具

### 4.1 打开测试工具

**方式一：使用在线版本**
- 直接访问 http://localhost:3000/developer/test-tool

**方式二：使用本地版本**
```bash
cd Developer/CallWeatherTest\ Tool
python -m http.server 8080
# 访问 http://localhost:8080
```

### 4.2 配置 API Key

1. 打开测试工具页面
2. 在「API Key」输入框中粘贴你的 Key
3. 在「API 地址」输入框确认地址：
   - 开发环境：`http://localhost:9000/api/v1`
   - 生产环境：`https://api.platform.com/api/v1`
4. 点击「保存」按钮

### 4.3 测试实时天气

**Step 1**: 选择接口

1. 在 Tab 栏中点击「实时天气」
2. 当前接口路径会显示：`GET /weather/current`

**Step 2**: 填写参数

1. 在「城市名称」输入框填写城市名（如：北京、上海、London）
2. 支持中文城市名和拼音

**Step 3**: 发送请求

1. 点击「发送请求」按钮
2. 等待响应（通常 < 1 秒）

**Step 4**: 查看结果

响应结果示例：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "city": "北京",
    "temperature": 25,
    "humidity": 60,
    "weather": "晴",
    "wind_speed": 3.5,
    "update_time": "2026-04-21 18:00:00"
  }
}
```

### 4.4 测试天气预报

1. 点击「天气预报」Tab
2. 填写城市名称
3. （可选）填写预报天数（默认 7 天）
4. 点击「发送请求」

**响应示例**：

```json
{
  "code": 0,
  "data": {
    "city": "北京",
    "forecast": [
      {
        "date": "2026-04-22",
        "temp_high": 28,
        "temp_low": 15,
        "weather": "多云"
      },
      {
        "date": "2026-04-23",
        "temp_high": 26,
        "temp_low": 14,
        "weather": "晴"
      }
    ]
  }
}
```

### 4.5 测试空气质量

1. 点击「空气质量」Tab
2. 填写城市名称
3. 点击「发送请求」

**响应示例**：

```json
{
  "code": 0,
  "data": {
    "city": "北京",
    "aqi": 85,
    "level": "良",
    "pm25": 58,
    "pm10": 102,
    "o3": 120,
    "so2": 15,
    "no2": 45
  }
}
```

### 4.6 测试天气预警

1. 点击「天气预警」Tab
2. 填写城市名称
3. 点击「发送请求」

**响应示例**：

```json
{
  "code": 0,
  "data": {
    "city": "北京",
    "alerts": [
      {
        "type": "暴雨",
        "level": "黄色",
        "title": "暴雨黄色预警",
        "description": "预计未来6小时..."
      }
    ]
  }
}
```

---

## 5. 常见问题

### Q1: 请求返回 401 错误

**原因**：API Key 无效或已过期

**解决方案**：
1. 检查 Key 是否正确粘贴（注意不要有空格）
2. 检查 Key 是否已过期（进入 Key 管理页面查看）
3. 如 Key 过期，重新创建一个新的 Key

### Q2: 请求返回 403 错误

**原因**：当前 Key 没有访问此接口的权限

**解决方案**：
1. 进入「API Key 管理」页面
2. 编辑 Key 权限，勾选对应接口
3. 重新发起请求

### Q3: 请求返回 429 错误

**原因**：请求频率超出限制

**解决方案**：
1. 降低请求频率
2. 等待 1 分钟后重试
3. 如需更高频率，联系平台升级配额

### Q4: 请求无响应

**原因**：可能是网络问题或 API 服务异常

**解决方案**：
1. 检查网络连接
2. 确认 API 平台服务是否正常运行
3. 稍后重试

### Q5: 响应数据为空

**原因**：查询的城市数据不存在

**解决方案**：
1. 确认城市名称拼写正确
2. 尝试使用城市拼音（如 beijing）
3. 确认城市在服务覆盖范围内

### Q6: 如何集成到我的应用？

**参考代码**：

```javascript
// JavaScript 示例
async function getWeather(city, apiKey) {
  const response = await fetch(
    `http://localhost:8000/api/v1/weather/current?city=${encodeURIComponent(city)}`,
    {
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      }
    }
  );
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  const result = await response.json();
  
  if (result.code !== 0) {
    throw new Error(result.message || 'API request failed');
  }
  
  return result.data;
}

// 使用
getWeather('北京', 'your-api-key')
  .then(data => console.log(data))
  .catch(err => console.error(err));
```

```python
# Python 示例
import requests

def get_weather(city, api_key):
    url = f"http://localhost:9000/api/v1/weather/current?city={city}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    result = response.json()
    if result['code'] != 0:
        raise Exception(result.get('message', 'API error'))
    
    return result['data']

# 使用
data = get_weather('北京', 'your-api-key')
print(data)
```

---

## 附录：接口速查

| 接口 | 方法 | 路径 | 必填参数 |
|------|------|------|----------|
| 实时天气 | GET | /weather/current | city |
| 天气预报 | GET | /weather/forecast | city, days(可选) |
| 空气质量 | GET | /weather/aqi | city |
| 天气预警 | GET | /weather/alerts | city |

---

**技术支持**：如有问题，请通过 Developer Portal 提交工单或发送邮件至 dev@platform.com

# Weather API 测试工具 - 开发 FAQ

## 文档控制

| 项目 | 内容 |
|------|------|
| 文档编号 | FAQ-DEVELOPER-2026-001 |
| 版本号 | V1.3 |
| 创建日期 | 2026-04-21 |
| 更新日期 | 2026-04-21 23:25 |

---

## FAQ 汇总

| 序号 | 问题标题 | 关键词 | 优先级 | 状态 |
|:----:|----------|--------|:------:|:----:|
| 101 | 如何获取 API Key | API Key、获取、Developer | P0 | ✅ 已解答 |
| 102 | 请求返回 401 错误怎么办 | 401、Unauthorized、无效 | P0 | ✅ 已解答 |
| 103 | 如何在代码中调用天气 API | 集成、JavaScript、Python | P1 | ✅ 已解答 |
| 104 | 支持哪些城市的数据 | 城市、覆盖范围 | P2 | ✅ 已解答 |
| 105 | API 调用频率限制是多少 | 限流、429、RPM | P1 | ✅ 已解答 |
| 106 | 如何测试不同的 API 接口 | 接口、测试工具、Tab | P1 | ✅ 已解答 |
| 107 | 测试工具调用 API 返回 404 或 CORS 错误 | 404、CORS、file://、端口 | P0 | ✅ 已解答 |
| 108 | API Key 验证正确但仍返回 401 错误 | 401、API Key、验证、路径 | P0 | ✅ 已解答 |
| 109 | 测试工具显示发送请求的 curl 命令 | curl、请求指令、复制 | P1 | ✅ 已解答 |

---

## 问题101：如何获取 API Key

### 问题描述

作为 Developer，第一次使用 API 平台，不知道如何获取 API Key。

### 解答

**获取步骤**：

1. **登录 Developer Portal**
   - 访问 http://localhost:3000
   - 使用 Developer 账号登录

2. **进入 API 市场**
   - 点击左侧菜单「API 市场」
   - 搜索「天气 API」或「weather」
   - 点击进入 API 详情页

3. **订阅 API**
   - 点击「订阅」按钮
   - 选择订阅方案
   - 确认订阅

4. **创建 API Key**
   - 进入「API Key 管理」页面
   - 点击「创建 Key」
   - 填写名称和权限
   - 点击「创建」并**立即复制 Key**

### 相关截图位置

[参考操作指南 - 获取 API Key 章节](./05_Developer操作指南.md#3-获取-api-key)

---

## 问题102：请求返回 401 错误怎么办

### 问题描述

调用接口时返回 401 错误，提示 `Unauthorized` 或 `Invalid API Key`。

### 问题原因

| 原因 | 说明 |
|------|------|
| Key 拼写错误 | 复制时多复制了空格或遗漏字符 |
| Key 已过期 | Key 设置了有效期，已自动失效 |
| Key 被禁用 | 账号异常或手动禁用了 Key |
| 请求头格式错误 | Authorization 头格式不正确 |

### 解决方案

**Step 1: 确认 Key 正确性**

1. 进入「API Key 管理」页面
2. 检查 Key 列表，确认 Key 存在
3. 点击「查看」确认 Key 内容

**Step 2: 重新复制 Key**

1. 点击 Key 旁边的「复制」图标
2. 在测试工具中粘贴
3. 确保没有多余的空格

**Step 3: 检查请求格式**

```javascript
// ✅ 正确格式
headers: {
  'Authorization': 'Bearer YOUR_API_KEY',
  'Content-Type': 'application/json'
}

// ❌ 错误格式
headers: {
  'Authorization': 'Bearer YOUR_API_KEY ',  // 多了空格
  'Authorization': 'YOUR_API_KEY',  // 缺少 Bearer
}
```

**Step 4: 如 Key 过期，创建一个新的**

1. 在 Key 列表中删除旧 Key
2. 点击「创建 Key」
3. 使用新 Key 测试

---

## 问题103：如何在代码中调用天气 API

### 问题描述

需要在项目中集成天气 API，不知道如何调用。

### 解答

### JavaScript/TypeScript

```javascript
/**
 * 获取实时天气
 * @param {string} city - 城市名称
 * @param {string} apiKey - API Key
 * @returns {Promise<Object>} 天气数据
 */
async function getCurrentWeather(city, apiKey) {
  try {
    const response = await fetch(
      `http://localhost:8000/api/v1/repositories/weather-api/api/v1/weather/current?city=${encodeURIComponent(city)}`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }

    const result = await response.json();

    if (result.code !== 0) {
      throw new Error(result.message || 'API Error');
    }

    return result.data;
  } catch (error) {
    console.error('Weather API Error:', error);
    throw error;
  }
}

// 使用示例
getCurrentWeather('北京', 'your-api-key')
  .then(data => {
    console.log(`温度: ${data.temperature}°C`);
    console.log(`天气: ${data.weather}`);
  })
  .catch(err => alert(err.message));
```

### Python

```python
import requests
from typing import Dict, Any

def get_current_weather(city: str, api_key: str) -> Dict[str, Any]:
    """
    获取实时天气
    
    Args:
        city: 城市名称
        api_key: API Key
    
    Returns:
        天气数据字典
    
    Raises:
        requests.HTTPError: 请求失败时抛出
    """
    url = "http://localhost:8000/api/v1/repositories/weather-api/api/v1/weather/current"
    params = {"city": city}
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    
    result = response.json()
    
    if result.get("code") != 0:
        raise Exception(result.get("message", "API Error"))
    
    return result["data"]

# 使用示例
if __name__ == "__main__":
    try:
        data = get_current_weather("北京", "your-api-key")
        print(f"温度: {data['temperature']}°C")
        print(f"天气: {data['weather']}")
    except Exception as e:
        print(f"错误: {e}")
```

### cURL

```bash
# 实时天气
curl -X GET "http://localhost:8000/api/v1/repositories/weather-api/api/v1/weather/current?city=北京" \
  -H "Authorization: Bearer YOUR_API_KEY"

# 天气预报
curl -X GET "http://localhost:8000/api/v1/repositories/weather-api/api/v1/weather/forecast?city=北京&days=3" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 问题104：支持哪些城市的数据

### 问题描述

测试时某些城市返回空数据，不知道支持哪些城市。

### 解答

**支持的城市范围**：

| 范围 | 数量 | 示例 |
|------|------|------|
| 中国大陆 | 300+ | 北京、上海、广州、深圳 |
| 港澳台 | 20+ | 香港、澳门、台北 |
| 国际主要城市 | 100+ | 纽约、东京、伦敦、巴黎 |

**覆盖的省份/地区**：

```
华北：北京、天津、河北、山西、内蒙古
东北：辽宁、吉林、黑龙江
华东：上海、江苏、浙江、安徽、福建、江西、山东
华中：河南、湖北、湖南
华南：广东、广西、海南
西南：重庆、四川、贵州、云南、西藏
西北：陕西、甘肃、青海、宁夏、新疆
港澳台：香港、澳门、台湾
国际：主要国家首都和热门城市
```

**常见问题**：

| 问题 | 解决方案 |
|------|----------|
| 城市找不到 | 尝试使用拼音（如 beijing） |
| 县级市无数据 | 尝试上级城市 |
| 国际城市无数据 | 确认城市英文拼写 |

---

## 问题105：API 调用频率限制是多少

### 问题描述

请求频繁时收到 429 错误，想了解限流规则。

### 解答

**默认限流规则**：

| 级别 | 限制 | 说明 |
|------|------|------|
| 免费用户 | 60 RPM | 每分钟 60 次 |
| 付费用户 | 1000 RPM | 每分钟 1000 次 |
| 企业用户 | 10000 RPM | 可申请更高配额 |

**RPM 含义**：

RPM = Requests Per Minute（每分钟请求数）

**避免限流的方法**：

1. **请求缓存**：相同结果缓存 5 分钟
2. **批量处理**：合并多次请求为一次
3. **异步队列**：将请求放入队列，限速发送
4. **预获取**：在低峰期预获取数据

**示例代码**：

```javascript
// 简单的请求缓存
const cache = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 5分钟

async function getWeatherWithCache(city, apiKey) {
  const cacheKey = `weather_${city}`;
  const cached = cache.get(cacheKey);
  
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    console.log('使用缓存数据');
    return cached.data;
  }
  
  const data = await getCurrentWeather(city, apiKey);
  cache.set(cacheKey, { data, timestamp: Date.now() });
  
  return data;
}
```

---

## 问题106：如何测试不同的 API 接口

### 问题描述

不熟悉测试工具的界面，不知道如何切换和测试不同接口。

### 解答

**测试工具界面说明**：

```
┌─────────────────────────────────────────────────────┐
│  [实时天气] [天气预报] [空气质量] [天气预警]  ← Tab 栏 │
│                                                      │
│  当前接口: GET /api/v1/weather/current              │
│                                                      │
│  参数输入区                                           │
│                                                      │
│  [━━━━━━━━━━━ 发送请求 ━━━━━━━━━━━]                   │
└─────────────────────────────────────────────────────┘
```

**测试步骤**：

1. **选择接口 Tab**
   - 点击对应的 Tab 名称
   - Tab 切换时，接口路径自动更新

2. **填写参数**
   - 必填参数用红色星号标识
   - 可选参数有默认值

3. **发送请求**
   - 点击「发送请求」按钮
   - 或使用快捷键 `Ctrl + Enter`

4. **查看结果**
   - 响应显示在下方区域
   - 绿色表示成功，红色表示失败

**接口速查**：

| Tab 名称 | 接口路径 | 必填参数 |
|----------|----------|----------|
| 实时天气 | /api/v1/weather/current | city |
| 天气预报 | /api/v1/weather/forecast | city |
| 空气质量 | /api/v1/weather/aqi | city |
| 天气预警 | /api/v1/weather/alerts | city |

---

## 问题107：测试工具调用 API 返回 404 或 CORS 错误

### 107.1 问题描述

使用 Developer 测试工具调用 Weather API 时遇到以下错误：

**错误1：CORS 跨域错误**
```
Access to fetch at 'http://localhost:8000/api/v1/...' from origin 'file:///...'
has been blocked by CORS policy
```

**错误2：file:// 协议安全问题**
```
unsafe attempt to load URL file:///... from frame with URL file:///...
'file:' URLs are treated as unique security origins.
```

**错误3：404 Repository not found**
```
{"detail":"Repository 'weather' not found"}
```

### 107.2 问题原因

| 原因 | 说明 |
|------|------|
| 直接双击 HTML 文件 | 使用 file:// 协议，浏览器阻止跨域请求 |
| API 地址配置错误 | 应配置为 API 平台地址，而非直接 Weather API |
| 端点路径缺少前缀 | 路径应为 /api/v1/weather/xxx，而非 /weather/xxx |
| API 平台未重启 | 新添加的动态路由需要重启服务 |

### 107.3 解决方案

#### 步骤1：必须通过 HTTP 服务器访问测试工具

**错误做法**：直接双击打开 `index.html` 文件
- 会使用 `file://` 协议
- 浏览器会阻止向 `http://` 地址发送请求

**正确做法**：启动 HTTP 服务器
```bash
cd D:\Work_Area\AI\API-Agent\Developer\CallWeatherTest Tool\src
python -m http.server 8080
```
然后在浏览器中访问：`http://localhost:8080`

#### 步骤2：配置正确的 API 地址

| 配置项 | 正确值 |
|--------|--------|
| API 地址 | `http://localhost:8000/api/v1/repositories/weather-api` |
| API Key | 有效的 API Key |

#### 步骤3：确保所有服务已启动

```bash
# 终端1：API 平台后端 (端口 8000)
cd D:\Work_Area\AI\API-Agent\api-platform
uvicorn src.main:app --reload --port 8000

# 终端2：Weather API (端口 8001)
cd D:\Work_Area\AI\API-Agent\OwnerServer
uvicorn src.main:app --reload --port 8001

# 终端3：测试工具 HTTP 服务器 (端口 8080)
cd D:\Work_Area\AI\API-Agent\Developer\CallWeatherTest Tool\src
python -m http.server 8080
```

### 107.4 调用流程图

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Developer 测试工具                               │
│                   (浏览器访问 http://localhost:8080)                  │
│                                                                     │
│  API 地址: http://localhost:8000/api/v1/repositories/weather-api   │
│  端点路径: /api/v1/weather/current                                  │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    API 平台后端 (8000)                                │
│                                                                     │
│  完整请求: /api/v1/repositories/weather-api/api/v1/weather/current  │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 Weather API - Owner仓库 (8001)                       │
│                                                                     │
│  后端请求: /api/v1/weather/current                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 107.5 常见错误排查

| 错误现象 | 可能原因 | 解决方案 |
|----------|----------|----------|
| CORS 错误 | 直接双击打开 HTML | 必须通过 http://localhost:8080 访问 |
| 404 Repository not found | 仓库 slug 不正确 | 确认 slug 为 `weather-api` |
| 404 Endpoint not found | API 平台未重启 | 重启 API 平台后端 |
| 连接失败 | 服务未启动 | 检查 8000 和 8001 端口 |

### 107.6 验证方法

**验证1：直接 curl 测试 API 平台**
```bash
curl http://localhost:8000/api/v1/repositories/weather-api/api/v1/weather/current?city=北京
```
应返回北京天气数据 JSON。

**验证2：浏览器直接访问**
```
http://localhost:8000/api/v1/repositories/weather-api/api/v1/weather/current?city=北京
```
应显示天气数据。

**验证3：测试工具测试**
1. 访问 http://localhost:8080
2. 配置 API 地址和 Key
3. 点击发送请求
4. 应显示天气数据

---

## 问题108：API Key 验证正确但仍返回 401 错误

### 108.1 问题描述

使用正确的 API Key 调用 Weather API 时仍然返回 401 Unauthorized 错误。

**错误日志示例**：
```
GET /api/v1/repositories/weather-api/api/v1/weather/alerts?city=北京 HTTP/1.1" 401 Unauthorized
[SRV-API] Request completed with warning: {'method': 'GET', 'path': '...', 'status': 401, ...}
```

### 108.2 问题原因

| 原因 | 说明 |
|------|------|
| API 平台未重启 | 动态路由或 API Key 验证代码更新后未重启服务 |
| 请求头名称错误 | 前端应使用 `X-Access-Key` 而非 `Authorization` |
| Key 格式不正确 | 复制的 Key 可能包含多余字符 |
| 路径重复 | 请求路径不应包含双重 `/api/v1` 前缀 |

### 108.3 解决方案

#### 步骤1：确认 API Key 请求头名称

前端发送请求时必须使用 `X-Access-Key` 请求头：

```javascript
// ✅ 正确格式
headers: {
  'X-Access-Key': apiKey,
  'Content-Type': 'application/json'
}

// ❌ 错误格式（会导致 401）
headers: {
  'Authorization': `Bearer ${apiKey}`,
  'Content-Type': 'application/json'
}
```

#### 步骤2：重启 API 平台后端

**必须重启**（热重载可能不生效）：

```bash
# 停止当前运行的服务 (Ctrl+C)

# 重新启动 API 平台
cd D:\Work_Area\AI\API-Agent\api-platform
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 步骤3：验证 API Key 有效性

在 Developer Portal 中：
1. 进入「API Key 管理」
2. 确认 Key 状态为「启用」
3. 点击复制按钮重新复制 Key

#### 步骤4：确认请求路径正确

**前端配置**：
- API 地址：`http://localhost:8000/api/v1`
- 端点路径：`/api/v1/weather/current`

**完整请求路径**：
```
http://localhost:8000/api/v1/repositories/weather-api/api/v1/weather/current?city=北京
```

**路径解析**：
| 部分 | 含义 |
|------|------|
| `http://localhost:8000` | API 平台地址 |
| `/api/v1` | API 版本前缀 |
| `/repositories/weather-api` | 仓库代理路由 |
| `/api/v1/weather/current` | Weather API 端点 |

### 108.4 API Key 验证流程

```
┌──────────────────────────────────────────────────────────────┐
│                    请求流程                                   │
└──────────────────────────────────────────────────────────────┘

1. 前端发送请求
   GET /api/v1/weather/current?city=北京
   Header: X-Access-Key: sk_live_xxxxx

2. API 平台接收请求
   → 匹配路由: /{repo_slug}/{path:path}
   → repo_slug = weather-api
   → path = api/v1/weather/current

3. API Key 验证
   → 从请求头读取 X-Access-Key
   → 与数据库中的 key_hash 比对
   → 验证通过后转发请求

4. 转发到 Weather API 后端
   Backend URL: http://localhost:8001/api/v1/weather/current

5. Weather API 响应
   → 返回天气数据 JSON
```

### 108.5 验证测试

**测试1：使用 curl 测试（带 API Key）**
```bash
curl -X GET "http://localhost:8000/api/v1/repositories/weather-api/api/v1/weather/current?city=北京" ^
  -H "X-Access-Key: YOUR_API_KEY"
```

**测试2：使用浏览器测试**
直接在浏览器访问（需先登录 Developer Portal 获取临时 Token）

### 108.6 常见错误排查

| 错误现象 | 可能原因 | 解决方案 |
|----------|----------|----------|
| 401 Unauthorized | API Key 无效或过期 | 重新获取 Key |
| 401 Invalid API Key | Key 格式错误 | 检查 Key 是否有空格 |
| 404 Not Found | 路径不正确 | 确认 API 地址配置 |
| 连接被拒绝 | 服务未启动 | 检查 8000 端口 |

---

## 问题109：测试工具显示发送请求的 curl 命令

### 109.1 功能说明

Developer 测试工具在发送 API 请求后，会在响应结果区域显示对应的 curl 命令，方便开发者复制到命令行或其他工具中使用。

### 109.2 功能特性

| 特性 | 说明 |
|------|------|
| Windows 兼容 | 使用 `^` 符号实现换行，可在 cmd.exe 中直接使用 |
| 完整参数 | 包含 URL、Headers、请求方法 |
| 一键复制 | 点击按钮即可复制到剪贴板 |

### 109.3 显示位置

在"响应结果"区域的状态栏下方，会显示一个深色背景的代码块：

```
┌─────────────────────────────────────────────────────┐
│  📋 curl 请求指令                          [复制]  │
├─────────────────────────────────────────────────────┤
│  curl -X GET "http://localhost:8000/..." ^         │
│    -H "X-Access-Key: sk_live_xxx" ^                │
│    -H "Content-Type: application/json"             │
└─────────────────────────────────────────────────────┘
```

### 109.4 使用方法

#### 发送请求后查看 curl

1. 在测试工具中输入 API Key 和参数
2. 点击"发送请求"
3. 滚动到响应结果区域，curl 命令会自动显示在状态栏下方

#### 复制到剪贴板

1. 点击 curl 命令区域右上角的"复制"按钮
2. 弹出提示"curl 命令已复制到剪贴板"
3. 可以在命令行或其他工具中粘贴使用

#### Windows 命令行使用

```bash
# 在 cmd.exe 中直接粘贴使用
curl -X GET "http://localhost:8000/api/v1/repositories/weather-api/api/v1/weather/current?city=北京" ^
  -H "X-Access-Key: sk_live_xxx" ^
  -H "Content-Type: application/json"
```

### 109.5 技术实现

**修改文件**：
- `Developer/CallWeatherTest Tool/src/index.html` - 添加 curl 命令显示区域
- `Developer/CallWeatherTest Tool/src/js/app.js` - 添加 curl 命令生成和复制逻辑

**关键代码**：

```javascript
// 生成 curl 命令
lastCurlCommand = `curl -X GET "${url}" ^\n  -H "X-Access-Key: ${apiKey}" ^\n  -H "Content-Type: application/json"`;

// 显示 curl 命令
if (lastCurlCommand) {
  requestCommandEl.classList.remove('hidden');
  document.getElementById('curlCommand').textContent = lastCurlCommand;
}
```

### 109.6 相关文件

| 文件路径 | 修改类型 | 说明 |
| `Developer/CallWeatherTest Tool/src/index.html` | 新增 | 添加 curl 命令显示区域 UI |
| `Developer/CallWeatherTest Tool/src/js/app.js` | 新增 | 添加 curl 命令生成、显示和复制功能 |

---

## 联系方式

如有更多问题：

- **工单系统**：通过 Developer Portal 提交
- **技术支持邮箱**：dev@platform.com
- **官方文档**：https://docs.platform.com

---

**文档更新记录**：

| 日期 | 版本 | 更新内容 | 更新人 |
:|------|------|----------|--------|
| 2026-04-21 | V1.0 | 初始版本，包含基础 FAQ | AI |
| 2026-04-21 | V1.1 | 新增问题 107：测试工具调用 API 返回 404 或 CORS 错误的解决方案；修正接口路径和 API 地址 | AI |
| 2026-04-21 | V1.2 | 新增问题 108：API Key 验证正确但仍返回 401 错误的解决方案；说明 X-Access-Key 请求头和路径配置 | AI |
| 2026-04-21 | V1.3 | 新增问题 109：测试工具显示发送请求的 curl 命令，方便开发者复制使用 | AI |

---

**文档结束**

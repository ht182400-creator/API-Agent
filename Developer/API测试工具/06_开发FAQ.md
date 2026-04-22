# API 测试工具常见问题解答 (FAQ)

## 目录

1. [快速入门](#1-快速入门)
2. [仓库配置](#2-仓库配置)
3. [功能使用](#3-功能使用)
4. [开发扩展](#4-开发扩展)
5. [故障排查](#5-故障排查)

---

## 1. 快速入门

### Q1: 如何访问 API 测试工具？

**访问地址**：
```
http://localhost:3000/developer/api-tester
```

**前提条件**：
- API 平台后端已启动（端口 8000）
- 已登录 Developer 账号

### Q2: 如何测试第一个 API？

**操作步骤**：

```
┌─────────────────────────────────────────────────────────────┐
│                    测试步骤图解                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 1: 选择仓库                                          │
│  ┌─────────────────────────────────────────────────┐       │
│  │  📦 仓库列表                                      │       │
│  │  ┌─────────────────────────────────────────┐   │       │
│  │  │ ☁️ 天气API ✅ ← 点击选中                  │   │       │
│  │  │ 🚚 物流API                                │   │       │
│  │  │ 💬 短信API                                │   │       │
│  │  └─────────────────────────────────────────┘   │       │
│  └─────────────────────────────────────────────────┘       │
│                          │                                 │
│                          ▼                                 │
│  Step 2: 选择端点                                          │
│  ┌─────────────────────────────────────────────────┐       │
│  │  🔗 API 端点                                    │       │
│  │  ┌─────────────────────────────────────────┐   │       │
│  │  │ GET 实时天气 ✅ ← 点击选中                │   │       │
│  │  │ GET 天气预报                             │   │       │
│  │  │ GET 空气质量                             │   │       │
│  │  └─────────────────────────────────────────┘   │       │
│  └─────────────────────────────────────────────────┘       │
│                          │                                 │
│                          ▼                                 │
│  Step 3: 填写参数并发送                                     │
│  ┌─────────────────────────────────────────────────┐       │
│  │  城市: [北京]  ← 输入城市名称                    │       │
│  │                                                   │       │
│  │  [🚀 发送请求]                                    │       │
│  └─────────────────────────────────────────────────┘       │
│                          │                                 │
│                          ▼                                 │
│  Step 4: 查看响应                                          │
│  ┌─────────────────────────────────────────────────┐       │
│  │  ✅ 成功                          200 OK        │       │
│  │  {                                                │       │
│  │    "city": "北京",                                │       │
│  │    "temperature": 25                              │       │
│  │  }                                                │       │
│  └─────────────────────────────────────────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Q3: 需要配置 API Key 吗？

**是的**，在发送请求前需要配置 API Key。

**配置方式**：
1. 在测试工具页面顶部的配置区域
2. 输入你的 API Key
3. 点击「保存」按钮

> ⚠️ **注意**：API Key 不会在刷新页面后保留，请妥善保存

---

## 2. 仓库配置

### Q4: 如何添加新的 API 仓库？

**添加步骤**：

```
添加新仓库流程：

1. 创建配置文件
   ├── src/config/repos/
   │   ├── weather.config.ts      ← 已有
   │   ├── logistics.config.ts    ← 已有
   │   └── third-party/
   │       ├── sms.config.ts      ← 已有
   │       └── payment.config.ts  ← 已有
   │
2. 在仓库配置中心注册
   └── src/config/repositories.config.ts
       └── 添加导入和数组项

3. 重启前端开发服务器
   └── npm run dev
```

**具体示例**：

```typescript
// 步骤1: 创建配置文件 src/config/repos/third-party/ocr.config.ts

import { Repository } from '../../../types/api-tester';

export const ocrRepository: Repository = {
  id: 'ocr-api',
  slug: 'ocr',
  name: 'OCR 文字识别 API',
  description: '提供图片文字识别、身份证识别等服务',
  icon: 'scan',
  category: 'third_party',  // 👈 标记为第三方
  baseUrl: '/api/v1/ocr',
  authType: 'api_key',
  authHeader: 'X-Access-Key',
  enabled: true,
  endpoints: [
    {
      id: 'recognize',
      name: '文字识别',
      path: '/recognize',
      method: 'POST',
      params: [],
      requestBody: [
        {
          name: 'image_url',
          type: 'string',
          required: true,
          description: '图片URL',
          in: 'body'
        }
      ]
    }
  ]
};
```

```typescript
// 步骤2: 在 repositories.config.ts 中注册

import { ocrRepository } from './repos/third-party/ocr.config';

export const repositories: Repository[] = [
  weatherRepository,
  logisticsRepository,
  smsRepository,
  paymentRepository,
  ocrRepository,  // 👈 新增这一行
];
```

### Q5: 自研仓库和第三方仓库有什么区别？

**对比表**：

| 特性 | 自研仓库 | 第三方仓库 |
|------|----------|------------|
| **分类标识** | 🏠 自研 | 🌐 第三方 |
| **代码位置** | `config/repos/` | `config/repos/third-party/` |
| **适用场景** | 平台自主开发 | 外部集成服务 |
| **维护方式** | 内部维护 | 第三方维护 |
| **配置方式** | 相同 | 相同 |

### Q6: 支持哪些图标？

**可用图标列表**：

| icon 值 | 显示图标 | 适用场景 |
|---------|----------|----------|
| `cloud` | ☁️ | 天气、气象服务 |
| `car` | 🚚 | 物流、运输服务 |
| `message` | 💬 | 短信、通讯服务 |
| `credit-card` | 💳 | 支付、结算服务 |
| `scan` | 📷 | OCR、扫描服务 |
| `map` | 🗺️ | 地图、位置服务 |
| `speech` | 🎤 | 语音、合成服务 |
| `default` | 📦 | 默认图标 |

---

## 3. 功能使用

### Q7: 支持哪些 HTTP 方法？

**支持的方法**：

| 方法 | 颜色 | 适用场景 |
|------|------|----------|
| **GET** | 🟢 绿色 | 查询、获取数据 |
| **POST** | 🔵 蓝色 | 创建、提交数据 |
| **PUT** | 🟠 橙色 | 更新、替换数据 |
| **DELETE** | 🔴 红色 | 删除数据 |
| **PATCH** | 🟣 紫色 | 部分更新数据 |

### Q8: 参数有哪些类型？

**支持的参数类型**：

| 类型 | 控件 | 说明 | 示例 |
|------|------|------|------|
| `string` | 文本框 | 普通字符串 | "北京" |
| `number` | 数字框 | 数值输入 | 123 |
| `boolean` | 复选框 | true/false | ✓ |
| `select` | 下拉框 | 预设选项 | [选项▼] |

### Q9: 如何使用 select 类型的参数？

```typescript
// 在端点配置中添加 options 数组

{
  name: 'days',
  type: 'select',
  options: [
    { label: '3天', value: '3' },
    { label: '5天', value: '5' },
    { label: '7天', value: '7' }   // ← 用户可选择
  ]
}
```

**显示效果**：
```
天数: [7天 ▼]
       ├─ 3天
       ├─ 5天
       └─ 7天
```

### Q10: 如何复制 curl 命令？

**操作步骤**：

```
1. 发送请求后，响应面板会显示 curl 命令

   ┌─────────────────────────────────────────────┐
   │  📋 curl 请求命令              [复制]       │
   │  ┌─────────────────────────────────────┐   │
   │  │ curl -X POST ".../api/v1/sms/send" │   │
   │  │   -H "X-Access-Key: xxx"           │   │
   │  └─────────────────────────────────────┘   │
   └─────────────────────────────────────────────┘

2. 点击「复制」按钮

3. 在终端中粘贴使用
```

### Q11: 历史记录保存在哪里？

**存储位置**：浏览器的 LocalStorage

**特点**：
- ✅ 关闭页面后数据保留
- ⚠️ 清除浏览器缓存会丢失
- ⚠️ 不同浏览器数据不共享
- 🔒 不会上传到服务器

**最大保存条数**：50 条

---

## 4. 开发扩展

### Q12: 如何添加新的参数类型控件？

**扩展步骤**：

```
1. 在 types/api-tester.ts 中定义新类型

   export type ParamType = 'string' | 'number' | 'boolean' 
                         | 'array' | 'date';  ← 新增

2. 在 DynamicForm.tsx 中添加渲染逻辑

   switch (param.type) {
     case 'string': return <TextInput />;
     case 'number': return <NumberInput />;
     case 'date':   return <DatePicker />;  ← 新增
     // ...
   }
```

### Q13: 如何添加新的认证方式？

**认证类型扩展**：

```typescript
// 1. 在 types/api-tester.ts 中定义

export type AuthType = 'api_key' | 'hmac' | 'oauth' | 'bearer';

// 2. 在 ApiTester.tsx 中扩展请求构建

const buildAuthHeader = (authType: AuthType, apiKey: string) => {
  switch (authType) {
    case 'api_key':
      return { 'X-Access-Key': apiKey };
    case 'bearer':
      return { 'Authorization': `Bearer ${apiKey}` };
    case 'hmac':
      // 实现 HMAC 签名逻辑
      return generateHmacHeaders(apiKey);
    // ...
  }
};
```

### Q14: 项目目录结构是怎样的？

**目录树**：

```
api-platform/web/src/
├── config/
│   ├── repositories.config.ts      # 仓库配置中心
│   └── repos/
│       ├── weather.config.ts       # 天气API
│       ├── logistics.config.ts     # 物流API
│       └── third-party/
│           ├── sms.config.ts       # 短信API
│           └── payment.config.ts   # 支付API
│
├── types/
│   └── api-tester.ts               # 类型定义
│
├── components/
│   └── api-tester/
│       ├── DynamicForm.tsx         # 动态表单
│       ├── RepositoryCard.tsx      # 仓库卡片
│       ├── EndpointList.tsx        # 端点列表
│       └── ResponsePanel.tsx       # 响应面板
│
└── pages/
    └── developer/
        ├── ApiTester.tsx           # 主页面
        └── ApiTester.module.css     # 样式
```

---

## 5. 故障排查

### Q15: 请求返回 401 错误？

**可能原因**：

| 原因 | 解决方法 |
|------|----------|
| API Key 未配置 | 在页面顶部配置并保存 Key |
| API Key 无效 | 在 Developer Portal 检查 Key |
| API Key 已过期 | 重新生成新的 Key |
| Key 权限不足 | 编辑 Key 权限，勾选对应接口 |

**排查流程**：

```
401 错误排查流程图：

┌─────────────────┐
│   发送请求       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  API Key 配置？  │──否──▶ 配置 API Key
└────────┬────────┘
         │是
         ▼
┌─────────────────┐
│  Key 有效？     │──否──▶ 重新生成 Key
└────────┬────────┘
         │是
         ▼
┌─────────────────┐
│  权限正确？     │──否──▶ 编辑 Key 权限
└────────┬────────┘
         │是
         ▼
    ┌────────┐
    │ 联系   │
    │ 管理员  │
    └────────┘
```

### Q16: 请求返回 CORS 错误？

**错误信息**：
```
Access to fetch at 'http://localhost:8000' from origin 
'http://localhost:3000' has been blocked by CORS policy
```

**解决方案**：

1. **检查后端 CORS 配置**（在 API Platform 后端）：

```python
# api-platform/src/core/middleware.py

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 👈 确保包含前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

2. **检查请求地址**：
   - 确保 API 地址是 `http://localhost:8000`
   - 不要使用 `http://127.0.0.1:8000`

### Q17: 页面显示空白？

**排查步骤**：

1. **检查控制台错误**
   - 按 F12 打开开发者工具
   - 查看 Console 标签页的错误信息

2. **常见错误及解决方案**：

| 错误信息 | 解决方案 |
|----------|----------|
| `Module not found` | 重新安装依赖 `npm install` |
| `Type error` | 检查 TypeScript 类型定义 |
| `Cannot read property` | 检查数据是否正确传递 |

3. **尝试清除缓存**
   ```
   # 删除 node_modules 和 package-lock.json
   rm -rf node_modules package-lock.json
   
   # 重新安装
   npm install
   
   # 重启开发服务器
   npm run dev
   ```

### Q18: 响应数据为空？

**可能原因**：

| 原因 | 解决方法 |
|------|----------|
| 参数错误 | 检查必填参数是否填写 |
| 城市不存在 | 尝试使用拼音或其他城市 |
| 接口未上线 | 联系 Owner 确认接口状态 |
| 服务异常 | 检查 Weather API 是否正常运行 |

### Q19: 如何查看详细请求信息？

**使用 curl 命令调试**：

```bash
# 复制页面生成的 curl 命令
curl -X GET "http://localhost:8000/api/v1/weather/current?city=北京" \
  -H "X-Access-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json"

# 查看详细响应
curl -v -X GET "..."   # -v 显示详细信息
```

---

## 附录：快捷键参考

| 快捷键 | 功能 |
|--------|------|
| `Ctrl + Enter` | 发送请求 |
| `Escape` | 关闭弹窗 |
| `Ctrl + C` (响应区) | 复制响应内容 |

---

**文档版本**：v1.0.0  
**最后更新**：2026-04-22  
**维护者**：Developer Team

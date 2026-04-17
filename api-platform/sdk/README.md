# API Platform SDK

官方提供的客户端开发工具包，包含认证模块、请求封装、响应解析、错误处理、重试机制五大核心功能。

## 支持的语言

| 语言 | 版本要求 | 状态 |
|------|----------|------|
| Python | 3.8+ | ✅ 已发布 |
| JavaScript | ES6+ | ✅ 已发布 |
| TypeScript | 4.0+ | ✅ 已发布 |
| Go | 1.18+ | 🔧 开发中 |
| Java | 11+ | 🔧 开发中 |
| PHP | 8.0+ | 📋 计划中 |

## 快速开始

### Python SDK

```bash
pip install api-platform-sdk
```

```python
from api_platform import Client

client = Client(
    api_key="sk_test_xxxxxxxxxxxx",
    base_url="https://api.platform.com/v1"
)

# 调用心理问答API
response = client.psychology.chat(message="我最近总是失眠怎么办？")
print(f"回答：{response.answer}")
print(f"费用：{response.usage.cost}")
```

### JavaScript/TypeScript SDK

```bash
npm install api-platform-sdk
```

```typescript
import { Client } from 'api-platform-sdk';

const client = new Client({
  apiKey: 'sk_test_xxxxxxxxxxxx',
  baseURL: 'https://api.platform.com/v1'
});

const response = await client.psychology.chat({
  message: '我最近总是失眠怎么办？'
});
console.log(`回答：${response.answer}`);
```

## 项目结构

```
sdk/
├── python/                 # Python SDK
│   ├── api_platform/      # SDK源码
│   │   ├── __init__.py
│   │   ├── client.py       # 客户端主类
│   │   ├── exceptions.py    # 异常类型
│   │   ├── http_client.py   # HTTP请求封装
│   │   └── utils.py         # 工具函数
│   ├── tests/              # 测试
│   ├── setup.py            # 安装配置
│   └── requirements.txt    # 依赖
│
└── js/                     # JavaScript/TypeScript SDK
    ├── src/               # 源码
    │   ├── client.ts      # 客户端主类
    │   ├── exceptions.ts   # 异常类型
    │   ├── httpClient.ts   # HTTP请求封装
    │   └── index.ts        # 入口文件
    ├── tests/             # 测试
    ├── package.json        # NPM配置
    └── tsconfig.json       # TypeScript配置
```

## 错误处理

SDK定义了完整的错误类型体系：

```python
from api_platform.exceptions import (
    APIError,              # 基类异常
    AuthenticationError,   # 认证失败（401）
    RateLimitError,        # 限流错误（429）
    QuotaExceededError,    # 配额超限
    ValidationError,       # 参数验证错误（400）
    NotFoundError,         # 资源不存在（404）
    ServerError,           # 服务器错误（500/503）
    NetworkError,          # 网络连接错误
    TimeoutError           # 请求超时
)
```

详细错误码请参考 [SDK使用手册](../../通用API服务平台文档/31_SDK使用手册.md)

## 许可证

MIT License

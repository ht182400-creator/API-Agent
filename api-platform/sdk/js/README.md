# API Platform JavaScript/TypeScript SDK

官方提供的JavaScript/TypeScript客户端开发工具包

## 安装

```bash
npm install api-platform-sdk
```

## 快速开始

### TypeScript

```typescript
import { Client } from 'api-platform-sdk';

const client = new Client({
  apiKey: 'sk_test_xxxxxxxxxxxx',
  baseURL: 'https://api.platform.com/v1'
});

// 心理问答
const response = await client.chat({
  message: '我最近总是失眠怎么办？'
});
console.log(`回答：${response.answer}`);
console.log(`费用：${response.usage.cost}`);

// 翻译服务
const translation = await client.translate({
  text: 'Hello, World!',
  source_lang: 'en',
  target_lang: 'zh'
});
console.log(`翻译：${translation.result}`);
```

### JavaScript

```javascript
const { Client } = require('api-platform-sdk');

const client = new Client({
  apiKey: 'sk_test_xxxxxxxxxxxx',
  baseURL: 'https://api.platform.com/v1'
});

async function main() {
  const response = await client.chat({
    message: '我最近总是失眠怎么办？'
  });
  console.log(`回答：${response.answer}`);
}

main();
```

## 错误处理

```typescript
import { Client } from 'api-platform-sdk';
import {
  AuthenticationError,
  RateLimitError,
  QuotaExceededError,
  ValidationError,
} from 'api-platform-sdk';

const client = new Client({ apiKey: 'sk_live_xxxxxxxxxxxx' });

try {
  const response = await client.chat({ message: '你好' });
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error(`认证失败：${error.message}`);
  } else if (error instanceof RateLimitError) {
    console.error(`限流，${error.retryAfter}秒后重试`);
  } else if (error instanceof QuotaExceededError) {
    console.error(`配额超限：${error.used}/${error.limit}`);
  } else if (error instanceof ValidationError) {
    console.error(`参数错误：${JSON.stringify(error.details)}`);
  } else {
    console.error(`未知错误：${error.message}`);
  }
}
```

## 许可证

MIT License

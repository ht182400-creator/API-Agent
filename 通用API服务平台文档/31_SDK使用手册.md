# 通用API服务平台 - SDK使用手册（增强版）

## 文档信息：

| 属性 | 内容 |
|------|------|
| **文档编号** | SDK-PLATFORM-2026-001 |
| **版本** | V1.2 |
| **日期** | 2026-04-17 |
| **更新说明** | 增强错误处理、完善业务场景示例 |

---

## 1. SDK概述

### 1.1 什么是SDK

SDK（Software Development Kit）是官方提供的客户端开发工具包，包含：认证模块、请求封装、响应解析、错误处理、重试机制五大核心功能。使用SDK可以让开发者无需关心签名算法、网络请求细节，专注于业务逻辑开发。

### 1.2 支持的语言和版本

| 语言 | 版本要求 | 状态 | 包管理器 |
|------|----------|------|----------|
| Python | 3.8+ | **已发布** | pip |
| JavaScript | ES6+ | **已发布** | npm |
| TypeScript | 4.0+ | **已发布** | npm |
| Go | 1.18+ | 开发中 | go get |
| Java | 11+ | 开发中 | Maven |
| PHP | 8.0+ | 计划中 | Composer |

---

## 2. Python SDK

### 2.1 安装和初始化

**安装SDK**：

```bash
pip install api-platform-sdk
```

**基础初始化**：

```python
from api_platform import Client

# 基础初始化（推荐用于开发测试）
client = Client(
    api_key="sk_test_xxxxxxxxxxxx",  # 测试Key
    api_secret="your_secret",
    base_url="https://api.platform.com/v1"  # 统一入口
)

# 生产环境初始化（推荐配置）
client = Client(
    api_key="sk_live_xxxxxxxxxxxx",  # 生产Key
    api_secret="your_secret",
    base_url="https://api.platform.com/v1",
    timeout=30,              # 请求超时（秒）
    max_retries=3,           # 最大重试次数
    retry_delay=1,           # 初始重试延迟（秒）
    retry_multiplier=2,      # 重试延迟倍数（指数退避）
    log_level="INFO"         # 日志级别：DEBUG/INFO/WARNING/ERROR
)
```

**生产环境密钥管理（重要）**：

```python
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

client = Client(
    api_key=os.environ.get('API_PLATFORM_KEY'),
    api_secret=os.environ.get('API_PLATFORM_SECRET'),
    base_url=os.environ.get('API_PLATFORM_URL', 'https://api.platform.com/v1')
)
```

**使用环境变量文件（.env）**：

```
API_PLATFORM_KEY=sk_live_xxxxxxxxxxxx
API_PLATFORM_SECRET=your_secret_here
API_PLATFORM_URL=https://api.platform.com/v1
```

---

## 3. 错误处理详解（核心部分）

### 3.1 错误类型体系

SDK定义了完整的错误类型体系，继承自基础异常类：

```python
from api_platform.exceptions import (
    APIError,              # 基类异常
    AuthenticationError,   # 认证失败（401）
    RateLimitError,         # 限流错误（429）
    QuotaExceededError,     # 配额超限
    ValidationError,        # 参数验证错误（400）
    NotFoundError,          # 资源不存在（404）
    ServerError,            # 服务器错误（500/503）
    NetworkError,           # 网络连接错误
    TimeoutError,           # 请求超时
    RetryExhaustedError     # 重试次数耗尽
)
```

### 3.2 错误码详解

| 错误码 | 名称 | HTTP状态 | 说明 | 解决方案 |
|--------|------|----------|------|----------|
| 0 | SUCCESS | 200 | 成功 | 无需处理 |
| 40001 | BAD_REQUEST | 400 | 请求参数错误 | 检查请求参数格式和必填项 |
| 40002 | INVALID_SIGNATURE | 400 | 签名无效 | 检查签名算法是否正确 |
| 40003 | TIMESTAMP_EXPIRED | 400 | 时间戳过期 | 同步服务器时间，建议误差<5分钟 |
| 40004 | NONCE_REUSED | 400 | Nonce重复 | 使用唯一随机字符串 |
| 40005 | INVALID_PARAMETER | 400 | 参数格式错误 | 检查参数类型和范围 |
| 40101 | UNAUTHORIZED | 401 | 未认证 | 检查API Key是否传递 |
| 40102 | INVALID_KEY | 401 | API Key无效 | 确认Key格式正确且未被禁用 |
| 40103 | KEY_DISABLED | 401 | Key已禁用 | 登录控制台启用Key |
| 40104 | KEY_EXPIRED | 401 | Key已过期 | 更新Key或申请延期 |
| 40301 | ACCESS_DENIED | 403 | 无权访问 | 确认Key有权限访问该仓库 |
| 40302 | REPO_NOT_ALLOWED | 403 | 未授权访问仓库 | 开通仓库访问权限 |
| 40401 | REPO_NOT_FOUND | 404 | 仓库不存在 | 检查仓库名称是否正确 |
| 40402 | ENDPOINT_NOT_FOUND | 404 | 接口不存在 | 检查接口路径是否正确 |
| 42901 | RATE_LIMIT_EXCEEDED | 429 | 请求过于频繁 | 降低请求频率，使用指数退避重试 |
| 42902 | QUOTA_EXCEEDED | 429 | 配额超限 | 充值账户或购买套餐 |
| 42903 | CONCURRENT_LIMIT | 429 | 并发超限 | 减少并发请求数量 |
| 50001 | INTERNAL_ERROR | 500 | 服务器内部错误 | 稍后重试或联系技术支持 |
| 50301 | REPO_UNAVAILABLE | 503 | 仓库服务不可用 | 检查仓库状态，等待恢复 |
| 50302 | REPO_TIMEOUT | 503 | 仓库响应超时 | 增加超时时间或稍后重试 |
| 50303 | REPO_ERROR | 503 | 仓库返回错误 | 查看仓库文档，联系仓库所有者 |

### 3.3 Python错误处理最佳实践

#### 3.3.1 基础错误处理

```python
from api_platform import Client
from api_platform.exceptions import (
    AuthenticationError, RateLimitError, QuotaExceededError,
    ValidationError, NotFoundError, ServerError, NetworkError
)

client = Client(api_key="sk_live_xxxxxxxxxxxx")

try:
    response = client.psychology.chat(message="我最近总是失眠怎么办？")
    print(f"回答：{response.answer}")
    print(f"Token数：{response.usage.tokens}")
    print(f"费用：{response.usage.cost}")
    print(f"请求ID：{response.request_id}")
    
except AuthenticationError as e:
    # 处理认证错误
    print(f"认证失败：{e.message}")
    print(f"错误码：{e.code}")
    print(f"请求ID：{e.request_id}")
    # 建议：检查API Key是否正确，检查Key是否启用
    
except RateLimitError as e:
    # 处理限流错误
    print(f"请求过于频繁：{e.message}")
    print(f"限制类型：{e.limit_type}")    # rpm/rph/daily/monthly
    print(f"限制值：{e.limit}")
    print(f"剩余配额：{e.remaining}")
    print(f"重试时间：{e.retry_after}秒")
    # 建议：使用指数退避重试，等待e.retry_after秒后重试
    
except QuotaExceededError as e:
    # 处理配额超限
    print(f"配额超限：{e.message}")
    print(f"已用配额：{e.used}")
    print(f"限制配额：{e.limit}")
    print(f"配额类型：{e.quota_type}")
    # 建议：充值账户或购买套餐
    
except ValidationError as e:
    # 处理参数验证错误
    print(f"参数错误：{e.message}")
    print(f"错误详情：{e.details}")
    # 建议：检查请求参数是否符合API要求
    
except NotFoundError as e:
    # 处理资源不存在错误
    print(f"资源不存在：{e.message}")
    print(f"资源类型：{e.resource_type}")
    print(f"资源ID：{e.resource_id}")
    # 建议：检查仓库名称或接口路径是否正确
    
except ServerError as e:
    # 处理服务器错误
    print(f"服务器错误：{e.message}")
    print(f"错误码：{e.code}")
    print(f"请求ID：{e.request_id}")
    # 建议：稍后重试，记录错误以便排查
    
except NetworkError as e:
    # 处理网络错误
    print(f"网络错误：{e.message}")
    print(f"原因：{e.cause}")
    # 建议：检查网络连接，尝试更换网络环境
    
except Exception as e:
    # 处理其他未知错误
    print(f"未知错误：{type(e).__name__}: {e}")
    # 建议：记录完整错误信息，联系技术支持
```

#### 3.3.2 带重试的错误处理

```python
import time
import logging
from api_platform import Client
from api_platform.exceptions import (
    RateLimitError, ServerError, NetworkError, RetryExhaustedError
)

logger = logging.getLogger(__name__)

class RetryableClient:
    """带自动重试的SDK封装"""
    
    def __init__(self, api_key, max_retries=3, base_delay=1, max_delay=60):
        self.client = Client(api_key=api_key)
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def call_with_retry(self, func, *args, **kwargs):
        """
        执行API调用，带指数退避重试
        
        Args:
            func: API调用函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            API响应对象
            
        Raises:
            RetryExhaustedError: 重试次数耗尽
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
                
            except RateLimitError as e:
                # 限流错误：使用服务端返回的重试时间
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = e.retry_after or (self.base_delay * (2 ** attempt))
                    logger.warning(
                        f"限流触发（第{attempt + 1}次尝试），等待{wait_time}秒后重试"
                    )
                    time.sleep(min(wait_time, self.max_delay))
                else:
                    logger.error(f"限流重试次数耗尽，最后错误：{e}")
                    
            except ServerError as e:
                # 服务器错误：使用指数退避
                last_exception = e
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.warning(
                        f"服务器错误（第{attempt + 1}次尝试），"
                        f"等待{delay}秒后重试，错误：{e.message}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"服务器错误重试次数耗尽，最后错误：{e}")
                    
            except NetworkError as e:
                # 网络错误：使用较短的重试间隔
                last_exception = e
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt), 10)
                    logger.warning(
                        f"网络错误（第{attempt + 1}次尝试），"
                        f"等待{delay}秒后重试"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"网络错误重试次数耗尽")
        
        raise RetryExhaustedError(
            f"重试{self.max_retries}次后仍然失败",
            last_exception=last_exception
        ) from last_exception

# 使用示例
retry_client = RetryableClient(api_key="sk_live_xxxxxxxxxxxx")

try:
    response = retry_client.call_with_retry(
        retry_client.client.psychology.chat,
        message="我最近总是失眠怎么办？"
    )
    print(f"成功获取回答：{response.answer}")
except RetryExhaustedError as e:
    print(f"API调用失败：{e}")
    # 建议：记录日志、发送告警、备用方案
```

#### 3.3.3 异步错误处理

```python
import asyncio
import logging
from api_platform import AsyncClient
from api_platform.exceptions import RateLimitError, ServerError

logger = logging.getLogger(__name__)

class AsyncRetryClient:
    """异步版本的带重试SDK封装"""
    
    def __init__(self, api_key, max_retries=3):
        self.client = AsyncClient(api_key=api_key)
        self.max_retries = max_retries
    
    async def call_with_retry(self, func, *args, **kwargs):
        """异步API调用，带指数退避重试"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
                
            except RateLimitError as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = e.retry_after or (1 * (2 ** attempt))
                    logger.warning(f"限流，等待{wait_time}秒")
                    await asyncio.sleep(wait_time)
                    
            except ServerError as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = 1 * (2 ** attempt)
                    logger.warning(f"服务器错误，等待{delay}秒后重试")
                    await asyncio.sleep(delay)
        
        raise last_exception

# 使用示例
async def main():
    client = AsyncRetryClient(api_key="sk_live_xxxxxxxxxxxx")
    
    try:
        response = await client.call_with_retry(
            client.client.psychology.chat,
            message="我最近总是失眠怎么办？"
        )
        print(f"回答：{response.answer}")
    except Exception as e:
        print(f"调用失败：{e}")

asyncio.run(main())
```

### 3.4 JavaScript错误处理

#### 3.4.1 基础错误处理

```typescript
import { 
  Client, 
  AuthenticationError, 
  RateLimitError,
  QuotaExceededError,
  ValidationError,
  NotFoundError,
  ServerError,
  NetworkError
} from 'api-platform-sdk';

const client = new Client({ 
  apiKey: 'sk_live_xxxxxxxxxxxx',
  maxRetries: 3
});

async function callAPI() {
  try {
    const response = await client.psychology.chat({ 
      message: '我最近总是失眠怎么办？' 
    });
    
    console.log(`回答：${response.answer}`);
    console.log(`Token数：${response.usage.tokens}`);
    console.log(`费用：${response.usage.cost}`);
    console.log(`请求ID：${response.requestId}`);
    
  } catch (error) {
    if (error instanceof AuthenticationError) {
      // 认证错误
      console.error(`认证失败：${error.message}`);
      console.error(`错误码：${error.code}`);
      console.error(`请求ID：${error.requestId}`);
      
    } else if (error instanceof RateLimitError) {
      // 限流错误
      console.error(`限流：${error.message}`);
      console.error(`限制类型：${error.limitType}`);
      console.error(`重试时间：${error.retryAfter}秒`);
      // 等待后重试
      await new Promise(resolve => setTimeout(resolve, error.retryAfter * 1000));
      
    } else if (error instanceof QuotaExceededError) {
      // 配额超限
      console.error(`配额超限：${error.message}`);
      console.error(`已用：${error.used}`);
      console.error(`限制：${error.limit}`);
      
    } else if (error instanceof ValidationError) {
      // 参数错误
      console.error(`参数错误：${error.message}`);
      console.error(`错误详情：${JSON.stringify(error.details)}`);
      
    } else if (error instanceof NotFoundError) {
      // 资源不存在
      console.error(`资源不存在：${error.message}`);
      console.error(`资源类型：${error.resourceType}`);
      
    } else if (error instanceof ServerError) {
      // 服务器错误
      console.error(`服务器错误：${error.message}`);
      console.error(`请求ID：${error.requestId}`);
      
    } else if (error instanceof NetworkError) {
      // 网络错误
      console.error(`网络错误：${error.message}`);
      
    } else {
      // 未知错误
      console.error(`未知错误：${error.message}`);
    }
  }
}
```

#### 3.4.2 异步重试处理

```typescript
import { Client } from 'api-platform-sdk';
import { 
  RateLimitError, 
  ServerError, 
  NetworkError 
} from 'api-platform-sdk';

class RetryClient {
  private client: Client;
  private maxRetries: number;
  
  constructor(apiKey: string, maxRetries = 3) {
    this.client = new Client({ apiKey, maxRetries: 0 }); // SDK不自动重试
    this.maxRetries = maxRetries;
  }
  
  async callWithRetry<T>(
    func: () => Promise<T>,
    context: string = ''
  ): Promise<T> {
    let lastError: Error | undefined;
    
    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        return await func();
        
      } catch (error) {
        lastError = error as Error;
        
        if (error instanceof RateLimitError) {
          const waitTime = error.retryAfter || Math.pow(2, attempt);
          console.log(`限流（第${attempt + 1}次），等待${waitTime}秒`);
          await this.sleep(waitTime * 1000);
          
        } else if (error instanceof ServerError) {
          const waitTime = Math.pow(2, attempt);
          console.log(`服务器错误（第${attempt + 1}次），等待${waitTime}秒`);
          await this.sleep(waitTime * 1000);
          
        } else if (error instanceof NetworkError) {
          const waitTime = Math.pow(2, Math.min(attempt, 4));
          console.log(`网络错误（第${attempt + 1}次），等待${waitTime}秒`);
          await this.sleep(waitTime * 1000);
          
        } else {
          // 非重试错误，直接抛出
          throw error;
        }
      }
    }
    
    throw lastError;
  }
  
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  async chat(message: string) {
    return this.callWithRetry(
      () => this.client.psychology.chat({ message }),
      `chat: ${message.substring(0, 20)}...`
    );
  }
}

// 使用示例
const retryClient = new RetryClient('sk_live_xxxxxxxxxxxx', 3);

try {
  const response = await retryClient.chat('我最近总是失眠怎么办？');
  console.log(`回答：${response.answer}`);
} catch (error) {
  console.error(`调用失败：${error.message}`);
}
```

---

## 4. 业务场景集成示例

### 4.1 心理问答应用

**场景描述**：开发一个心理问答小程序，用户可以提问并获取专业建议。

```python
from api_platform import Client
from api_platform.exceptions import (
    AuthenticationError, RateLimitError, QuotaExceededError, ServerError
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PsychologyApp:
    """心理问答应用封装"""
    
    def __init__(self, api_key):
        self.client = Client(
            api_key=api_key,
            timeout=30,
            max_retries=3
        )
    
    def ask_question(self, question: str, user_context: dict = None) -> dict:
        """
        提问并获取回答
        
        Args:
            question: 用户问题
            user_context: 用户上下文（可选）
            
        Returns:
            包含回答和建议的字典
            
        Raises:
            ValueError: 参数错误
            RuntimeError: 服务不可用
        """
        # 参数验证
        if not question or len(question.strip()) == 0:
            raise ValueError("问题不能为空")
        
        if len(question) > 1000:
            raise ValueError("问题长度不能超过1000字符")
        
        # 构建请求参数
        params = {
            "message": question.strip(),
            "user_id": user_context.get("user_id") if user_context else None,
            "context": {
                "age": user_context.get("age") if user_context else None,
                "gender": user_context.get("gender") if user_context else None,
                "occupation": user_context.get("occupation") if user_context else None
            }
        }
        
        # 过滤None值
        params = {k: v for k, v in params.items() if v is not None}
        
        try:
            # 调用API
            response = self.client.psychology.chat(**params)
            
            return {
                "success": True,
                "answer": response.answer,
                "suggestions": response.suggestions,
                "request_id": response.request_id,
                "tokens": response.usage.tokens,
                "cost": response.usage.cost
            }
            
        except RateLimitError as e:
            logger.warning(f"限流触发，建议稍后重试：{e.message}")
            return {
                "success": False,
                "error": "rate_limit",
                "message": "请求过于频繁，请稍后再试",
                "retry_after": e.retry_after
            }
            
        except QuotaExceededError as e:
            logger.error(f"配额用尽：{e.message}")
            return {
                "success": False,
                "error": "quota_exceeded",
                "message": "免费额度已用完，请充值后继续使用"
            }
            
        except ServerError as e:
            logger.error(f"服务器错误：{e.message}，请求ID：{e.request_id}")
            return {
                "success": False,
                "error": "server_error",
                "message": "服务暂时不可用，请稍后重试"
            }
            
        except Exception as e:
            logger.exception(f"未知错误：{e}")
            return {
                "success": False,
                "error": "unknown",
                "message": "系统错误，请联系客服"
            }
    
    def batch_ask(self, questions: list) -> list:
        """
        批量提问
        
        Args:
            questions: 问题列表
            
        Returns:
            回答列表
        """
        results = []
        for question in questions:
            result = self.ask_question(question)
            results.append(result)
            
            # 避免限流
            if "retry_after" in result:
                import time
                time.sleep(result["retry_after"])
        
        return results

# 使用示例
if __name__ == "__main__":
    app = PsychologyApp(api_key="sk_live_xxxxxxxxxxxx")
    
    # 单次提问
    result = app.ask_question(
        question="我最近总是失眠怎么办？",
        user_context={"age": 30, "gender": "male"}
    )
    
    if result["success"]:
        print(f"回答：{result['answer']}")
        print(f"建议：{result['suggestions']}")
        print(f"费用：{result['cost']}元")
    else:
        print(f"错误：{result['message']}")
```

### 4.2 翻译服务集成

**场景描述**：为企业应用集成多语言翻译服务。

```python
from api_platform import Client
from api_platform.exceptions import (
    ValidationError, RateLimitError, QuotaExceededError
)
from typing import List, Dict
import hashlib

class TranslationService:
    """翻译服务封装"""
    
    SUPPORTED_LANGUAGES = {
        "zh": "中文",
        "en": "英语",
        "ja": "日语",
        "ko": "韩语",
        "fr": "法语",
        "de": "德语",
        "es": "西班牙语",
        "ru": "俄语",
        "ar": "阿拉伯语"
    }
    
    def __init__(self, api_key):
        self.client = Client(
            api_key=api_key,
            timeout=60,
            max_retries=3
        )
    
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        engine: str = "accurate"
    ) -> dict:
        """
        单次翻译
        
        Args:
            text: 待翻译文本
            source_lang: 源语言代码
            target_lang: 目标语言代码
            engine: 引擎选择（accurate/fast）
            
        Returns:
            翻译结果字典
        """
        # 参数验证
        if not text:
            raise ValueError("翻译文本不能为空")
        
        if source_lang not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"不支持的源语言：{source_lang}")
        
        if target_lang not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"不支持的目标语言：{target_lang}")
        
        if source_lang == target_lang:
            return {
                "success": True,
                "source_text": text,
                "translated_text": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "detected_lang": source_lang,
                "cost": 0
            }
        
        try:
            response = self.client.translation.translate(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                engine=engine
            )
            
            return {
                "success": True,
                "source_text": text,
                "translated_text": response.result,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "detected_lang": getattr(response, "detected_lang", source_lang),
                "cost": response.usage.cost
            }
            
        except ValidationError as e:
            raise ValueError(f"翻译参数错误：{e.message}")
            
        except RateLimitError as e:
            raise RuntimeError(f"翻译服务限流，请稍后再试（{e.retry_after}秒）")
            
        except QuotaExceededError:
            raise RuntimeError("翻译配额已用完，请充值")
    
    def batch_translate(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str
    ) -> List[dict]:
        """
        批量翻译
        
        Args:
            texts: 待翻译文本列表
            source_lang: 源语言代码
            target_lang: 目标语言代码
            
        Returns:
            翻译结果列表
        """
        results = []
        
        for i, text in enumerate(texts):
            try:
                result = self.translate(
                    text=text,
                    source_lang=source_lang,
                    target_lang=target_lang
                )
                results.append(result)
                
            except Exception as e:
                results.append({
                    "success": False,
                    "source_text": text,
                    "error": str(e)
                })
            
            # 避免触发限流
            if i < len(texts) - 1:
                import time
                time.sleep(0.1)
        
        return results
    
    def translate_document(
        self,
        document: str,
        source_lang: str,
        target_lang: str,
        paragraph_separator: str = "\n\n"
    ) -> dict:
        """
        翻译文档（自动分段落）
        
        Args:
            document: 待翻译文档内容
            source_lang: 源语言代码
            target_lang: 目标语言代码
            paragraph_separator: 段落分隔符
            
        Returns:
            翻译后的文档
        """
        paragraphs = document.split(paragraph_separator)
        translated_paragraphs = []
        total_cost = 0.0
        
        for paragraph in paragraphs:
            if paragraph.strip():
                result = self.translate(
                    text=paragraph.strip(),
                    source_lang=source_lang,
                    target_lang=target_lang
                )
                translated_paragraphs.append(result["translated_text"])
                total_cost += result["cost"]
            else:
                translated_paragraphs.append("")
        
        return {
            "success": True,
            "translated_document": paragraph_separator.join(translated_paragraphs),
            "paragraphs_count": len(paragraphs),
            "total_cost": total_cost
        }

# 使用示例
if __name__ == "__main__":
    translator = TranslationService(api_key="sk_live_xxxxxxxxxxxx")
    
    # 单次翻译
    result = translator.translate(
        text="Hello, World!",
        source_lang="en",
        target_lang="zh"
    )
    print(f"翻译结果：{result['translated_text']}")
    
    # 批量翻译
    texts = [
        "Good morning",
        "Good afternoon",
        "Good evening",
        "Good night"
    ]
    results = translator.batch_translate(
        texts=texts,
        source_lang="en",
        target_lang="zh"
    )
    for r in results:
        print(f"{r['source_text']} -> {r['translated_text']}")
```

### 4.3 图像识别集成

**场景描述**：集成图像OCR和识别服务到内容管理系统。

```python
from api_platform import Client
from api_platform.exceptions import ValidationError, RateLimitError
import base64
import os

class ImageRecognitionService:
    """图像识别服务封装"""
    
    TASK_TYPES = {
        "ocr": "文字识别（OCR）",
        "id_card": "身份证识别",
        "business_card": "名片识别",
        "license_plate": "车牌识别",
        " handwriting": "手写文字识别",
        "label": "图像标签",
        "face": "人脸检测",
        "object": "物体检测"
    }
    
    def __init__(self, api_key):
        self.client = Client(
            api_key=api_key,
            timeout=60,
            max_retries=2
        )
    
    def recognize_from_url(self, image_url: str, task: str = "ocr") -> dict:
        """
        从URL识别图像
        
        Args:
            image_url: 图像URL地址
            task: 识别任务类型
            
        Returns:
            识别结果
        """
        if task not in self.TASK_TYPES:
            raise ValueError(f"不支持的识别任务：{task}")
        
        try:
            response = self.client.vision.recognize(
                image_url=image_url,
                task=task
            )
            
            return {
                "success": True,
                "task": task,
                "result": self._format_result(response),
                "cost": response.usage.cost
            }
            
        except Exception as e:
            return {
                "success": False,
                "task": task,
                "error": str(e)
            }
    
    def recognize_from_file(self, file_path: str, task: str = "ocr") -> dict:
        """
        从本地文件识别图像
        
        Args:
            file_path: 本地文件路径
            task: 识别任务类型
            
        Returns:
            识别结果
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在：{file_path}")
        
        # 检查文件大小（限制10MB）
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:
            raise ValueError("图片大小不能超过10MB")
        
        # 检查文件类型
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"]:
            raise ValueError(f"不支持的图片格式：{ext}")
        
        with open(file_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        try:
            response = self.client.vision.recognize(
                image_data=image_data,
                task=task
            )
            
            return {
                "success": True,
                "task": task,
                "result": self._format_result(response),
                "cost": response.usage.cost
            }
            
        except Exception as e:
            return {
                "success": False,
                "task": task,
                "error": str(e)
            }
    
    def batch_recognize_from_urls(
        self,
        urls: list,
        task: str = "ocr"
    ) -> list:
        """
        批量从URL识别
        
        Args:
            urls: URL列表
            task: 识别任务类型
            
        Returns:
            识别结果列表
        """
        results = []
        
        for i, url in enumerate(urls):
            print(f"正在处理第{i + 1}/{len(urls)}张图片...")
            
            result = self.recognize_from_url(url, task)
            results.append(result)
            
            # 避免限流
            if i < len(urls) - 1:
                import time
                time.sleep(0.2)
        
        return results
    
    def _format_result(self, response) -> dict:
        """格式化识别结果"""
        if hasattr(response, "text"):
            return {"text": response.text}
        elif hasattr(response, "labels"):
            return {"labels": response.labels}
        elif hasattr(response, "faces"):
            return {"faces": response.faces}
        else:
            return {"raw": response}

# 使用示例
if __name__ == "__main__":
    service = ImageRecognitionService(api_key="sk_live_xxxxxxxxxxxx")
    
    # OCR识别
    result = service.recognize_from_url(
        image_url="https://example.com/document.jpg",
        task="ocr"
    )
    
    if result["success"]:
        print(f"识别结果：{result['result']['text']}")
        print(f"费用：{result['cost']}元")
    
    # 本地文件识别
    result = service.recognize_from_file(
        file_path="./id_card.jpg",
        task="id_card"
    )
```

### 4.4 高并发场景处理

**场景描述**：处理大量并发请求的应用场景。

```python
from api_platform import Client
from api_platform.exceptions import RateLimitError, QuotaExceededError
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import threading
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HighConcurrencyClient:
    """
    高并发场景的SDK封装
    
    特性：
    - 线程安全
    - 自动限流
    - 熔断机制
    - 失败重试
    """
    
    def __init__(
        self,
        api_key: str,
        max_workers: int = 10,
        rpm_limit: int = 100
    ):
        self.client = Client(
            api_key=api_key,
            timeout=30,
            max_retries=2
        )
        self.max_workers = max_workers
        self.rpm_limit = rpm_limit
        
        # 限流器
        self.rate_limiter = TokenBucket(rpm_limit, 60)
        
        # 熔断器
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=10,
            recovery_timeout=60
        )
        
        # 线程锁
        self._lock = threading.Lock()
    
    def call(self, func, *args, **kwargs):
        """线程安全的API调用"""
        # 检查熔断器
        if not self.circuit_breaker.can_execute():
            raise CircuitOpenError("Circuit breaker is open")
        
        # 限流
        self.rate_limiter.acquire()
        
        try:
            with self._lock:
                result = func(*args, **kwargs)
            
            self.circuit_breaker.record_success()
            return result
            
        except RateLimitError as e:
            self.circuit_breaker.record_failure()
            # 等待限流恢复
            time.sleep(e.retry_after or 1)
            raise
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise


class TokenBucket:
    """令牌桶限流器"""
    
    def __init__(self, capacity: int, refill_rate: int):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def acquire(self):
        """获取令牌"""
        with self._lock:
            self._refill()
            
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.refill_rate
                time.sleep(wait_time)
                self._refill()
            
            self.tokens -= 1
    
    def _refill(self):
        """补充令牌"""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now


class CircuitBreaker:
    """熔断器"""
    
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = self.CLOSED
        self._lock = threading.Lock()
    
    def can_execute(self) -> bool:
        """检查是否可以执行"""
        with self._lock:
            if self.state == self.CLOSED:
                return True
            
            if self.state == self.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = self.HALF_OPEN
                    return True
                return False
            
            if self.state == self.HALF_OPEN:
                return True
            
            return False
    
    def record_success(self):
        """记录成功"""
        with self._lock:
            self.failures = 0
            self.state = self.CLOSED
    
    def record_failure(self):
        """记录失败"""
        with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()
            
            if self.failures >= self.failure_threshold:
                self.state = self.OPEN
                logger.warning(f"Circuit breaker opened after {self.failures} failures")


class CircuitOpenError(Exception):
    """熔断器打开异常"""
    pass


# 使用示例
def main():
    client = HighConcurrencyClient(
        api_key="sk_live_xxxxxxxxxxxx",
        max_workers=10,
        rpm_limit=100
    )
    
    questions = [
        f"问题{i + 1}" for i in range(100)
    ]
    
    results = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(
                client.call,
                client.client.psychology.chat,
                message=q
            ): q for q in questions
        }
        
        for future in as_completed(futures):
            q = futures[future]
            try:
                result = future.result()
                results.append({"question": q, "success": True, "result": result})
            except Exception as e:
                results.append({"question": q, "success": False, "error": str(e)})
    
    success_count = sum(1 for r in results if r["success"])
    print(f"成功：{success_count}/{len(results)}")


if __name__ == "__main__":
    main()
```

---

## 5. TypeScript类型定义

### 5.1 完整类型定义

```typescript
// api-platform-sdk/types.ts

// 客户端配置
export interface ClientOptions {
  apiKey: string;
  apiSecret?: string;
  baseURL?: string;
  timeout?: number;
  maxRetries?: number;
  retryDelay?: number;
  retryMultiplier?: number;
  logLevel?: 'debug' | 'info' | 'warn' | 'error';
}

// 错误类型
export enum ErrorCode {
  SUCCESS = 0,
  BAD_REQUEST = 40001,
  INVALID_SIGNATURE = 40002,
  TIMESTAMP_EXPIRED = 40003,
  NONCE_REUSED = 40004,
  INVALID_PARAMETER = 40005,
  UNAUTHORIZED = 40101,
  INVALID_KEY = 40102,
  KEY_DISABLED = 40103,
  KEY_EXPIRED = 40104,
  ACCESS_DENIED = 40301,
  REPO_NOT_ALLOWED = 40302,
  REPO_NOT_FOUND = 40401,
  ENDPOINT_NOT_FOUND = 40402,
  RATE_LIMIT_EXCEEDED = 42901,
  QUOTA_EXCEEDED = 42902,
  CONCURRENT_LIMIT = 42903,
  INTERNAL_ERROR = 50001,
  REPO_UNAVAILABLE = 50301,
  REPO_TIMEOUT = 50302,
  REPO_ERROR = 50303
}

// 基础错误类
export class APIError extends Error {
  code: ErrorCode;
  requestId: string;
  details?: Record<string, unknown>;
  
  constructor(
    message: string,
    code: ErrorCode,
    requestId?: string,
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'APIError';
    this.code = code;
    this.requestId = requestId || '';
    this.details = details;
  }
}

// 认证错误
export class AuthenticationError extends APIError {
  constructor(message: string, code: ErrorCode = ErrorCode.UNAUTHORIZED) {
    super(message, code);
    this.name = 'AuthenticationError';
  }
}

// 限流错误
export class RateLimitError extends APIError {
  limitType: 'rpm' | 'rph' | 'daily' | 'monthly';
  limit: number;
  remaining: number;
  retryAfter: number;
  
  constructor(
    message: string,
    limitType: string,
    limit: number,
    remaining: number,
    retryAfter: number
  ) {
    super(message, ErrorCode.RATE_LIMIT_EXCEEDED);
    this.name = 'RateLimitError';
    this.limitType = limitType as any;
    this.limit = limit;
    this.remaining = remaining;
    this.retryAfter = retryAfter;
  }
}

// 配额超限错误
export class QuotaExceededError extends APIError {
  quotaType: string;
  used: number;
  limit: number;
  
  constructor(message: string, quotaType: string, used: number, limit: number) {
    super(message, ErrorCode.QUOTA_EXCEEDED);
    this.name = 'QuotaExceededError';
    this.quotaType = quotaType;
    this.used = used;
    this.limit = limit;
  }
}

// 心理问答请求
export interface ChatOptions {
  message: string;
  userId?: string;
  context?: {
    age?: number;
    gender?: string;
    occupation?: string;
    [key: string]: any;
  };
  timeout?: number;
}

// 心理问答响应
export interface ChatResponse {
  answer: string;
  suggestions: string[];
  requestId: string;
  usage: {
    tokens: number;
    cost: number;
  };
}

// 翻译请求
export interface TranslationOptions {
  text: string;
  sourceLang: string;
  targetLang: string;
  engine?: 'accurate' | 'fast';
}

// 翻译响应
export interface TranslationResponse {
  result: string;
  detectedLang: string;
  usage: {
    tokens: number;
    cost: number;
  };
}

// 图像识别请求
export interface RecognitionOptions {
  imageUrl?: string;
  imageData?: string; // base64
  task: 'ocr' | 'label' | 'face' | 'object';
}

// 图像识别响应
export interface RecognitionResponse {
  text?: string;
  labels?: Array<{ label: string; confidence: number }>;
  faces?: Array<{ bbox: number[]; confidence: number }>;
  objects?: Array<{ label: string; bbox: number[]; confidence: number }>;
  usage: {
    tokens: number;
    cost: number;
  };
}
```

---

## 6. 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.2.0 | 2026-04-17 | 增强错误处理文档，完善业务场景示例 |
| v1.1.0 | 2026-04-16 | 新增TypeScript类型定义 |
| v1.0.0 | 2026-04-15 | 初始版本 |

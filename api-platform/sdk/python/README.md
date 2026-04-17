# API Platform Python SDK

官方提供的Python客户端开发工具包

## 安装

```bash
pip install api-platform-sdk
```

## 快速开始

```python
from api_platform import Client

client = Client(
    api_key="sk_test_xxxxxxxxxxxx",
    base_url="https://api.platform.com/v1"
)

# 心理问答
response = client.psychology.chat(message="我最近总是失眠怎么办？")
print(f"回答：{response.answer}")
print(f"费用：{response.usage.cost}")

# 翻译服务
response = client.translation.translate(
    text="Hello, World!",
    source_lang="en",
    target_lang="zh"
)
print(f"翻译：{response.result}")
```

## 错误处理

```python
from api_platform import Client
from api_platform.exceptions import (
    AuthenticationError,
    RateLimitError,
    QuotaExceededError,
    ValidationError
)

client = Client(api_key="sk_live_xxxxxxxxxxxx")

try:
    response = client.psychology.chat(message="你好")
except AuthenticationError as e:
    print(f"认证失败：{e.message}")
except RateLimitError as e:
    print(f"限流，请{e.retry_after}秒后重试")
except QuotaExceededError as e:
    print(f"配额超限，请充值")
except ValidationError as e:
    print(f"参数错误：{e.details}")
```

## 许可证

MIT License

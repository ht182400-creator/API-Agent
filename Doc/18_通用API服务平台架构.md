# 通用API服务平台架构方案

**文档编号**：PLATFORM-API-2026-001  
**版本**：V1.0  
**更新日期**：2026-04-16  
**状态**：初稿

---

## 1. 业务模式分析

### 1.1 传统模式 vs 平台模式

```
┌─────────────────────────────────────────────────────────────────────┐
│                        传统模式                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────┐                                                      │
│   │  开发者  │ ──────── 直接对接 ────────▶ [仓库A]                  │
│   └──────────┘                                                      │
│   ┌──────────┐                                                      │
│   │  开发者  │ ──────── 直接对接 ────────▶ [仓库B]                  │
│   └──────────┘                                                      │
│   ┌──────────┐                                                      │
│   │  开发者  │ ──────── 直接对接 ────────▶ [仓库C]                  │
│   └──────────┘                                                      │
│                                                                      │
│   问题：                                                             │
│   • 每个仓库需要单独对接                                             │
│   • 认证方式各不相同                                                 │
│   • 没有统一监控和计费                                               │
│   • 维护成本高                                                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        平台模式（推荐）                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────┐      ┌──────────────────────────────────────────┐   │
│   │  开发者  │ ───▶ │           API聚合平台                     │   │
│   └──────────┘      │  ┌────────────────────────────────────┐   │   │
│   ┌──────────┐      │  │  统一认证 | 路由分发 | 计费统计   │   │   │
│   │  开发者  │ ───▶ │  │  监控告警 | 文档中心 | 开发者门户  │   │   │
│   └──────────┘      │  └────────────────────────────────────┘   │   │
│   ┌──────────┐      │                    │                      │   │
│   │  开发者  │ ───▶ │                    ▼                      │   │
│   └──────────┘      │  ┌────────┐ ┌────────┐ ┌────────┐        │   │
│                      │  │仓库A   │ │仓库B   │ │仓库C   │        │   │
│                      │  │心理问答│ │交易咨询│ │更多... │        │   │
│                      │  └────────┘ └────────┘ └────────┘        │   │
│                      └──────────────────────────────────────────┘   │
│                                                                      │
│   优势：                                                             │
│   • 一次对接，接入所有仓库                                           │
│   • 统一认证、计费、监控                                             │
│   • 可扩展、插件化架构                                               │
│   • 商业化变现                                                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心价值

| 角色 | 痛点 | 平台解决方案 |
|------|------|-------------|
| **开发者** | 对接多个仓库耗时 | 一次对接，调用所有 |
| **仓库方** | 获客和计费困难 | 流量导入+分成结算 |
| **平台方** | - | 抽取佣金+增值服务 |

---

## 2. 平台架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         API聚合平台架构                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                        接入层 (Gateway)                          │ │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │ │
│  │  │  HTTPS  │  │   WAF   │  │  限流   │  │   路由   │          │ │
│  │  │  证书   │  │  防护   │  │  控制   │  │  分发   │          │ │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘          │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                │                                     │
│                                ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                        认证层 (Auth)                              │ │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │ │
│  │  │ API Key │  │  JWT    │  │ OAuth   │  │  权限   │          │ │
│  │  │  验证   │  │  Token  │  │  授权   │  │  控制   │          │ │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘          │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                │                                     │
│                                ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                      业务逻辑层 (Core Services)                   │ │
│  │                                                                  │ │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐ │ │
│  │  │ 路由引擎   │  │  协议转换  │  │  限流引擎  │  │  计费引擎  │ │ │
│  │  │           │  │           │  │           │  │           │ │ │
│  │  │ 动态路由  │  │ REST/WS   │  │ 配额控制  │  │  按量计费  │ │ │
│  │  │ 负载均衡  │  │ gRPC适配  │  │ 熔断降级  │  │  包月套餐  │ │ │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘ │ │
│  │                                                                  │ │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐ │ │
│  │  │ 插件管理   │  │  监控日志  │  │  告警通知  │  │  SDK中心  │ │ │
│  │  │           │  │           │  │           │  │           │ │ │
│  │  │ 仓库注册  │  │ 请求追踪  │  │ 异常告警  │  │ 代码生成  │ │ │
│  │  │ 热更新   │  │ 性能指标  │  │ 配额告警  │  │ 文档生成  │ │ │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘ │ │
│  │                                                                  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                │                                     │
│         ┌──────────────────────┼──────────────────────┐             │
│         │                      │                      │             │
│         ▼                      ▼                      ▼             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐         │
│  │   仓库适配层  │      │   数据层    │      │   外部服务   │         │
│  │              │      │              │      │              │         │
│  │ HTTP适配器   │      │ PostgreSQL   │      │  仓库节点A   │         │
│  │ WebSocket    │      │ Redis        │      │  仓库节点B   │         │
│  │ gRPC代理     │      │ ClickHouse   │      │  仓库节点C   │         │
│  │ 自定义协议   │      │ Kafka        │      │  更多仓库... │         │
│  └─────────────┘      └─────────────┘      └─────────────┘         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 请求流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                         API调用完整流程                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  开发者 ───▶ ① 认证 ───▶ ② 限流 ───▶ ③ 路由 ───▶ ④ 计费 ───▶ ⑤ 调用 │
│                 │                │               │               │     │
│                 ▼                ▼               ▼               ▼     │
│           ┌─────────┐      ┌─────────┐      ┌─────────┐    ┌────────┐│
│           │验证Key │      │检查配额 │      │转发请求 │    │返回响应││
│           │JWT验证 │      │熔断降级 │      │协议转换 │    │记录日志││
│           └─────────┘      └─────────┘      └─────────┘    └────────┘│
│                 │                │               │               │     │
│                 ▼                ▼               ▼               ▼     │
│           ⑥ 返回 ───▶ ⑦ 更新配额 ───▶ ⑧ 记录日志 ───▶ ⑨ 完成    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. 仓库（Plugin）接入机制

### 3.1 仓库定义

| 术语 | 定义 |
|------|------|
| **仓库 (Repository)** | 提供特定API服务的外部系统或节点 |
| **插件 (Plugin)** | 连接平台与仓库的适配器 |
| **节点 (Node)** | 仓库的具体实例 |

### 3.2 仓库分类

| 类型 | 说明 | 示例 |
|------|------|------|
| **内部仓库** | 平台自建的服务 | 课程问答、翻译服务 |
| **外部仓库** | 第三方接入的服务 | 心理问答、股票查询 |
| **混合仓库** | 内外结合 | AI模型池 |

### 3.3 仓库注册接口

```yaml
# POST /v1/repositories
{
    "name": "心理咨询API",
    "code": "psychology_qa",
    "version": "1.0.0",
    "category": "consultation",
    "description": "专业心理咨询问答服务",
    "endpoint": "https://api.psychology.example.com",
    "protocol": "REST",
    "auth_type": "api_key",
    "auth_config": {
        "header_name": "X-API-Key",
        "credentials": "${PSYCHOLOGY_API_KEY}"
    },
    "rate_limit": {
        "rpm": 60,
        "rph": 1000
    },
    "pricing": {
        "type": "per_call",
        "price": 0.01
    },
    "capabilities": [
        "text_chat",
        "voice_convert"
    ],
    "schemas": {
        "request": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "user_id": {"type": "string"}
            }
        },
        "response": {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "confidence": {"type": "number"}
            }
        }
    },
    "status": "active"
}
```

### 3.4 仓库适配器设计

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel

class RequestContext(BaseModel):
    """请求上下文"""
    user_id: str
    api_key_id: str
    repository_id: str
    method: str
    path: str
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]]
    query_params: Dict[str, Any]
    client_ip: str

class RepositoryAdapter(ABC):
    """仓库适配器基类"""
    
    @abstractmethod
    def get_repository_id(self) -> str:
        """获取仓库ID"""
        pass
    
    @abstractmethod
    def get_repository_name(self) -> str:
        """获取仓库名称"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
    
    @abstractmethod
    async def invoke(self, context: RequestContext) -> Dict[str, Any]:
        """调用仓库"""
        pass
    
    async def before_invoke(self, context: RequestContext) -> RequestContext:
        """调用前处理"""
        return context
    
    async def after_invoke(self, context: RequestContext, response: Dict) -> Dict:
        """调用后处理"""
        return response


class HTTPRepositoryAdapter(RepositoryAdapter):
    """HTTP仓库适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.endpoint = config['endpoint']
        self.timeout = config.get('timeout', 30)
        self.retry_count = config.get('retry_count', 3)
    
    async def invoke(self, context: RequestContext) -> Dict[str, Any]:
        # 构建请求
        headers = self._build_headers(context)
        url = self._build_url(context)
        
        # 发送请求
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=context.method,
                url=url,
                headers=headers,
                json=context.body,
                params=context.query_params,
                timeout=self.timeout
            )
        
        return {
            "status_code": response.status_code,
            "body": response.json(),
            "headers": dict(response.headers)
        }
    
    def _build_headers(self, context: RequestContext) -> Dict[str, str]:
        # 添加认证头
        headers = {
            "Content-Type": "application/json",
            "X-Platform-Request-Id": context.client_ip,
            "X-User-Id": context.user_id,
        }
        
        # 添加仓库特定的认证信息
        if 'auth_headers' in self.config:
            headers.update(self.config['auth_headers'])
        
        return headers


class WebSocketRepositoryAdapter(RepositoryAdapter):
    """WebSocket仓库适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.endpoint = config['endpoint']
    
    async def invoke(self, context: RequestContext) -> Dict[str, Any]:
        # 建立WebSocket连接
        async with websockets.connect(self.endpoint) as ws:
            # 发送消息
            await ws.send(json.dumps({
                "action": context.method,
                "data": context.body,
                "user_id": context.user_id
            }))
            
            # 接收响应
            response = await ws.recv()
        
        return json.loads(response)


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self._plugins: Dict[str, RepositoryAdapter] = {}
        self._lock = asyncio.Lock()
    
    async def register(self, adapter: RepositoryAdapter):
        """注册插件"""
        async with self._lock:
            self._plugins[adapter.get_repository_id()] = adapter
    
    async def unregister(self, repository_id: str):
        """注销插件"""
        async with self._lock:
            if repository_id in self._plugins:
                del self._plugins[repository_id]
    
    async def get_adapter(self, repository_id: str) -> Optional[RepositoryAdapter]:
        """获取适配器"""
        return self._plugins.get(repository_id)
    
    async def invoke(self, repository_id: str, context: RequestContext) -> Dict[str, Any]:
        """调用仓库"""
        adapter = await self.get_adapter(repository_id)
        if not adapter:
            raise RepositoryNotFoundError(repository_id)
        
        # 前置处理
        context = await adapter.before_invoke(context)
        
        # 调用
        response = await adapter.invoke(context)
        
        # 后置处理
        response = await adapter.after_invoke(context, response)
        
        return response
```

### 3.5 仓库热更新机制

```yaml
# 仓库配置热更新流程
┌─────────────────────────────────────────────────────────────────────┐
│                         热更新流程                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. 配置变更 ──▶ 2. 验证配置 ──▶ 3. 灰度发布 ──▶ 4. 全量生效         │
│                                                                      │
│  ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐    │
│  │ 管理员   │      │  配置    │      │ 单节点   │      │ 全量    │    │
│  │ 修改配置 │ ──▶ │ 验证    │ ──▶ │ 更新   │ ──▶ │ 生效   │    │
│  └─────────┘      └─────────┘      └─────────┘      └─────────┘    │
│                      │                                      │       │
│                      ▼                                      ▼       │
│                ┌─────────┐                            ┌─────────┐   │
│                │ 失败    │                            │  回滚   │   │
│                │ 提示错误 │                            │  机制   │   │
│                └─────────┘                            └─────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. 核心API设计

### 4.1 统一API规范

```yaml
openapi: 3.0.3
info:
  title: API聚合平台
  version: 1.0.0
  description: 统一的API聚合平台，支持多仓库接入

servers:
  - url: https://api.platform.com/v1
    description: 正式环境
  - url: https://sandbox.platform.com/v1
    description: 沙箱环境

paths:
  # 仓库管理
  /repositories:
    get:
      summary: 获取仓库列表
      tags: [仓库管理]
      parameters:
        - name: category
          in: query
          schema:
            type: string
        - name: search
          in: query
          schema:
            type: string
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RepositoryList'

  /repositories/{repository_id}:
    get:
      summary: 获取仓库详情
      tags: [仓库管理]
      parameters:
        - $ref: '#/components/parameters/repository_id'
      responses:
        '200':
          description: 成功

  # 统一调用入口
  /{repository_code}/invoke:
    post:
      summary: 调用仓库API
      tags: [API调用]
      parameters:
        - name: repository_code
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              type: object
      responses:
        '200':
          description: 成功
        '404':
          description: 仓库不存在
        '429':
          description: 限流

  # 认证
  /auth/login:
    post:
      summary: 用户登录
      tags: [认证]
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                email:
                  type: string
                password:
                  type: string
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token:
                    type: string
                  refresh_token:
                    type: string
                  expires_in:
                    type: integer

  # API Key管理
  /keys:
    get:
      summary: 获取API Key列表
      tags: [认证]
    post:
      summary: 创建API Key
      tags: [认证]
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
                permissions:
                  type: array
                  items:
                    type: string

  # 调用日志
  /logs:
    get:
      summary: 查询调用日志
      tags: [日志]
      parameters:
        - name: repository_id
          in: query
        - name: start_time
          in: query
        - name: end_time
          in: query
      responses:
        '200':
          description: 成功

  # 统计分析
  /stats:
    get:
      summary: 获取使用统计
      tags: [统计]
      responses:
        '200':
          description: 成功

components:
  schemas:
    Repository:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
        code:
          type: string
        category:
          type: string
        description:
          type: string
        endpoint:
          type: string
        status:
          type: string
          enum: [active, inactive, maintenance]
        pricing:
          type: object
        rate_limit:
          type: object

    RepositoryList:
      type: object
      properties:
        data:
          type: array
          items:
            $ref: '#/components/schemas/Repository'
        pagination:
          type: object

  parameters:
    repository_id:
      name: repository_id
      in: path
      required: true
      schema:
        type: string
```

### 4.2 调用示例

```python
import requests

API_KEY = "your_api_key"
BASE_URL = "https://api.platform.com/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 1. 获取可用仓库列表
response = requests.get(f"{BASE_URL}/repositories", headers=headers)
repositories = response.json()['data']

# 2. 根据分类筛选
response = requests.get(
    f"{BASE_URL}/repositories?category=consultation",
    headers=headers
)

# 3. 调用心理问答仓库
response = requests.post(
    f"{BASE_URL}/psychology_qa/invoke",
    headers=headers,
    json={
        "question": "我最近总是失眠怎么办？",
        "user_id": "user_123",
        "context": {
            "age": 25,
            "gender": "male"
        }
    }
)
print(response.json())

# 4. 调用股票查询仓库
response = requests.post(
    f"{BASE_URL}/stock_query/invoke",
    headers=headers,
    json={
        "symbol": "AAPL",
        "fields": ["price", "volume", "change"]
    }
)

# 5. 查询调用日志
response = requests.get(
    f"{BASE_URL}/logs?repository_id=psychology_qa&start_time=2026-04-01",
    headers=headers
)
```

---

## 5. 计费与配额系统

### 5.1 计费模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **按调用次数** | 每个请求固定费用 | 大多数API |
| **按Token量** | 根据输入输出Token计费 | AI服务 |
| **按流量** | 根据数据量计费 | 文件处理 |
| **包月套餐** | 固定费用无限调用 | 高频用户 |
| **混合计费** | 基础+增量 | 复杂场景 |

### 5.2 计费配置

```python
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel
from typing import List, Optional

class PricingType(str, Enum):
    PER_CALL = "per_call"           # 按次
    PER_TOKEN = "per_token"         # 按Token
    PER流量 = "per_traffic"         # 按流量
    SUBSCRIPTION = "subscription"    # 包月
    HYBRID = "hybrid"               # 混合

class PricingConfig(BaseModel):
    """计费配置"""
    type: PricingType
    base_price: Decimal = Decimal("0")           # 基础价格
    per_call_price: Decimal = Decimal("0.01")     # 单次价格
    per_token_price: Decimal = Decimal("0.0001") # Token单价
    per_mb_price: Decimal = Decimal("0.1")       # MB单价
    free_tier: int = 100                          # 免费额度
    volume_discounts: List[dict] = []             # 批量折扣

class QuotaConfig(BaseModel):
    """配额配置"""
    daily_limit: int = 1000          # 日配额
    monthly_limit: int = 30000       # 月配额
    rpm: int = 60                    # 每分钟请求
    rph: int = 1000                  # 每小时请求
    burst: int = 10                  # 突发限制

# 仓库计费示例
REPOSITORY_CONFIGS = {
    "psychology_qa": {
        "name": "心理咨询API",
        "pricing": {
            "type": "per_call",
            "per_call_price": Decimal("0.05"),  # 5分钱/次
            "free_tier": 10
        },
        "quota": {
            "daily_limit": 100,
            "rpm": 10
        }
    },
    "stock_query": {
        "name": "股票查询API",
        "pricing": {
            "type": "per_call",
            "per_call_price": Decimal("0.01")    # 1分钱/次
        },
        "quota": {
            "daily_limit": 1000,
            "rpm": 60
        }
    },
    "ai_chat": {
        "name": "AI对话服务",
        "pricing": {
            "type": "per_token",
            "per_token_price": Decimal("0.0001"),  # 1厘/Token
            "base_price": Decimal("9.9"),           # 包月9.9元
            "free_tier": 1000                       # 免费1000 Token
        },
        "quota": {
            "daily_limit": 50000,
            "rpm": 30
        }
    }
}
```

### 5.3 计费计算器

```python
from decimal import Decimal
from datetime import datetime
from typing import Dict

class BillingCalculator:
    """计费计算器"""
    
    def __init__(self, config: PricingConfig):
        self.config = config
    
    def calculate(self, usage: Dict) -> Decimal:
        """计算费用"""
        if self.config.type == PricingType.PER_CALL:
            return self._calculate_per_call(usage)
        elif self.config.type == PricingType.PER_TOKEN:
            return self._calculate_per_token(usage)
        elif self.config.type == PricingType.SUBSCRIPTION:
            return self._calculate_subscription(usage)
        elif self.config.type == PricingType.HYBRID:
            return self._calculate_hybrid(usage)
    
    def _calculate_per_call(self, usage: Dict) -> Decimal:
        """按次计费"""
        call_count = usage.get('call_count', 0)
        
        # 减去免费额度
        billable = max(0, call_count - self.config.free_tier)
        
        # 计算费用
        return Decimal(billable) * self.config.per_call_price
    
    def _calculate_per_token(self, usage: Dict) -> Decimal:
        """按Token计费"""
        input_tokens = usage.get('input_tokens', 0)
        output_tokens = usage.get('output_tokens', 0)
        total_tokens = input_tokens + output_tokens
        
        # 减去免费额度
        billable = max(0, total_tokens - self.config.free_tier)
        
        # 计算费用
        return Decimal(billable) * self.config.per_token_price
    
    def _calculate_subscription(self, usage: Dict) -> Decimal:
        """包月计费"""
        return self.config.base_price
    
    def _calculate_hybrid(self, usage: Dict) -> Decimal:
        """混合计费"""
        base = self.config.base_price
        call_fee = self._calculate_per_call(usage)
        token_fee = self._calculate_per_token(usage)
        
        return base + call_fee + token_fee

# 使用示例
config = PricingConfig(
    type=PricingType.PER_TOKEN,
    per_token_price=Decimal("0.0001"),
    free_tier=1000
)

calculator = BillingCalculator(config)

usage = {
    'input_tokens': 500,
    'output_tokens': 1000,
    'call_count': 10
}

cost = calculator.calculate(usage)
print(f"本次费用: ¥{cost:.4f}")
```

---

## 6. 数据库设计

### 6.1 ER关系图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         数据模型关系图                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────┐      ┌─────────┐      ┌─────────┐                      │
│  │  users  │──1:N──│api_keys │──N:1──│repos   │                      │
│  └────┬────┘      └────┬────┘      └────┬────┘                      │
│       │                 │                 │                         │
│       │                 │                 │                         │
│       ▼                 ▼                 ▼                         │
│  ┌─────────┐      ┌─────────┐      ┌─────────┐                      │
│  │key_perms│      │ call_   │──N:1──│ repo_   │                      │
│  └─────────┘      │ logs    │      │ configs │                      │
│                   └────┬────┘      └─────────┘                      │
│                        │                                        │
│                        ▼                                        │
│                   ┌─────────┐                                    │
│                   │ billing │                                    │
│                   └─────────┘                                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 核心表结构

```sql
-- 仓库表
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) UNIQUE NOT NULL,      -- 仓库代码
    name VARCHAR(255) NOT NULL,              -- 仓库名称
    category VARCHAR(50),                   -- 分类
    description TEXT,                       -- 描述
    endpoint VARCHAR(500),                  -- 目标地址
    protocol VARCHAR(20) DEFAULT 'HTTP',   -- 协议
    auth_type VARCHAR(20),                  -- 认证类型
    auth_config JSONB,                      -- 认证配置（加密存储）
    pricing_type VARCHAR(20),               -- 计费类型
    pricing_config JSONB,                   -- 计费配置
    rate_limit JSONB,                       -- 限流配置
    status VARCHAR(20) DEFAULT 'active',   -- 状态
    version VARCHAR(50),                    -- 版本
    config_schema JSONB,                    -- 配置JSON Schema
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    name VARCHAR(100),
    company VARCHAR(255),
    plan VARCHAR(20) DEFAULT 'free',        -- free/pro/enterprise
    balance DECIMAL(10, 2) DEFAULT 0,       -- 余额
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- API Key表
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(100),
    api_key VARCHAR(64) UNIQUE NOT NULL,
    secret_key VARCHAR(64),
    permissions JSONB,                       -- ["psychology_qa:invoke", "stock_query:invoke"]
    enabled BOOLEAN DEFAULT true,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 调用日志表
CREATE TABLE call_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    api_key_id UUID REFERENCES api_keys(id),
    repository_id UUID REFERENCES repositories(id),
    repository_code VARCHAR(100),
    
    -- 请求信息
    request_method VARCHAR(10),
    request_path VARCHAR(255),
    request_headers JSONB,
    request_body JSONB,
    request_params JSONB,
    client_ip INET,
    user_agent TEXT,
    
    -- 响应信息
    response_status INTEGER,
    response_body JSONB,
    latency_ms INTEGER,
    
    -- 计费信息
    tokens_used INTEGER,
    cost DECIMAL(10, 4),
    
    -- 追踪
    trace_id VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 配额表
CREATE TABLE quotas (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    api_key_id UUID REFERENCES api_keys(id),
    repository_id UUID REFERENCES repositories(id),
    
    quota_type VARCHAR(20),                 -- daily/monthly/total
    quota_limit INTEGER,                     -- 配额上限
    quota_used INTEGER DEFAULT 0,           -- 已使用
    reset_at TIMESTAMP,                      -- 重置时间
    
    UNIQUE(user_id, api_key_id, repository_id, quota_type)
);

-- 账单表
CREATE TABLE bills (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    billing_period VARCHAR(20),             -- 2026-04
    total_amount DECIMAL(10, 2),             -- 总金额
    paid_amount DECIMAL(10, 2) DEFAULT 0,   -- 已支付
    status VARCHAR(20) DEFAULT 'pending',    -- pending/paid/overdue
    created_at TIMESTAMP DEFAULT NOW(),
    paid_at TIMESTAMP
);

-- 账单明细表
CREATE TABLE bill_items (
    id BIGSERIAL PRIMARY KEY,
    bill_id INTEGER REFERENCES bills(id),
    repository_id UUID REFERENCES repositories(id),
    
    call_count INTEGER,                      -- 调用次数
    token_count INTEGER,                     -- Token数
    traffic_mb DECIMAL(10, 2),              -- 流量MB
    
    unit_price DECIMAL(10, 4),              -- 单价
    amount DECIMAL(10, 2),                  -- 金额
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_call_logs_user ON call_logs(user_id);
CREATE INDEX idx_call_logs_repo ON call_logs(repository_id);
CREATE INDEX idx_call_logs_time ON call_logs(created_at DESC);
CREATE INDEX idx_quotas_user_key ON quotas(user_id, api_key_id);
CREATE INDEX idx_repositories_code ON repositories(code);
CREATE INDEX idx_repositories_category ON repositories(category);
```

---

## 7. SDK设计

### 7.1 Python SDK

```python
# api-platform-sdk
"""
API聚合平台 Python SDK
"""

from typing import Any, Dict, List, Optional
from .client import APIClient
from .exceptions import *

__version__ = "1.0.0"

class Platform:
    """API聚合平台主类"""
    
    def __init__(self, api_key: str, secret_key: Optional[str] = None):
        self.client = APIClient(api_key, secret_key)
        self._repositories = None
    
    @property
    def repositories(self) -> Dict[str, Any]:
        """获取仓库字典"""
        if self._repositories is None:
            self._repositories = RepositoryManager(self.client)
        return self._repositories
    
    def psychology_qa(self) -> 'PsychologyQA':
        """心理咨询仓库"""
        return PsychologyQA(self.client)
    
    def stock_query(self) -> 'StockQuery':
        """股票查询仓库"""
        return StockQuery(self.client)
    
    def ai_chat(self) -> 'AIChat':
        """AI对话仓库"""
        return AIChat(self.client)
    
    def list_repositories(self, category: Optional[str] = None) -> List[Dict]:
        """获取仓库列表"""
        return self.client.list_repositories(category)
    
    def get_usage(self) -> Dict:
        """获取使用统计"""
        return self.client.get_usage()


class RepositoryManager:
    """仓库管理器"""
    
    def __init__(self, client: APIClient):
        self.client = client
    
    def __getattr__(self, name: str):
        """动态获取仓库"""
        return DynamicRepository(self.client, name)


class DynamicRepository:
    """动态仓库"""
    
    def __init__(self, client: APIClient, code: str):
        self.client = client
        self.code = code
    
    def invoke(self, **kwargs) -> Dict:
        """调用仓库"""
        return self.client.invoke(self.code, **kwargs)


class PsychologyQA:
    """心理咨询仓库"""
    
    def __init__(self, client: APIClient):
        self.client = client
    
    def ask(self, question: str, context: Optional[Dict] = None) -> Dict:
        """提问"""
        return self.client.invoke("psychology_qa", question=question, context=context)
    
    def chat(self, messages: List[Dict]) -> Dict:
        """对话"""
        return self.client.invoke("psychology_qa", messages=messages)


class StockQuery:
    """股票查询仓库"""
    
    def __init__(self, client: APIClient):
        self.client = client
    
    def get_price(self, symbol: str) -> Dict:
        """获取价格"""
        return self.client.invoke("stock_query", action="price", symbol=symbol)
    
    def get_history(self, symbol: str, days: int = 7) -> Dict:
        """获取历史"""
        return self.client.invoke("stock_query", action="history", symbol=symbol, days=days)


# 使用示例
if __name__ == "__main__":
    # 初始化
    platform = Platform(
        api_key="pk_live_xxx...",
        secret_key="sk_secret_xxx..."
    )
    
    # 方式1: 使用特定仓库
    result = platform.psychology_qa().ask(
        question="我最近总是失眠怎么办？",
        context={"age": 25}
    )
    
    # 方式2: 动态调用
    result = platform.repositories.psychology_qa.invoke(
        question="压力大如何缓解？"
    )
    
    # 方式3: 通用调用
    result = platform.client.invoke("stock_query", action="price", symbol="AAPL")
    
    print(result)
```

### 7.2 JavaScript SDK

```javascript
// api-platform-sdk
/**
 * API聚合平台 JavaScript SDK
 */

class APIClient {
    constructor(apiKey, secretKey, options = {}) {
        this.apiKey = apiKey;
        this.secretKey = secretKey;
        this.baseURL = options.baseURL || 'https://api.platform.com/v1';
        this.timeout = options.timeout || 30000;
    }

    async request(method, endpoint, data) {
        const url = `${this.baseURL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            'X-API-Key': this.apiKey,
        };

        const options = { method, headers };

        if (data && ['POST', 'PUT', 'PATCH'].includes(method)) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);
        return response.json();
    }

    async invoke(repositoryCode, params) {
        return this.request('POST', `/${repositoryCode}/invoke`, params);
    }
}

class Platform {
    constructor(apiKey, secretKey) {
        this.client = new APIClient(apiKey, secretKey);
    }

    // 心理咨询
    psychologyQA() {
        return {
            ask: (question, context) =>
                this.client.invoke('psychology_qa', { question, context }),
            chat: (messages) =>
                this.client.invoke('psychology_qa', { messages }),
        };
    }

    // 股票查询
    stockQuery() {
        return {
            getPrice: (symbol) =>
                this.client.invoke('stock_query', { action: 'price', symbol }),
            getHistory: (symbol, days = 7) =>
                this.client.invoke('stock_query', { action: 'history', symbol, days }),
        };
    }

    // AI对话
    aiChat() {
        return {
            chat: (messages, options = {}) =>
                this.client.invoke('ai_chat', { messages, ...options }),
        };
    }

    // 通用调用
    async invoke(repositoryCode, params) {
        return this.client.invoke(repositoryCode, params);
    }

    // 仓库列表
    async listRepositories(category) {
        const url = category ? `/repositories?category=${category}` : '/repositories';
        return this.client.request('GET', url);
    }

    // 使用统计
    async getUsage() {
        return this.client.request('GET', '/stats');
    }
}

// 使用示例
const platform = new Platform('pk_live_xxx...', 'sk_secret_xxx...');

// 心理咨询
const result = await platform.psychologyQA().ask('我最近总是失眠怎么办？', {
    age: 25,
    gender: 'male'
});

// 股票查询
const price = await platform.stockQuery().getPrice('AAPL');

// AI对话
const response = await platform.aiChat().chat(
    [{ role: 'user', content: '你好' }],
    { temperature: 0.7, max_tokens: 500 }
);

console.log(result);
```

---

## 8. 实现路径

### Phase 1: 基础平台（4周）

| 任务 | 工期 | 说明 |
|------|------|------|
| 项目初始化 | 3天 | FastAPI + React脚手架 |
| 用户认证 | 1周 | 注册/登录/JWT/API Key |
| 仓库管理 | 1周 | CRUD + 状态管理 |
| 通用调用 | 1周 | 路由/转发/响应 |

### Phase 2: 核心功能（4周）

| 任务 | 工期 | 说明 |
|------|------|------|
| 计费系统 | 1周 | 多种计费模式 |
| 配额控制 | 1周 | 限流/熔断 |
| 调用日志 | 1周 | 记录/查询/导出 |
| 开发者门户 | 1周 | 仓库浏览/文档/SDK |

### Phase 3: 插件生态（4周）

| 任务 | 工期 | 说明 |
|------|------|------|
| 插件市场 | 1周 | 仓库展示/搜索 |
| 插件SDK | 1周 | 仓库接入规范 |
| Webhook | 1周 | 事件通知 |
| 开放API | 1周 | 平台自身API |

### Phase 4: 运营功能（2周）

| 任务 | 工期 | 说明 |
|------|------|------|
| 账单系统 | 1周 | 计费/支付/发票 |
| 数据分析 | 1周 | 仪表盘/报表 |
| 告警通知 | 0.5周 | 邮件/短信/Slack |
| 文档完善 | 0.5周 | 帮助中心 |

---

## 9. 技术栈总结

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **后端框架** | FastAPI | 高性能、自动文档 |
| **前端框架** | React + Ant Design Pro | 企业级UI |
| **数据库** | PostgreSQL + Redis | 主存储+缓存 |
| **消息队列** | Kafka | 异步日志 |
| **分析引擎** | ClickHouse | OLAP分析 |
| **缓存层** | Redis | 会话+限流 |
| **网关** | Kong/Nginx | 流量网关 |
| **监控** | Prometheus + Grafana | 指标监控 |
| **日志** | ELK Stack | 日志收集 |
| **容器** | Docker + K8s | 容器化部署 |

---

## 10. 仓库接入示例

### 10.1 心理问答仓库

```python
class PsychologyQARepository(RepositoryAdapter):
    """心理咨询仓库"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.endpoint = config['endpoint']
        self.api_key = config['api_key']
    
    def get_repository_id(self) -> str:
        return "psychology_qa"
    
    def get_repository_name(self) -> str:
        return "心理咨询API"
    
    async def invoke(self, context: RequestContext) -> Dict:
        # 构建请求
        payload = {
            "question": context.body.get("question"),
            "user_context": context.body.get("context", {}),
            "session_id": context.headers.get("X-Session-Id"),
        }
        
        # 调用外部API
        response = await http_post(
            f"{self.endpoint}/v1/chat",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30
        )
        
        return {
            "answer": response['content'],
            "confidence": response.get('confidence', 0.9),
            "session_id": response.get('session_id'),
            "tokens_used": response.get('usage', {}).get('total', 0),
        }
    
    def get_pricing(self) -> PricingConfig:
        return PricingConfig(
            type=PricingType.PER_CALL,
            per_call_price=Decimal("0.05"),
            free_tier=10
        )
```

### 10.2 股票查询仓库

```python
class StockQueryRepository(RepositoryAdapter):
    """股票查询仓库"""
    
    def get_repository_id(self) -> str:
        return "stock_query"
    
    def get_repository_name(self) -> str:
        return "股票查询API"
    
    async def invoke(self, context: RequestContext) -> Dict:
        action = context.body.get("action")
        
        if action == "price":
            return await self._get_price(context.body.get("symbol"))
        elif action == "history":
            return await self._get_history(
                context.body.get("symbol"),
                context.body.get("days", 7)
            )
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _get_price(self, symbol: str) -> Dict:
        # 调用股票API获取实时价格
        ...
        return {"symbol": symbol, "price": 150.25, "change": 2.5}
    
    async def _get_history(self, symbol: str, days: int) -> Dict:
        # 获取历史K线
        ...
        return {"symbol": symbol, "history": [...]}
```

---

## 附录

### A. 仓库分类

| 分类代码 | 分类名称 | 示例仓库 |
|----------|----------|----------|
| consultation | 咨询类 | 心理问答、法律咨询、医疗问诊 |
| finance | 金融类 | 股票查询、汇率转换、支付 |
| ai | AI服务 | 文本生成、图像识别、语音合成 |
| data | 数据类 | 天气查询、地图服务、物流跟踪 |
| utility | 工具类 | 翻译、压缩、PDF转换 |

### B. 错误码

| 错误码 | 说明 | HTTP状态 |
|--------|------|----------|
| 10001 | 仓库不存在 | 404 |
| 10002 | 仓库暂停服务 | 503 |
| 10003 | 仓库配额用完 | 429 |
| 10004 | 无权访问仓库 | 403 |
| 20001 | 认证失败 | 401 |
| 20002 | API Key无效 | 401 |
| 20003 | 权限不足 | 403 |
| 30001 | 请求超时 | 504 |
| 30002 | 仓库响应错误 | 502 |
| 40001 | 参数错误 | 400 |
| 40002 | 请求体过大 | 413 |

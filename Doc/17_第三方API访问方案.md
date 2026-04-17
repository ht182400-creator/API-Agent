# 第三方API访问方案

**文档编号**：THIRD-PARTY-API-API-2026-001  
**版本**：V1.0  
**更新日期**：2026-04-16  
**状态**：初稿

---

## 1. 文档概述

### 1.1 编写目的

本文档详细说明第三方开发者如何通过HTTP请求访问API服务，包括认证授权、请求签名、请求示例、错误处理等完整的技术指南。

### 1.2 适用范围

- 第三方开发者集成
- 学生课程项目调用
- 企业客户API对接
- SDK开发参考

### 1.3 术语定义

| 术语 | 定义 |
|------|------|
| API Key | 客户端标识符，用于身份验证 |
| Secret Key | 密钥，用于签名验证 |
| Signature | 请求签名，防止篡改 |
| Timestamp | 时间戳，防止重放攻击 |
| Nonce | 随机字符串，防止重放攻击 |

---

## 2. 认证授权方式

### 2.1 支持的认证方式

| 方式 | 说明 | 适用场景 | 安全性 |
|------|------|----------|--------|
| **API Key** | 简单密钥认证 | 快速集成、测试环境 | ⭐⭐⭐ |
| **API Key + Secret** | 密钥对认证 | 生产环境 | ⭐⭐⭐⭐ |
| **JWT Token** | 令牌认证 | 需要会话管理 | ⭐⭐⭐⭐⭐ |
| **OAuth 2.0** | 授权协议 | 第三方登录 | ⭐⭐⭐⭐⭐ |

### 2.2 认证流程对比

```
┌─────────────────────────────────────────────────────────────────────┐
│                        认证方式对比                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  方式一: API Key (最简单)                                            │
│  ┌──────────┐          ┌──────────┐          ┌──────────┐           │
│  │  客户端  │ ──────▶ │  Header  │ ──────▶ │   API   │           │
│  │          │  X-API-Key: xxx  │ 验证Key  │          │           │
│  └──────────┘          └──────────┘          └──────────┘           │
│                                                                      │
│  方式二: API Key + Secret (推荐)                                     │
│  ┌──────────┐          ┌──────────┐          ┌──────────┐           │
│  │  客户端  │ ──────▶ │  签名    │ ──────▶ │  验证    │           │
│  │          │ HMAC签名  │ Header   │ 签名验证 │          │           │
│  └──────────┘          └──────────┘          └──────────┘           │
│                                                                      │
│  方式三: JWT Token                                                    │
│  ┌──────────┐          ┌──────────┐          ┌──────────┐           │
│  │  客户端  │ ──────▶ │  登录    │ ──────▶ │  API    │           │
│  │          │ 获取Token │ 返回JWT │ 携带JWT  │          │           │
│  └──────────┘          └──────────┘          └──────────┘           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. 认证方式一：API Key认证

### 3.1 原理说明

API Key是最简单的认证方式，客户端在请求头中携带API Key即可。

### 3.2 请求格式

```http
GET /v1/models HTTP/1.1
Host: api.example.com
X-API-Key: sk-api_a1b2c3d4e5f6...
Content-Type: application/json
```

### 3.3 Python调用示例

```python
import requests

API_KEY = "sk-api_a1b2c3d4e5f6..."
BASE_URL = "https://api.example.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# GET请求
response = requests.get(
    f"{BASE_URL}/v1/models",
    headers=headers
)

print(response.json())
```

### 3.4 JavaScript调用示例

```javascript
const API_KEY = "sk-api_a1b2c3d4e5f6...";
const BASE_URL = "https://api.example.com";

const response = await fetch(`${BASE_URL}/v1/models`, {
    method: 'GET',
    headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
    }
});

const data = await response.json();
console.log(data);
```

### 3.5 Java调用示例

```java
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

// 设置API Key
String apiKey = "sk-api_a1b2c3d4e5f6...";

// 创建请求
HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("https://api.example.com/v1/models"))
    .header("X-API-Key", apiKey)
    .header("Content-Type", "application/json")
    .GET()
    .build();

// 发送请求
HttpClient client = HttpClient.newHttpClient();
HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

System.out.println(response.body());
```

---

## 4. 认证方式二：API Key + HMAC签名（推荐）

### 4.1 原理说明

使用HMAC-SHA256对请求进行签名，防止请求被篡改，提高安全性。

```
签名计算公式：
Signature = HMAC-SHA256(SecretKey, StringToSign)
StringToSign = HTTP_METHOD + "\n" + PATH + "\n" + TIMESTAMP + "\n" + NONCE + "\n" + BODY_HASH
BODY_HASH = SHA256(RequestBody) 或空字符串
```

### 4.2 签名流程图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HMAC签名流程                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. 准备签名材料                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  HTTP_METHOD    = POST                                      │   │
│  │  REQUEST_PATH   = /v1/chat/completions                      │   │
│  │  TIMESTAMP      = 1713206400 (Unix时间戳)                   │   │
│  │  NONCE          = a1b2c3d4e5f6 (随机字符串)                  │   │
│  │  REQUEST_BODY   = {"model":"gpt-3.5-turbo",...}            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  2. 计算BODY_HASH                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  BODY_HASH = SHA256('{"model":"gpt-3.5-turbo",...}')       │   │
│  │           = "a1b2c3d4e5f6..." (64位十六进制)                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  3. 构造签名字符串                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  StringToSign =                                              │   │
│  │    "POST\n"                                                   │   │
│  │    "/v1/chat/completions\n"                                  │   │
│  │    "1713206400\n"                                             │   │
│  │    "a1b2c3d4e5f6\n"                                           │   │
│  │    "a1b2c3d4e5f6..."                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  4. 计算HMAC签名                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Signature = HMAC-SHA256(SecretKey, StringToSign)           │   │
│  │            = "x9f8e7d6c5b4a3..." (64位十六进制)              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 请求头格式

```http
POST /v1/chat/completions HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-API-Key: sk-api_a1b2c3d4e5f6...
X-Timestamp: 1713206400
X-Nonce: a1b2c3d4e5f6
X-Signature: x9f8e7d6c5b4a3...
X-Content-Hash: a1b2c3d4e5f6...
```

### 4.4 Python完整调用示例

```python
import hashlib
import hmac
import time
import secrets
import requests
from typing import Optional, Dict, Any

class APIClient:
    """支持HMAC签名的API客户端"""
    
    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://api.example.com"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip('/')
    
    def _generate_nonce(self) -> str:
        """生成随机字符串"""
        return secrets.token_hex(16)
    
    def _sha256_hash(self, data: str) -> str:
        """计算SHA256哈希"""
        if data:
            return hashlib.sha256(data.encode('utf-8')).hexdigest()
        return hashlib.sha256(b'').hexdigest()
    
    def _create_signature(self, method: str, path: str, timestamp: str, 
                         nonce: str, body_hash: str) -> str:
        """创建HMAC签名"""
        string_to_sign = f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def request(self, method: str, endpoint: str, 
                 data: Optional[Dict[str, Any]] = None,
                 timeout: int = 30) -> Dict[str, Any]:
        """发送API请求"""
        url = f"{self.base_url}{endpoint}"
        timestamp = str(int(time.time()))
        nonce = self._generate_nonce()
        
        # 序列化请求体
        body_str = ""
        body_hash = ""
        if data is not None:
            import json
            body_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            body_hash = self._sha256_hash(body_str)
        
        # 生成签名
        signature = self._create_signature(
            method=method,
            path=endpoint,
            timestamp=timestamp,
            nonce=nonce,
            body_hash=body_hash
        )
        
        # 设置请求头
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'X-API-Key': self.api_key,
            'X-Timestamp': timestamp,
            'X-Nonce': nonce,
            'X-Signature': signature,
            'X-Content-Hash': body_hash,
            'User-Agent': 'APIClient/1.0'
        }
        
        # 发送请求
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, data=body_str, timeout=timeout)
        elif method.upper() == 'PUT':
            response = requests.put(url, headers=headers, data=body_str, timeout=timeout)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        return response.json()
    
    # 便捷方法
    def chat_completions(self, model: str, messages: list, **kwargs):
        """聊天补全"""
        data = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        return self.request('POST', '/v1/chat/completions', data)
    
    def list_models(self):
        """获取模型列表"""
        return self.request('GET', '/v1/models')
    
    def create_embedding(self, input_text: str, model: str = "text-embedding-ada-002"):
        """创建文本嵌入"""
        data = {
            "model": model,
            "input": input_text
        }
        return self.request('POST', '/v1/embeddings', data)


# 使用示例
if __name__ == "__main__":
    client = APIClient(
        api_key="sk-api_a1b2c3d4e5f6...",
        secret_key="sk-secret_x9y8z7w6v5u4..."
    )
    
    # 调用聊天API
    result = client.chat_completions(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "你是一个有帮助的助手"},
            {"role": "user", "content": "你好，请介绍一下你自己"}
        ],
        temperature=0.7,
        max_tokens=500
    )
    
    print(result)
```

### 4.5 JavaScript完整调用示例

```javascript
import crypto from 'crypto';

/**
 * 支持HMAC签名的API客户端
 */
class APIClient {
    constructor(apiKey, secretKey, baseUrl = 'https://api.example.com') {
        this.apiKey = apiKey;
        this.secretKey = secretKey;
        this.baseUrl = baseUrl.replace(/\/$/, '');
    }

    /**
     * 生成随机字符串
     */
    generateNonce() {
        return crypto.randomBytes(16).toString('hex');
    }

    /**
     * 计算SHA256哈希
     */
    sha256Hash(data) {
        if (data) {
            return crypto.createHash('sha256').update(data, 'utf8').digest('hex');
        }
        return crypto.createHash('sha256').update('', 'utf8').digest('hex');
    }

    /**
     * 创建HMAC签名
     */
    createSignature(method, path, timestamp, nonce, bodyHash) {
        const stringToSign = [
            method.toUpperCase(),
            path,
            timestamp,
            nonce,
            bodyHash
        ].join('\n');

        return crypto
            .createHmac('sha256', this.secretKey)
            .update(stringToSign)
            .digest('hex');
    }

    /**
     * 发送API请求
     */
    async request(method, endpoint, data = null, timeout = 30000) {
        const url = `${this.baseUrl}${endpoint}`;
        const timestamp = Math.floor(Date.now() / 1000).toString();
        const nonce = this.generateNonce();

        // 序列化请求体
        let bodyStr = '';
        let bodyHash = '';
        if (data !== null) {
            bodyStr = JSON.stringify(data);
            bodyHash = this.sha256Hash(bodyStr);
        }

        // 生成签名
        const signature = this.createSignature(
            method,
            endpoint,
            timestamp,
            nonce,
            bodyHash
        );

        // 设置请求头
        const headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'X-API-Key': this.apiKey,
            'X-Timestamp': timestamp,
            'X-Nonce': nonce,
            'X-Signature': signature,
            'X-Content-Hash': bodyHash,
            'User-Agent': 'APIClient/1.0'
        };

        // 发送请求
        const options = {
            method: method.toUpperCase(),
            headers,
            timeout
        };

        if (data && ['POST', 'PUT', 'PATCH'].includes(options.method)) {
            options.body = bodyStr;
        }

        const response = await fetch(url, options);
        return response.json();
    }

    /**
     * 聊天补全
     */
    async chatCompletions(model, messages, options = {}) {
        const data = { model, messages, ...options };
        return this.request('POST', '/v1/chat/completions', data);
    }

    /**
     * 获取模型列表
     */
    async listModels() {
        return this.request('GET', '/v1/models');
    }

    /**
     * 创建文本嵌入
     */
    async createEmbedding(input, model = 'text-embedding-ada-002') {
        const data = { model, input };
        return this.request('POST', '/v1/embeddings', data);
    }
}

// 使用示例
const client = new APIClient(
    'sk-api_a1b2c3d4e5f6...',
    'sk-secret_x9y8z7w6v5u4...'
);

// 调用聊天API
const result = await client.chatCompletions(
    'gpt-3.5-turbo',
    [
        { role: 'system', content: '你是一个有帮助的助手' },
        { role: 'user', content: '你好，请介绍一下你自己' }
    ],
    { temperature: 0.7, max_tokens: 500 }
);

console.log(result);
```

### 4.6 Go完整调用示例

```go
package main

import (
    "bytes"
    "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "strconv"
    "time"

    "github.com/google/uuid"
)

type APIClient struct {
    apiKey    string
    secretKey string
    baseURL   string
    client    *http.Client
}

func NewAPIClient(apiKey, secretKey, baseURL string) *APIClient {
    return &APIClient{
        apiKey:    apiKey,
        secretKey: secretKey,
        baseURL:   baseURL,
        client: &http.Client{
            Timeout: 30 * time.Second,
        },
    }
}

func (c *APIClient) generateNonce() string {
    return uuid.New().String()
}

func (c *APIClient) sha256Hash(data string) string {
    if data == "" {
        data = ""
    }
    hash := sha256.Sum256([]byte(data))
    return hex.EncodeToString(hash[:])
}

func (c *APIClient) createSignature(method, path, timestamp, nonce, bodyHash string) string {
    stringToSign := method + "\n" + path + "\n" + timestamp + "\n" + nonce + "\n" + bodyHash

    mac := hmac.New(sha256.New, []byte(c.secretKey))
    mac.Write([]byte(stringToSign))
    return hex.EncodeToString(mac.Sum(nil))
}

func (c *APIClient) Request(method, endpoint string, data interface{}) (map[string]interface{}, error) {
    url := c.baseURL + endpoint
    timestamp := strconv.FormatInt(time.Now().Unix(), 10)
    nonce := c.generateNonce()

    var bodyBytes []byte
    var bodyHash string

    if data != nil {
        bodyBytes, _ = json.Marshal(data)
        bodyHash = c.sha256Hash(string(bodyBytes))
    } else {
        bodyHash = c.sha256Hash("")
    }

    signature := c.createSignature(method, endpoint, timestamp, nonce, bodyHash)

    var req *http.Request
    var err error

    if bodyBytes != nil {
        req, err = http.NewRequest(method, url, bytes.NewBuffer(bodyBytes))
    } else {
        req, err = http.NewRequest(method, url, nil)
    }

    if err != nil {
        return nil, err
    }

    req.Header.Set("Content-Type", "application/json; charset=utf-8")
    req.Header.Set("X-API-Key", c.apiKey)
    req.Header.Set("X-Timestamp", timestamp)
    req.Header.Set("X-Nonce", nonce)
    req.Header.Set("X-Signature", signature)
    req.Header.Set("X-Content-Hash", bodyHash)
    req.Header.Set("User-Agent", "APIClient/1.0")

    resp, err := c.client.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    body, _ := io.ReadAll(resp.Body)

    var result map[string]interface{}
    json.Unmarshal(body, &result)

    return result, nil
}

func (c *APIClient) ChatCompletions(model string, messages []map[string]string, options map[string]interface{}) (map[string]interface{}, error) {
    data := map[string]interface{}{
        "model":    model,
        "messages": messages,
    }
    for k, v := range options {
        data[k] = v
    }
    return c.Request("POST", "/v1/chat/completions", data)
}

func (c *APIClient) ListModels() (map[string]interface{}, error) {
    return c.Request("GET", "/v1/models", nil)
}

func main() {
    client := NewAPIClient(
        "sk-api_a1b2c3d4e5f6...",
        "sk-secret_x9y8z7w6v5u4...",
        "https://api.example.com",
    )

    result, err := client.ChatCompletions(
        "gpt-3.5-turbo",
        []map[string]string{
            {"role": "system", "content": "你是一个有帮助的助手"},
            {"role": "user", "content": "你好，请介绍一下你自己"},
        },
        map[string]interface{}{
            "temperature": 0.7,
            "max_tokens":  500,
        },
    )

    if err != nil {
        fmt.Println("Error:", err)
        return
    }

    fmt.Printf("%+v\n", result)
}
```

---

## 5. 认证方式三：JWT Token认证

### 5.1 原理说明

JWT（JSON Web Token）是一种自包含的令牌格式，可以存储用户身份信息和权限。

### 5.2 认证流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                        JWT认证流程                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   1. 获取Token                                                        │
│   ┌──────────┐      ┌──────────┐      ┌──────────┐                │
│   │  客户端   │ ───▶ │  登录API  │ ───▶ │  返回JWT │                │
│   │          │ email │ /v1/auth │ token │  令牌   │                │
│   │          │ pass  │  /login  │       │          │                │
│   └──────────┘      └──────────┘      └──────────┘                │
│                                                                      │
│   2. 使用Token                                                        │
│   ┌──────────┐      ┌──────────┐      ┌──────────┐                │
│   │  客户端   │ ───▶ │  API验证  │ ───▶ │  处理请求 │                │
│   │          │ JWT  │  中间件   │ 解密  │          │                │
│   │          │ Bearer│          │ 验证  │          │                │
│   └──────────┘      └──────────┘      └──────────┘                │
│                                                                      │
│   3. 刷新Token                                                        │
│   ┌──────────┐      ┌──────────┐      ┌──────────┐                │
│   │  客户端   │ ───▶ │ 刷新Token │ ───▶ │  返回新JWT│                │
│   │          │ JWT  │ /v1/auth │       │  令牌   │                │
│   │          │      │ /refresh │       │          │                │
│   └──────────┘      └──────────┘      └──────────┘                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.3 JWT Token结构

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzEyMyIsImVtYWlsIjoiYUBleGFtcGxlLmNvbSIsImFwaV9rZXlzIjpbInNrLWFwaV9hMWIyYzNkNCIsInNrLWFwaV94ezN5NHoiXX0sImV4cCI6MTcxMzIwNjQwMH0.dGhpcyBpcyBhIHNhbXBsZSBzaWduYXR1cmU=

┌─────────────────────────────────────────────────────────────────────┐
│                        JWT Token 组成                                │
├──────────────────────┬──────────────────────┬──────────────────────┤
│     Header           │       Payload        │      Signature      │
│   (头部)             │      (载荷)          │      (签名)          │
├──────────────────────┼──────────────────────┼──────────────────────┤
│ {                   │ {                    │                      │
│   "alg": "HS256",  │   "sub": "user_123", │   HMAC-SHA256(       │
│   "typ": "JWT"     │   "email": "a@...", │     secret,          │
│ }                   │   "api_keys": [...],│     header.payload   │
│                      │   "exp": 1713206400,│   )                  │
│                      │   "iat": 1713202800 │                      │
│                      │ }                   │                      │
└──────────────────────┴──────────────────────┴──────────────────────┘
```

### 5.4 请求格式

```http
POST /v1/chat/completions HTTP/1.1
Host: api.example.com
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 5.5 Python调用示例

```python
import requests

# 1. 登录获取Token
BASE_URL = "https://api.example.com"

login_response = requests.post(
    f"{BASE_URL}/v1/auth/login",
    json={
        "email": "user@example.com",
        "password": "your_password"
    }
)

token = login_response.json()["access_token"]

# 2. 使用Token调用API
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

response = requests.post(
    f"{BASE_URL}/v1/chat/completions",
    headers=headers,
    json={
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Hello!"}
        ]
    }
)

print(response.json())

# 3. 刷新Token
refresh_response = requests.post(
    f"{BASE_URL}/v1/auth/refresh",
    headers={"Authorization": f"Bearer {token}"}
)

new_token = refresh_response.json()["access_token"]
```

---

## 6. API Key管理接口

### 6.1 创建API Key

```http
POST /v1/api-keys HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
    "name": "Production Key",
    "permissions": ["chat:create", "embeddings:create"],
    "quota": 10000,
    "expires_days": 365
}
```

**响应示例**

```json
{
    "id": "key_abc123",
    "name": "Production Key",
    "api_key": "sk-api_a1b2c3d4e5f6...",
    "secret_key": "sk-secret_x9y8z7w6v5u4...",
    "permissions": ["chat:create", "embeddings:create"],
    "quota": 10000,
    "used": 0,
    "status": "active",
    "expires_at": "2027-04-16T00:00:00Z",
    "created_at": "2026-04-16T10:00:00Z"
}
```

> **重要提示**：创建API Key时，`api_key`和`secret_key`仅显示一次，请妥善保存！

### 6.2 列出API Keys

```http
GET /v1/api-keys HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**响应示例**

```json
{
    "data": [
        {
            "id": "key_abc123",
            "name": "Production Key",
            "api_key_prefix": "sk-api_a1b2...",
            "permissions": ["chat:create", "embeddings:create"],
            "quota": 10000,
            "used": 1523,
            "status": "active",
            "expires_at": "2027-04-16T00:00:00Z",
            "created_at": "2026-04-16T10:00:00Z"
        }
    ],
    "pagination": {
        "page": 1,
        "page_size": 10,
        "total": 1,
        "total_pages": 1
    }
}
```

### 6.3 删除API Key

```http
DELETE /v1/api-keys/{key_id} HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 7. 核心API接口

### 7.1 聊天补全

```http
POST /v1/chat/completions HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
    "model": "gpt-3.5-turbo",
    "messages": [
        {
            "role": "system",
            "content": "你是一个有帮助的AI助手。"
        },
        {
            "role": "user",
            "content": "请介绍一下Python的优点。"
        }
    ],
    "temperature": 0.7,
    "max_tokens": 1000,
    "stream": false
}
```

**响应示例**

```json
{
    "id": "chatcmpl_abc123",
    "object": "chat.completion",
    "created": 1713206400,
    "model": "gpt-3.5-turbo",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Python是一种高级编程语言，具有以下优点：\n\n1. **易学易用**：语法简洁，适合初学者...\n2. **丰富的库**：拥有庞大的标准库和第三方库...\n3. **广泛应用**：Web开发、数据科学、AI等领域..."
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 50,
        "completion_tokens": 200,
        "total_tokens": 250
    }
}
```

### 7.2 文本嵌入

```http
POST /v1/embeddings HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
    "model": "text-embedding-ada-002",
    "input": "The quick brown fox jumps over the lazy dog"
}
```

**响应示例**

```json
{
    "object": "list",
    "data": [
        {
            "object": "embedding",
            "embedding": [
                0.0023064255,
                -0.009327292,
                ... (1536 dimensions)
            ],
            "index": 0
        }
    ],
    "model": "text-embedding-ada-002",
    "usage": {
        "prompt_tokens": 8,
        "total_tokens": 8
    }
}
```

### 7.3 模型列表

```http
GET /v1/models HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**响应示例**

```json
{
    "object": "list",
    "data": [
        {
            "id": "gpt-3.5-turbo",
            "object": "model",
            "owned_by": "openai",
            "permission": ["use:*"],
            "context_window": 16385,
            "type": "chat"
        },
        {
            "id": "gpt-4",
            "object": "model",
            "owned_by": "openai",
            "permission": ["use:*"],
            "context_window": 8192,
            "type": "chat"
        }
    ]
}
```

---

## 8. 错误处理

### 8.1 错误码定义

| HTTP状态码 | 错误码 | 说明 |
|------------|--------|------|
| 400 | `invalid_request` | 请求格式错误 |
| 401 | `unauthorized` | 未授权或Token无效 |
| 403 | `forbidden` | 无权限访问 |
| 404 | `not_found` | 资源不存在 |
| 422 | `validation_error` | 参数验证失败 |
| 429 | `rate_limit_exceeded` | 请求过于频繁 |
| 500 | `internal_error` | 服务器内部错误 |
| 503 | `service_unavailable` | 服务不可用 |

### 8.2 错误响应格式

```json
{
    "error": {
        "code": "rate_limit_exceeded",
        "message": "请求过于频繁，请稍后再试",
        "details": {
            "retry_after": 60,
            "limit": 100,
            "remaining": 0,
            "reset_at": "2026-04-16T10:01:00Z"
        },
        "request_id": "req_abc123xyz"
    }
}
```

### 8.3 Python错误处理示例

```python
import requests
from typing import Optional

class APIError(Exception):
    """API异常基类"""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

class RateLimitError(APIError):
    """限流异常"""
    def __init__(self, retry_after: int, message: str = "请求过于频繁"):
        super().__init__("rate_limit_exceeded", message, {"retry_after": retry_after})
        self.retry_after = retry_after

class AuthenticationError(APIError):
    """认证异常"""
    def __init__(self, message: str = "认证失败"):
        super().__init__("unauthorized", message)

def call_api_with_retry(client: APIClient, max_retries: int = 3):
    """带重试的API调用"""
    for attempt in range(max_retries):
        try:
            response = client.chat_completions(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}]
            )
            return response
        
        except RateLimitError as e:
            if attempt < max_retries - 1:
                import time
                print(f"限流，等待 {e.retry_after} 秒后重试...")
                time.sleep(e.retry_after)
            else:
                raise
        
        except AuthenticationError as e:
            raise
        
        except APIError as e:
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise

# 使用
try:
    result = call_api_with_retry(client)
except RateLimitError:
    print("达到最大重试次数，请稍后再试")
except AuthenticationError:
    print("认证失败，请检查API Key")
except APIError as e:
    print(f"API错误: {e.code} - {e.message}")
```

---

## 9. 限流与配额

### 9.1 限流说明

| 限流维度 | 限制值 | 说明 |
|----------|--------|------|
| 每分钟请求数 | 60 RPM | 每分钟最多60次请求 |
| 每小时请求数 | 1000 RPH | 每小时最多1000次请求 |
| 每秒请求数 | 10 RPS | 每秒最多10次请求（突发） |
| 单次请求体大小 | 10 MB | 最大请求体 |
| 单次响应体大小 | 100 MB | 最大响应体 |

### 9.2 限流响应头

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1713206460
X-RateLimit-Policy: 60;w=60
Retry-After: 45
```

### 9.3 配额说明

| 配额类型 | 说明 |
|----------|------|
| 日配额 | 每天可用调用次数 |
| 月配额 | 每月可用调用次数 |
| 总量配额 | 累计可用调用次数 |

### 9.4 查询配额使用情况

```http
GET /v1/account/usage HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**响应示例**

```json
{
    "object": "account_usage",
    "daily_usage": {
        "date": "2026-04-16",
        "total_calls": 523,
        "total_tokens": 125000,
        "quota": 10000,
        "remaining": 9477
    },
    "monthly_usage": {
        "month": "2026-04",
        "total_calls": 15230,
        "quota": 300000,
        "remaining": 284770
    },
    "api_keys": [
        {
            "id": "key_abc123",
            "name": "Production",
            "used": 10523,
            "quota": 100000,
            "remaining": 89477
        }
    ]
}
```

---

## 10. 日志查询API

### 10.1 查询调用日志

```http
GET /v1/logs?start_time=2026-04-01&end_time=2026-04-16&page=1&page_size=100 HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**响应示例**

```json
{
    "data": [
        {
            "id": "log_abc123",
            "timestamp": "2026-04-16T10:30:00Z",
            "api_key_id": "key_abc123",
            "api_key_prefix": "sk-api_a1b2...",
            "endpoint": "/v1/chat/completions",
            "method": "POST",
            "status_code": 200,
            "latency_ms": 250,
            "tokens_used": 150,
            "ip_address": "192.168.1.1",
            "user_agent": "APIClient/1.0"
        }
    ],
    "pagination": {
        "page": 1,
        "page_size": 100,
        "total": 1523,
        "total_pages": 16
    }
}
```

### 10.2 查询参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_time | string | 否 | 开始时间 (ISO8601) |
| end_time | string | 否 | 结束时间 (ISO8601) |
| event_type | string | 否 | 事件类型 (LOGIN/API_CALL/ERROR) |
| api_key_id | string | 否 | API Key ID |
| ip_address | string | 否 | IP地址 |
| status | string | 否 | SUCCESS/FAILED |
| page | integer | 否 | 页码 (默认1) |
| page_size | integer | 否 | 每页数量 (默认100, 最大1000) |

---

## 11. SDK下载与使用

### 11.1 官方SDK列表

| 语言 | 包管理器 | 安装命令 | 仓库地址 |
|------|----------|----------|----------|
| Python | pip | `pip install api-sdk` | github.com/example/api-sdk-python |
| JavaScript | npm | `npm install api-sdk` | github.com/example/api-sdk-js |
| Java | Maven | 见Maven Central | Maven Central |
| Go | go mod | `go get github.com/example/api-sdk-go` | github.com/example/api-sdk-go |
| C# | NuGet | `dotnet add package ApiSdk` | NuGet Gallery |

### 11.2 Python SDK使用

```bash
# 安装
pip install api-sdk
```

```python
from api_sdk import APIClient

# 初始化客户端
client = APIClient(
    api_key="sk-api_a1b2c3d4e5f6...",
    secret_key="sk-secret_x9y8z7w6v5u4..."
)

# 聊天补全
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": "Hello, world!"}
    ],
    temperature=0.7
)

print(response.choices[0].message.content)
```

### 11.3 JavaScript SDK使用

```bash
# 安装
npm install api-sdk
```

```javascript
import { APIClient } from 'api-sdk';

// 初始化客户端
const client = new APIClient({
    apiKey: 'sk-api_a1b2c3d4e5f6...',
    secretKey: 'sk-secret_x9y8z7w6v5u4...'
});

// 聊天补全
const response = await client.chat.completions.create({
    model: 'gpt-3.5-turbo',
    messages: [
        { role: 'user', content: 'Hello, world!' }
    ],
    temperature: 0.7
});

console.log(response.choices[0].message.content);
```

---

## 12. 最佳实践

### 12.1 安全建议

| 建议 | 说明 |
|------|------|
| 使用HTTPS | 所有请求必须使用HTTPS |
| 保护Secret Key | Secret Key只在服务端使用，不要暴露在前端 |
| 轮换Key | 定期更换API Key |
| 限制权限 | 按需分配API Key权限 |
| 监控使用 | 定期检查API使用情况 |

### 12.2 性能建议

| 建议 | 说明 |
|------|------|
| 使用连接池 | 复用HTTP连接 |
| 重试机制 | 实现指数退避重试 |
| 批量处理 | 尽量批量调用 |
| 异步处理 | 非实时需求使用异步 |

### 12.3 错误处理建议

```python
import time
import logging
from api_sdk import APIClient, RateLimitError, APIError

logger = logging.getLogger(__name__)

def robust_call(client: APIClient, max_retries: int = 3):
    """健壮的API调用"""
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}]
            )
        except RateLimitError as e:
            wait_time = e.retry_after or (2 ** attempt)
            logger.warning(f"限流，等待 {wait_time} 秒...")
            time.sleep(wait_time)
        except APIError as e:
            if e.code in ["internal_error", "server_error"]:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            raise
    raise Exception("达到最大重试次数")
```

---

## 附录

### A. 完整请求示例

```python
import requests
import hashlib
import hmac
import time
import secrets
import json

API_KEY = "sk-api_a1b2c3d4e5f6..."
SECRET_KEY = "sk-secret_x9y8z7w6v5u4..."
BASE_URL = "https://api.example.com"

def make_request(method, endpoint, data=None):
    url = f"{BASE_URL}{endpoint}"
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    
    body_str = json.dumps(data, separators=(',', ':')) if data else ""
    body_hash = hashlib.sha256(body_str.encode()).hexdigest()
    
    string_to_sign = f"{method.upper()}\n{endpoint}\n{timestamp}\n{nonce}\n{body_hash}"
    signature = hmac.new(
        SECRET_KEY.encode(),
        string_to_sign.encode(),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
        "X-Content-Hash": body_hash
    }
    
    if method.upper() == "GET":
        return requests.get(url, headers=headers).json()
    elif method.upper() == "POST":
        return requests.post(url, headers=headers, data=body_str).json()

# 调用示例
result = make_request(
    "POST",
    "/v1/chat/completions",
    {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Hello"}]
    }
)
print(result)
```

### B. cURL示例

```bash
# 获取Token
curl -X POST https://api.example.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"your_password"}'

# 使用Token调用API
curl -X POST https://api.example.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user","content": "Hello"}]
  }'

# 使用API Key + 签名
curl -X POST https://api.example.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-api_a1b2c3d4e5f6..." \
  -H "X-Timestamp: 1713206400" \
  -H "X-Nonce: random_nonce" \
  -H "X-Signature: computed_signature" \
  -H "X-Content-Hash: body_hash" \
  -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"Hello"}]}'
```

### C. Postman配置

在Postman中配置API Key认证：

1. 选择 Authorization 类型为 **API Key**
2. Key 填写 `X-API-Key`
3. Value 填写你的 API Key
4. Add to 选择 **Header**

### D. 参考链接

| 资源 | 链接 |
|------|------|
| API文档 | https://api.example.com/docs |
| Swagger UI | https://api.example.com/swagger |
| 开发者门户 | https://developer.example.com |
| 技术支持 | support@example.com |

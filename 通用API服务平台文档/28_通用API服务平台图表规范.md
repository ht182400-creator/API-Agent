# 通用API服务平台 - 图表规范

## 文档信息

| 属性 | 内容 |
|------|------|
| **文档编号** | DIAGRAM-PLATFORM-2026-001 |
| **版本** | V1.0 |
| **日期** | 2026-04-16 |

---

## 1. 图表规范概述

### 1.1 图表工具选择

本项目采用 **Mermaid** 作为标准图表绘制工具，原因如下：

| 优势 | 说明 |
|------|------|
| **广泛支持** | GitHub、GitLab、VS Code、Notion等主流平台原生支持 |
| **文本编辑** | 纯文本格式，便于版本控制和协作 |
| **实时预览** | 大多数Markdown编辑器支持实时渲染 |
| **丰富类型** | 支持流程图、时序图、类图、ER图等 |

### 1.2 Mermaid图表类型对照表

| 图表类型 | Mermaid语法 | 适用场景 |
|----------|------------|----------|
| **流程图** | `graph TD/BT/LR/RL` | 业务流程、数据流向 |
| **时序图** | `sequenceDiagram` | API调用时序、交互流程 |
| **类图** | `classDiagram` | 数据模型、接口定义 |
| **ER图** | `erDiagram` | 数据库实体关系 |
| **状态图** | `stateDiagram` | 状态流转、生命周期 |
| **甘特图** | `gantt` | 项目计划、里程碑 |

---

## 2. 标准图表模板

### 2.1 平台整体架构图

```mermaid
graph TB
    subgraph Client["客户端层"]
        Developer[开发者]
        Owner[仓库所有者]
        Admin[管理员]
    end

    subgraph Gateway["接入层"]
        APIGateway[API网关<br/>APISIX]
        WebSocketGW[WebSocket网关]
        AdminAPI[Admin API]
    end

    subgraph Core["核心服务层"]
        AuthService[认证服务]
        RepoService[仓库服务]
        BillingService[计费服务]
        UserService[用户服务]
        LogService[日志服务]
        NotifyService[通知服务]
    end

    subgraph Adapter["仓库适配层"]
        HTTPAdapter[HTTP适配器]
        GRPCAdapter[gRPC适配器]
        WSAdapter[WebSocket适配器]
    end

    subgraph Data["数据层"]
        PostgreSQL[(PostgreSQL)]
        Redis[(Redis)]
        Kafka[(Kafka)]
    end

    Developer -->|API调用| APIGateway
    Owner -->|管理操作| AdminAPI
    Admin -->|运维管理| AdminAPI

    APIGateway --> AuthService
    APIGateway --> RepoService
    APIGateway --> BillingService

    AuthService --> Redis
    RepoService --> PostgreSQL
    BillingService --> PostgreSQL
    LogService --> Kafka

    RepoService --> HTTPAdapter
    RepoService --> GRPCAdapter
    RepoService --> WSAdapter

    HTTPAdapter -->|内部仓库| InternalA[内部仓库A]
    GRPCAdapter -->|外部仓库| ExternalB[外部仓库B]
    WSAdapter -->|外部仓库| ExternalC[外部仓库C]

    style Gateway fill:#e1f5ff,stroke:#01579b
    style Core fill:#fff3e0,stroke:#e65100
    style Adapter fill:#e8f5e9,stroke:#2e7d32
    style Data fill:#f3e5f5,stroke:#7b1fa2
```

### 2.2 内部仓库接入架构图

```mermaid
graph LR
    subgraph Client["开发者"]
        APIRequest[API请求]
    end

    subgraph Gateway["API网关"]
        Auth[认证模块]
        Route[路由模块]
        RateLimit[限流模块]
    end

    subgraph Direct["直连调用"]
        LB[负载均衡器]
        InternalRepo[内部仓库<br/>REST API]
    end

    APIRequest -->|HTTPS| Auth
    Auth -->|认证通过| Route
    Route -->|路由分发| RateLimit
    RateLimit -->|转发请求| LB
    LB -->|内网调用| InternalRepo

    style Gateway fill:#e1f5ff,stroke:#01579b
    style Direct fill:#e8f5e9,stroke:#2e7d32
```

### 2.3 外部仓库接入架构图

```mermaid
graph TB
    subgraph Client["开发者"]
        Request[API请求]
    end

    subgraph Gateway["API网关"]
        Auth[认证模块]
        Billing[计费模块]
    end

    subgraph AdapterLayer["适配器层"]
        AdapterMgr[适配器管理器]
        HTTPAdapter[HTTP适配器]
        GRPCAdapter[gRPC适配器]
        WSAdapter[WebSocket适配器]
    end

    subgraph External["外部仓库"]
        RepoA[外部仓库A<br/>REST]
        RepoB[外部仓库B<br/>gRPC]
        RepoC[外部仓库C<br/>WebSocket]
    end

    Request -->|HTTPS| Auth
    Auth -->|认证通过| Billing
    Billing -->|计费检查| AdapterMgr
    AdapterMgr --> HTTPAdapter
    AdapterMgr --> GRPCAdapter
    AdapterMgr --> WSAdapter

    HTTPAdapter --> RepoA
    GRPCAdapter --> RepoB
    WSAdapter --> RepoC

    style Gateway fill:#e1f5ff,stroke:#01579b
    style AdapterLayer fill:#fff3e0,stroke:#e65100
    style External fill:#ffebee,stroke:#c62828
```

### 2.4 适配器架构图

```mermaid
graph TB
    subgraph Platform["平台网关"]
        PlatformReq[平台请求]
        PlatformResp[平台响应]
    end

    subgraph Adapter["适配器层"]
        ReqTransform[请求转换]
        RespTransform[响应转换]
        ErrorHandle[错误处理]
        Retry[重试策略]
    end

    subgraph Vendor["外部仓库"]
        VendorReq[仓库请求]
        VendorResp[仓库响应]
    end

    PlatformReq --> ReqTransform
    ReqTransform -->|协议转换| VendorReq
    VendorReq --> Vendor[外部仓库]
    Vendor --> VendorResp
    VendorResp --> RespTransform
    RespTransform -->|数据映射| PlatformResp

    VendorResp -.->|异常| ErrorHandle
    ErrorHandle -.->|可重试| Retry
    Retry -.->|重试| ReqTransform

    style Adapter fill:#fff3e0,stroke:#e65100
    style Vendor fill:#ffebee,stroke:#c62828
```

### 2.5 统一认证流程图

```mermaid
sequenceDiagram
    participant Dev as 开发者
    participant GW as API网关
    participant Auth as 认证服务
    participant DB as 数据库

    Dev->>GW: API请求 + API Key
    GW->>Auth: 验证请求
    Auth->>DB: 查询Key信息
    DB-->>Auth: Key详情
    Auth->>Auth: 检查Key状态
    Auth->>Auth: 检查配额
    alt 认证成功 & 配额充足
        Auth-->>GW: 认证通过
        GW->>GW: 处理请求
        GW-->>Dev: 返回响应
    else 认证失败
        Auth-->>GW: 401 未授权
        GW-->>Dev: 401 认证失败
    else 配额不足
        Auth-->>GW: 429 配额超限
        GW-->>Dev: 429 配额不足
    end
```

### 2.6 计费流程图

```mermaid
graph TD
    Start[API调用请求] --> CheckQuota{配额检查}
    CheckQuota -->|有配额| Execute[执行调用]
    CheckQuota -->|无配额| Reject[返回429<br/>配额超限]
    
    Execute --> Record[记录用量]
    Record --> Calc[计算费用]
    Calc --> Deduct[扣减配额]
    
    Deduct -->|成功| Response[返回响应]
    Deduct -->|失败| Rollback[回滚操作]
    Rollback --> Error[返回错误]
    
    Response --> Complete[调用完成]

    style CheckQuota fill:#fff3e0,stroke:#e65100
    style Reject fill:#ffebee,stroke:#c62828
    style Execute fill:#e8f5e9,stroke:#2e7d32
```

### 2.7 数据库ER图

```mermaid
erDiagram
    USERS ||--o{ API_KEYS : has
    USERS ||--o{ REPOSITORIES : owns
    USERS ||--o{ BILLS : has
    USERS ||--o{ ACCOUNTS : has
    
    API_KEYS ||--o{ QUOTAS : has
    API_KEYS ||--o{ CALL_LOGS : generates
    
    REPOSITORIES ||--o{ REPO_CONFIGS : has
    REPOSITORIES ||--o{ REPO_PRICING : has
    REPOSITORIES ||--o{ REPO_STATS : has
    REPOSITORIES ||--o{ CALL_LOGS : generates
    
    REPOSITORIES }o--o{ ADAPTERS : uses
    
    USERS {
        uuid id PK
        string email UK
        string password_hash
        string user_type
        string user_status
        timestamp created_at
    }
    
    API_KEYS {
        uuid id PK
        uuid user_id FK
        string key_hash UK
        string key_name
        int rate_limit_rpm
        string status
        timestamp created_at
    }
    
    REPOSITORIES {
        uuid id PK
        uuid owner_id FK
        string name
        string repo_type
        string protocol
        string status
        timestamp created_at
    }
    
    ADAPTERS {
        uuid id PK
        string name
        string adapter_type
        string version
        jsonb config_schema
        string status
    }
    
    BILLS {
        bigint id PK
        uuid user_id FK
        string bill_no UK
        decimal amount
        string bill_type
        string status
        timestamp created_at
    }
```

### 2.8 仓库接入流程图

```mermaid
graph TD
    subgraph Internal["内部仓库接入"]
        I1[Step 1: 仓库开发] --> I2[Step 2: 平台注册]
        I2 --> I3[Step 3: 上线发布]
        I3 --> I4[仓库上线]
    end

    subgraph External["外部仓库接入"]
        E1[Step 1: 入驻申请] --> E2[Step 2: 平台审核]
        E2 --> E3[Step 3: 适配器开发]
        E3 --> E4[Step 4: API映射]
        E4 --> E5[Step 5: 定价配置]
        E5 --> E6[Step 6: 上线发布]
        E6 --> E7[仓库上线]
    end

    style Internal fill:#e8f5e9,stroke:#2e7d32
    style External fill:#fff3e0,stroke:#e65100
```

### 2.9 客户端需求矩阵图

```mermaid
graph TB
    subgraph Developer["开发者功能"]
        D1[注册登录]
        D2[Key管理]
        D3[仓库市场]
        D4[费用中心]
        D5[日志查询]
        D6[API调用]
    end

    subgraph Owner["仓库所有者功能"]
        O1[入驻申请]
        O2[仓库配置]
        O3[适配器配置]
        O4[API管理]
        O5[收益管理]
        O6[数据统计]
    end

    subgraph Admin["管理员功能"]
        A1[仓库审核]
        A2[监控面板]
        A3[用户管理]
        A4[计费配置]
    end

    D1:::need --> D6:::noneed
    O1:::need --> O6:::need
    A1:::need --> A4:::need

    classDef need fill:#e1f5ff,stroke:#01579b
    classDef noneed fill:#f5f5f5,stroke:#9e9e9e
```

### 2.10 部署架构图

```mermaid
graph TB
    subgraph LB["负载均衡层"]
        SLB[SLB负载均衡]
    end

    subgraph Gateway["网关集群"]
        GW1[API Gateway 1]
        GW2[API Gateway 2]
        GW3[API Gateway 3]
    end

    subgraph Service["服务集群"]
        AuthS[认证服务]
        RepoS[仓库服务]
        BillingS[计费服务]
        UserS[用户服务]
    end

    subgraph Data["数据层"]
        PG[(PostgreSQL<br/>主从)]
        RD[(Redis<br/>集群)]
        KK[(Kafka)]
    end

    subgraph Repo["仓库层"]
        Internal[内部仓库]
        Adapter1[适配器1]
        Adapter2[适配器2]
        External[外部仓库]
    end

    SLB --> GW1
    SLB --> GW2
    SLB --> GW3

    GW1 --> AuthS
    GW2 --> RepoS
    GW3 --> BillingS

    AuthS --> UserS
    RepoS --> Adapter1
    RepoS --> Adapter2

    AuthS --> PG
    RepoS --> PG
    BillingS --> RD

    Adapter1 --> Internal
    Adapter2 --> External

    style LB fill:#e1f5ff,stroke:#01579b
    style Gateway fill:#fff3e0,stroke:#e65100
    style Service fill:#e8f5e9,stroke:#2e7d32
    style Data fill:#f3e5f5,stroke:#7b1fa2
```

---

## 3. 图表渲染环境配置

### 3.1 VS Code 配置

在 `.vscode/settings.json` 中添加：

```json
{
  "mermaid.diagrams": [
    "flowchart",
    "sequence",
    "class",
    "state",
    "er",
    "gantt"
  ],
  "markdown.mermaid.enable": true
}
```

安装扩展：**Markdown Preview Mermaid Support**

### 3.2 GitHub 配置

GitHub 原生支持 Mermaid，无需额外配置。

### 3.3 独立渲染HTML

如需生成独立图片，可使用以下方式：

```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
</head>
<body>
    <div class="mermaid">
        graph TD
        A[Start] --> B[End]
    </div>
    <script>mermaid.initialize({startOnLoad:true});</script>
</body>
</html>
```

---

## 4. 图表配色规范

### 4.1 标准化配色方案

| 用途 | 填充色 | 边框色 | 示例 |
|------|--------|--------|------|
| **接入层** | `#e1f5ff` | `#01579b` | API网关 |
| **核心服务** | `#fff3e0` | `#e65100` | 业务服务 |
| **适配器层** | `#e8f5e9` | `#2e7d32` | 协议转换 |
| **数据层** | `#f3e5f5` | `#7b1fa2` | 数据库 |
| **客户端** | `#fce4ec` | `#c2185b` | 用户端 |
| **外部依赖** | `#ffebee` | `#c62828` | 外部服务 |

### 4.2 状态配色

| 状态 | 填充色 | 边框色 |
|------|--------|--------|
| **成功** | `#c8e6c9` | `#388e3c` |
| **警告** | `#fff9c4` | `#f9a825` |
| **错误** | `#ffcdd2` | `#d32f2f` |
| **信息** | `#bbdefb` | `#1976d2` |

---

## 5. 附录

### 5.1 Mermaid 语法速查

```mermaid
%% 流程图方向
graph TD/BT/LR/RL

%% 节点形状
A[矩形]
B(圆角矩形)
C([体育场形])
D[[子程序]]
E((圆形))
F{菱形}

%% 连接线
A --> B    %% 箭头实线
A --- B    %% 无箭头实线
A -.-> B   %% 箭头虚线
A -.-> B   %% 无箭头虚线
A ==> B    %% 加粗箭头

%% 样式
style A fill:#f9f,stroke:#333,stroke-width:4px
class A need
```

### 5.2 参考资源

- [Mermaid 官方文档](https://mermaid.js.org/)
- [Mermaid Live Editor](https://mermaid.live/)
- [GitHub Mermaid 支持](https://github.blog/2022-02-14-include-diagrams-markdown-files-mermaid/)

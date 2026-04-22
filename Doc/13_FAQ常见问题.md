# API服务改造项目 - 常见问题解答（FAQ）

## 文档控制

| 项目 | 内容 |
|------|------|
| 文档编号 | FAQ-API-2026-001 |
| 版本号 | V2.2 |
| 创建日期 | 2026-04-16 |
| 更新日期 | 2026-04-22 |

---

## FAQ 汇总列表

> 新增 FAQ 时，请在此处添加条目，并更新关联的详细文档

### 第一部分：基础问题（第1-18问）

| 序号 | 问题标题 | 关键词 | 优先级 | 状态 |
|:----:|----------|--------|:------:|:----:|
| Q1 | 如何搭建本地开发环境？ | 开发环境、Docker、Python | P0 | ✅ |
| Q2 | API响应格式是什么？ | API、响应格式、JSON | P0 | ✅ |
| Q3 | 如何添加新的API接口？ | API、路由、FastAPI | P1 | ✅ |
| Q4 | 如何处理数据库迁移？ | 数据库、Alembic、迁移 | P1 | ✅ |
| Q5 | 日志如何配置和使用？ | 日志、logging、配置 | P1 | ✅ |
| Q6 | 如何进行一键部署？ | 部署、Docker、自动化 | P1 | ✅ |
| Q7 | 部署后服务无法启动怎么办？ | 部署、故障、排查 | P1 | ✅ |
| Q8 | 如何查看和监控服务状态？ | 监控、服务状态、Docker | P1 | ✅ |
| Q9 | 如何备份和恢复数据？ | 备份、恢复、数据库 | P1 | ✅ |
| Q10 | 如何升级到新版本？ | 升级、版本、更新 | P1 | ✅ |
| Q11 | API Key如何使用？ | API Key、认证、签名 | P0 | ✅ |
| Q12 | Token过期了怎么办？ | Token、刷新、过期 | P0 | ✅ |
| Q13 | 如何申请更高限流配额？ | 限流、配额、申请 | P2 | ✅ |
| Q14 | 如何创建和管理租户？ | 租户、管理、API | P1 | ✅ |
| Q15 | 如何查看API调用统计？ | 统计、调用量、报表 | P1 | ✅ |
| Q16 | Swagger文档在哪里？ | Swagger、API文档 | P1 | ✅ |
| Q17 | 如何获取技术支持？ | 技术支持、工单、联系 | P2 | ✅ |
| Q18 | API响应时间慢怎么办？ | 性能、优化、响应时间 | P1 | ✅ |

### 第二部分：部署环境问题（第19-25问）

| 序号 | 问题标题 | 关键词 | 优先级 | 状态 |
|:----:|----------|--------|:------:|:----:|
| Q19 | Docker镜像拉取失败 - "content size of zero" | Docker、镜像、拉取失败 | P0 | ✅ |
| Q20 | 使用本机已安装的PostgreSQL和Redis替代Docker | PostgreSQL、Redis、本机 | P1 | ✅ |
| Q21 | Windows环境下print()导致OSError | Windows、print、OSError | P0 | ✅ |
| Q22 | 本机安装Redis（Windows） | Redis、Windows、安装 | P1 | ✅ |
| Q23 | 数据库初始化常见问题 | 数据库、初始化、错误 | P1 | ✅ |
| Q24 | API服务启动后无法访问 | API、启动、访问 | P1 | ✅ |
| Q25 | Windows PowerShell环境变量设置 | PowerShell、环境变量 | P2 | ✅ |

### 第三部分：认证与登录问题（第26-30问）

| 序号 | 问题标题 | 关键词 | 优先级 | 状态 |
|:----:|----------|--------|:------:|:----:|
| Q26 | 登录失败时提示"登录已过期"，但明明是第一次登录 | 登录、过期、错误提示 | P0 | ✅ |
| Q35 | 添加 username 和 role 字段，支持用户名登录和权限管理 | username、role、权限 | P0 | ✅ |
| Q36 | 前端API调用返回数据缺少access_token - 统一响应格式问题 | 前端、响应格式、data字段 | P0 | ✅ |
| Q37 | 添加查看 API Key 明文功能 | API Key、查看、明文 | P1 | ✅ |
| Q38 | 配额使用情况页面报错：AttributeError: '_isnull' | 配额、SQLAlchemy、Bug | P0 | ✅ |
| Q39 | 账单中心报错：function sum(character varying) does not exist | 账单、PostgreSQL、Bug | P0 | ✅ |
| Q40 | 账单中心按月统计报错：timestamp | string comparison not supported | 账单、timestamp、datetime | P0 | ✅ |
| Q41 | 日志管理功能使用指南 | 日志、查看、导出、备份 | P1 | ✅ |
| Q42 | 不同用户角色登录后看到不同的界面吗？ | 用户角色、权限、界面 | P1 | ✅ |
| Q43 | 如何创建和分配不同角色的用户？ | 角色分配、用户管理 | P1 | ✅ |
| Q46 | 浏览器自动填充导致登录页面显示密码 | 浏览器、自动填充、密码 | P1 | ✅ |
| Q48 | 通知功能缺失（基础版） | 通知、通知中心、下拉面板 | P1 | ✅ |
| Q49 | 通知功能完善（完整版） | 通知、数据库、API、已读状态 | P0 | ✅ |

### 第五部分：支付与限流问题（V2.0新增）

| 序号 | 问题标题 | 关键词 | 优先级 | 状态 |
|:----:|----------|--------|:------:|:----:|
| Q50 | 支付功能概述 | 支付、充值、套餐 | P0 | ✅ |
| Q51 | 如何进行账户充值？ | 充值、套餐、支付 | P0 | ✅ |
| Q52 | 限流检查是如何工作的？ | 限流、RPM、RPH、配额 | P0 | ✅ |
| Q53 | 配额超限怎么办？ | 配额、超限、充值 | P1 | ✅ |
| Q54 | 后端服务配置说明 | 后端、endpoint、代理 | P1 | ✅ |

### 第六部分：消费明细与集成测试问题（V2.1新增）

| 序号 | 问题标题 | 关键词 | 优先级 | 状态 |
|:----:|----------|--------|:------:|:----:|
| Q55 | 消费明细页面显示空数据 | 消费明细、空数据、字段 | P0 | ✅ |
| Q56 | 集成测试工具调用返回404 | 集成测试、404、URL路径 | P0 | ✅ |
| Q57 | API调用日志缺少调用者和请求参数 | 调用者、请求参数、日志 | P1 | ✅ |
| Q58 | 如何添加仓库到集成测试页面 | 添加仓库、测试页面、配置 | P1 | ✅ |


**详细说明**：详见 [33_FAQ_登录错误提示问题详解.md](33_FAQ_登录错误提示问题详解.md)

### 第四部分：扩展问题（第31+问）

> 如有更多问题，请创建新文档如 `3x_FAQ_xxx.md`，并在下方添加条目

**优先级说明**：P0=紧急/影响核心功能，P1=重要/影响常用功能，P2=一般/影响体验

---

## 第一章 开发相关问题

### Q1: 如何搭建本地开发环境？

**问题描述**：新加入团队，需要搭建开发环境。

**解答**：

1. **安装必要软件**：
   - Docker Desktop 24.0+
   - Python 3.11+
   - VS Code 或 PyCharm
   - Git

2. **克隆代码**：
   ```bash
   git clone https://github.com/your-org/api-service.git
   cd api-service
   ```

3. **启动依赖服务**：
   ```bash
   docker-compose up -d postgres redis minio
   ```

4. **安装Python依赖**：
   ```bash
   pip install -r requirements.txt
   ```

5. **配置环境变量**：
   ```bash
   cp .env.example .env
   # 编辑 .env 配置数据库连接等
   ```

6. **运行开发服务器**：
   ```bash
   uvicorn src.api.main:app --reload
   ```

**参考文档**：[培训材料 - 第三章](12_培训材料.md)

---

### Q2: API响应格式是什么？

**问题描述**：不清楚API的统一响应格式。

**解答**：

**成功响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": { /* 业务数据 */ },
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1713200000
}
```

**错误响应**：
```json
{
  "code": 400,
  "message": "参数错误",
  "error": {
    "field": "email",
    "reason": "邮箱格式不正确"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1713200000
}
```

**参考文档**：[接口设计文档](09_接口设计文档.md)

---

### Q3: 如何添加新的API接口？

**问题描述**：需要在现有基础上添加新的业务接口。

**解答**：

1. **定义路由**（在 `src/api/routes/` 下）：
   ```python
   # src/api/routes/example.py
   from fastapi import APIRouter, Depends
   
   router = APIRouter(prefix="/example", tags=["示例"])
   
   @router.get("/items")
   async def get_items():
       return {"items": []}
   ```

2. **注册路由**（在 `main.py` 中）：
   ```python
   from src.api.routes import example
   
   app.include_router(example.router)
   ```

3. **定义Schema**（在 `src/api/schemas/` 下）：
   ```python
   from pydantic import BaseModel
   
   class ItemResponse(BaseModel):
       id: str
       name: str
   ```

4. **编写单元测试**（在 `tests/` 下）

**参考文档**：[代码规范培训](12_培训材料.md)

---

### Q4: 如何处理数据库迁移？

**问题描述**：修改了数据库模型，需要进行迁移。

**解答**：

使用 Alembic 进行数据库迁移：

```bash
# 创建迁移
alembic revision --autogenerate -m "add new column"

# 查看迁移列表
alembic history

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

**参考文档**：[数据库设计文档](08_数据库设计文档.md)

---

### Q5: 日志如何配置和使用？

**问题描述**：不清楚如何正确使用日志系统。

**解答**：

**日志配置**：
```python
import logging
from logging.config import dictConfig

dictConfig({
    "version": 1,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
})

# 使用日志
logger = logging.getLogger(__name__)
logger.info("这是一条信息日志")
logger.error("这是一条错误日志", exc_info=True)
```

**参考文档**：[实施文档 - 日志系统](02_项目实施方案.md)

---

## 第二章 部署运维问题

### Q6: 如何进行一键部署？

**问题描述**：生产环境如何部署新版本？

**解答**：

```bash
# 1. 登录服务器
ssh user@server

# 2. 进入项目目录
cd /data/api-service

# 3. 拉取最新代码
git pull origin main

# 4. 执行部署脚本
./deploy.sh

# 5. 检查部署状态
docker-compose ps
curl http://localhost:8000/health
```

**紧急回滚**：
```bash
# 回滚到上一个版本
./rollback.sh v1.0.1
```

**参考文档**：[部署运维手册](10_部署运维手册.md)

---

### Q7: 部署后服务无法启动怎么办？

**问题描述**：执行 `docker-compose up -d` 后服务启动失败。

**解答**：

**排查步骤**：

1. **查看容器状态**：
   ```bash
   docker-compose ps
   ```

2. **查看日志**：
   ```bash
   docker-compose logs -f
   docker-compose logs api  # 查看API服务日志
   docker-compose logs postgres  # 查看数据库日志
   ```

3. **常见原因和解决方案**：

   | 原因 | 解决方案 |
   |------|----------|
   | 端口被占用 | `netstat -tlnp \| grep 端口` 查看并释放 |
   | 环境变量错误 | 检查 `.env` 文件配置 |
   | 磁盘空间不足 | `df -h` 查看并清理 |
   | 数据库连接失败 | 检查数据库是否启动 |
   | 镜像拉取失败 | 检查网络连接 |

4. **重新构建**：
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

**参考文档**：[部署运维手册 - 故障处理](10_部署运维手册.md)

---

### Q8: 如何查看和监控服务状态？

**问题描述**：需要了解服务运行状态和性能指标。

**解答**：

**查看服务状态**：
```bash
# 查看容器状态
docker-compose ps

# 查看资源使用
docker stats

# 检查健康状态
curl http://localhost:8000/health
```

**健康检查响应**：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 86400,
  "services": {
    "database": "connected",
    "redis": "connected",
    "minio": "connected"
  }
}
```

**查看日志**：
```bash
# 实时日志
docker-compose logs -f

# 最近100行
docker-compose logs --tail=100

# 错误日志
docker-compose logs | grep ERROR
```

**参考文档**：[部署运维手册 - 监控告警](10_部署运维手册.md)

---

### Q9: 如何备份和恢复数据？

**问题描述**：需要备份数据库和上传文件。

**解答**：

**备份数据库**：
```bash
# 方式1：使用docker exec
docker exec api-postgres pg_dump -U api_user api_service > backup_$(date +%Y%m%d).sql

# 方式2：使用备份脚本
./scripts/backup.sh
```

**恢复数据库**：
```bash
# 方式1：使用docker exec
cat backup_20260416.sql | docker exec -i api-postgres psql -U api_user api_service

# 方式2：使用恢复脚本
./scripts/restore.sh 20260416
```

**备份文件**：
```bash
tar -czf backup_files_$(date +%Y%m%d).tar.gz /data/api-service/uploads/
```

**参考文档**：[部署运维手册 - 备份恢复](10_部署运维手册.md)

---

### Q10: 如何升级到新版本？

**问题描述**：需要升级系统到新版本。

**解答**：

**升级步骤**：

1. **通知相关方**：提前通知用户升级时间

2. **备份**：执行数据备份
   ```bash
   ./scripts/backup.sh
   ```

3. **拉取新版本**：
   ```bash
   git pull origin main
   ```

4. **执行升级脚本**：
   ```bash
   ./upgrade.sh v2.0.0
   ```

5. **验证升级**：
   ```bash
   curl http://localhost:8000/health
   docker-compose ps
   ```

**回滚（如有问题）**：
```bash
./rollback.sh v1.9.0
```

**参考文档**：[部署运维手册](10_部署运维手册.md)

---

## 第三章 安全相关问题

### Q11: API Key如何使用？

**问题描述**：获得了API Key，不知道如何使用。

**解答**：

**方式1：Header方式**
```
X-API-Key: APIK_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**方式2：带签名验证**
```python
import hmac
import hashlib
import time

def sign_request(secret: str, method: str, path: str, body: str):
    timestamp = str(int(time.time()))
    body_hash = hashlib.sha256(body.encode()).hexdigest()
    string_to_sign = f"{method}\n{path}\n{timestamp}\n{body_hash}"
    signature = hmac.new(secret.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()
    return signature

# 使用示例
headers = {
    "X-API-Key": "APIK_xxx",
    "X-Signature": sign_request(secret, "GET", "/api/v1/business/data", ""),
    "X-Timestamp": str(int(time.time()))
}
```

**参考文档**：[接口设计文档 - 签名验证](09_接口设计文档.md)

---

### Q12: Token过期了怎么办？

**问题描述**：API返回401，Token已过期。

**解答**：

**Access Token过期**：使用Refresh Token刷新
```python
import requests

# 刷新Token
response = requests.post(
    "https://api.example.com/api/v1/auth/refresh",
    json={"refresh_token": "your_refresh_token"}
)

# 获取新的Access Token
new_access_token = response.json()["data"]["access_token"]
```

**Refresh Token也过期**：需要重新登录
```python
# 重新登录获取新Token
response = requests.post(
    "https://api.example.com/api/v1/auth/login",
    json={"email": "user@example.com", "password": "password"}
)
```

**参考文档**：[接口设计文档 - 认证接口](09_接口设计文档.md)

---

### Q13: 如何申请更高限流配额？

**问题描述**：当前限流配额不足，需要提升。

**解答**：

**申请流程**：

1. **提交工单**：在管理后台提交限流配额申请
2. **审核**：运营团队审核申请
3. **配置**：通过后运维团队调整配置
4. **验证**：确认新配额生效

**申请内容**：
```
申请类型：限流配额提升
当前配额：100 QPS / 10000次/日
目标配额：200 QPS / 50000次/日
使用场景：[说明业务需求]
预计增长：[预计调用量增长]
```

**参考文档**：[接口设计文档 - 限流规则](09_接口设计文档.md)

---

## 第四章 业务相关问题

### Q14: 如何创建和管理租户？

**问题描述**：作为管理员，需要创建和管理租户。

**解答**：

**通过管理后台**：
1. 登录管理后台（admin.example.com）
2. 进入"租户管理"模块
3. 点击"创建租户"按钮
4. 填写租户信息
5. 配置配额和权限
6. 提交创建

**通过API**：
```bash
curl -X POST https://api.example.com/api/v1/admin/tenants \
  -H "Authorization: Bearer {admin_token}" \
  -d '{
    "name": "新租户",
    "code": "new_tenant",
    "quota_qps": 100,
    "quota_daily": 10000
  }'
```

**参考文档**：[接口设计文档 - 管理接口](09_接口设计文档.md)

---

### Q15: 如何查看API调用统计？

**问题描述**：需要查看API使用情况统计。

**解答**：

**通过管理后台**：
1. 登录管理后台
2. 进入"统计报表"模块
3. 选择时间范围
4. 查看调用量趋势图
5. 导出Excel报表

**通过API**：
```bash
curl -X GET "https://api.example.com/api/v1/admin/stats?start_date=2026-04-01&end_date=2026-04-16" \
  -H "Authorization: Bearer {admin_token}"
```

**响应示例**：
```json
{
  "data": {
    "summary": {
      "total_requests": 1000000,
      "total_success": 990000,
      "avg_response_time": 85.5
    },
    "timeline": [
      {"date": "2026-04-16", "requests": 50000}
    ]
  }
}
```

**参考文档**：[接口设计文档 - 统计接口](09_接口设计文档.md)

---

## 第五章 其他问题

### Q16: Swagger文档在哪里？

**问题描述**：需要查看API文档进行开发。

**解答**：

**在线文档地址**：
- Swagger UI: https://api.example.com/docs
- ReDoc: https://api.example.com/redoc

**本地访问**：
```bash
# 开发环境
http://localhost:8000/docs
```

**使用Swagger**：
1. 点击右上角"Authorize"按钮
2. 输入API Key或Token
3. 展开接口，填写参数
4. 点击"Execute"发送请求
5. 查看响应结果

---

### Q17: 如何获取技术支持？

**问题描述**：遇到问题需要技术支持。

**解答**：

| 问题类型 | 渠道 | 响应时间 |
|----------|------|----------|
| 一般问题 | 技术交流群 | 24小时内 |
| 紧急问题 | 紧急电话 | 即时 |
| 功能建议 | 工单系统 | 48小时内 |
| 文档问题 | 提交Issue | 72小时内 |

**提交工单格式**：
```
标题：[问题简述]
环境：生产环境 / 测试环境
版本：v1.0.0
问题描述：
  [详细描述问题]
复现步骤：
  1. [步骤1]
  2. [步骤2]
  3. [步骤3]
错误信息：
  [粘贴错误日志]
```

---

### Q18: API响应时间慢怎么办？

**问题描述**：API响应时间较长，影响使用。

**解答**：

**排查步骤**：

1. **检查网络**：确认网络延迟
   ```bash
   curl -w "\nTime: %{time_total}s\n" https://api.example.com/health
   ```

2. **检查数据库**：查看慢查询
   ```sql
   SELECT * FROM pg_stat_statements 
   ORDER BY mean_exec_time DESC 
   LIMIT 10;
   ```

3. **检查Redis缓存**：确认缓存命中
   ```bash
   redis-cli INFO stats | grep keyspace
   ```

4. **查看监控**：检查资源使用
   ```bash
   docker stats
   ```

**常见优化**：
- 添加数据库索引
- 启用Redis缓存
- 优化SQL查询
- 增加资源配额

**参考文档**：[安全设计文档 - 性能优化](11_安全设计文档.md)

---

**FAQ文档结束**

---

## 第六章 部署环境问题（2026年4月18日新增）

### Q19: Docker Desktop 镜像拉取失败 - "unable to fetch descriptor ... content size of zero"

**问题描述**：
执行 `docker pull redis:7-alpine` 或 `docker pull postgres:15-alpine` 时报错：
```
Error response from daemon: unable to fetch descriptor (sha256:119c9edaa6389b4c141f7faa74dae3f3b91ac50c3376d39596044ef07c2592e2) which reports content size of zero: invalid argument
```

**原因分析**：
1. Docker Hub 注册表连接异常
2. 镜像缓存损坏
3. 网络问题导致下载中断
4. Docker 镜像加速器配置不正确

**解决方案**：

**方案1：配置 Docker 镜像加速器（推荐）**

1. 打开 Docker Desktop 设置
2. 选择 "Docker Engine"
3. 修改 JSON 配置，添加镜像源：

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "registry-mirrors": [
    "https://docker.xuanyuan.me",
    "https://hub-mirror.c.163.com",
    "https://mirror.ccs.tencentyun.com",
    "https://hub.rat.dev",
    "https://docker.1ms.run",
    "https://pull.m.daocloud.io"
  ]
}
```

4. 点击 "Apply & Restart" 重启 Docker Desktop

**方案2：清理 Docker 缓存后重试**

```powershell
# 清理所有未使用的资源
docker system prune -a -f --volumes

# 重启 Docker Desktop 后重新拉取
docker pull redis:7-alpine
docker pull postgres:15-alpine
```

**方案3：使用特定的镜像源**

```powershell
# 指定镜像源拉取
docker pull docker.1ms.run/library/redis:7-alpine
docker pull docker.1ms.run/library/postgres:15-alpine
```

**方案4：完全重启 Docker Desktop**

1. 关闭 Docker Desktop（右键托盘图标 → Quit Docker Desktop）
2. 等待完全退出
3. 重新启动 Docker Desktop
4. 等待 Docker 完全启动后再拉取镜像

---

### Q20: 使用本机已安装的 PostgreSQL 和 Redis 替代 Docker

**问题描述**：
由于 Docker 镜像拉取困难，想使用本机已安装的 PostgreSQL 和 Redis。

**解决方案**：

**1. 检查本机服务状态**

```powershell
# 检查 PostgreSQL 端口（默认5432）
netstat -an | findstr "5432"

# 检查 Redis 端口（默认6379）
netstat -an | findstr "6379"
```

**2. 配置 .env 文件**

```env
# PostgreSQL 配置
DATABASE_URL=postgresql://postgres:<密码>@localhost:5432/api_platform

# Redis 配置（无密码）
REDIS_URL=redis://localhost:6379/0
```

**3. 初始化数据库**

```powershell
cd D:\Work_Area\AI\API-Agent\api-platform

# 创建数据库表
python scripts/init_db.py

# 填充测试数据
python scripts/seed_data.py
```

**4. 启动 API 服务**

```powershell
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**测试账号**：

| 用户类型 | 用户名 | 邮箱 | 密码 |
|---------|--------|------|------|
| 超级管理员 | superadmin | superadmin@example.com | super123456 |
| 管理员 | admin | admin@example.com | admin123 |
| 仓库所有者 | owner | owner@example.com | owner123 |
| 开发者 | developer | developer@example.com | dev123456 |
| 普通用户 | test | test@example.com | test123 |

---

### Q21: Windows 环境下 print() 导致 OSError: [Errno 22] Invalid argument

**问题描述**：
在 Windows 上运行 FastAPI 应用时，登录接口报错：
```
OSError: [Errno 22] Invalid argument
```

错误堆栈显示问题出在 `print()` 语句：
```python
File "auth.py", line 164, in login
    print(f"[DEBUG LOGIN] Attempt for: {login_value}")
OSError: [Errno 22] Invalid argument
```

**原因分析**：
在 Windows 平台上，`print()` 在异步环境（asyncio）中写入标准输出时可能触发此错误，特别是当标准输出被重定向或管道传输时。

**解决方案**：

将所有 `print()` 语句替换为日志记录器：

```python
# 错误写法（Windows 异步环境不兼容）
print(f"[DEBUG LOGIN] Attempt for: {login_value}")

# 正确写法
import logging
logging.getLogger("api_platform.auth").debug(f"Login attempt for: {login_value}")
```

**批量替换示例**：

```python
# 在文件开头添加
import logging

# 将所有 print 替换为日志
# 原来: print(f"[DEBUG] message")
# 改为: logging.getLogger("api_platform.auth").debug("message")
```

**推荐使用日志模块**：

```python
from src.config.logging_config import get_logger

logger = get_logger("auth")
logger.debug(f"Login attempt for: {login_value}")
logger.info("Login successful")
logger.error("Login failed")
```

**参考文档**：[LOGGING_GUIDE.md](api-platform/docs/LOGGING_GUIDE.md)

---

### Q22: 本机安装 Redis（Windows）

**问题描述**：
需要在本机 Windows 上安装 Redis 服务。

**解决方案**：

**方法1：使用 Memurai（推荐，Redis 兼容）**

1. 下载地址：https://www.memurai.com/get-download
2. 安装后自动注册为 Windows 服务
3. 默认监听端口：6379

**方法2：使用 Docker 运行 Redis**

```powershell
# 拉取并运行 Redis 容器
docker pull redis:7-alpine
docker run -d --name my-redis -p 6379:6379 redis:7-alpine
```

**方法3：使用 WSL2 安装 Redis**

```bash
# 在 WSL2 终端中
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

**验证 Redis 是否运行**：

```powershell
# 检查端口
netstat -an | findstr "6379"

# 测试连接
redis-cli ping
# 返回 PONG 表示成功
```

---

### Q23: 数据库初始化常见问题

**问题描述**：
运行 `python scripts/init_db.py` 或 `python scripts/seed_data.py` 时出现错误。

**常见错误及解决方案**：

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `connection refused` | PostgreSQL 未运行 | 启动 PostgreSQL 服务 |
| `password authentication failed` | 密码错误 | 检查 .env 中的密码 |
| `database "xxx" does not exist` | 数据库不存在 | 先创建数据库 |
| `permission denied` | 用户权限不足 | 使用 postgres 超级用户 |

**创建数据库**：

```powershell
# Windows 下使用 pgAdmin 或命令行
createdb -U postgres api_platform

# 或在 psql 中
psql -U postgres -c "CREATE DATABASE api_platform;"
```

**完全重置数据库**：

```powershell
cd D:\Work_Area\AI\API-Agent\api-platform

# 删除并重建表
python scripts/init_db.py --drop

# 重新填充数据
python scripts/seed_data.py
```

---

### Q24: API 服务启动后无法访问

**问题描述**：
API 服务已启动，但无法访问 http://localhost:8000

**排查步骤**：

1. **确认服务正在运行**
```powershell
# 检查端口监听
netstat -an | findstr "8000"
```

2. **检查防火墙**
```powershell
# 允许端口通过防火墙
netsh advfirewall firewall add rule name="API Platform" dir=in action=allow protocol=tcp localport=8000
```

3. **查看启动日志**
```powershell
# 检查是否有错误
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

4. **检查环境变量**
确认 .env 文件中：
- `DATABASE_URL` 正确
- `REDIS_URL` 正确
- `DEBUG=true`

5. **检查数据库连接**
```powershell
python -c "from src.config.database import async_engine; print('DB OK')"
```

**参考文档**：[E2E_TEST_GUIDE.md](api-platform/web/docs/E2E_TEST_GUIDE.md)

---

### Q25: Windows PowerShell 环境变量设置

**问题描述**：
需要在 PowerShell 中设置环境变量运行服务。

**常用命令**：

```powershell
# 临时设置环境变量（当前会话）
$env:DATABASE_URL = "postgresql://postgres:password@localhost:5432/api_platform"
$env:REDIS_URL = "redis://localhost:6379/0"

# 查看环境变量
Get-ChildItem Env:

# 永久设置（用户级）
[System.Environment]::SetEnvironmentVariable("DATABASE_URL", "postgresql://...", "User")

# 永久设置（系统级，需要管理员权限）
[System.Environment]::SetEnvironmentVariable("DATABASE_URL", "postgresql://...", "Machine")
```

**使用 .env 文件（推荐）**

项目根目录的 `.env` 文件会被自动加载，无需手动设置环境变量。

---

---

### Q26: 登录失败时提示"登录已过期"，但明明是第一次登录

**问题描述**：
使用用户名/邮箱登录时，后端返回"用户名/邮箱或密码错误"，但前端显示的错误提示是"登录已过期"。

**原因分析**：
系统没有正确区分不同的认证失败场景：
- **40101**：用户名/邮箱或密码错误
- **40102**：Token无效或已过期

前端根据 HTTP 状态码 401 显示固定标题"登录已过期"，导致用户困惑。

**解决方案**：
1. **后端已优化**：新增 `TokenExpiredError` 和 `InvalidCredentialsError` 异常类型，区分不同的认证失败场景
2. **前端已优化**：错误提示现在会显示后端返回的具体错误信息

**错误码对照表**：

| 错误码 | 场景 | 提示消息 |
|--------|------|----------|
| 40101 | 用户名/邮箱或密码错误 | "用户名/邮箱或密码错误" |
| 40102 | Token无效或已过期 | "Token无效或已过期，请重新登录" |

**测试正确的账号**：

| 角色 | 邮箱 | 密码 |
|------|------|------|
| 管理员 | admin@example.com | admin123 |
| 开发者 | developer@example.com | admin123 |
| 仓库所有者 | owner@example.com | admin123 |

**注意**：请使用邮箱登录，不要使用用户名（如 `admin`）。

---

### Q36: 前端API调用返回数据缺少access_token - 统一响应格式问题

**问题描述**：
登录时提示"登录失败：未获取到访问令牌"，但后端日志显示登录成功并返回了 Token。

**原因分析**：
后端 API 返回统一响应格式：
```json
{
    "code": 0,
    "message": "success",
    "data": {
        "access_token": "eyJhbGc...",
        "refresh_token": "eyJhbGc...",
        "expires_in": 1800
    }
}
```

前端 Axios 拦截器需要自动提取 `data` 字段，而不是直接返回整个响应对象。

**解决方案**：
修改前端 `client.ts` 响应拦截器，自动提取 `data` 字段：

```typescript
// src/api/client.ts
client.interceptors.response.use((response) => {
    const data = response.data
    // 统一处理业务错误码
    if (data.code !== undefined && data.code !== 0) {
        // 错误处理...
    }
    // 自动提取 data 字段
    if (data?.data !== undefined) {
        return { ...response, data: data.data }
    }
    return response
})
```

**验证修复**：
修改后，前端 API 调用直接返回业务数据：
```typescript
// 修复前：response = { code: 0, message: "success", data: {...} }
// 修复后：response = { access_token, refresh_token, expires_in }
const { access_token } = await authApi.login({ email, password })
```

**相关文件**：
- 前端：`web/src/api/client.ts`
- 后端：`src/schemas/response.py`

---

## 附录：常用命令速查

### Docker 相关
```powershell
# 启动 Docker Desktop 中的服务
cd D:\Work_Area\AI\API-Agent\api-platform\docker
docker-compose up -d postgres redis

# 查看容器状态
docker ps -a

# 查看容器日志
docker logs <容器名>
```

### 数据库相关
```powershell
# 连接 PostgreSQL
psql -U postgres -d api_platform

# 重置数据库
python scripts/init_db.py --drop
python scripts/init_db.py

# 填充测试数据
python scripts/seed_data.py
```

### API 服务相关
```powershell
# 启动服务
cd D:\Work_Area\AI\API-Agent\api-platform
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# API 文档地址
# http://localhost:8000/docs
# http://localhost:8000/redoc
```

### 测试登录
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

---

### Q42: 不同用户角色登录后看到不同的界面吗？

**问题描述**：
系统有多种用户类型（超级管理员、管理员、仓库所有者、开发者、普通用户），登录后看到的界面是否不同？

**解答**：

是的！系统实现了完整的**角色权限系统(RBAC)**，不同用户类型登录后会看到完全不同的界面和功能。

**用户类型与界面对照**：

| 用户类型 | 登录入口 | 专属界面 | 主要功能 |
|---------|---------|---------|---------|
| **超级管理员** | `/superadmin` | 超级管理员控制台 | 全局用户管理、角色权限配置、系统配置 |
| **管理员** | `/admin` | 管理员面板 | 用户管理、仓库审核、日志管理、系统设置 |
| **仓库所有者** | `/owner` | 仓库管理后台 | 仓库管理、数据分析、收益结算 |
| **开发者** | `/` | 开发者仪表板 | API Keys、配额、日志、账单 |
| **普通用户** | `/` | 用户仪表板 | 基础功能（受限） |

**详细说明**：请参阅 [角色权限系统设计文档](../api-platform/docs/ROLE_PERMISSION_GUIDE.md)

---

### Q43: 如何创建和分配不同角色的用户？

**问题描述**：
如何创建新用户并分配不同的用户类型/角色？

**解答**：

**方法一：通过注册页面注册（普通用户）**

1. 访问注册页面：`/register`
2. 填写用户名、邮箱、密码
3. 选择账号类型：普通用户/开发者/仓库所有者
4. 点击注册

**方法二：通过后台创建用户（管理员/超级管理员）**

1. 使用管理员账号登录
2. 进入用户管理页面
3. 点击"创建用户"或"编辑"按钮
4. 设置用户类型：
   - `super_admin`：超级管理员（仅超级管理员可分配）
   - `admin`：管理员
   - `owner`：仓库所有者
   - `developer`：开发者
   - `user`：普通用户

**测试账户**：

| 用户类型 | 用户名 | 邮箱 | 密码 |
|---------|--------|------|------|
| 超级管理员 | superadmin | superadmin@example.com | super123456 |
| 管理员 | admin | admin@example.com | admin123 |
| 仓库所有者 | owner | owner@example.com | owner123 |
| 开发者 | developer | developer@example.com | dev123456 |
| 普通用户 | test | test@example.com | test123 |

> **说明**：开发者可以创建 API Keys，普通用户只能查看。

**运行种子脚本添加测试用户**：
```bash
cd api-platform
python scripts/init_db_with_data.py --drop
```

> 注意：使用 `--drop` 参数会删除现有数据库并重新创建，确保测试数据与文档一致。

---

### Q44: 退出登录后，为什么密码字段会被清空？

**问题描述**：
退出登录后再次打开登录页面，发现密码输入框是空的。这是正常的吗？

**解答**：
这是**正常且安全**的设计！系统出于安全考虑，会在以下情况自动清空密码字段：

**清空时机**：
1. ✅ 用户退出登录后
2. ✅ 用户从注册页面跳转到登录页面
3. ✅ 登录/注册页面重新挂载时

**清空的敏感数据包括**：
- 表单中的密码字段
- 浏览器自动填充的密码数据
- sessionStorage 中可能残留的敏感信息
- 剪贴板中可能存在的密码内容

**为什么这样设计？**
- **防止信息泄露**：多人共用设备时，防止他人看到之前的密码
- **防止自动填充**：浏览器的密码自动填充可能带来安全风险
- **最佳实践**：金融类、政务类应用普遍采用的安全策略

**相关安全措施**：
- 密码输入框支持可见/隐藏切换
- 登录失败不会自动重试（防止暴力破解）
- Token 过期后需要重新登录

---

### Q45: 系统有哪些安全防护措施？

**问题描述**：
系统提供了哪些安全保障措施？

**解答**：

**前端安全措施**：
| 措施 | 说明 |
|------|------|
| 密码清空 | 退出登录后自动清空敏感数据 |
| Token 管理 | Access Token 和 Refresh Token 分离 |
| 路由守卫 | 未登录用户无法访问受保护页面 |
| 角色权限 | 不同角色看到不同的界面和功能 |

**后端安全措施**：
| 措施 | 说明 |
|------|------|
| 密码加密 | 使用 bcrypt 加密存储，不可逆 |
| 错误码区分 | 40101（密码错误）vs 40102（Token过期） |
| 请求限流 | 防止暴力破解 |
| HTTPS | 全站强制 HTTPS |
| CORS | 跨域访问控制 |

**建议用户**：
1. 定期更换密码
2. 不在公共设备保存密码
3. 使用强密码（8位以上，字母+数字+特殊字符）
4. 发现异常登录及时修改密码

---

### Q46: 浏览器自动填充导致登录页面显示密码

**问题描述**：
首次打开登录页面 `localhost:3000` 时，密码输入框中已经显示了之前保存的密码（带圆点遮罩）。退出登录后重新打开，密码框仍有残留数据。

**原因分析**：
这不是代码 Bug，而是**浏览器的自动填充功能**导致的：
1. 用户之前登录时，浏览器提示"保存密码"，用户点击了"保存"
2. 浏览器会在同源的登录页面自动填充保存的凭据
3. 浏览器的填充时机在 JavaScript 之后，导致代码清空的值被覆盖

**解决方案**：

**方法一：清除浏览器保存的密码**
```
Chrome: 设置 → 密码 → 已保存的密码 → 删除
Firefox: 设置 → 隐私与安全 → 已保存的登录信息 → 删除
Edge: 设置 → 密码 → 管理密码 → 删除
```

**方法二：使用隐私/无痕模式**
```
Chrome: Ctrl + Shift + N
Firefox: Ctrl + Shift + P
Edge: Ctrl + Shift + N
```

**方法三：代码已做的改进**
系统代码已添加多重安全措施：
1. `autoComplete="off/new-password"` - 禁用浏览器自动填充
2. `MutationObserver` - 持续监听DOM变化，捕获延迟填充
3. 多次延迟清空（300ms/1s/2s/3s）- 兜底策略处理极端情况
4. 退出登录时清除所有敏感数据（包括剪贴板、sessionStorage）

**详细说明**：请参阅 [33_FAQ_登录错误提示问题详解.md](33_FAQ_登录错误提示问题详解.md) - 问题44

---

### Q48: 通知功能缺失 - 点击通知图标无响应

**问题描述**：
用户点击右上角的**通知图标**（铃铛图标）时：
1. 没有任何下拉面板弹出
2. 点击"查看全部通知"也没有任何反馈

**原因分析**：
发现两个问题：
1. **通知图标缺少点击事件**：代码中通知图标只是一个 UI 展示，缺少 `Dropdown` 包裹
2. **通知页面路由不存在**：点击"查看全部通知"时导航到 `/notifications`，但该路由未在 `App.tsx` 中定义

**解决方案**：

**1. 添加通知下拉面板** (`Layout.tsx`)

使用 Ant Design 的 `Dropdown` 组件为通知图标添加下拉面板：

```tsx
<Dropdown
  trigger={['click']}
  placement="bottomRight"
  overlay={
    <div className={styles.notificationPanel}>
      <div className={styles.notificationHeader}>
        <span>通知中心</span>
        <span className={styles.notificationCount}>5 条未读</span>
      </div>
      <div className={styles.notificationList}>
        {/* 通知项... */}
      </div>
      <div className={styles.notificationFooter}>
        <span onClick={() => navigate('/notifications')}>查看全部通知</span>
      </div>
    </div>
  }
>
  <Badge count={5} size="small">
    <BellOutlined className={styles.headerIcon} />
  </Badge>
</Dropdown>
```

**2. 创建通知页面** (`pages/notifications/Notifications.tsx`)

创建通知列表页面，支持全部通知/未读通知 Tab 切换。

**3. 添加路由配置** (`App.tsx`)

```tsx
import Notifications from './pages/notifications/Notifications'

// 添加路由
<Route path="notifications" element={<Notifications />} />
```

**涉及文件**：

| 文件 | 修改/新增内容 |
|------|--------------|
| `web/src/components/Layout.tsx` | 添加通知下拉面板 Dropdown |
| `web/src/components/Layout.module.css` | 添加通知面板样式 |
| `web/src/pages/notifications/Notifications.tsx` | **新增**：通知列表页面 |
| `web/src/pages/notifications/Notifications.module.css` | **新增**：通知页面样式 |
| `web/src/App.tsx` | 添加 `/notifications` 路由 |

**功能说明**：
- 点击铃铛图标显示通知下拉面板
- 面板显示最新3条通知摘要
- 支持"查看全部通知"跳转到完整通知列表页面
- 通知列表页面支持全部/未读 Tab 切换

**待完善功能**（后续迭代）：
- 后端通知接口（目前使用模拟数据）
- 实时通知推送（WebSocket/SSE）
- 通知分类管理
- 通知标记已读
- 通知偏好设置

**补充说明 - 路由路径问题修复**：

点击"查看全部通知"后页面闪烁不显示内容，这是因为导航路径与用户类型不匹配。

**原因**：不同用户类型的路由基础路径不同：
- 开发者用户：`/notifications` ✓
- 管理员：`/admin/notifications`
- 仓库所有者：`/owner/notifications`
- 超级管理员：`/superadmin/notifications`

使用绝对路径 `/notifications` 会导致非开发者用户无法正确导航。

**解决方案**：根据用户类型使用正确的绝对路径：
```tsx
const basePath = user?.user_type === 'super_admin' ? '/superadmin' 
  : user?.user_type === 'admin' ? '/admin' 
  : user?.user_type === 'owner' ? '/owner' 
  : ''
navigate(`${basePath}/notifications`)
```

**详细说明**：请参阅 [33_FAQ_开发过程中的FAQ_更新.md](33_FAQ_开发过程中的FAQ_更新.md) - 问题48

---

### Q49: 通知功能完善（完整版）

**问题描述**：

Q48实现的通知功能存在以下问题：
1. 模拟数据硬编码在代码中，未从数据库获取
2. 点击下拉菜单后不会自动关闭
3. 刷新页面后已读状态丢失
4. 功能不完整，缺少主流通知系统的常用功能

**问题分析**：

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 模拟数据 | 缺少后端API和数据库表 | 创建通知模型和服务 |
| 菜单不关闭 | Dropdown overlay点击事件冒泡 | 添加 `onClick={e => e.stopPropagation()}` |
| 状态不持久 | 无数据库存储 | 创建 `notifications` 表存储 |
| 功能缺失 | 设计不完善 | 完善API和前端功能 |

**解决方案概述**：

**1. 后端实现**
- 创建 `Notification` 数据模型（通知表）
- 创建 `NotificationPreference` 数据模型（用户偏好设置）
- 创建 `NotificationService` 服务层
- 创建通知API接口（CRUD + 标记已读 + 批量操作）

**2. 前端实现**
- 创建 `notification.ts` API服务
- 修改 `Layout.tsx` 通知下拉面板，使用真实API
- 修复下拉菜单关闭问题（阻止事件冒泡）
- 修改 `Notifications.tsx` 通知列表页面，支持完整功能

**3. 数据库**
- 创建 `scripts/migrate_notifications.py` 迁移脚本
- 自动为现有用户创建测试通知

**功能清单**：
- ✅ 通知列表（分页）
- ✅ 未读/已读分类（Tab切换）
- ✅ 标记已读（单条/全部）
- ✅ 删除通知（单条/删除已读）
- ✅ 下拉面板（快速查看）
- ✅ 未读数Badge（实时更新）
- ✅ 通知偏好设置
- ✅ 广播通知（管理员功能）

**详细说明**：请参阅 [33_FAQ_开发过程中的FAQ_更新.md](33_FAQ_开发过程中的FAQ_更新.md) - 问题49

---

**FAQ文档结束**

---

## 第七章 支付与限流问题（V2.0新增）

### Q50: 支付功能概述

**问题描述**：
系统有哪些支付功能？如何进行账户充值？

**解答**：

系统提供完整的支付和计费功能，包括：

**核心功能**：
| 功能 | 说明 |
|------|------|
| 充值套餐 | 多种充值额度可选，支持赠送金额 |
| 支付下单 | 支持微信、支付宝、银行卡 |
| 账户余额 | 余额查询、增加、扣除、冻结 |
| 账单记录 | 收支明细查询和统计 |
| 退款功能 | 管理员可进行退款操作 |

**API 接口**：
| 接口 | 方法 | 说明 |
|------|------|------|
| `/payments/packages` | GET | 获取充值套餐列表 |
| `/payments/packages/{id}` | GET | 获取套餐详情 |
| `/payments/create` | POST | 创建支付订单 |
| `/payments/status/{no}` | GET | 查询支付状态 |
| `/payments/cancel/{no}` | POST | 取消订单 |
| `/payments/records` | GET | 获取支付记录 |

**Web 页面**：
- 充值中心：`/developer/recharge`
- 账单中心：`/developer/billing`（添加了"充值"按钮）

**充值套餐示例**：
| 套餐 | 价格 | 赠送 |
|------|------|------|
| 基础套餐 | ¥10 | 无 |
| 标准套餐 | ¥50 | 10% |
| 高级套餐 | ¥100 | 15% |
| 企业套餐 | ¥500 | 20% |

---

### Q51: 如何进行账户充值？

**问题描述**：
用户如何充值账户余额？

**解答**：

**方法一：通过充值中心页面充值**

1. 登录开发者账号
2. 进入"充值中心"（左侧菜单 → 充值中心）
3. 选择充值套餐（推荐套餐会有"推荐"标签）
4. 选择支付方式（微信/支付宝/银行卡）
5. 点击"立即充值"创建订单
6. 完成支付后自动到账

**方法二：通过账单中心充值**

1. 进入"账单中心"
2. 点击右上角"充值"按钮
3. 跳转到充值中心完成后续步骤

**支付流程**：
```
选择套餐 → 选择支付方式 → 创建订单 → 完成支付 → 自动到账
```

**余额提醒**：
当余额低于 ¥1 时，系统会在"配额使用"页面显示警告提示，并提供"立即充值"快捷入口。

---

### Q52: 限流检查是如何工作的？

**问题描述**：
系统是如何限制 API 调用频率的？什么是 RPM/RPH？

**解答**：

系统实现了多级限流检查，在每次 API 调用时自动进行：

**限流层级**：

| 层级 | 字段 | 默认值 | 说明 |
|------|------|--------|------|
| RPM | `rate_limit_rpm` | 1000 | 每分钟请求数上限 |
| RPH | `rate_limit_rph` | 10000 | 每小时请求数上限 |
| 日配额 | `daily_quota` | 可配置 | 每日调用上限 |
| 月配额 | `monthly_quota` | 可配置 | 每月调用上限 |

**检查时机**：
每次 API Key 验证时（`AuthService.verify_api_key`）自动检查。

**Web 页面展示**：
进入"配额使用"页面，可查看：
- 每日/每月配额使用进度
- RPM 实时使用情况（最近1分钟）
- RPH 实时使用情况（最近1小时）

**超限响应**：
当限流触发时，返回 HTTP 429 错误：
```json
{
  "code": 429,
  "message": "今日配额已用完，请明天再试（日配额: 1000）",
  "data": null
}
```

**配置说明**：
限流参数可在创建/编辑 API Key 时设置：
- `rate_limit_rpm`：每分钟请求数
- `rate_limit_rph`：每小时请求数
- `daily_quota`：每日配额（不填则无限制）
- `monthly_quota`：每月配额（不填则无限制）

---

### Q53: 配额超限怎么办？

**问题描述**：
API 调用时提示配额超限，应该如何处理？

**解答**：

**解决方案**：

**方案一：等待配额重置**
- 日配额：次日零点自动重置
- 月配额：次月1日自动重置
- RPM/RPH：1分钟/1小时后自动恢复

**方案二：充值提升配额**
1. 进入"充值中心"购买更高额度套餐
2. 或联系管理员调整配额限制

**方案三：配置余额扣费（高级功能）**
- 在 API Key 设置中启用 `is_balance_enabled`
- 系统会按调用次数从余额扣费
- 余额不足时给出警告（可配置是否阻止）

**余额提醒设置**：
当余额低于阈值（默认 ¥1）时：
- 配额页面显示橙色警告
- 低于 ¥0 时显示红色警告
- 提供"立即充值"快捷入口

**避免限流的建议**：
1. 合理设置限流参数
2. 实现请求缓存减少重复调用
3. 使用异步队列批量处理请求
4. 监控使用量提前预警

---

### Q54: 后端服务配置说明

**问题描述**：
仓库如何配置实际的后端服务 URL？

**解答**：

**配置说明**：

每个仓库可以配置实际的后端 API 地址，系统会自动将请求代理转发到后端服务。

**配置字段**：

| 字段 | 表字段 | 说明 |
|------|--------|------|
| 后端地址 | `endpoint_url` | 仓库 API 根地址 |
| 健康检查 | `health_check_url` | 健康检查地址 |
| 超时配置 | `request_timeout` | 请求超时时间 |

**配置示例**：
```json
{
  "name": "psychology-api",
  "display_name": "心理问答API",
  "endpoint_url": "https://psychology-backend.example.com/api/v1",
  "repo_type": "psychology",
  "protocol": "http"
}
```

**代理流程**：
```
POST /repositories/psychology-api/chat
    ↓
读取 repo.endpoint_url
    ↓
POST https://psychology-backend.example.com/api/v1/chat
    ↓
返回响应 + 记录日志
```

**错误处理**：

| 情况 | HTTP 状态码 | 说明 |
|------|-------------|------|
| 超时 | 504 | 后端响应超过30秒 |
| 后端错误 | 502 | 后端服务异常 |
| 无配置 | 200（模拟） | 返回模拟数据用于测试 |

**回退机制**：
如果仓库未配置 `endpoint_url`，系统会返回模拟数据，方便开发测试。

**参考文档**：[01_项目需求规格说明书.md](01_项目需求规格说明书.md) - 第十三章

---

**FAQ文档结束**

| 版本 | 日期 | 更新内容 | 作者 |
|------|------|---------|------|
| V1.0 | 2026-04-16 | 初始版本 | - |
| V1.1 | 2026-04-18 | 新增第六章：部署环境问题（Q19-Q25）| AI Assistant |
| V1.2 | 2026-04-18 | 新增FAQ汇总列表、Q26登录失败提示说明 | AI Assistant |
| V1.3 | 2026-04-19 | 新增Q42-Q43角色权限FAQ | AI Assistant |
| V1.4 | 2026-04-19 | 新增Q44-Q45密码安全FAQ | AI Assistant |
| V1.5 | 2026-04-19 | 新增Q46浏览器自动填充FAQ | AI Assistant |
| V1.6 | 2026-04-19 | Q46增强：MutationObserver持续监听方案 | AI Assistant |
| V1.7 | 2026-04-19 | 新增Q48：通知功能缺失FAQ | AI Assistant |
| V2.0 | 2026-04-20 | 新增第五章：支付与限流问题（Q50-Q54）| AI Assistant |
| V1.8 | 2026-04-19 | Q48补充：修复通知路由路径问题 - 根据用户类型使用正确的绝对路径导航 | AI Assistant |
| V1.9 | 2026-04-19 | 新增Q49：通知功能完善（完整版）- 后端数据库模型、API接口、前端真实数据、下拉菜单修复、已读状态管理 | AI Assistant |
| V2.1 | 2026-04-22 | 新增第六章：消费明细与集成测试问题（Q55-Q57）- 集成测试工具改造、消费明细新增字段 | AI Assistant |

如需补充问题，请联系项目组。

---

## 第七章 消费明细与集成测试问题（V2.1新增）

### Q55: 消费明细页面显示空数据

**问题描述**：在集成测试工具中调用API后，消费明细页面的"调用者"和"请求参数"列显示为空或"-"。

**问题原因**：
1. 数据库 `api_call_logs` 表缺少 `request_params`、`tester` 等字段
2. 数据库迁移未执行

**解决方案**：

1. **执行数据库迁移**：运行迁移脚本添加新字段

```bash
cd d:/Work_Area/AI/API-Agent/api-platform
python -m scripts.migrate_add_request_params_tester
```

迁移脚本会添加以下字段：
- `request_params (TEXT)` - 请求参数
- `tester (VARCHAR(100))` - 测试人员
- `request_id (VARCHAR(64))` - 全链路追踪ID
- `request_path (VARCHAR(500))` - 请求路径
- `request_method (VARCHAR(10))` - 请求方法

2. **验证数据库更新**：

```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'api_call_logs'
ORDER BY ordinal_position;
```

**详细说明**：详见 [35_开发过程中的FAQ_更新01.md](35_开发过程中的FAQ_更新01.md)

---

### Q56: 集成测试工具调用返回404

**问题描述**：集成测试工具调用API后，响应返回200但内容为空，显示 `{"detail": "Not Found"}`。

**问题原因**：
1. 前端URL构建错误：前端构建的URL是 `/weather-api/current`，但后端proxy接口完整路径是 `/api/v1/repositories/{repo_slug}/{path}`
2. 路由匹配问题：`/{repo_slug}` 路由在 `/{repo_slug}/{path:path}` 之前定义
3. 仓库 `endpoint_url` 未配置：数据库中Weather仓库的 `endpoint_url` 为NULL

**解决方案**：

1. **修复前端URL构建逻辑**：修改 `ApiTester.tsx` 中的 `buildUrl` 函数

```typescript
// 正确的URL格式
const buildUrl = useCallback((repo: Repository, endpoint: Endpoint): string => {
    // ...
    return `/api/v1/repositories/${repo.slug}${path}${queryString ? '?' + queryString : ''}`;
}, [paramValues]);
```

2. **修复后端路由匹配**：修改 `repositories.py`，在 `get_repository` 函数中添加路径检查

```python
# 防止路由错误匹配
if "/" in repo_slug:
    raise HTTPException(status_code=404, detail="Repository not found")
```

3. **更新数据库仓库配置**：

```sql
UPDATE repositories
SET endpoint_url = 'http://localhost:8001/api/v1/weather'
WHERE slug = 'weather-api';
```

4. **重启后端服务**

```bash
python -m uvicorn src.main:app --reload
```

**详细说明**：详见 [35_开发过程中的FAQ_更新01.md](35_开发过程中的FAQ_更新01.md)

---

### Q57: API调用日志缺少调用者和请求参数

**问题描述**：消费明细页面需要显示"调用者"和"请求参数"列，但日志记录中缺少这些信息。

**问题原因**：代码中没有记录 `tester` 和 `request_params` 字段。

**解决方案**：

1. **修改后端日志记录逻辑**：在 `repo_service.py` 的 `_log_api_call` 函数中添加字段记录

```python
async def _log_api_call(
    db: AsyncSession,
    repo_id: str,
    endpoint: str,
    method: str,
    status_code: int,
    response_time: str,
    error_message: Optional[str] = None,
    # 新增参数
    tester: Optional[str] = None,
    request_params: Optional[str] = None,
    request_path: Optional[str] = None,
    request_method: Optional[str] = None,
    request_id: Optional[str] = None,
):
    log_entry = APICallLog(
        request_id=request_id,
        repo_id=repo_id,
        endpoint=endpoint,
        method=method,
        request_path=request_path,
        request_method=request_method,
        request_params=request_params,
        tester=tester,  # 记录调用者
        status_code=status_code,
        response_time=response_time,
        error_message=error_message,
    )
    # ...
```

2. **更新前端调用**：传入当前用户信息

```typescript
// 在 repositories.py proxy 接口中
from src.services.repo_service import RepoService

user = request.state.user if hasattr(request.state, 'user') else None
tester = user.username if user else None

# 获取请求参数
request_params = {
    **dict(request.query_params),
    **(await request.json() if request.method in ['POST', 'PUT', 'PATCH'] else {})
}

await repo_service._log_api_call(
    db=db,
    repo_id=str(repo.id),
    tester=tester,
    request_params=json.dumps(request_params),
    # ...
)
```

3. **更新前端页面**：在 `ConsumptionDetails.tsx` 中添加新列

```typescript
{
    title: '调用者',
    dataIndex: 'tester',
    key: 'tester',
    render: (tester: string) => <Tag color="purple">{tester || '-'}</Tag>,
},
{
    title: '请求参数',
    dataIndex: 'request_params',
    key: 'request_params',
    render: (params: string) => {
        if (!params) return '-';
        try {
            const parsed = JSON.parse(params);
            return (
                <Tooltip title={<pre>{JSON.stringify(parsed, null, 2)}</pre>}>
                    <Tag color="blue">查看参数</Tag>
                </Tooltip>
            );
        } catch {
            return params;
        }
    },
},
```

**详细说明**：详见 [35_开发过程中的FAQ_更新01.md](35_开发过程中的FAQ_更新01.md)

---

### Q58: 如何添加仓库到集成测试页面？

**问题描述**：想在API测试工具中添加新的仓库选项，应该如何操作？

**解决方案**：

**步骤1：创建仓库配置文件**

在 `web/src/config/repos/` 目录下创建新的配置文件，如 `example.config.ts`：

```typescript
import { Repository } from '../../../types/api-tester';

export const exampleRepository: Repository = {
  id: 'example-api',
  slug: 'example-api',  // 必须与数据库 repositories 表的 slug 一致
  name: '示例API',
  description: 'API描述',
  icon: 'api',
  category: 'self',  // self=自研, third=第三方
  baseUrl: '/api/v1/repositories/example-api',
  apiUrl: 'http://localhost:8000',
  authType: 'api_key',
  authHeader: 'X-Access-Key',
  enabled: true,
  version: '1.0.0',
  endpoints: [
    {
      id: 'endpoint1',
      name: '示例接口',
      description: '接口描述',
      path: '/example',
      method: 'GET',
      params: [
        {
          name: 'param1',
          type: 'string',
          required: true,
          description: '参数描述',
          placeholder: '请输入',
          in: 'query'
        }
      ],
      tags: ['示例']
    }
  ]
};
```

**步骤2：在仓库索引中注册**

编辑 `web/src/config/repositories.config.ts`：

```typescript
import { exampleRepository } from './repos/example.config';

export const repositories = [
  exampleRepository,
  // ... 其他仓库
];
```

**步骤3：确保数据库有对应记录**

```sql
INSERT INTO repositories (id, name, slug, endpoint_url, status)
VALUES ('example-api', '示例API', 'example-api', 'http://目标服务地址', 'online');
```

**步骤4：重启前端服务**

刷新页面后，新仓库会出现在测试工具的选择框中。

**注意事项**：
1. `slug` 必须与数据库中 `repositories` 表的 `slug` 字段一致
2. `endpoint_url` 必须指向实际的后端服务地址
3. 如果是第三方API，`category` 应设置为 `third`

**详细说明**：详见 [35_开发过程中的FAQ_更新01.md](35_开发过程中的FAQ_更新01.md)

---

**FAQ文档结束**

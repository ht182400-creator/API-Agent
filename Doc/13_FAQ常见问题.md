# API服务改造项目 - 常见问题解答（FAQ）

## 文档控制

| 项目 | 内容 |
|------|------|
| 文档编号 | FAQ-API-2026-001 |
| 版本号 | V1.8 |
| 创建日期 | 2026-04-16 |
| 更新日期 | 2026-04-19 |

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
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

**测试账号**：

| 角色 | 邮箱 | 密码 |
|------|------|------|
| 管理员 | admin@example.com | admin123 |
| 开发者 | developer@example.com | dev123456 |
| 仓库所有者 | owner@example.com | owner123456 |

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
API 服务已启动，但无法访问 http://localhost:8080

**排查步骤**：

1. **确认服务正在运行**
```powershell
# 检查端口监听
netstat -an | findstr "8080"
```

2. **检查防火墙**
```powershell
# 允许端口通过防火墙
netsh advfirewall firewall add rule name="API Platform" dir=in action=allow protocol=tcp localport=8080
```

3. **查看启动日志**
```powershell
# 检查是否有错误
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
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
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8080

# API 文档地址
# http://localhost:8080/docs
# http://localhost:8080/redoc
```

### 测试登录
```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

---

**FAQ文档结束**

| 版本 | 日期 | 更新内容 | 作者 |
|------|------|---------|------|
| V1.0 | 2026-04-16 | 初始版本 | - |
| V1.1 | 2026-04-18 | 新增第六章：部署环境问题（Q19-Q25）| AI Assistant |
| V1.2 | 2026-04-18 | 新增FAQ汇总列表、Q26登录失败提示说明 | AI Assistant |

如需补充问题，请联系项目组。

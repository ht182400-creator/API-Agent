# API服务改造项目 - 常见问题解答（FAQ）

## 文档控制

| 项目 | 内容 |
|------|------|
| 文档编号 | FAQ-API-2026-001 |
| 版本号 | V1.0 |
| 创建日期 | 2026-04-16 |

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

如需补充问题，请联系项目组。

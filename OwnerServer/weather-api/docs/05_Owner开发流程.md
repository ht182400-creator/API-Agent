# Weather API Owner 开发指南

## 目录

1. [概述](#1-概述)
2. [开发环境](#2-开发环境)
3. [代码结构](#3-代码结构)
4. [开发规范](#4-开发规范)
5. [测试指南](#5-测试指南)
6. [提交审核](#6-提交审核)

---

## 1. 概述

### 1.1 文档目的

本文档为 API 产品 Owner 提供 Weather API 的开发指导。

### 1.2 目标读者

- API 产品 Owner
- 后端开发工程师

---

## 2. 开发环境

### 2.1 环境要求

| 组件 | 版本要求 |
|------|----------|
| Python | 3.10+ |
| PostgreSQL | 14+ |
| Redis | 6+ |
| Docker | 20+ |

### 2.2 项目初始化

```bash
# 克隆项目
git clone <repository-url>
cd OwnerServer/weather-api

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python scripts/init_db.py
```

**⚠️ 常见问题**：如果启动时报 `ModuleNotFoundError`，请手动安装缺失的依赖：

```bash
pip install loguru pydantic-settings
```

### 2.3 依赖说明

| 依赖包 | 版本 | 说明 |
|--------|------|------|
| fastapi | 0.109.0 | Web 框架 |
| uvicorn | 0.27.0 | ASGI 服务器 |
| pydantic | 2.5.3 | 数据验证 |
| pydantic-settings | 2.1.0 | 配置管理 |
| httpx | 0.26.0 | HTTP 客户端 |
| python-dotenv | 1.0.0 | 环境变量加载 |
| loguru | 0.7.2 | 日志库 |

### 2.4 环境变量配置

创建 `.env` 文件：

```env
# 应用配置
APP_NAME=Weather API
APP_VERSION=1.0.0
DEBUG=false

# 服务器配置
HOST=0.0.0.0
PORT=8000

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/weather_api.log

# 数据源配置
WEATHER_API_URL=https://api.weather.gov.cn
WEATHER_API_KEY=your_api_key

# 缓存配置
CACHE_ENABLED=true
CACHE_TTL=1800

# 限流配置
RATE_LIMIT_PER_MINUTE=60
```

---

## 3. 代码结构

### 3.1 目录结构

```
src/
├── __init__.py           # 包初始化
├── main.py               # FastAPI 应用入口
├── config.py             # 配置管理
├── endpoints/            # API 端点
│   ├── __init__.py
│   └── weather.py        # 天气 API 路由
├── models/               # 数据模型
│   ├── __init__.py
│   ├── request.py        # 请求模型
│   └── response.py       # 响应模型
├── services/            # 业务服务
│   ├── __init__.py
│   └── weather_service.py
└── utils/               # 工具函数
    ├── __init__.py
    └── helpers.py
```

### 3.2 核心文件说明

| 文件 | 职责 |
|------|------|
| `main.py` | FastAPI 应用初始化、路由注册、中间件配置 |
| `config.py` | 环境变量读取、配置管理 |
| `endpoints/weather.py` | API 路由定义、请求处理 |
| `models/request.py` | 请求参数验证模型 |
| `models/response.py` | 响应数据结构模型 |
| `services/weather_service.py` | 天气数据获取、缓存处理 |

---

## 4. 开发规范

### 4.1 API 设计规范

#### 路由命名

```
GET  /weather/current    # 实时天气
GET  /weather/forecast   # 天气预报
GET  /weather/aqi        # 空气质量
GET  /weather/alerts     # 天气预警
```

#### 请求参数

- 必填参数使用 Path 或 Query(..., ...)
- 可选参数设置默认值
- 添加参数描述和示例

```python
@router.get("/current")
async def get_current_weather(
    city: str = Query(..., description="城市名称", min_length=1),
    unit: str = Query(default="c", description="温度单位")
):
    pass
```

#### 响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "request_id": "req_xxx",
  "timestamp": 1745210400
}
```

### 4.2 错误处理规范

| HTTP 状态码 | 使用场景 |
|-------------|----------|
| 200 | 成功响应 |
| 400 | 参数错误 |
| 401 | 未授权 |
| 403 | 权限不足 |
| 404 | 资源未找到 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |

```python
try:
    data = await weather_service.get_current_weather(city)
    return {"code": 200, "data": data}
except ValueError as e:
    raise HTTPException(status_code=404, detail="城市未找到")
except Exception as e:
    logger.error(f"服务异常: {str(e)}")
    raise HTTPException(status_code=500, detail="服务器内部错误")
```

### 4.3 日志规范

```python
from loguru import logger

# 记录信息
logger.info(f"获取天气成功: {city}")

# 记录警告
logger.warning(f"缓存未命中: {city}")

# 记录错误
logger.error(f"获取天气失败: {str(e)}")
```

### 4.4 代码注释规范

```python
def get_current_weather(city: str) -> dict:
    """
    获取实时天气数据
    
    Args:
        city: 城市名称（支持中文或拼音）
    
    Returns:
        实时天气数据字典，包含以下字段：
        - city: 城市名称
        - temperature: 温度
        - weather: 天气状况
        ...
    
    Raises:
        ValueError: 城市不存在时抛出
    
    Example:
        >>> data = await get_current_weather("北京")
        >>> print(data["temperature"])
        25
    """
    pass
```

---

## 5. 测试指南

### 5.1 单元测试

```python
# tests/test_weather_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_current_weather():
    """测试实时天气查询"""
    response = await client.get("/api/v1/weather/current?city=北京")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "temperature" in data["data"]
```

### 5.2 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_weather_api.py -v

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

### 5.3 测试清单

| 测试项 | 描述 | 优先级 |
|--------|------|--------|
| 正常查询 | 输入正确城市返回数据 | P0 |
| 城市不存在 | 输入错误城市返回 404 | P0 |
| 参数校验 | 缺少必填参数返回 422 | P1 |
| 限流测试 | 超过 QPS 返回 429 | P1 |
| 认证测试 | 无 API Key 返回 401 | P0 |

---

## 6. 提交审核

### 6.1 提交前检查

- [ ] 所有测试通过
- [ ] 代码符合规范
- [ ] API 文档已更新
- [ ] 无敏感信息泄露
- [ ] 日志级别设置正确

### 6.2 提交信息格式

```
feat(weather-api): 添加实时天气查询接口

- 新增 GET /api/v1/weather/current 接口
- 新增温度单位转换功能
- 添加城市名称模糊匹配
- 完善错误处理和日志记录

Closes #123
```

### 6.3 审核流程

```
代码提交 → 自动检查 → Owner 审核 → 测试环境验证 → 生产发布
```

---

**文档结束**

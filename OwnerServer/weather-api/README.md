# Weather API 产品开发指南

## 目录结构

```
OwnerServer/weather-api/
├── README.md                    # 项目说明
├── requirements.txt             # Python 依赖
├── src/                         # 源代码
│   ├── __init__.py
│   ├── main.py                  # FastAPI 应用入口
│   ├── config.py                # 配置管理
│   ├── endpoints/               # API 端点
│   │   ├── __init__.py
│   │   └── weather.py          # 天气 API 路由
│   ├── models/                  # 数据模型
│   │   ├── __init__.py
│   │   ├── request.py          # 请求模型
│   │   └── response.py         # 响应模型
│   ├── services/               # 业务服务
│   │   ├── __init__.py
│   │   ├── weather_service.py  # 天气数据服务
│   │   └── aqi_service.py      # 空气质量服务
│   └── utils/                   # 工具函数
│       ├── __init__.py
│       └── helpers.py           # 辅助函数
├── tests/                       # 测试文件
│   ├── __init__.py
│   ├── test_weather_api.py      # API 测试
│   └── test_services.py         # 服务测试
├── scripts/                     # 脚本
│   └── init_db.py               # 数据库初始化
├── deploy/                      # 部署配置
│   ├── docker-compose.yml       # Docker Compose 配置
│   ├── Dockerfile               # Docker 镜像
│   └── nginx.conf               # Nginx 配置
└── docs/                        # 文档
    ├── 01_需求规格说明书.md
    ├── 02_API产品设计.md
    └── 03_发布说明_v1.0.0.md
```

## 快速开始

### 前置要求

- Python 3.10+
- PostgreSQL 14+（可选）
- Redis 6+（可选）

### 安装依赖

```bash
# 进入项目目录
cd OwnerServer/weather-api

# 安装依赖
pip install -r requirements.txt

# 如果启动时报 ModuleNotFoundError，手动安装缺失的依赖
pip install loguru pydantic-settings
```

### 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

### 启动服务

```bash
# 开发环境（使用 8001 端口，避免与 API 平台冲突）
uvicorn src.main:app --reload --host 0.0.0.0 --port 8001

# Docker 环境
docker-compose up -d
```

### 运行测试

```bash
pytest tests/ -v
```

## Owner 操作流程

### 1. 创建 API 产品

1. 登录 Owner Portal
2. 点击「创建 API 产品」
3. 填写产品信息：
   - 产品名称：Weather API
   - API 前缀：/api/v1/weather
   - 定价策略：免费版/专业版/企业版
4. 创建后获得 Product ID

### 2. 开发 API

按照 `src/` 目录下的代码结构实现接口：

- `endpoints/weather.py` - 定义 API 路由
- `services/` - 实现业务逻辑
- `models/` - 定义数据模型

### 3. 沙箱测试

1. 在控制台创建测试应用
2. 获取测试 API Key
3. 调用沙箱环境测试

### 4. 发布生产

1. 提交代码审核
2. 通过后点击「发布」
3. 配置生产环境 API Key
4. 监控调用数据

## 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| API 平台后端 | 8000 | 通用 API 服务平台后端 |
| Weather API | 8001 | Owner 开发的天气 API 产品 |

> ⚠️ **注意**：两个服务使用不同端口，不会冲突。Weather API 部署到平台后，由平台的网关统一管理。

## 相关文档

- [需求规格说明书](./docs/01_需求规格说明书.md)
- [API 设计文档](./docs/02_API产品设计.md)
- [发布说明](./docs/03_发布说明_v1.0.0.md)
- [Owner 部署流程](./docs/04_Owner部署流程.md)
- [Owner 开发流程](./docs/05_Owner开发流程.md)
- [Owner 平台操作指南](./docs/06_Owner平台操作指南.md) ⭐ **详细部署步骤**

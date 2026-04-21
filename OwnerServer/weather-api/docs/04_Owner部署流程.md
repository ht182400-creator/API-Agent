# Weather API Owner 部署流程指南

## 概述

本文档指导 API 产品 Owner 如何将 Weather API 部署到通用 API 服务平台。

---

## 1. 部署前准备

### 1.1 前提条件

| 条件 | 要求 |
|------|------|
| 平台账号 | Owner 角色权限 |
| 代码仓库 | 已完成开发和测试的代码 |
| 产品配置 | API 定价和计费策略 |
| 端口配置 | Weather API 使用 8001，避免与平台 8000 冲突 |

### 1.2 检查清单

- [ ] 代码已完成本地测试
- [ ] API 文档已完成
- [ ] 定价策略已配置
- [ ] 测试环境已验证

---

## 2. 开发阶段

### 2.1 代码开发

按照项目结构开发 API 代码：

```
OwnerServer/weather-api/
├── src/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── endpoints/           # API 路由
│   ├── models/              # 数据模型
│   └── services/            # 业务逻辑
├── tests/                   # 测试代码
└── deploy/                  # 部署配置
```

### 2.2 本地测试

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest tests/ -v

# 启动服务
uvicorn src.main:app --reload --port 8000

# 测试接口
curl http://localhost:8000/api/v1/weather/current?city=北京
```

---

## 3. 平台部署流程

### 3.1 步骤一：创建 API 产品

1. 登录 Owner Portal
2. 进入「API 产品管理」
3. 点击「创建新产品」
4. 填写基本信息：

| 字段 | 示例 |
|------|------|
| 产品名称 | Weather API |
| API 前缀 | /api/v1/weather |
| 产品分类 | 天气服务 |
| 产品描述 | 提供实时天气查询... |
| 定价策略 | 免费版/专业版/企业版 |

5. 保存后获得 Product ID

### 3.2 步骤二：配置 API 路由

1. 进入产品详情
2. 点击「API 路由管理」
3. 添加路由配置：

```yaml
# 路由配置示例
routes:
  - path: /current
    method: GET
    description: 实时天气查询
    auth_required: true
    rate_limit: 60/min
    
  - path: /forecast
    method: GET
    description: 天气预报查询
    auth_required: true
    rate_limit: 60/min
```

### 3.3 步骤三：部署代码

**方式一：Docker 部署**

```bash
cd deploy/

# 构建镜像
docker build -t weather-api:v1.0.0 -f Dockerfile ..

# 推送镜像
docker push registry.platform.com/owner/weather-api:v1.0.0

# 在平台上配置容器部署
```

**方式二：直接部署**

1. 将代码打包上传到平台
2. 配置运行环境（Python 3.11）
3. 设置启动命令：`uvicorn src.main:app --host 0.0.0.0 --port 8000`

### 3.4 步骤四：配置认证

1. 进入「认证配置」
2. 配置 API Key 认证方式
3. 设置 Key 格式：`wa_{随机字符串}`
4. 配置 Key 有效期

### 3.5 步骤五：配置限流

| 套餐 | QPS 限制 | 每日限制 |
|------|----------|----------|
| 免费版 | 10 | 1,000 |
| 专业版 | 100 | 100,000 |
| 企业版 | 1000 | 无限制 |

---

## 4. 测试验证

### 4.1 沙箱环境测试

1. 创建测试应用
2. 获取测试 API Key
3. 调用测试接口：

```bash
# 测试实时天气
curl -X GET "https://sandbox.platform.com/api/v1/weather/current?city=北京" \
  -H "Authorization: Bearer test_key_xxxx"

# 预期响应
{
  "code": 200,
  "message": "success",
  "data": {
    "city": "北京",
    "weather": "晴",
    "temperature": 25
  }
}
```

### 4.2 生产环境测试

1. 切换到正式环境
2. 使用正式 API Key 测试
3. 验证计费功能

---

## 5. 监控与运维

### 5.1 监控指标

| 指标 | 告警阈值 | 说明 |
|------|----------|------|
| 响应时间 P95 | > 500ms | 性能监控 |
| 错误率 | > 1% | 错误监控 |
| QPS | > 阈值 80% | 限流预警 |
| CPU 使用率 | > 80% | 资源预警 |

### 5.2 日志查看

```bash
# 查看 API 日志
kubectl logs -f weather-api-xxx | grep "ERROR"

# 查看访问日志
tail -f /var/log/weather-api/access.log
```

---

## 6. 版本管理

### 6.1 发布新版本

1. 开发新功能
2. 更新版本号（如 v1.1.0）
3. 提交代码审核
4. 测试验证
5. 发布新版本
6. 监控运行状态

### 6.2 回滚操作

如遇问题，可快速回滚到上一版本：

1. 进入「版本管理」
2. 选择历史版本
3. 点击「回滚」
4. 确认回滚

---

## 7. 常见问题

### 7.1 部署失败

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 镜像构建失败 | 依赖安装错误 | 检查 requirements.txt |
| 端口冲突 | 8000 端口被占用 | 修改端口配置 |
| 启动失败 | 代码错误 | 查看启动日志 |

### 7.2 接口报错

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 401 未授权 | API Key 无效 | 检查 Key 配置 |
| 429 超限 | 请求过于频繁 | 调整限流策略 |
| 404 未找到 | 路由配置错误 | 检查路由配置 |

---

**文档结束**

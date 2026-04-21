# Weather API 测试工具 - src

## 快速开始

### 方式一：使用 Python HTTP 服务器（推荐）

```bash
cd src
python -m http.server 8080
# 访问 http://localhost:8080
```

### 方式二：使用 Node.js serve

```bash
cd src
npx serve .
# 访问 http://localhost:3000
```

### 方式三：直接打开 HTML 文件

直接用浏览器打开 `src/index.html` 文件即可使用。

## 目录结构

```
src/
├── index.html      # 主页面
├── css/
│   └── style.css   # 自定义样式
├── js/
│   └── app.js      # 核心逻辑
└── README.md       # 本文件
```

## 配置说明

首次使用需要配置：

1. **API Key**: 在页面上输入从 Developer Portal 获取的 API Key
2. **API 地址**: 默认 `http://localhost:8000/api/v1`
   - 开发环境：`http://localhost:8000/api/v1`
   - 生产环境：`https://api.platform.com/api/v1`

配置会自动保存在浏览器本地存储中。

## 功能说明

- 📡 **实时天气**: 获取当前天气数据
- 📅 **天气预报**: 获取未来天气预报
- 💨 **空气质量**: 获取 AQI 数据
- ⚠️ **天气预警**: 获取天气预警信息

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl + Enter | 发送请求 |
| Esc | 关闭弹窗 |

## API 端点

| 接口 | 方法 | 路径 | 必填参数 |
|------|------|------|----------|
| 实时天气 | GET | /weather/current | city |
| 天气预报 | GET | /weather/forecast | city, days(可选) |
| 空气质量 | GET | /weather/aqi | city |
| 天气预警 | GET | /weather/alerts | city |

## 技术栈

- HTML5
- Tailwind CSS (CDN)
- Vanilla JavaScript (ES6+)
- LocalStorage (数据持久化)

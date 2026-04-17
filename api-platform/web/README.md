# API Platform Web Console

通用API服务平台 - 前端管理控制台

## 技术栈

- **框架**: React 18 + TypeScript
- **路由**: React Router v6
- **状态管理**: Zustand
- **UI组件**: Ant Design 5
- **HTTP客户端**: Axios
- **构建工具**: Vite

## 项目结构

```
web/
├── public/                 # 静态资源
├── src/
│   ├── api/               # API调用
│   │   ├── client.ts      # API客户端
│   │   ├── auth.ts        # 认证API
│   │   ├── repo.ts        # 仓库API
│   │   ├── billing.ts     # 计费API
│   │   └── quota.ts       # 配额API
│   ├── components/         # 公共组件
│   │   ├── Layout/
│   │   ├── Header/
│   │   └── Form/
│   ├── pages/             # 页面
│   │   ├── auth/          # 认证页面
│   │   ├── developer/     # 开发者控制台
│   │   ├── owner/         # 仓库所有者控制台
│   │   └── admin/         # 管理员控制台
│   ├── stores/            # 状态管理
│   ├── hooks/             # 自定义Hooks
│   ├── types/             # TypeScript类型
│   ├── utils/             # 工具函数
│   └── App.tsx
└── package.json
```

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 访问地址

- 开发服务器: http://localhost:3000
- API代理: /api/v1/*

## 功能模块

### 开发者控制台

- API Key管理（创建、查看、禁用）
- 配额使用查看
- 调用日志查询
- 账单明细

### 仓库所有者控制台

- 仓库管理（创建、编辑、上下线）
- API接入配置
- 收益统计
- 调用分析

### 管理员控制台

- 用户管理
- 系统设置
- 运营数据
- 安全监控

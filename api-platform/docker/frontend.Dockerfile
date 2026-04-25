# 前端 Dockerfile - 多阶段构建
# 阶段1: 构建前端资源

FROM node:18-alpine AS builder

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV NODE_ENV=builder \
    NPM_CONFIG_LOGLEVEL=warn \
    NPM_CONFIG_REGISTRY=https://registry.npmmirror.com

# 复制依赖文件
COPY package*.json ./

# 安装依赖 (使用npm ci确保版本一致性)
RUN npm ci --only=production

# 复制源代码
COPY . .

# 构建生产版本
ARG BUILD_ENV=production
ARG VITE_API_URL=/api
ARG VITE_APP_TITLE=API Platform

ENV VITE_API_URL=${VITE_API_URL} \
    VITE_APP_TITLE=${VITE_APP_TITLE}

RUN npm run build

# 阶段2: 运行Nginx服务器

FROM nginx:alpine AS production

# 安装 curl (用于健康检查)
RUN apk add --no-cache curl

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制自定义 Nginx 配置
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/conf.d/default.conf /etc/nginx/conf.d/default.conf

# 创建非root用户
RUN adduser -D -u 1000 nginx-user && \
    chown -R nginx-user:nginx-user /usr/share/nginx/html && \
    chown -R nginx-user:nginx-user /var/log/nginx && \
    chown -R nginx-user:nginx-user /var/cache/nginx

# 切换到非root用户
USER nginx-user

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]

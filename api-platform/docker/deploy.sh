#!/bin/bash
# Docker Compose 部署脚本
# 使用方法: ./deploy.sh [dev|prod] [up|down|restart|logs|ps]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 默认环境
ENV=${1:-prod}
ACTION=${2:-up}

# 打印函数
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker 是否运行
check_docker() {
    print_info "检查 Docker 状态..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker 未运行，请启动 Docker Desktop 或 Docker Engine"
        exit 1
    fi
    print_info "Docker 运行正常"
}

# 检查环境变量文件
check_env_file() {
    if [ ! -f .env ]; then
        print_warn ".env 文件不存在，创建默认配置..."
        cp .env.example .env
        print_info "已创建 .env 文件，请根据需要修改配置"
        print_warn "请确保修改 POSTGRES_PASSWORD 和 REDIS_PASSWORD 等敏感信息"
    fi
}

# 加载环境变量
load_env() {
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
        print_info "已加载环境变量"
    fi
}

# 选择 docker-compose 文件
get_compose_file() {
    if [ "$ENV" = "dev" ]; then
        echo "docker-compose.yml -f docker-compose.dev.yml"
    else
        echo "docker-compose.yml"
    fi
}

# 启动服务
start_services() {
    print_info "启动 $ENV 环境服务..."
    local compose_file=$(get_compose_file)
    
    docker-compose -f $compose_file up -d
    
    print_info "等待服务启动..."
    sleep 5
    
    print_info "服务状态:"
    docker-compose -f $compose_file ps
    
    print_info "部署完成！"
    print_info "前端访问地址: <ADDRESS_REDACTED>
    print_info "后端API地址: <ADDRESS_REDACTED>
    print_info "MinIO控制台: <ADDRESS_REDACTED>
}

# 停止服务
stop_services() {
    print_info "停止 $ENV 环境服务..."
    local compose_file=$(get_compose_file)
    docker-compose -f $compose_file down
    print_info "服务已停止"
}

# 重启服务
restart_services() {
    print_info "重启 $ENV 环境服务..."
    local compose_file=$(get_compose_file)
    docker-compose -f $compose_file restart
    print_info "服务已重启"
}

# 查看日志
show_logs() {
    local compose_file=$(get_compose_file)
    docker-compose -f $compose_file logs -f ${3:-}
}

# 查看服务状态
show_status() {
    local compose_file=$(get_compose_file)
    docker-compose -f $compose_file ps
}

# 备份数据
backup_data() {
    print_info "开始备份数据..."
    
    local backup_dir="./backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p $backup_dir
    
    # 备份 PostgreSQL
    print_info "备份 PostgreSQL..."
    docker-compose exec -T postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > $backup_dir/postgres.sql
    
    # 备份 Redis
    print_info "备份 Redis..."
    docker-compose exec -T redis redis-cli --rdb /data/dump.rdb
    docker cp $(docker-compose ps -q redis):/data/dump.rdb $backup_dir/redis.rdb 2>/dev/null || true
    
    # 备份 MinIO
    print_info "备份 MinIO..."
    docker run --rm -v $(docker-compose ps -q minio):/data -v $PWD/$backup_dir:/backup alpine tar czf /backup/minio.tar.gz /data
    
    print_info "备份完成: $backup_dir"
}

# 恢复数据
restore_data() {
    if [ -z "$3" ]; then
        print_error "请指定备份目录: ./deploy.sh $ENV restore <backup_dir>"
        exit 1
    fi
    
    local backup_dir=$3
    
    if [ ! -d "$backup_dir" ]; then
        print_error "备份目录不存在: $backup_dir"
        exit 1
    fi
    
    print_warn "即将恢复数据，这将覆盖现有数据！"
    read -p "确认继续? (y/N): " confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        print_info "已取消"
        exit 0
    fi
    
    print_info "恢复 PostgreSQL..."
    docker-compose exec -T postgres psql -U $POSTGRES_USER $POSTGRES_DB < $backup_dir/postgres.sql
    
    print_info "恢复 Redis..."
    docker cp $backup_dir/redis.rdb $(docker-compose ps -q redis):/data/dump.rdb
    docker-compose restart redis
    
    print_info "恢复 MinIO..."
    docker run --rm -v $(docker-compose ps -q minio):/data -v $PWD/$backup_dir:/backup alpine tar xzf /backup/minio.tar.gz -C /
    docker-compose restart minio
    
    print_info "恢复完成"
}

# 清理资源
cleanup() {
    print_warn "即将停止服务并删除数据卷！"
    read -p "确认继续? (y/N): " confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        print_info "已取消"
        exit 0
    fi
    
    local compose_file=$(get_compose_file)
    docker-compose -f $compose_file down -v
    docker system prune -f
    
    print_info "清理完成"
}

# 主函数
main() {
    print_info "API Platform 部署脚本"
    print_info "环境: $ENV"
    print_info "操作: $ACTION"
    echo ""
    
    check_docker
    check_env_file
    load_env
    
    case $ACTION in
        up)
            start_services
            ;;
        down)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            show_logs
            ;;
        ps)
            show_status
            ;;
        backup)
            backup_data
            ;;
        restore)
            restore_data
            ;;
        cleanup)
            cleanup
            ;;
        *)
            print_error "未知操作: $ACTION"
            echo "使用方法: ./deploy.sh [dev|prod] [up|down|restart|logs|ps|backup|restore|cleanup]"
            exit 1
            ;;
    esac
}

# 执行主函数
main

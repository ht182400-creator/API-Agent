#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复 weather-api 仓库端点数据的脚本
使用同步数据库连接，避免 Windows 事件循环问题
"""

import sys
import os
import io

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import Session
from src.models.repository import Repository, RepoEndpoint

# 从环境变量或配置中获取数据库 URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/api_platform"
)


def main():
    """主函数"""
    # 设置输出编码为 UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("weather-api 端点数据修复脚本")
    print("=" * 60)
    
    # 创建同步引擎
    engine = create_engine(DATABASE_URL, echo=False)
    
    with Session(engine) as db:
        # 1. 查找 weather-api 仓库
        print("\n[1] 查找 weather-api 仓库...")
        result = db.execute(select(Repository).where(Repository.slug == "weather-api"))
        repo = result.scalar_one_or_none()
        
        if not repo:
            print("ERROR: 未找到 weather-api 仓库！")
            return
        
        repo_id = str(repo.id)
        print(f"OK: 找到仓库: {repo.name} (ID: {repo_id})")
        
        # 2. 查看当前端点
        print("\n[2] 检查现有端点...")
        result = db.execute(select(RepoEndpoint).where(RepoEndpoint.repo_id == repo_id))
        existing_endpoints = result.scalars().all()
        print(f"   现有端点数量: {len(existing_endpoints)}")
        
        for ep in existing_endpoints:
            print(f"   - {ep.method} {ep.path}")
        
        # 3. 删除旧端点
        print("\n[3] 删除旧端点...")
        if existing_endpoints:
            db.execute(delete(RepoEndpoint).where(RepoEndpoint.repo_id == repo_id))
            print("   OK: 已删除旧端点")
        
        # 4. 创建正确的端点
        print("\n[4] 创建新端点...")
        endpoints_data = [
            {
                "path": "/api/v1/weather/current",
                "method": "GET",
                "description": "获取当前天气"
            },
            {
                "path": "/api/v1/weather/forecast",
                "method": "GET",
                "description": "获取天气预报"
            },
            {
                "path": "/api/v1/weather/aqi",
                "method": "GET",
                "description": "获取AQI数据"
            },
            {
                "path": "/api/v1/weather/alerts",
                "method": "GET",
                "description": "获取预警信息"
            }
        ]
        
        for ep_data in endpoints_data:
            endpoint = RepoEndpoint(
                repo_id=repo_id,
                path=ep_data["path"],
                method=ep_data["method"],
                description=ep_data["description"]
            )
            db.add(endpoint)
            print(f"   OK: 添加端点: {ep_data['method']} {ep_data['path']}")
        
        # 5. 提交事务
        print("\n[5] 保存更改...")
        db.commit()
        print("   OK: 更改已保存")
        
        # 6. 验证（需要重新查询）
        print("\n[6] 验证结果...")
        db.expire_all()  # 清除缓存
        result = db.execute(select(RepoEndpoint).where(RepoEndpoint.repo_id == repo_id))
        final_endpoints = result.scalars().all()
        print(f"   最终端点数量: {len(final_endpoints)}")
        for ep in final_endpoints:
            print(f"   OK: {ep.method} {ep.path} - {ep.description}")
        
        # 7. 检查 endpoint_url
        print("\n[7] 检查后端地址配置...")
        db.expire_all()
        result = db.execute(select(Repository).where(Repository.slug == "weather-api"))
        repo = result.scalar_one_or_none()
        if repo and repo.endpoint_url:
            print(f"   OK: 后端地址: {repo.endpoint_url}")
        else:
            print("   WARNING: 后端地址未配置！")
            print("   请在 Owner Portal 中设置后端地址为: http://localhost:8001")
    
    print("\n" + "=" * 60)
    print("修复完成！")
    print("=" * 60)
    print("\n后续操作:")
    print("1. 刷新 Owner Portal 页面查看端点")
    print("2. 如果后端地址未配置，请在编辑页面设置 http://localhost:8001")
    print("3. 使用测试工具测试 API 调用")


if __name__ == "__main__":
    main()

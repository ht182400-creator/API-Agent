"""
修复 weather-api 仓库端点数据
运行: python scripts/fix_weather_endpoints.py
"""
import asyncio
import sys
sys.path.insert(0, 'd:/Work_Area/AI/API-Agent/api-platform')

from sqlalchemy import select, delete
from src.config.database import AsyncSessionLocal
from src.models.repository import Repository, RepoEndpoint, RepoLimits


async def fix_weather_endpoints():
    """修复 weather-api 仓库的端点数据"""
    print("开始修复 weather-api 端点数据...")
    
    async with AsyncSessionLocal() as db:
        # 1. 找到 weather-api 仓库
        result = await db.execute(
            select(Repository).where(Repository.slug == 'weather-api')
        )
        repo = result.scalar_one_or_none()
        
        if not repo:
            print("错误: 未找到 weather-api 仓库!")
            return
        
        print(f"找到仓库: {repo.name} (ID: {repo.id})")
        
        # 2. 删除现有的端点（如果有的话）
        result = await db.execute(
            delete(RepoEndpoint).where(RepoEndpoint.repo_id == repo.id)
        )
        print(f"删除了 {result.rowcount} 个旧端点")
        
        # 3. 创建新的端点
        weather_endpoints = [
            {
                "path": "/api/v1/weather/current",
                "method": "GET",
                "description": "获取当前天气",
                "category": "weather",
                "display_order": 1,
                "enabled": True,
            },
            {
                "path": "/api/v1/weather/forecast",
                "method": "GET",
                "description": "获取天气预报",
                "category": "weather",
                "display_order": 2,
                "enabled": True,
            },
            {
                "path": "/api/v1/weather/aqi",
                "method": "GET",
                "description": "获取AQI数据",
                "category": "weather",
                "display_order": 3,
                "enabled": True,
            },
            {
                "path": "/api/v1/weather/alerts",
                "method": "GET",
                "description": "获取预警信息",
                "category": "weather",
                "display_order": 4,
                "enabled": True,
            },
        ]
        
        for ep_data in weather_endpoints:
            endpoint = RepoEndpoint(repo_id=repo.id, **ep_data)
            db.add(endpoint)
            print(f"添加端点: {ep_data['method']} {ep_data['path']}")
        
        # 4. 确保有 limits 配置
        result = await db.execute(
            select(RepoLimits).where(RepoLimits.repo_id == repo.id)
        )
        existing_limits = result.scalar_one_or_none()
        
        if not existing_limits:
            limits = RepoLimits(
                repo_id=repo.id,
                rpm=1000,
                rph=10000,
                rpd=100000,
                burst_limit=50,
                concurrent_limit=10,
                daily_quota=50000,
                monthly_quota=1000000,
                request_timeout=30,
                connect_timeout=10,
            )
            db.add(limits)
            print("添加限流配置")
        
        await db.commit()
        print("\n修复完成!")
        
        # 5. 验证
        result = await db.execute(
            select(RepoEndpoint).where(RepoEndpoint.repo_id == repo.id)
        )
        endpoints = result.scalars().all()
        print(f"\n验证: weather-api 仓库现有 {len(endpoints)} 个端点")
        for ep in endpoints:
            print(f"  - {ep.method} {ep.path}")


async def cleanup_orphan_endpoints():
    """清理孤立端点（repo_id 不对应任何仓库的端点）"""
    print("\n检查孤立端点...")
    
    async with AsyncSessionLocal() as db:
        # 获取所有仓库 ID
        result = await db.execute(select(Repository.id))
        repo_ids = set(row[0] for row in result.fetchall())
        
        # 获取所有端点
        result = await db.execute(select(RepoEndpoint))
        all_endpoints = result.scalars().all()
        
        deleted = 0
        for ep in all_endpoints:
            if ep.repo_id not in repo_ids:
                print(f"删除孤立端点: {ep.id} -> {ep.path}")
                await db.delete(ep)
                deleted += 1
        
        if deleted > 0:
            await db.commit()
            print(f"删除了 {deleted} 个孤立端点")
        else:
            print("没有孤立端点")


if __name__ == "__main__":
    asyncio.run(fix_weather_endpoints())
    asyncio.run(cleanup_orphan_endpoints())

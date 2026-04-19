"""Seed endpoints and limits for existing repositories"""
import asyncio
import sys
sys.path.insert(0, 'd:/Work_Area/AI/API-Agent/api-platform')

from sqlalchemy import select, text
from src.config.database import AsyncSessionLocal
from src.models.repository import Repository, RepoEndpoint, RepoLimits

async def seed_existing_repos():
    """Add endpoints and limits to existing repositories"""
    print("Seeding endpoints and limits for existing repositories...")
    
    async with AsyncSessionLocal() as db:
        # Get all repositories
        result = await db.execute(select(Repository))
        repos = result.scalars().all()
        
        for repo in repos:
            # Check if endpoints already exist
            result = await db.execute(
                select(RepoEndpoint).where(RepoEndpoint.repo_id == repo.id)
            )
            existing_endpoints = result.scalars().all()
            
            if not existing_endpoints:
                print(f"Adding endpoints for: {repo.name}")
                # Add default endpoints based on repo type
                endpoints_data = get_endpoints_for_repo(repo)
                for ep_data in endpoints_data:
                    endpoint = RepoEndpoint(
                        repo_id=repo.id,
                        **ep_data
                    )
                    db.add(endpoint)
            
            # Check if limits already exist
            result = await db.execute(
                select(RepoLimits).where(RepoLimits.repo_id == repo.id)
            )
            existing_limits = result.scalar_one_or_none()
            
            if not existing_limits:
                print(f"Adding limits for: {repo.name}")
                limits_data = get_limits_for_repo(repo)
                limits = RepoLimits(repo_id=repo.id, **limits_data)
                db.add(limits)
        
        await db.commit()
        print("Done!")


def get_endpoints_for_repo(repo):
    """Get default endpoints based on repository type"""
    endpoints_map = {
        "openai-gpt4": [
            {"path": "/v1/chat/completions", "method": "POST", "description": "Chat completions", "category": "chat", "display_order": 1},
            {"path": "/v1/completions", "method": "POST", "description": "Text completions", "category": "completion", "display_order": 2},
            {"path": "/v1/embeddings", "method": "POST", "description": "Text embeddings", "category": "embedding", "display_order": 3},
            {"path": "/v1/models", "method": "GET", "description": "List available models", "category": "models", "display_order": 4},
        ],
        "anthropic-claude": [
            {"path": "/v1/messages", "method": "POST", "description": "Send message to Claude", "category": "chat", "display_order": 1},
            {"path": "/v1/models", "method": "GET", "description": "List available models", "category": "models", "display_order": 2},
            {"path": "/v1/count_tokens", "method": "POST", "description": "Count tokens", "category": "tokens", "display_order": 3},
        ],
        "vision-api": [
            {"path": "/ocr/text", "method": "POST", "description": "文字识别OCR", "category": "ocr", "display_order": 1},
            {"path": "/ocr/document", "method": "POST", "description": "文档识别", "category": "ocr", "display_order": 2},
            {"path": "/analyze/image", "method": "POST", "description": "图像分析", "category": "analyze", "display_order": 3},
            {"path": "/recognize/face", "method": "POST", "description": "人脸识别", "category": "recognize", "display_order": 4},
            {"path": "/detect/object", "method": "POST", "description": "物体检测", "category": "detect", "display_order": 5},
        ],
    }
    
    return endpoints_map.get(repo.slug, [
        {"path": "/chat", "method": "POST", "description": "通用对话接口", "category": "chat", "display_order": 1},
        {"path": "/analyze", "method": "POST", "description": "分析接口", "category": "analyze", "display_order": 2},
    ])


def get_limits_for_repo(repo):
    """Get default limits based on repository type"""
    limits_map = {
        "openai-gpt4": {
            "rpm": 3000,
            "rph": 30000,
            "rpd": 300000,
            "burst_limit": 100,
            "concurrent_limit": 20,
            "daily_quota": 100000,
            "monthly_quota": 2000000,
            "request_timeout": 60,
            "connect_timeout": 10,
        },
        "anthropic-claude": {
            "rpm": 2000,
            "rph": 20000,
            "rpd": 200000,
            "burst_limit": 80,
            "concurrent_limit": 15,
            "daily_quota": 80000,
            "monthly_quota": 1500000,
            "request_timeout": 60,
            "connect_timeout": 10,
        },
        "vision-api": {
            "rpm": 500,
            "rph": 5000,
            "rpd": 50000,
            "burst_limit": 50,
            "concurrent_limit": 10,
            "daily_quota": 20000,
            "monthly_quota": 400000,
            "request_timeout": 120,
            "connect_timeout": 30,
        },
    }
    
    return limits_map.get(repo.slug, {
        "rpm": 1000,
        "rph": 10000,
        "rpd": 100000,
        "burst_limit": 50,
        "concurrent_limit": 10,
        "daily_quota": 50000,
        "monthly_quota": 1000000,
        "request_timeout": 30,
        "connect_timeout": 10,
    })


if __name__ == "__main__":
    asyncio.run(seed_existing_repos())

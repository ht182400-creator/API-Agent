"""
Repository Service - 仓库服务
完整的API实现逻辑
"""

import uuid
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from src.models.repository import Repository
from src.models.api_key import APIKey
from src.core.exceptions import (
    NotFoundError,
    ValidationError,
)
from src.adapters.base import BaseAdapter
from src.adapters.http_adapter import HTTPAdapter
from src.adapters.grpc_adapter import GRPCAdapter


class RepoService:
    """仓库服务 - 核心业务逻辑"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._adapters: Dict[str, BaseAdapter] = {
            "http": HTTPAdapter(),
            "grpc": GRPCAdapter(),
        }

    async def list_repositories(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_public: bool = True,
        owner_id: Optional[str] = None,
    ) -> Tuple[List[Repository], int]:
        """
        获取仓库列表

        Args:
            page: 页码
            page_size: 每页数量
            category: 分类筛选
            search: 搜索关键词
            is_public: 是否公开
            owner_id: 所有者ID

        Returns:
            (仓库列表, 总数)
        """
        query = select(Repository)
        count_query = select(func.count(Repository.id))

        # 筛选条件
        filters = []
        if is_public is not None:
            filters.append(Repository.is_public == is_public)
        if category:
            filters.append(Repository.category == category)
        if owner_id:
            filters.append(Repository.owner_id == owner_id)
        if search:
            filters.append(
                or_(
                    Repository.name.ilike(f"%{search}%"),
                    Repository.description.ilike(f"%{search}%"),
                )
            )

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # 统计总数
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        query = query.order_by(Repository.created_at.desc())

        result = await self.db.execute(query)
        repositories = result.scalars().all()

        return list(repositories), total

    async def get_repository(self, repo_id: str) -> Repository:
        """
        获取仓库详情

        Args:
            repo_id: 仓库ID

        Returns:
            仓库对象
        """
        result = await self.db.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        repo = result.scalar_one_or_none()

        if not repo:
            raise NotFoundError(f"仓库不存在: {repo_id}")

        return repo

    async def get_repository_by_name(self, repo_name: str) -> Repository:
        """
        通过名称获取仓库

        Args:
            repo_name: 仓库名称

        Returns:
            仓库对象
        """
        result = await self.db.execute(
            select(Repository).where(Repository.name == repo_name)
        )
        repo = result.scalar_one_or_none()

        if not repo:
            raise NotFoundError(f"仓库不存在: {repo_name}")

        return repo

    async def create_repository(
        self,
        owner_id: str,
        name: str,
        description: str,
        category: str,
        adapter_type: str = "http",
        endpoint: str = "",
        auth_type: str = "none",
        auth_config: Optional[Dict] = None,
        pricing: Optional[Dict] = None,
        rate_limit: Optional[Dict] = None,
        is_public: bool = True,
        config: Optional[Dict] = None,
    ) -> Repository:
        """
        创建仓库

        Args:
            owner_id: 所有者ID
            name: 仓库名称
            description: 描述
            category: 分类
            adapter_type: 适配器类型
            endpoint: API端点
            auth_type: 认证类型
            auth_config: 认证配置
            pricing: 定价配置
            rate_limit: 速率限制
            is_public: 是否公开
            config: 其他配置

        Returns:
            创建的仓库对象
        """
        # 检查名称唯一性
        existing = await self.db.execute(
            select(Repository).where(Repository.name == name)
        )
        if existing.scalar_one_or_none():
            raise ValidationError(f"仓库名称已存在: {name}")

        # 创建仓库
        repo = Repository(
            name=name,
            display_name=name,
            description=description,
            category=category,
            owner_id=owner_id,
            adapter_type=adapter_type,
            endpoint=endpoint,
            auth_type=auth_type,
            auth_config=auth_config or {},
            pricing=pricing or {},
            rate_limit=rate_limit or {"rpm": 100, "rph": 1000},
            is_public=is_public,
            config=config or {},
            status="active",
        )

        self.db.add(repo)
        await self.db.flush()
        await self.db.refresh(repo)

        return repo

    async def update_repository(
        self,
        repo_id: str,
        owner_id: str,
        **kwargs,
    ) -> Repository:
        """
        更新仓库

        Args:
            repo_id: 仓库ID
            owner_id: 所有者ID（用于权限校验）
            **kwargs: 更新字段

        Returns:
            更新后的仓库
        """
        repo = await self.get_repository(repo_id)

        # 权限校验
        if repo.owner_id != owner_id:
            raise ValidationError("无权操作此仓库")

        # 更新字段
        allowed_fields = [
            "description", "category", "endpoint", "auth_type",
            "auth_config", "pricing", "rate_limit", "is_public", "config"
        ]
        for field in allowed_fields:
            if field in kwargs:
                setattr(repo, field, kwargs[field])

        repo.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(repo)

        return repo

    async def delete_repository(self, repo_id: str, owner_id: str) -> bool:
        """
        删除仓库

        Args:
            repo_id: 仓库ID
            owner_id: 所有者ID

        Returns:
            是否成功
        """
        repo = await self.get_repository(repo_id)

        if repo.owner_id != owner_id:
            raise ValidationError("无权操作此仓库")

        await self.db.delete(repo)
        await self.db.flush()

        return True

    async def get_repo_stats(self, repo_id: str) -> Dict[str, Any]:
        """
        获取仓库统计信息

        Args:
            repo_id: 仓库ID

        Returns:
            统计数据
        """
        repo = await self.get_repository(repo_id)

        # 统计调用量
        from src.models.billing import APICallLog

        today = datetime.now(timezone.utc).date()
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        # 今日调用量
        today_result = await self.db.execute(
            select(func.count(APICallLog.id)).where(
                and_(
                    APICallLog.repo_id == uuid.UUID(repo_id),
                    func.date(APICallLog.created_at) == today,
                )
            )
        )
        today_calls = today_result.scalar()

        # 本周调用量
        week_result = await self.db.execute(
            select(func.count(APICallLog.id)).where(
                and_(
                    APICallLog.repo_id == uuid.UUID(repo_id),
                    APICallLog.created_at >= week_ago,
                )
            )
        )
        week_calls = week_result.scalar()

        # 总调用量
        total_result = await self.db.execute(
            select(func.count(APICallLog.id)).where(
                APICallLog.repo_id == uuid.UUID(repo_id)
            )
        )
        total_calls = total_result.scalar()

        return {
            "repo_id": repo_id,
            "today_calls": today_calls,
            "week_calls": week_calls,
            "total_calls": total_calls,
            "status": repo.status,
        }

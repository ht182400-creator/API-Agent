"""
Quota Service - 配额服务
完整的API实现逻辑
"""

import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from src.models.billing import Quota, Account
from src.models.api_key import APIKey
from src.models.repository import Repository
from src.core.exceptions import QuotaExceededError, ValidationError, NotFoundError


class QuotaService:
    """配额服务 - 核心业务逻辑"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_quota(
        self,
        api_key_id: str,
        repo_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        检查配额使用情况

        Args:
            api_key_id: API Key ID
            repo_id: 仓库ID（可选）

        Returns:
            配额信息
        """
        # 获取API Key
        result = await self.db.execute(
            select(APIKey).where(APIKey.id == api_key_id)
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise NotFoundError(f"API Key不存在: {api_key_id}")

        # 计算当前使用量
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 今日使用量
        daily_query = select(
            func.count(Quota.id),
            func.sum(Quota.quota_used)
        ).where(
            and_(
                Quota.key_id == uuid.UUID(api_key_id),
                Quota.quota_type == "daily",
                Quota.reset_at >= today_start,
            )
        )
        daily_result = await self.db.execute(daily_query)
        daily_row = daily_result.one()
        daily_used = daily_row.count or 0
        daily_amount = float(daily_row.sum or 0)

        # 月度使用量
        monthly_query = select(
            func.count(Quota.id),
            func.sum(Quota.quota_used)
        ).where(
            and_(
                Quota.key_id == uuid.UUID(api_key_id),
                Quota.quota_type == "monthly",
                Quota.reset_at >= month_start,
            )
        )
        monthly_result = await self.db.execute(monthly_query)
        monthly_row = monthly_result.one()
        monthly_used = monthly_row.count or 0
        monthly_amount = float(monthly_row.sum or 0)

        # 计算剩余配额
        daily_limit = api_key.daily_quota or float('inf')
        monthly_limit = api_key.monthly_quota or float('inf')

        daily_remaining = max(0, daily_limit - daily_amount)
        monthly_remaining = max(0, monthly_limit - monthly_amount)

        return {
            "api_key_id": str(api_key_id),
            "daily": {
                "used": daily_amount,
                "limit": daily_limit if daily_limit != float('inf') else None,
                "remaining": daily_remaining if daily_limit != float('inf') else None,
            },
            "monthly": {
                "used": monthly_amount,
                "limit": monthly_limit if monthly_limit != float('inf') else None,
                "remaining": monthly_remaining if monthly_limit != float('inf') else None,
            },
        }

    async def consume_quota(
        self,
        api_key_id: str,
        amount: float = 1,
        repo_id: Optional[str] = None,
    ) -> Quota:
        """
        消耗配额

        Args:
            api_key_id: API Key ID
            amount: 消耗数量
            repo_id: 仓库ID

        Returns:
            配额使用记录
        """
        now = datetime.utcnow()

        # 检查并更新配额记录
        result = await self.db.execute(
            select(Quota).where(
                and_(
                    Quota.key_id == uuid.UUID(api_key_id),
                    Quota.quota_type == "daily",
                    Quota.repo_id == (uuid.UUID(repo_id) if repo_id else None)
                )
            )
        )
        quota = result.scalar_one_or_none()

        if quota:
            quota.quota_used += int(amount)
            quota.updated_at = now
        else:
            quota = Quota(
                user_id=uuid.uuid4(),  # 需要从API Key获取
                key_id=uuid.UUID(api_key_id),
                repo_id=uuid.UUID(repo_id) if repo_id else None,
                quota_type="daily",
                quota_limit=0,
                quota_used=int(amount),
                reset_type="daily",
                reset_at=now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
            )
            self.db.add(quota)

        await self.db.flush()
        await self.db.refresh(quota)

        return quota

    async def set_quota(
        self,
        api_key_id: str,
        daily_quota: Optional[int] = None,
        monthly_quota: Optional[int] = None,
    ) -> APIKey:
        """
        设置配额限制

        Args:
            api_key_id: API Key ID
            daily_quota: 每日配额
            monthly_quota: 每月配额

        Returns:
            更新后的API Key
        """
        result = await self.db.execute(
            select(APIKey).where(APIKey.id == api_key_id)
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise NotFoundError(f"API Key不存在: {api_key_id}")

        if daily_quota is not None:
            api_key.daily_quota = daily_quota
        if monthly_quota is not None:
            api_key.monthly_quota = monthly_quota

        await self.db.flush()
        await self.db.refresh(api_key)

        return api_key

    async def reset_quota(
        self,
        api_key_id: str,
        period_type: str = "all",
    ) -> bool:
        """
        重置配额

        Args:
            api_key_id: API Key ID
            period_type: 重置类型 (daily/monthly/all)

        Returns:
            是否成功
        """
        query = select(Quota).where(
            Quota.key_id == uuid.UUID(api_key_id)
        )

        if period_type == "daily":
            today_start = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            query = query.where(
                and_(
                    Quota.quota_type == "daily",
                    Quota.reset_at >= today_start,
                )
            )
        elif period_type == "monthly":
            month_start = datetime.utcnow().replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            query = query.where(
                and_(
                    Quota.quota_type == "monthly",
                    Quota.reset_at >= month_start,
                )
            )

        result = await self.db.execute(query)
        quotas = result.scalars().all()

        for quota in quotas:
            quota.quota_used = 0
            quota.updated_at = datetime.utcnow()

        await self.db.flush()
        return True

    async def get_usage_history(
        self,
        api_key_id: str,
        period_type: str = "daily",
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        获取配额使用历史

        Args:
            api_key_id: API Key ID
            period_type: 周期类型
            days: 天数

        Returns:
            使用历史列表
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        query = select(
            Quota.reset_at,
            func.sum(Quota.quota_used).label("total_used"),
            func.count(Quota.id).label("call_count"),
        ).where(
            and_(
                Quota.key_id == uuid.UUID(api_key_id),
                Quota.quota_type == period_type,
                Quota.updated_at >= start_date,
            )
        ).group_by(
            Quota.reset_at
        ).order_by(
            Quota.reset_at
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "date": row.reset_at.date().isoformat() if row.reset_at else None,
                "total_used": float(row.total_used or 0),
                "call_count": row.call_count,
            }
            for row in rows
        ]

    async def get_top_repos(
        self,
        api_key_id: str,
        limit: int = 10,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        获取使用量最高的仓库

        Args:
            api_key_id: API Key ID
            limit: 返回数量
            days: 天数

        Returns:
            仓库使用列表
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        query = select(
            Quota.repo_id,
            func.sum(Quota.quota_used).label("total_used"),
            func.count(Quota.id).label("call_count"),
        ).where(
            and_(
                Quota.key_id == uuid.UUID(api_key_id),
                Quota.repo_id.isnot(None),
                Quota.updated_at >= start_date,
            )
        ).group_by(
            Quota.repo_id
        ).order_by(
            func.sum(Quota.quota_used).desc()
        ).limit(limit)

        result = await self.db.execute(query)
        rows = result.all()

        top_repos = []
        for row in rows:
            repo_id = str(row.repo_id)
            # 获取仓库名称
            repo_result = await self.db.execute(
                select(Repository).where(Repository.id == uuid.UUID(repo_id))
            )
            repo = repo_result.scalar_one_or_none()
            
            top_repos.append({
                "repo_id": repo_id,
                "repo_name": repo.name if repo else "Unknown",
                "total_used": float(row.total_used or 0),
                "call_count": row.call_count,
            })

        return top_repos

    async def create_free_quota(
        self,
        user_id: str,
        daily_quota: int = 100,
        monthly_quota: int = 1000,
        description: str = "新用户免费配额",
    ) -> APIKey:
        """
        为新用户创建免费配额API Key

        Args:
            user_id: 用户ID
            daily_quota: 每日配额
            monthly_quota: 每月配额
            description: 描述

        Returns:
            创建的API Key
        """
        from src.services.auth_service import AuthService

        auth_service = AuthService(self.db)
        api_key, secret = await auth_service.create_api_key(
            user_id=user_id,
            name=f"免费配额Key",
            auth_type="api_key",
            daily_quota=daily_quota,
            monthly_quota=monthly_quota,
        )

        return await self.db.execute(
            select(APIKey).where(APIKey.id == uuid.UUID(api_key))
        )

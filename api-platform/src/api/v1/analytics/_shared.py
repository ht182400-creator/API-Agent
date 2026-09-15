"""
Analytics 子域共享设施（P1-4 拆分产物）

本模块集中放置 `/analytics/*` 各端点共用的常量、权限校验、可见范围解析与缓存作用域构造。
拆分自原 `src/api/v1/analytics.py`（716 行），**业务逻辑逐字未变**，仅移动位置。
"""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logging_config import get_logger
from src.core.exceptions import AuthorizationError
from src.models.repository import Repository
from src.models.user import User
from src.services.permission_service import PermissionService

logger = get_logger("analytics")

# 分析结果缓存时长（秒）：统计类接口可容忍 1 分钟延迟，换取数据库压力大幅下降
ANALYTICS_CACHE_TTL_SECONDS = 60

# "全部时间"统计的起点锚点：远早于任何真实数据，等价于"无下界"
ALL_TIME_START_UTC = datetime(1970, 1, 1, tzinfo=timezone.utc)


def cache_scope(current_user: User, user_repo_ids: Optional[List[uuid.UUID]]) -> str:
    """
    构造缓存作用域标识 —— **必须**体现数据可见范围，否则不同用户会互相串号（越权）。

    管理员：全局数据 → ``admin``
    开发者：仅自己仓库 → ``user:{id}:{仓库集合指纹}``
        （带指纹：仓库增删后旧缓存 key 自动变化，不会继续命中过期范围的数据）
    """
    if user_repo_ids is None:
        return "admin"
    fingerprint = hashlib.md5(
        ",".join(sorted(str(repo) for repo in user_repo_ids)).encode("utf-8")
    ).hexdigest()[:8]
    return f"user:{current_user.id}:{fingerprint}"


def check_analytics_permission(current_user: User):
    """检查是否有数据分析权限（管理员或开发者）"""
    if not PermissionService.is_developer(current_user):
        raise AuthorizationError("需要开发者或管理员权限")


def is_admin_user(current_user: User) -> bool:
    """检查是否为管理员（管理员可看全局数据）"""
    return PermissionService.is_admin(current_user)


async def get_user_repo_ids(db: AsyncSession, current_user: User) -> List[uuid.UUID]:
    """获取用户可以访问的仓库ID列表（非管理员只能访问自己创建的仓库）"""
    if is_admin_user(current_user):
        # 管理员可以访问所有仓库
        return None  # None 表示不限制

    # 非管理员只能访问自己创建的仓库
    result = await db.execute(
        select(Repository.id).where(Repository.owner_id == current_user.id)
    )
    return list(result.scalars().all())

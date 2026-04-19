"""Admin API - 管理员专用接口"""

from typing import Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
from functools import lru_cache

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_, cast, Numeric
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.user import User
from src.models.repository import Repository
from src.models.api_key import APIKey
from src.models.billing import Account, Bill
from src.schemas.response import BaseResponse
from src.services.auth_service import get_current_admin_user

router = APIRouter(tags=["管理员"])

# 简单的内存缓存
_stats_cache = {"data": None, "timestamp": 0}
_CACHE_TTL = 300  # 缓存5分钟


def _get_cached_stats():
    """获取缓存的统计数据"""
    now = datetime.utcnow().timestamp()
    if _stats_cache["data"] and (now - _stats_cache["timestamp"]) < _CACHE_TTL:
        return _stats_cache["data"]
    return None


def _set_cached_stats(data):
    """设置统计数据缓存"""
    _stats_cache["data"] = data
    _stats_cache["timestamp"] = datetime.utcnow().timestamp()


# ==================== 统计接口 ====================

class AdminDashboardStats(BaseModel):
    """管理员仪表板统计数据"""
    total_users: int
    active_users: int
    total_repos: int
    today_new_users: int
    total_api_keys: int
    total_revenue: float
    today_calls: int


@router.get("/dashboard/stats", response_model=BaseResponse[AdminDashboardStats])
async def get_admin_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
    refresh: bool = Query(False, description="是否强制刷新缓存"),
):
    """
    获取管理员仪表板统计数据
    
    返回管理员可见的统计信息，包括用户数、仓库数等。
    注意：管理员只能看到非超级管理员的数据。
    """
    # 检查缓存（除非强制刷新）
    if not refresh:
        cached = _get_cached_stats()
        if cached:
            return BaseResponse(data=cached)
    
    # 统计用户总数（排除超级管理员）
    total_users_result = await db.execute(
        select(func.count(User.id)).where(User.user_type != "super_admin")
    )
    total_users = total_users_result.scalar() or 0
    
    # 统计活跃用户（30天内有登录，排除超级管理员）
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.last_login_at >= thirty_days_ago,
                User.user_type != "super_admin"
            )
        )
    )
    active_users = active_users_result.scalar() or 0
    
    # 统计今日新增用户（排除超级管理员）
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_new_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.created_at >= today_start,
                User.user_type != "super_admin"
            )
        )
    )
    today_new_users = today_new_result.scalar() or 0
    
    # 统计仓库总数
    repos_result = await db.execute(select(func.count(Repository.id)))
    total_repos = repos_result.scalar() or 0
    
    # 统计 API Keys 总数
    keys_result = await db.execute(select(func.count(APIKey.id)))
    total_api_keys = keys_result.scalar() or 0
    
    # 统计总收入（所有账户余额之和，需要转换为数字）
    revenue_result = await db.execute(
        select(func.sum(cast(Account.balance, Numeric)))
    )
    total_revenue = revenue_result.scalar() or Decimal("0")
    
    # 今日调用次数（从 api_call_logs 表统计）
    from src.models.billing import APICallLog
    today_calls_result = await db.execute(
        select(func.count(APICallLog.id)).where(
            func.date(APICallLog.created_at) == datetime.utcnow().date()
        )
    )
    today_calls = today_calls_result.scalar() or 0
    
    data = {
        "total_users": total_users,
        "active_users": active_users,
        "total_repos": total_repos,
        "today_new_users": today_new_users,
        "total_api_keys": total_api_keys,
        "total_revenue": float(total_revenue),
        "today_calls": today_calls,
    }
    
    # 设置缓存
    _set_cached_stats(data)
    
    return BaseResponse(data=data)


# ==================== 用户管理接口（管理员版） ====================

class AdminUserListItem(BaseModel):
    """管理员可查看的用户列表项"""
    id: str
    username: Optional[str]
    email: str
    phone: Optional[str]
    user_type: str
    role: str
    user_status: str
    vip_level: int
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.get("/users")
async def list_admin_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = Query(None, description="搜索关键词（用户名/邮箱）"),
    user_type: Optional[str] = Query(None, description="用户类型过滤"),
    user_status: Optional[str] = Query(None, description="状态过滤"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    获取用户列表（管理员版）
    
    管理员只能查看和操作非超级管理员的用户。
    """
    # 构建查询条件（排除超级管理员）
    conditions = [User.user_type != "super_admin"]
    
    if keyword:
        conditions.append(
            or_(
                User.username.ilike(f"%{keyword}%"),
                User.email.ilike(f"%{keyword}%")
            )
        )
    if user_type:
        conditions.append(User.user_type == user_type)
    if user_status:
        conditions.append(User.user_status == user_status)
    
    # 查询总数
    count_query = select(func.count(User.id)).where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    offset = (page - 1) * page_size
    query = select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size)
    query = query.where(and_(*conditions))
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    items = [
        AdminUserListItem(
            id=str(user.id),
            username=user.username,
            email=user.email,
            phone=user.phone,
            user_type=user.user_type,
            role=user.role,
            user_status=user.user_status,
            vip_level=user.vip_level,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
        for user in users
    ]
    
    return BaseResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


# 导入 or_ 函数
from sqlalchemy import or_

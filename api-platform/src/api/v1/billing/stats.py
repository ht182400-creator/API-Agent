"""
计费接口 —— 账单统计与趋势

由 `scripts/dev/split_api_router.py` 从 `src/api/v1/billing.py` 精确搬移生成，
函数体与原实现逐字一致（仅移动位置）。
"""

from datetime import datetime, timedelta
from fastapi import Depends, Query, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, Numeric, DECIMAL
from src.config.database import get_db
from src.schemas.response import BaseResponse
from src.services.auth_service import get_current_user
from src.models.user import User
from src.models.billing import Bill, APICallLog
from src.models.repository import Repository
from src.utils.environment import resolve_environment, env_match
from src.utils.time_range import CST, cst_now, cst_date_str
from src.config.logging_config import get_logger

logger = get_logger("billing")

router = APIRouter()




@router.get("/monthly-summary", response_model=BaseResponse[dict])
async def get_monthly_summary(
    year: int = Query(None),
    month: int = Query(None),
    environment: str = Query(None, description="环境过滤：simulation/production/all（all=不过滤）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取月度汇总

    默认统计当前环境，支持 environment=all 合并统计两个环境。
    """
    from datetime import datetime
    from src.config.settings import settings
    
    # 解析环境过滤（默认当前环境，支持 all 通配）
    environment = resolve_environment(environment)
    
    if year is None:
        year = cst_now().year
    if month is None:
        month = cst_now().month
    
    # 计算月份范围 (使用 datetime 对象而非字符串)
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # 查询充值总额 (amount 是字符串，需要转换) - 带环境过滤
    recharge_result = await db.execute(
        select(func.coalesce(func.sum(func.cast(Bill.amount, Numeric)), 0)).where(
            Bill.user_id == current_user.id,
            Bill.bill_type == "recharge",
            env_match(Bill.environment, environment),
            Bill.created_at >= start_date,
            Bill.created_at < end_date,
        )
    )
    total_recharge = float(recharge_result.scalar() or 0)
    
    # 查询消费总额 (amount 是字符串，需要转换) - 带环境过滤
    consume_result = await db.execute(
        select(func.coalesce(func.sum(func.cast(Bill.amount, Numeric)), 0)).where(
            Bill.user_id == current_user.id,
            Bill.bill_type == "consume",
            env_match(Bill.environment, environment),
            Bill.created_at >= start_date,
            Bill.created_at < end_date,
        )
    )
    total_consumption = float(consume_result.scalar() or 0)
    
    # 查询账单数量 - 带环境过滤
    count_result = await db.execute(
        select(func.count(Bill.id)).where(
            Bill.user_id == current_user.id,
            Bill.bill_type == "consume",
            env_match(Bill.environment, environment),
            Bill.created_at >= start_date,
            Bill.created_at < end_date,
        )
    )
    consumption_count = count_result.scalar() or 0
    
    # 从 APICallLog 表计算消费分布
    repo_stats_result = await db.execute(
        select(
            APICallLog.repo_id,
            func.count(APICallLog.id).label("call_count"),
            func.coalesce(func.sum(func.cast(APICallLog.cost, Numeric)), 0).label("total_cost")
        ).where(
            APICallLog.user_id == current_user.id,
            APICallLog.created_at >= start_date,
            APICallLog.created_at < end_date,
        ).group_by(APICallLog.repo_id).order_by(desc("call_count"))
    )
    repo_stats = repo_stats_result.all()
    
    # 获取仓库名称
    repo_ids = [str(stat.repo_id) for stat in repo_stats if stat.repo_id]
    repo_names = {}
    if repo_ids:
        repo_result = await db.execute(
            select(Repository).where(Repository.id.in_(repo_ids))
        )
        for repo in repo_result.scalars().all():
            repo_names[str(repo.id)] = repo.display_name or repo.name
    
    by_repository = []
    for stat in repo_stats:
        repo_id_str = str(stat.repo_id) if stat.repo_id else None
        by_repository.append({
            "repo_id": repo_id_str,
            "repo_name": repo_names.get(repo_id_str, "未知仓库") if repo_id_str else "未知仓库",
            "call_count": stat.call_count,
            "total": float(stat.total_cost),
        })
    
    return BaseResponse(
        data={
            "year": year,
            "month": month,
            "total_recharge": total_recharge,
            "total_consumption": total_consumption,
            "consumption_count": consumption_count,
            "net_change": total_recharge - total_consumption,
            "by_repository": by_repository,
            "environment": environment,
            "mock_mode": settings.payment_mock_mode,
        }
    )


@router.get("/balance-history", response_model=BaseResponse[list])
async def get_balance_history(
    days: int = Query(30, ge=1, le=365),
    environment: str = Query(None, description="环境过滤：simulation/production/all（all=不过滤）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取余额历史

    默认统计当前环境，支持 environment=all 合并两个环境。
    """
    from datetime import datetime, timedelta
    
    # 解析环境过滤（默认当前环境，支持 all 通配）
    environment = resolve_environment(environment)
    
    # 获取最近 N 天的余额变化
    start_date = cst_now() - timedelta(days=days)
    
    result = await db.execute(
        select(Bill).where(
            Bill.user_id == current_user.id,
            env_match(Bill.environment, environment),  # 环境过滤
            Bill.created_at >= start_date,
        ).order_by(desc(Bill.created_at))
    )
    bills = result.scalars().all()
    
    # 按日期分组，取每天最后的余额
    daily_data = {}
    for bill in bills:
        # created_at 为 aware UTC，需转北京时间后再取日期
        date_str = bill.created_at.astimezone(CST).strftime("%Y-%m-%d") if bill.created_at else "unknown"
        if date_str not in daily_data:
            daily_data[date_str] = {
                "date": date_str,
                "daily_change": 0,
                "balance": float(bill.balance_after)
            }
            # 计算日变化
            if bill.bill_type == "recharge":
                daily_data[date_str]["daily_change"] += float(bill.amount)
            elif bill.bill_type == "consume":
                daily_data[date_str]["daily_change"] -= float(bill.amount)
    
    return BaseResponse(
        data=list(daily_data.values())[:days]
    )


@router.get("/consumption-trend", response_model=BaseResponse[list])
async def get_consumption_trend(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取消费趋势
    """
    from datetime import datetime, timedelta
    
    start_date = cst_now() - timedelta(days=days)
    
    # 查询消费账单并按日期聚合
    query = """
        SELECT 
            DATE(created_at) as date,
            SUM(ABS(CAST(amount AS DECIMAL))) as total_amount
        FROM bills
        WHERE user_id = :user_id
        AND bill_type = 'consume'
        AND created_at >= :start_date
        GROUP BY DATE(created_at)
        ORDER BY date
    """
    
    result = await db.execute(
        select(Bill).where(
            Bill.user_id == current_user.id,
            Bill.bill_type == "consume",
            Bill.created_at >= start_date,
        ).order_by(Bill.created_at)
    )
    bills = result.scalars().all()
    
    # 按日期聚合
    daily_data = {}
    for bill in bills:
        # created_at 为 aware UTC，需转北京时间后再取日期
        date_str = bill.created_at.astimezone(CST).strftime("%Y-%m-%d") if bill.created_at else "unknown"
        if date_str not in daily_data:
            daily_data[date_str] = {"date": date_str, "amount": 0}
        daily_data[date_str]["amount"] += abs(float(bill.amount))
    
    return BaseResponse(
        data=list(daily_data.values()) if daily_data else [
            {"date": cst_date_str(i), "amount": 0}
            for i in range(days, 0, -1)
        ]
    )

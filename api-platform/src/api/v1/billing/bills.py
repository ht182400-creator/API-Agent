"""
计费接口 —— 账单查询与导出

由 `scripts/dev/split_api_router.py` 从 `src/api/v1/billing.py` 精确搬移生成，
函数体与原实现逐字一致（仅移动位置）。
"""

from datetime import datetime, timedelta
from fastapi import Depends, Query, APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text
from src.config.database import get_db
from src.schemas.response import BaseResponse
from src.services.auth_service import get_current_user
from src.models.user import User
from src.models.billing import Bill
from src.utils.environment import resolve_environment, env_match
from src.utils.time_range import utc_now
from src.config.logging_config import get_logger
from src.api.v1.billing._shared import _to_utc_iso_string

logger = get_logger("billing")

router = APIRouter()




@router.get("/bills", response_model=BaseResponse[dict])
async def get_bills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    bill_type: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    environment: str = Query(None, description="环境过滤：simulation/production/all（all=不过滤）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取账单列表

    环境过滤规则：
    - 不传 environment：默认查询"当前环境"（模拟/生产）
    - environment=all：同时查询模拟与真实数据（用于排查与对账）
    - environment=simulation/production：显式查询指定环境
    """
    from src.config.settings import settings
    
    # 解析环境过滤（默认当前环境，支持 all 通配）
    environment = resolve_environment(environment)
    
    # 构建查询和计数查询
    base_conditions = [
        Bill.user_id == current_user.id,
        env_match(Bill.environment, environment),
    ]
    
    if bill_type:
        base_conditions.append(Bill.bill_type == bill_type)
    
    query = select(Bill).where(*base_conditions)
    count_query = select(func.count(Bill.id)).where(*base_conditions)
    
    # 日期范围过滤（start_date 和 end_date 是北京时间，需要转换为 UTC）
    if start_date:
        try:
            # 解析北京时间 YYYY-MM-DD，转换为 UTC 00:00:00 +8小时
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            # 北京时间 00:00:00 = UTC 前一天 16:00:00
            start_utc = start_dt - timedelta(hours=8)
            query = query.where(Bill.created_at >= start_utc)
            count_query = count_query.where(Bill.created_at >= start_utc)
        except ValueError:
            pass
    
    if end_date:
        try:
            # 解析北京时间 YYYY-MM-DD，转换为 UTC 23:59:59 +8小时
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            # 北京时间 23:59:59 = UTC 当天 15:59:59
            end_utc = end_dt - timedelta(hours=8)
            query = query.where(Bill.created_at <= end_utc)
            count_query = count_query.where(Bill.created_at <= end_utc)
        except ValueError:
            pass
    
    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询（按id倒序，id越大创建越晚，最可靠）
    offset = (page - 1) * page_size
    query = query.order_by(desc(Bill.id)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    bills = result.scalars().all()
    
    return BaseResponse(
        data={
            "items": [
                {
                    "id": str(bill.id),
                    "account_id": str(bill.user_id),
                    "bill_type": bill.bill_type,
                    "amount": float(bill.amount),
                    "balance_after": float(bill.balance_after),
                    "payment_method": bill.payment_method,
                    "payment_id": bill.transaction_id,
                    "description": bill.description,
                    "environment": bill.environment,
                    "created_at": _to_utc_iso_string(bill.created_at),
                }
                for bill in bills
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            },
            "environment": environment,
            "mock_mode": settings.payment_mock_mode,
        }
    )


@router.get("/bills/export")
async def export_bills(
    bill_type: str = Query(None, description="账单类型筛选"),
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    environment: str = Query(None, description="环境过滤：simulation/production/all（all=不过滤）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    导出账单列表为CSV文件

    默认导出当前环境的账单，支持 environment=all 导出全部环境数据。
    """
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    # 解析环境过滤（默认当前环境，支持 all 通配）
    environment = resolve_environment(environment)
    
    # 构建查询 - 获取所有符合条件的账单
    query = select(Bill).where(
        Bill.user_id == current_user.id,
        env_match(Bill.environment, environment),
    ).order_by(desc(Bill.created_at))
    
    if bill_type:
        query = query.where(Bill.bill_type == bill_type)
    
    if start_date:
        from datetime import datetime
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.where(Bill.created_at >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        from datetime import datetime
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.where(Bill.created_at <= end_dt)
        except ValueError:
            pass
    
    result = await db.execute(query)
    bills = result.scalars().all()
    
    # 生成CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow(['时间', '类型', '金额', '余额', '描述', '仓库', '支付方式', '交易ID', '环境'])
    
    # 写入数据
    bill_type_map = {
        'recharge': '充值',
        'consume': '消费',
        'refund': '退款',
        'freeze': '冻结',
        'unfreeze': '解冻',
        'settlement': '结算',
    }
    
    for bill in bills:
        # 使用 _to_utc_iso_string 确保时间格式一致
        created_at_str = _to_utc_iso_string(bill.created_at)
        if created_at_str:
            # 从 ISO 字符串中提取日期时间部分
            created_at_display = created_at_str.replace('+00:00', 'Z').replace('T', ' ').split('+')[0].replace('Z', '')
        else:
            created_at_display = ''
        writer.writerow([
            created_at_display,
            bill_type_map.get(bill.bill_type, bill.bill_type),
            f"{float(bill.amount):.2f}",
            f"{float(bill.balance_after):.2f}",
            bill.description or '',
            '',  # repo_name 需要关联查询，这里留空
            bill.payment_method or '',
            bill.transaction_id or '',
            bill.environment,
        ])
    
    # 生成文件名
    from datetime import datetime
    filename = f"bills_{current_user.id}_{utc_now().strftime('%Y%m%d%H%M%S')}.csv"
    
    # 返回文件流
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )

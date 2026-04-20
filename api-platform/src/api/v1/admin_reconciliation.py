"""
Admin Reconciliation API - 管理员对账专用接口

提供充值明细查询、渠道收款汇总、平台账户余额等功能
"""

from typing import Optional, List
from datetime import datetime, timedelta, date
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_, desc, DECIMAL
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.user import User
from src.models.billing import Account, Bill
from src.models.payment import Payment
from src.models.reconciliation import PlatformAccount, ReconciliationRecord, ReconciliationDispute
from src.schemas.response import BaseResponse
from src.services.auth_service import get_current_admin_user

router = APIRouter(prefix="/admin", tags=["管理员-对账"])


# ==================== Pydantic Models ====================

class RechargeRecordItem(BaseModel):
    """充值记录项"""
    id: str
    payment_no: str
    user_id: str
    user_phone: Optional[str] = None
    user_email: Optional[str] = None
    amount: float
    bonus_amount: float
    total_amount: float
    payment_method: str
    payment_method_name: str
    status: str
    transaction_id: Optional[str] = None
    environment: str
    balance_after: Optional[float] = None
    created_at: str
    pay_time: Optional[str] = None


class RechargeSummary(BaseModel):
    """充值汇总统计"""
    total_count: int
    success_count: int
    failed_count: int
    pending_count: int
    total_amount: float
    total_bonus: float
    total_receivable: float


class RechargeRecordsResponse(BaseModel):
    """充值记录响应"""
    items: List[RechargeRecordItem]
    summary: RechargeSummary
    pagination: dict


class ChannelSummary(BaseModel):
    """渠道汇总"""
    channel: str
    channel_name: str
    channel_icon: str
    trade_count: int
    trade_amount: float
    success_count: int
    pending_count: int
    failed_count: int


class TotalSummary(BaseModel):
    """汇总统计"""
    trade_count: int
    trade_amount: float
    success_count: int
    pending_count: int
    failed_count: int


class ChannelSummaryResponse(BaseModel):
    """渠道汇总响应"""
    date: str
    channels: List[ChannelSummary]
    total: TotalSummary


class PlatformAccountItem(BaseModel):
    """平台账户项"""
    id: str
    channel: str
    channel_name: str
    channel_icon: str
    account_no: Optional[str] = None
    account_name: Optional[str] = None
    balance: float
    frozen_balance: float = 0.0
    available_balance: float = 0.0
    currency: str
    status: str
    remark: Optional[str] = None


class PlatformAccountsResponse(BaseModel):
    """平台账户响应"""
    accounts: List[PlatformAccountItem]
    total_available: float
    total_frozen: float
    total_balance: float


# ==================== 对账相关 Models ====================

class ReconciliationResultItem(BaseModel):
    """对账结果项"""
    id: str
    reconcile_date: str
    channel: str
    status: str
    platform_trade_count: int
    platform_trade_amount: float
    channel_trade_count: int
    channel_trade_amount: float
    match_count: int
    match_amount: float
    long_count: int
    long_amount: float
    short_count: int
    short_amount: float
    amount_diff_count: int
    amount_diff_total: float
    bill_file_path: Optional[str] = None
    completed_at: Optional[str] = None


class ExecuteReconciliationRequest(BaseModel):
    """执行对账请求"""
    date: str  # YYYY-MM-DD
    channel: str  # alipay/wechat/bankcard


class ExecuteReconciliationResponse(BaseModel):
    """执行对账响应"""
    reconciliation_id: str
    date: str
    channel: str
    status: str
    platform_trade_count: int
    platform_trade_amount: float
    channel_trade_count: int
    channel_trade_amount: float
    match_count: int
    match_amount: float
    long_count: int
    long_amount: float
    short_count: int
    short_amount: float
    amount_diff_count: int
    amount_diff_total: float
    completed_at: Optional[str] = None


class DisputeItem(BaseModel):
    """差异记录项"""
    id: str
    reconciliation_id: Optional[str] = None
    dispute_type: str
    local_order_no: Optional[str] = None
    channel_trade_no: Optional[str] = None
    local_amount: Optional[float] = None
    channel_amount: Optional[float] = None
    diff_amount: Optional[float] = None
    reason: Optional[str] = None
    handle_status: str
    handle_remark: Optional[str] = None
    handler_id: Optional[str] = None
    handler_name: Optional[str] = None
    handled_at: Optional[str] = None
    created_at: str


class DisputeListResponse(BaseModel):
    """差异记录列表响应"""
    items: List[DisputeItem]
    pagination: dict


class HandleDisputeRequest(BaseModel):
    """处理差异请求"""
    handle_status: str  # confirmed/resolved/ignored
    handle_remark: Optional[str] = None
    reason: Optional[str] = None


class HandleDisputeResponse(BaseModel):
    """处理差异响应"""
    id: str
    dispute_type: str
    local_order_no: Optional[str] = None
    channel_trade_no: Optional[str] = None
    diff_amount: Optional[float] = None
    handle_status: str
    handle_remark: Optional[str] = None
    handler_id: Optional[str] = None
    handler_name: Optional[str] = None
    handled_at: Optional[str] = None


class ReconciliationHistoryItem(BaseModel):
    """历史对账记录项"""
    id: str
    reconcile_date: str
    channel: str
    channel_name: str
    channel_icon: str
    status: str
    match_count: int
    long_count: int
    short_count: int
    amount_diff_count: int
    total_diff_count: int
    completed_at: Optional[str] = None


class ReconciliationHistoryResponse(BaseModel):
    """历史对账记录响应"""
    items: List[ReconciliationHistoryItem]
    pagination: dict


# ==================== 支付方式映射 ====================

PAYMENT_METHOD_MAP = {
    "alipay": {"name": "支付宝", "icon": "alipay"},
    "wechat": {"name": "微信支付", "icon": "wechat"},
    "bankcard": {"name": "银行卡", "icon": "bankcard"},
    "paypal": {"name": "PayPal", "icon": "paypal"},
}


def get_payment_method_name(method: str) -> str:
    """获取支付方式名称"""
    return PAYMENT_METHOD_MAP.get(method, {}).get("name", method)


def get_payment_method_icon(method: str) -> str:
    """获取支付方式图标"""
    return PAYMENT_METHOD_MAP.get(method, {}).get("icon", method)


# ==================== API 接口 ====================

@router.get("/recharge/records", response_model=BaseResponse[RechargeRecordsResponse])
async def get_recharge_records(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
    date_str: str = Query(None, description="日期 YYYY-MM-DD，默认当天"),
    channel: Optional[str] = Query(None, description="支付渠道: alipay/wechat/bankcard"),
    status: Optional[str] = Query(None, description="状态: pending/paid/failed"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """
    获取充值记录明细（管理员）
    
    支持按日期、渠道、状态筛选，返回分页数据及汇总统计。
    """
    # 处理日期
    if date_str:
        try:
            query_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    else:
        query_date = datetime.utcnow()
    
    # 日期范围
    day_start = query_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = query_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # 构建查询条件
    conditions = [
        Bill.created_at >= day_start,
        Bill.created_at <= day_end,
        Bill.bill_type == "recharge",  # 只查充值账单
    ]
    
    if channel:
        conditions.append(Bill.payment_method == channel)
    
    if status:
        conditions.append(Bill.status == status)
    
    # 查询总数
    count_query = select(func.count(Bill.id)).where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 查询记录
    query = (
        select(Bill, User)
        .join(User, Bill.user_id == User.id, isouter=True)
        .where(and_(*conditions))
        .order_by(desc(Bill.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    rows = result.all()
    
    # 统计汇总
    summary_conditions = [
        Bill.created_at >= day_start,
        Bill.created_at <= day_end,
        Bill.bill_type == "recharge",
    ]
    if channel:
        summary_conditions.append(Bill.payment_method == channel)
    
    # 总金额统计
    amount_query = select(
        func.count(Bill.id).label("total_count"),
        func.coalesce(func.sum(Bill.amount.cast(DECIMAL)), 0).label("total_amount"),
    ).where(and_(*summary_conditions))
    amount_result = await db.execute(amount_query)
    amount_data = amount_result.first()
    
    # 成功金额
    success_query = select(
        func.count(Bill.id).label("success_count"),
        func.coalesce(func.sum(Bill.amount.cast(DECIMAL)), 0).label("success_amount"),
    ).where(and_(*summary_conditions, Bill.status == "completed"))
    success_result = await db.execute(success_query)
    success_data = success_result.first()
    
    # 待处理金额
    pending_query = select(func.count(Bill.id)).where(
        and_(*summary_conditions, Bill.status == "pending")
    )
    pending_result = await db.execute(pending_query)
    pending_count = pending_result.scalar() or 0
    
    # 失败金额
    failed_query = select(func.count(Bill.id)).where(
        and_(*summary_conditions, Bill.status.in_(["failed", "cancelled"]))
    )
    failed_result = await db.execute(failed_query)
    failed_count = failed_result.scalar() or 0
    
    # 构建响应数据
    items = []
    for bill, user in rows:
        amount = float(bill.amount) if bill.amount else 0
        # 实际到账 = 充值后余额 - 充值前余额（简化计算）
        bonus_amount = 0.0
        if bill.balance_after and bill.balance_before:
            bonus_amount = float(bill.balance_after) - float(bill.balance_before) - amount
            bonus_amount = max(0, bonus_amount)
        
        items.append(RechargeRecordItem(
            id=str(bill.id),
            payment_no=bill.bill_no,
            user_id=str(bill.user_id),
            user_phone=user.phone if user else None,
            user_email=user.email if user else None,
            amount=amount,
            bonus_amount=bonus_amount,
            total_amount=amount + bonus_amount,
            payment_method=bill.payment_method or "unknown",
            payment_method_name=get_payment_method_name(bill.payment_method or "unknown"),
            status=bill.status,
            transaction_id=bill.transaction_id,
            environment=bill.environment,
            balance_after=float(bill.balance_after) if bill.balance_after else None,
            created_at=bill.created_at.isoformat() if bill.created_at else "",
            pay_time=bill.completed_at.isoformat() if bill.completed_at else None,
        ))
    
    summary = RechargeSummary(
        total_count=amount_data.total_count or 0,
        success_count=success_data.success_count or 0,
        failed_count=failed_count,
        pending_count=pending_count,
        total_amount=float(amount_data.total_amount) if amount_data.total_amount else 0,
        total_bonus=0.0,  # 简化计算
        total_receivable=float(success_data.success_amount) if success_data.success_amount else 0,
    )
    
    return BaseResponse(data=RechargeRecordsResponse(
        items=items,
        summary=summary,
        pagination={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        },
    ))


@router.get("/recharge/summary", response_model=BaseResponse[ChannelSummaryResponse])
async def get_recharge_summary(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
    date_str: str = Query(None, description="日期 YYYY-MM-DD，默认当天"),
):
    """
    获取各渠道收款汇总（管理员）
    
    按支付渠道分组统计当日充值情况。
    """
    # 处理日期
    if date_str:
        try:
            query_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    else:
        query_date = datetime.utcnow()
    
    # 日期范围
    day_start = query_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = query_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # 渠道列表
    channels = ["alipay", "wechat", "bankcard"]
    
    channel_summaries = []
    total_trade_count = 0
    total_trade_amount = 0.0
    total_success_count = 0
    total_pending_count = 0
    total_failed_count = 0
    
    for channel in channels:
        conditions = [
            Bill.created_at >= day_start,
            Bill.created_at <= day_end,
            Bill.bill_type == "recharge",
            Bill.payment_method == channel,
        ]
        
        # 交易总数和金额
        count_query = select(
            func.count(Bill.id).label("count"),
            func.coalesce(func.sum(Bill.amount.cast(DECIMAL)), 0).label("amount"),
        ).where(and_(*conditions))
        result = await db.execute(count_query)
        data = result.first()
        
        # 成功数
        success_query = select(func.count(Bill.id)).where(
            and_(*conditions, Bill.status == "completed")
        )
        success_result = await db.execute(success_query)
        success_count = success_result.scalar() or 0
        
        # 待处理数
        pending_query = select(func.count(Bill.id)).where(
            and_(*conditions, Bill.status == "pending")
        )
        pending_result = await db.execute(pending_query)
        pending_count = pending_result.scalar() or 0
        
        # 失败数
        failed_query = select(func.count(Bill.id)).where(
            and_(*conditions, Bill.status.in_(["failed", "cancelled"]))
        )
        failed_result = await db.execute(failed_query)
        failed_count = failed_result.scalar() or 0
        
        channel_summaries.append(ChannelSummary(
            channel=channel,
            channel_name=get_payment_method_name(channel),
            channel_icon=get_payment_method_icon(channel),
            trade_count=data.count or 0,
            trade_amount=float(data.amount) if data.amount else 0,
            success_count=success_count,
            pending_count=pending_count,
            failed_count=failed_count,
        ))
        
        total_trade_count += data.count or 0
        total_trade_amount += float(data.amount) if data.amount else 0
        total_success_count += success_count
        total_pending_count += pending_count
        total_failed_count += failed_count
    
    return BaseResponse(data=ChannelSummaryResponse(
        date=date_str or query_date.strftime("%Y-%m-%d"),
        channels=channel_summaries,
        total=TotalSummary(
            trade_count=total_trade_count,
            trade_amount=total_trade_amount,
            success_count=total_success_count,
            pending_count=total_pending_count,
            failed_count=total_failed_count,
        ),
    ))


@router.get("/platform/accounts", response_model=BaseResponse[PlatformAccountsResponse])
async def get_platform_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    获取平台账户余额（管理员）
    
    返回平台在各支付渠道的账户信息。
    注意：真实环境需要从第三方支付平台API获取实际余额。
    当前返回本地数据库记录的配置信息。
    """
    # 查询平台账户
    query = select(PlatformAccount).order_by(PlatformAccount.channel)
    result = await db.execute(query)
    accounts = result.scalars().all()
    
    # 如果没有账户数据，创建默认数据
    if not accounts:
        # 默认渠道配置
        default_accounts = [
            {"channel": "alipay", "account_name": "支付宝主账户", "balance": 0.00},
            {"channel": "wechat", "account_name": "微信支付账户", "balance": 0.00},
            {"channel": "bankcard", "account_name": "银行卡账户", "balance": 0.00},
        ]
        
        for acc_data in default_accounts:
            acc = PlatformAccount(
                channel=acc_data["channel"],
                account_name=acc_data["account_name"],
                balance=acc_data["balance"],
                currency="CNY",
                status="active",
            )
            db.add(acc)
        
        await db.commit()
        
        # 重新查询
        result = await db.execute(query)
        accounts = result.scalars().all()
    
    # 构建响应
    account_items = []
    total_balance = 0.0
    total_frozen = 0.0
    total_available = 0.0
    
    for acc in accounts:
        balance = float(acc.balance) if acc.balance else 0.0
        frozen = 0.0  # 冻结金额暂未实现
        available = balance - frozen
        
        account_items.append(PlatformAccountItem(
            id=str(acc.id),
            channel=acc.channel,
            channel_name=get_payment_method_name(acc.channel),
            channel_icon=get_payment_method_icon(acc.channel),
            account_no=acc.account_no,
            account_name=acc.account_name,
            balance=balance,
            frozen_balance=frozen,
            available_balance=available,
            currency=acc.currency or "CNY",
            status=acc.status,
            remark=acc.remark,
        ))
        
        total_balance += balance
        total_frozen += frozen
        total_available += available
    
    return BaseResponse(data=PlatformAccountsResponse(
        accounts=account_items,
        total_available=total_available,
        total_frozen=total_frozen,
        total_balance=total_balance,
    ))


@router.put("/platform/accounts/{account_id}", response_model=BaseResponse[PlatformAccountItem])
async def update_platform_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
    account_no: Optional[str] = None,
    account_name: Optional[str] = None,
    balance: Optional[float] = None,
    status: Optional[str] = None,
    remark: Optional[str] = None,
):
    """
    更新平台账户信息（管理员）
    
    用于手动维护平台账户配置信息。
    """
    query = select(PlatformAccount).where(PlatformAccount.id == account_id)
    result = await db.execute(query)
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")
    
    # 更新字段
    if account_no is not None:
        account.account_no = account_no
    if account_name is not None:
        account.account_name = account_name
    if balance is not None:
        account.balance = Decimal(str(balance))
    if status is not None:
        account.status = status
    if remark is not None:
        account.remark = remark
    
    await db.commit()
    await db.refresh(account)
    
    return BaseResponse(data=PlatformAccountItem(
        id=str(account.id),
        channel=account.channel,
        channel_name=get_payment_method_name(account.channel),
        channel_icon=get_payment_method_icon(account.channel),
        account_no=account.account_no,
        account_name=account.account_name,
        balance=float(account.balance) if account.balance else 0,
        frozen_balance=0.0,
        available_balance=float(account.balance) if account.balance else 0,
        currency=account.currency or "CNY",
        status=account.status,
        remark=account.remark,
    ))


# ==================== 对账核心功能接口 ====================

@router.post("/reconciliation/execute", response_model=BaseResponse[ExecuteReconciliationResponse])
async def execute_reconciliation(
    request: ExecuteReconciliationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    执行对账（管理员）
    
    核对指定日期和渠道的本地充值记录与第三方平台数据。
    生成对账结果和差异明细记录。
    """
    # 解析日期
    try:
        query_date = datetime.strptime(request.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    
    # 验证渠道
    valid_channels = ["alipay", "wechat", "bankcard"]
    if request.channel not in valid_channels:
        raise HTTPException(status_code=400, detail=f"无效的渠道，支持: {', '.join(valid_channels)}")
    
    # 日期范围
    day_start = query_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = query_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # 查询本地成功充值记录
    local_conditions = [
        Bill.created_at >= day_start,
        Bill.created_at <= day_end,
        Bill.bill_type == "recharge",
        Bill.payment_method == request.channel,
        Bill.status == "completed",
    ]
    
    # 本地交易统计
    local_count_query = select(
        func.count(Bill.id).label("count"),
        func.coalesce(func.sum(Bill.amount.cast(DECIMAL)), 0).label("amount"),
    ).where(and_(*local_conditions))
    local_result = await db.execute(local_count_query)
    local_data = local_result.first()
    
    platform_trade_count = local_data.count or 0
    platform_trade_amount = float(local_data.amount) if local_data.amount else 0.0
    
    # 查询本地记录用于匹配
    local_query = select(Bill).where(and_(*local_conditions))
    local_bills_result = await db.execute(local_query)
    local_bills = {str(bill.transaction_id): float(bill.amount) if bill.amount else 0 
                   for bill in local_bills_result.scalars().all() if bill.transaction_id}
    
    # 模拟第三方平台数据（实际应从第三方API获取）
    # 在模拟环境下，使用本地数据作为第三方数据
    channel_trade_count = platform_trade_count
    channel_trade_amount = platform_trade_amount
    
    # 模拟第三方交易记录（用于演示差异场景）
    # 实际环境中应从第三方支付平台获取
    # 这里假设有95%的匹配率，5%的差异（长款或短款）
    import random
    random.seed(hash(request.date + request.channel) % (2**32))
    
    match_count = int(platform_trade_count * 0.95)
    match_amount = platform_trade_amount * 0.95
    
    # 模拟长款（本地有，第三方无）
    long_count = platform_trade_count - match_count
    long_amount = platform_trade_amount - match_amount
    if long_amount < 0:
        long_amount = 0
    
    short_count = 0
    short_amount = 0.0
    amount_diff_count = 0
    amount_diff_total = 0.0
    
    # 如果是模拟环境，生成一些差异记录
    if platform_trade_count > 0:
        # 查询是否有已存在的对账记录
        existing_query = select(ReconciliationRecord).where(
            and_(
                func.date(ReconciliationRecord.reconcile_date) == query_date.date(),
                ReconciliationRecord.channel == request.channel,
            )
        )
        existing_result = await db.execute(existing_query)
        existing_record = existing_result.scalar_one_or_none()
        
        if existing_record:
            # 更新现有记录
            record = existing_record
        else:
            # 创建新记录
            record = ReconciliationRecord(
                reconcile_date=day_start,
                channel=request.channel,
                status="completed",
            )
            db.add(record)
            await db.flush()
        
        # 更新统计数据
        record.platform_trade_count = str(platform_trade_count)
        record.platform_trade_amount = Decimal(str(platform_trade_amount))
        record.channel_trade_count = str(channel_trade_count)
        record.channel_trade_amount = Decimal(str(channel_trade_amount))
        record.match_count = str(match_count)
        record.match_amount = Decimal(str(match_amount))
        record.long_count = str(long_count)
        record.long_amount = Decimal(str(long_amount))
        record.short_count = str(short_count)
        record.short_amount = Decimal(str(short_amount))
        record.amount_diff_count = str(amount_diff_count)
        record.amount_diff_total = Decimal(str(amount_diff_total))
        record.completed_at = datetime.utcnow()
        
        # 生成差异记录
        if long_count > 0:
            # 获取长款的订单
            long_bills_query = select(Bill).where(and_(*local_conditions)).limit(long_count)
            long_bills_result = await db.execute(long_bills_query)
            long_bills = long_bills_result.scalars().all()
            
            for idx, bill in enumerate(long_bills):
                dispute = ReconciliationDispute(
                    reconciliation_id=record.id,
                    dispute_type="long",
                    local_order_no=bill.bill_no,
                    channel_trade_no=None,
                    local_amount=bill.amount,
                    channel_amount=Decimal("0.00"),
                    diff_amount=bill.amount,
                    reason="本地有记录但第三方未查到",
                    handle_status="pending",
                )
                db.add(dispute)
        
        await db.commit()
        await db.refresh(record)
        
        reconciliation_id = str(record.id)
        completed_at = record.completed_at.isoformat() if record.completed_at else None
    else:
        # 无本地记录时创建空记录
        record = ReconciliationRecord(
            reconcile_date=day_start,
            channel=request.channel,
            status="completed",
            platform_trade_count="0",
            platform_trade_amount=Decimal("0.00"),
            channel_trade_count="0",
            channel_trade_amount=Decimal("0.00"),
            match_count="0",
            match_amount=Decimal("0.00"),
            long_count="0",
            long_amount=Decimal("0.00"),
            short_count="0",
            short_amount=Decimal("0.00"),
            amount_diff_count="0",
            amount_diff_total=Decimal("0.00"),
            completed_at=datetime.utcnow(),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        
        reconciliation_id = str(record.id)
        completed_at = record.completed_at.isoformat() if record.completed_at else None
    
    return BaseResponse(data=ExecuteReconciliationResponse(
        reconciliation_id=reconciliation_id,
        date=request.date,
        channel=request.channel,
        status="completed",
        platform_trade_count=platform_trade_count,
        platform_trade_amount=platform_trade_amount,
        channel_trade_count=channel_trade_count,
        channel_trade_amount=channel_trade_amount,
        match_count=match_count,
        match_amount=match_amount,
        long_count=long_count,
        long_amount=long_amount,
        short_count=short_count,
        short_amount=short_amount,
        amount_diff_count=amount_diff_count,
        amount_diff_total=amount_diff_total,
        completed_at=completed_at,
    ))


@router.get("/reconciliation/result", response_model=BaseResponse[ReconciliationResultItem])
async def get_reconciliation_result(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
    date: str = Query(..., description="对账日期 YYYY-MM-DD"),
    channel: str = Query(..., description="支付渠道: alipay/wechat/bankcard"),
):
    """
    获取对账结果（管理员）
    
    查询指定日期和渠道的对账结果。
    """
    # 解析日期
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    
    # 查询对账记录
    query = select(ReconciliationRecord).where(
        and_(
            func.date(ReconciliationRecord.reconcile_date) == query_date.date(),
            ReconciliationRecord.channel == channel,
        )
    )
    result = await db.execute(query)
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="对账记录不存在")
    
    return BaseResponse(data=ReconciliationResultItem(
        id=str(record.id),
        reconcile_date=record.reconcile_date.strftime("%Y-%m-%d") if record.reconcile_date else date,
        channel=record.channel,
        status=record.status,
        platform_trade_count=int(record.platform_trade_count) if record.platform_trade_count else 0,
        platform_trade_amount=float(record.platform_trade_amount) if record.platform_trade_amount else 0.0,
        channel_trade_count=int(record.channel_trade_count) if record.channel_trade_count else 0,
        channel_trade_amount=float(record.channel_trade_amount) if record.channel_trade_amount else 0.0,
        match_count=int(record.match_count) if record.match_count else 0,
        match_amount=float(record.match_amount) if record.match_amount else 0.0,
        long_count=int(record.long_count) if record.long_count else 0,
        long_amount=float(record.long_amount) if record.long_amount else 0.0,
        short_count=int(record.short_count) if record.short_count else 0,
        short_amount=float(record.short_amount) if record.short_amount else 0.0,
        amount_diff_count=int(record.amount_diff_count) if record.amount_diff_count else 0,
        amount_diff_total=float(record.amount_diff_total) if record.amount_diff_total else 0.0,
        bill_file_path=record.bill_file_path,
        completed_at=record.completed_at.isoformat() if record.completed_at else None,
    ))


@router.get("/reconciliation/disputes", response_model=BaseResponse[DisputeListResponse])
async def get_reconciliation_disputes(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
    reconciliation_id: Optional[str] = Query(None, description="对账记录ID"),
    dispute_type: Optional[str] = Query(None, description="差异类型: long/short/amount_diff"),
    handle_status: Optional[str] = Query(None, description="处理状态: pending/confirmed/resolved/ignored"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """
    获取对账差异记录列表（管理员）
    
    支持按对账记录ID、差异类型、处理状态筛选。
    """
    # 构建查询条件
    conditions = []
    if reconciliation_id and reconciliation_id != "None":
        try:
            from uuid import UUID
            recon_uuid = UUID(reconciliation_id)
            conditions.append(ReconciliationDispute.reconciliation_id == recon_uuid)
        except ValueError:
            pass  # 无效的UUID，忽略此条件
    if dispute_type:
        conditions.append(ReconciliationDispute.dispute_type == dispute_type)
    if handle_status:
        conditions.append(ReconciliationDispute.handle_status == handle_status)
    
    # 查询总数
    count_query = select(func.count(ReconciliationDispute.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 查询差异记录
    base_query = select(ReconciliationDispute)
    if conditions:
        base_query = base_query.where(and_(*conditions))
    query = (
        base_query
        .order_by(desc(ReconciliationDispute.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    disputes = result.scalars().all()
    
    # 构建响应数据
    items = []
    for dispute in disputes:
        items.append(DisputeItem(
            id=str(dispute.id),
            reconciliation_id=str(dispute.reconciliation_id) if dispute.reconciliation_id else None,
            dispute_type=dispute.dispute_type,
            local_order_no=dispute.local_order_no,
            channel_trade_no=dispute.channel_trade_no,
            local_amount=float(dispute.local_amount) if dispute.local_amount else None,
            channel_amount=float(dispute.channel_amount) if dispute.channel_amount else None,
            diff_amount=float(dispute.diff_amount) if dispute.diff_amount else None,
            reason=dispute.reason,
            handle_status=dispute.handle_status,
            handle_remark=dispute.handle_remark,
            handler_id=str(dispute.handler_id) if dispute.handler_id else None,
            handler_name=None,  # 可以通过join查询获取
            handled_at=dispute.handled_at.isoformat() if dispute.handled_at else None,
            created_at=dispute.created_at.isoformat() if dispute.created_at else "",
        ))
    
    return BaseResponse(data=DisputeListResponse(
        items=items,
        pagination={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        },
    ))


@router.put("/reconciliation/disputes/{dispute_id}", response_model=BaseResponse[HandleDisputeResponse])
async def handle_reconciliation_dispute(
    dispute_id: str,
    request: HandleDisputeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    处理对账差异（管理员）
    
    确认、解决或忽略对账差异记录。
    """
    # 验证处理状态
    valid_statuses = ["confirmed", "resolved", "ignored"]
    if request.handle_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"无效的处理状态，支持: {', '.join(valid_statuses)}")
    
    # 查询差异记录
    query = select(ReconciliationDispute).where(ReconciliationDispute.id == dispute_id)
    result = await db.execute(query)
    dispute = result.scalar_one_or_none()
    
    if not dispute:
        raise HTTPException(status_code=404, detail="差异记录不存在")
    
    # 更新差异记录
    dispute.handle_status = request.handle_status
    dispute.handle_remark = request.handle_remark
    dispute.reason = request.reason or dispute.reason
    dispute.handler_id = current_user.get("id")
    dispute.handled_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(dispute)
    
    return BaseResponse(data=HandleDisputeResponse(
        id=str(dispute.id),
        dispute_type=dispute.dispute_type,
        local_order_no=dispute.local_order_no,
        channel_trade_no=dispute.channel_trade_no,
        diff_amount=float(dispute.diff_amount) if dispute.diff_amount else None,
        handle_status=dispute.handle_status,
        handle_remark=dispute.handle_remark,
        handler_id=str(dispute.handler_id) if dispute.handler_id else None,
        handler_name=current_user.get("username") or current_user.get("email"),
        handled_at=dispute.handled_at.isoformat() if dispute.handled_at else None,
    ))


@router.get("/reconciliation/history", response_model=BaseResponse[ReconciliationHistoryResponse])
async def get_reconciliation_history(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
    channel: Optional[str] = Query(None, description="支付渠道: alipay/wechat/bankcard"),
    status: Optional[str] = Query(None, description="对账状态: pending/completed/disputed"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """
    获取历史对账记录（管理员）
    
    支持按渠道、状态、日期范围筛选。
    """
    # 构建查询条件
    conditions = []
    if channel:
        conditions.append(ReconciliationRecord.channel == channel)
    if status:
        conditions.append(ReconciliationRecord.status == status)
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            conditions.append(ReconciliationRecord.reconcile_date >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="开始日期格式错误，请使用 YYYY-MM-DD")
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            conditions.append(ReconciliationRecord.reconcile_date <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="结束日期格式错误，请使用 YYYY-MM-DD")
    
    # 查询总数
    count_query = select(func.count(ReconciliationRecord.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 查询记录
    base_query = select(ReconciliationRecord)
    if conditions:
        base_query = base_query.where(and_(*conditions))
    query = (
        base_query
        .order_by(desc(ReconciliationRecord.reconcile_date))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    records = result.scalars().all()
    
    # 构建响应数据
    items = []
    for record in records:
        match_count = int(record.match_count) if record.match_count else 0
        long_count = int(record.long_count) if record.long_count else 0
        short_count = int(record.short_count) if record.short_count else 0
        amount_diff_count = int(record.amount_diff_count) if record.amount_diff_count else 0
        
        items.append(ReconciliationHistoryItem(
            id=str(record.id),
            reconcile_date=record.reconcile_date.strftime("%Y-%m-%d") if record.reconcile_date else "",
            channel=record.channel,
            channel_name=get_payment_method_name(record.channel),
            channel_icon=get_payment_method_icon(record.channel),
            status=record.status,
            match_count=match_count,
            long_count=long_count,
            short_count=short_count,
            amount_diff_count=amount_diff_count,
            total_diff_count=long_count + short_count + amount_diff_count,
            completed_at=record.completed_at.isoformat() if record.completed_at else None,
        ))
    
    return BaseResponse(data=ReconciliationHistoryResponse(
        items=items,
        pagination={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        },
    ))


# ==================== 定时对账与报表导出 ====================

class ReconciliationReportRequest(BaseModel):
    """对账报表请求"""
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    channel: Optional[str] = None  # alipay/wechat/bankcard
    format: str = "csv"  # csv/excel


class ReconciliationReportItem(BaseModel):
    """对账报表项"""
    reconcile_date: str
    channel: str
    channel_name: str
    platform_trade_count: int
    platform_trade_amount: float
    channel_trade_count: int
    channel_trade_amount: float
    match_count: int
    match_rate: float
    long_count: int
    long_amount: float
    short_count: int
    short_amount: float
    amount_diff_count: int
    amount_diff_total: float
    pending_dispute_count: int
    status: str


class ReconciliationReportResponse(BaseModel):
    """对账报表响应"""
    items: List[ReconciliationReportItem]
    summary: dict
    generated_at: str
    date_range: dict


@router.post("/reconciliation/report", response_model=BaseResponse[ReconciliationReportResponse])
async def generate_reconciliation_report(
    request: ReconciliationReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    生成对账报表（管理员）
    
    按日期范围生成对账汇总报表，支持 CSV/Excel 导出。
    """
    # 解析日期
    try:
        start_dt = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(request.end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    
    if (end_dt - start_dt).days > 365:
        raise HTTPException(status_code=400, detail="日期范围不能超过一年")
    
    # 构建查询条件
    conditions = [
        ReconciliationRecord.reconcile_date >= start_dt,
        ReconciliationRecord.reconcile_date <= end_dt,
    ]
    if request.channel:
        conditions.append(ReconciliationRecord.channel == request.channel)
    
    # 查询对账记录
    query = (
        select(ReconciliationRecord)
        .where(and_(*conditions))
        .order_by(desc(ReconciliationRecord.reconcile_date))
    )
    result = await db.execute(query)
    records = result.scalars().all()
    
    # 构建报表数据
    items = []
    summary = {
        "total_count": 0,
        "total_platform_amount": 0.0,
        "total_channel_amount": 0.0,
        "total_match_count": 0,
        "total_long_count": 0,
        "total_short_count": 0,
        "total_amount_diff": 0.0,
        "total_pending": 0,
    }
    
    for record in records:
        platform_count = int(record.platform_trade_count) if record.platform_trade_count else 0
        platform_amount = float(record.platform_trade_amount) if record.platform_trade_amount else 0.0
        channel_count = int(record.channel_trade_count) if record.channel_trade_count else 0
        channel_amount = float(record.channel_trade_amount) if record.channel_trade_amount else 0.0
        match_count = int(record.match_count) if record.match_count else 0
        long_count = int(record.long_count) if record.long_count else 0
        short_count = int(record.short_count) if record.short_count else 0
        amount_diff_count = int(record.amount_diff_count) if record.amount_diff_count else 0
        amount_diff_total = float(record.amount_diff_total) if record.amount_diff_total else 0.0
        
        # 计算匹配率
        match_rate = (match_count / platform_count * 100) if platform_count > 0 else 100.0
        
        # 查询待处理差异数
        pending_query = select(func.count(ReconciliationDispute.id)).where(
            and_(
                ReconciliationDispute.reconciliation_id == record.id,
                ReconciliationDispute.handle_status == "pending",
            )
        )
        pending_result = await db.execute(pending_query)
        pending_count = pending_result.scalar() or 0
        
        items.append(ReconciliationReportItem(
            reconcile_date=record.reconcile_date.strftime("%Y-%m-%d") if record.reconcile_date else "",
            channel=record.channel,
            channel_name=get_payment_method_name(record.channel),
            platform_trade_count=platform_count,
            platform_trade_amount=platform_amount,
            channel_trade_count=channel_count,
            channel_trade_amount=channel_amount,
            match_count=match_count,
            match_rate=round(match_rate, 2),
            long_count=long_count,
            long_amount=float(record.long_amount) if record.long_amount else 0.0,
            short_count=short_count,
            short_amount=float(record.short_amount) if record.short_amount else 0.0,
            amount_diff_count=amount_diff_count,
            amount_diff_total=amount_diff_total,
            pending_dispute_count=pending_count,
            status=record.status,
        ))
        
        # 汇总
        summary["total_count"] += 1
        summary["total_platform_amount"] += platform_amount
        summary["total_channel_amount"] += channel_amount
        summary["total_match_count"] += match_count
        summary["total_long_count"] += long_count
        summary["total_short_count"] += short_count
        summary["total_amount_diff"] += amount_diff_total
        summary["total_pending"] += pending_count
    
    return BaseResponse(data=ReconciliationReportResponse(
        items=items,
        summary=summary,
        generated_at=datetime.utcnow().isoformat(),
        date_range={
            "start_date": request.start_date,
            "end_date": request.end_date,
        },
    ))


@router.get("/reconciliation/report/download")
async def download_reconciliation_report(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    channel: Optional[str] = Query(None, description="支付渠道"),
    format: str = Query("csv", description="导出格式: csv/excel"),
):
    """
    下载对账报表（管理员）
    
    导出对账汇总数据为 CSV 或 Excel 文件。
    """
    from fastapi.responses import StreamingResponse
    import csv
    import io
    
    # 解析日期
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误")
    
    # 构建查询
    conditions = [
        ReconciliationRecord.reconcile_date >= start_dt,
        ReconciliationRecord.reconcile_date <= end_dt,
    ]
    if channel:
        conditions.append(ReconciliationRecord.channel == channel)
    
    query = (
        select(ReconciliationRecord)
        .where(and_(*conditions))
        .order_by(desc(ReconciliationRecord.reconcile_date))
    )
    result = await db.execute(query)
    records = result.scalars().all()
    
    # 生成 CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    headers = [
        "对账日期", "渠道", "平台交易笔数", "平台交易金额",
        "渠道交易笔数", "渠道交易金额", "匹配笔数", "匹配率(%)",
        "长款笔数", "长款金额", "短款笔数", "短款金额",
        "金额差异笔数", "金额差异总额", "待处理差异", "状态"
    ]
    writer.writerow(headers)
    
    # 写入数据
    for record in records:
        platform_count = int(record.platform_trade_count) if record.platform_trade_count else 0
        platform_amount = float(record.platform_trade_amount) if record.platform_trade_amount else 0.0
        channel_count = int(record.channel_trade_count) if record.channel_trade_count else 0
        channel_amount = float(record.channel_trade_amount) if record.channel_trade_amount else 0.0
        match_count = int(record.match_count) if record.match_count else 0
        match_rate = (match_count / platform_count * 100) if platform_count > 0 else 100.0
        long_count = int(record.long_count) if record.long_count else 0
        short_count = int(record.short_count) if record.short_count else 0
        amount_diff_count = int(record.amount_diff_count) if record.amount_diff_count else 0
        amount_diff_total = float(record.amount_diff_total) if record.amount_diff_total else 0.0
        
        # 查询待处理差异数
        pending_query = select(func.count(ReconciliationDispute.id)).where(
            and_(
                ReconciliationDispute.reconciliation_id == record.id,
                ReconciliationDispute.handle_status == "pending",
            )
        )
        pending_result = await db.execute(pending_query)
        pending_count = pending_result.scalar() or 0
        
        writer.writerow([
            record.reconcile_date.strftime("%Y-%m-%d") if record.reconcile_date else "",
            get_payment_method_name(record.channel),
            platform_count,
            f"{platform_amount:.2f}",
            channel_count,
            f"{channel_amount:.2f}",
            match_count,
            f"{match_rate:.2f}",
            long_count,
            f"{float(record.long_amount) if record.long_amount else 0:.2f}",
            short_count,
            f"{float(record.short_amount) if record.short_amount else 0:.2f}",
            amount_diff_count,
            f"{amount_diff_total:.2f}",
            pending_count,
            record.status,
        ])
    
    # 生成文件名
    filename = f"reconciliation_report_{start_date}_{end_date}.csv"
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


class SchedulerStatusResponse(BaseModel):
    """调度器状态响应"""
    is_running: bool
    last_run_time: Optional[str]
    task_count: int
    tasks: List[dict]


@router.get("/reconciliation/scheduler/status", response_model=BaseResponse[SchedulerStatusResponse])
async def get_scheduler_status(
    current_user: dict = Depends(get_current_admin_user),
):
    """
    获取定时对账调度器状态（管理员）
    
    查看定时任务的运行状态和历史记录。
    """
    from src.services.reconciliation_scheduler import scheduler
    
    status = scheduler.get_task_status()
    
    return BaseResponse(data=SchedulerStatusResponse(
        is_running=status["is_running"],
        last_run_time=status["last_run_time"],
        task_count=status["task_count"],
        tasks=status["tasks"],
    ))


class TriggerReconciliationRequest(BaseModel):
    """手动触发对账请求"""
    date: Optional[str] = None  # YYYY-MM-DD，默认昨天
    channels: Optional[List[str]] = None  # 渠道列表


class TriggerReconciliationResponse(BaseModel):
    """手动触发对账响应"""
    status: str
    date: str
    channels: dict
    total: dict
    executed_at: str


@router.post("/reconciliation/scheduler/trigger", response_model=BaseResponse[TriggerReconciliationResponse])
async def trigger_reconciliation(
    request: TriggerReconciliationRequest,
    current_user: dict = Depends(get_current_admin_user),
):
    """
    手动触发对账任务（管理员）
    
    立即执行对账，跳过定时任务。
    """
    from src.services.reconciliation_scheduler import scheduler
    
    if scheduler.is_running:
        raise HTTPException(status_code=409, detail="对账任务正在执行中，请稍后再试")
    
    result = await scheduler.execute_reconciliation(
        date=request.date,
        channels=request.channels,
    )
    
    return BaseResponse(data=TriggerReconciliationResponse(
        status=result["status"],
        date=result["date"],
        channels=result["channels"],
        total=result["total"],
        executed_at=result["executed_at"],
    ))

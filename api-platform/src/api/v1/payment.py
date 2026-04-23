"""Payment API - 支付接口"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.schemas.response import BaseResponse
from src.services.payment_service import PaymentService
from src.services.auth_service import get_current_user
from src.models.user import User

router = APIRouter(prefix="/payments", tags=["支付"])


# ==================== 请求/响应模型 ====================

class RechargePackageResponse(BaseModel):
    """充值套餐响应"""
    id: str
    name: str
    description: Optional[str]
    original_amount: float
    price: float
    bonus_amount: float
    bonus_ratio: Optional[float]
    min_amount: Optional[float]
    max_amount: Optional[float]
    included_calls: Optional[int]
    validity_days: Optional[int]
    is_active: bool
    is_featured: bool
    is_custom: bool


class RechargeConfigResponse(BaseModel):
    """充值配置响应"""
    min_amount: float
    max_amount: float
    default_bonus_ratio: float
    mock_mode: bool  # 是否为模拟模式


class CreateCustomRechargeRequest(BaseModel):
    """自定义金额充值请求"""
    amount: float
    payment_method: str = "alipay"


class CreatePaymentRequest(BaseModel):
    """创建支付请求"""
    package_id: str
    payment_method: str = "alipay"
    callback_url: Optional[str] = None


class CreatePaymentResponse(BaseModel):
    """创建支付响应"""
    payment_no: str
    order_no: str
    amount: float
    status: str
    payment_url: str
    qr_code: Optional[str] = None


class PaymentRecordResponse(BaseModel):
    """支付记录响应"""
    id: str
    payment_no: str
    order_no: str
    package_name: str
    amount: float
    payment_method: str
    status: str
    pay_time: Optional[datetime]
    created_at: datetime


class PaymentStatusResponse(BaseModel):
    """支付状态响应"""
    payment_no: str
    status: str
    amount: float
    pay_time: Optional[datetime]


# ==================== 充值套餐接口 ====================

@router.get("/config", response_model=BaseResponse[RechargeConfigResponse])
async def get_recharge_config():
    """
    获取充值配置（全局最小/最大金额等）
    """
    from src.config.settings import settings
    
    return BaseResponse(
        data=RechargeConfigResponse(
            min_amount=settings.recharge_min_amount,
            max_amount=settings.recharge_max_amount,
            default_bonus_ratio=settings.recharge_default_bonus_ratio,
            mock_mode=settings.payment_mock_mode,
        )
    )


@router.get("/packages", response_model=BaseResponse[List[RechargePackageResponse]])
async def list_recharge_packages(
    db: AsyncSession = Depends(get_db),
):
    """
    获取可用充值套餐列表
    
    返回所有启用的充值套餐，按排序顺序排列。
    """
    service = PaymentService(db)
    packages = await service.list_packages(is_active=True)
    
    return BaseResponse(
        data=[
            RechargePackageResponse(
                id=str(pkg.id),
                name=pkg.name,
                description=pkg.description,
                original_amount=float(pkg.original_amount),
                price=float(pkg.price),
                bonus_amount=float(pkg.bonus_amount) if pkg.bonus_amount else 0,
                bonus_ratio=float(pkg.bonus_ratio) if pkg.bonus_ratio else None,
                min_amount=float(pkg.min_amount) if pkg.min_amount else None,
                max_amount=float(pkg.max_amount) if pkg.max_amount else None,
                included_calls=pkg.included_calls,
                validity_days=pkg.validity_days,
                is_active=pkg.is_active == "true",
                is_featured=pkg.is_featured == "true",
                is_custom=pkg.is_custom == "true",
            )
            for pkg in packages
        ]
    )


@router.get("/packages/{package_id}", response_model=BaseResponse[RechargePackageResponse])
async def get_recharge_package(
    package_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取充值套餐详情
    
    Args:
        package_id: 套餐ID
    """
    service = PaymentService(db)
    package = await service.get_package(package_id)
    
    if not package:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("套餐不存在")
    
    return BaseResponse(
        data=RechargePackageResponse(
            id=str(package.id),
            name=package.name,
            description=package.description,
            original_amount=float(package.original_amount),
            price=float(package.price),
            bonus_amount=float(package.bonus_amount) if package.bonus_amount else 0,
            included_calls=package.included_calls,
            validity_days=package.validity_days,
            is_featured=package.is_featured == "true",
        )
    )


# ==================== 支付订单接口 ====================

@router.post("/custom", response_model=BaseResponse[CreatePaymentResponse])
async def create_custom_recharge(
    request: CreateCustomRechargeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    自定义金额充值
    
    Args:
        request: 充值请求
        - amount: 充值金额
        - payment_method: 支付方式
    """
    service = PaymentService(db)
    
    try:
        payment, payment_url = await service.create_custom_recharge(
            user_id=str(current_user.id),
            amount=request.amount,
            payment_method=request.payment_method,
        )
        
        return BaseResponse(
            data=CreatePaymentResponse(
                payment_no=payment.payment_no,
                order_no=payment.order_no,
                amount=float(payment.amount),
                status=payment.status,
                payment_url=payment_url,
            )
        )
    except ValidationError as e:
        raise e


@router.post("/create", response_model=BaseResponse[CreatePaymentResponse])
async def create_payment(
    request: CreatePaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建支付订单
    
    Args:
        request: 支付请求参数
        - package_id: 套餐ID
        - payment_method: 支付方式 (alipay/wechat/paypal)
        - callback_url: 回调通知地址
    """
    service = PaymentService(db)
    payment, payment_url = await service.create_payment(
        user_id=str(current_user.id),
        package_id=request.package_id,
        payment_method=request.payment_method,
        callback_url=request.callback_url,
    )
    
    return BaseResponse(
        data=CreatePaymentResponse(
            payment_no=payment.payment_no,
            order_no=payment.order_no,
            amount=float(payment.amount),
            status=payment.status,
            payment_url=payment_url,
        )
    )


@router.get("/status/{payment_no}", response_model=BaseResponse[PaymentStatusResponse])
async def query_payment_status(
    payment_no: str,
    db: AsyncSession = Depends(get_db),
):
    """
    查询支付状态
    
    Args:
        payment_no: 支付单号
    """
    service = PaymentService(db)
    payment = await service.query_payment(payment_no)
    
    if not payment:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("支付记录不存在")
    
    return BaseResponse(
        data=PaymentStatusResponse(
            payment_no=payment.payment_no,
            status=payment.status,
            amount=float(payment.amount),
            pay_time=payment.pay_time,
        )
    )


@router.post("/cancel/{payment_no}", response_model=BaseResponse[PaymentRecordResponse])
async def cancel_payment(
    payment_no: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    取消支付订单
    
    Args:
        payment_no: 支付单号
    """
    service = PaymentService(db)
    payment = await service.cancel_payment(
        payment_no=payment_no,
        user_id=str(current_user.id),
    )
    
    return BaseResponse(
        data=PaymentRecordResponse(
            id=str(payment.id),
            payment_no=payment.payment_no,
            order_no=payment.order_no,
            package_name=payment.package_name or "",
            amount=float(payment.amount),
            payment_method=payment.payment_method or "",
            status=payment.status,
            pay_time=payment.pay_time,
            created_at=payment.created_at,
        )
    )


# ==================== 支付记录查询 ====================

@router.get("/records", response_model=BaseResponse[dict])
async def list_payment_records(
    status: Optional[str] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取用户的支付记录
    
    Args:
        status: 支付状态 (pending/completed/failed/cancelled/refunded)
        page: 页码
        page_size: 每页数量
    """
    service = PaymentService(db)
    payments, total = await service.list_user_payments(
        user_id=str(current_user.id),
        status=status,
        page=page,
        page_size=page_size,
    )
    
    return BaseResponse(
        data={
            "items": [
                {
                    "id": str(p.id),
                    "payment_no": p.payment_no,
                    "order_no": p.order_no,
                    "package_name": p.package_name or "",
                    "amount": float(p.amount),
                    "payment_method": p.payment_method or "",
                    "status": p.status,
                    "pay_time": p.pay_time.isoformat() if p.pay_time else None,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in payments
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


# ==================== 支付回调接口（内部使用） ====================

class PaymentCallbackRequest(BaseModel):
    """支付回调请求"""
    payment_no: str
    transaction_id: str
    status: str  # success/failed
    payer_info: Optional[dict] = None
    sign: Optional[str] = None


@router.post("/callback", response_model=BaseResponse[dict])
async def payment_callback(
    request: PaymentCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    支付回调通知接口
    
    由支付渠道回调，用于更新支付状态和发放资金。
    此接口应仅允许支付渠道服务器访问，需要做IP白名单或签名验证。
    
    根据 payment_mock_mode 配置：
    - True (开发模式): 允许模拟回调，测试用
    - False (生产模式): 需要真实支付渠道回调
    
    Args:
        request: 回调参数
    """
    from src.config.settings import settings
    from src.config.logging_config import get_logger
    
    logger = get_logger("payment")
    logger.info(f"[PaymentCallback] Received callback: payment_no={request.payment_no}, status={request.status}")
    
    # 检查是否启用模拟模式
    if not settings.payment_mock_mode:
        # 生产模式：检查必要的签名验证
        if not request.sign:
            return BaseResponse(
                data={"success": False, "message": "生产模式需要签名验证"}
            )
        
        # TODO: 实现真实支付渠道的签名验证逻辑
        # 这里需要根据实际的支付渠道（支付宝/微信）实现签名验证
        # 暂时返回错误提示
        return BaseResponse(
            data={
                "success": False, 
                "message": "生产模式请接入真实支付渠道（支付宝/微信支付SDK）"
            }
        )
    
    # 开发/模拟模式：允许模拟回调
    service = PaymentService(db)
    
    try:
        success = await service.handle_payment_callback(
            payment_no=request.payment_no,
            transaction_id=request.transaction_id,
            status=request.status,
            payer_info=request.payer_info,
            raw_data=request.dict(),
        )
        
        return BaseResponse(data={"success": success, "message": "回调处理成功"})
    except Exception as e:
        logger.error(f"[PaymentCallback] Error processing callback: {e}", exc_info=True)
        return BaseResponse(data={"success": False, "message": str(e)})


# ==================== 管理员接口 ====================

@router.post("/packages", response_model=BaseResponse[RechargePackageResponse])
async def admin_create_package(
    name: str = Query(...),
    price: float = Query(...),
    original_amount: float = Query(None),
    bonus_amount: str = Query("0"),
    bonus_ratio: str = Query(None),
    validity_days: int = Query(None),
    description: str = Query(None),
    is_featured: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建充值套餐（管理员）
    
    Args:
        name: 套餐名称
        price: 售价
        original_amount: 原价
        bonus_amount: 赠送金额
        bonus_ratio: 赠送比例
        validity_days: 有效期天数
        description: 描述
        is_featured: 是否推荐
    """
    from src.services.auth_service import check_admin_permission
    
    check_admin_permission(current_user)
    
    service = PaymentService(db)
    package = await service.create_package(
        name=name,
        price=price,
        original_amount=original_amount,
        bonus_amount=bonus_amount,
        bonus_ratio=bonus_ratio,
        validity_days=validity_days,
        description=description,
        is_featured=is_featured,
    )
    
    return BaseResponse(
        data=RechargePackageResponse(
            id=str(package.id),
            name=package.name,
            description=package.description,
            original_amount=float(package.original_amount),
            price=float(package.price),
            bonus_amount=float(package.bonus_amount) if package.bonus_amount else 0,
            included_calls=package.included_calls,
            validity_days=package.validity_days,
            is_featured=package.is_featured == "true",
        )
    )


@router.post("/refund/{payment_no}", response_model=BaseResponse[PaymentRecordResponse])
async def admin_refund_payment(
    payment_no: str,
    reason: str = Query(..., description="退款原因"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    退款（管理员）
    
    Args:
        payment_no: 支付单号
        reason: 退款原因
    """
    from src.services.auth_service import check_admin_permission
    
    check_admin_permission(current_user)
    
    service = PaymentService(db)
    payment = await service.refund_payment(
        payment_no=payment_no,
        reason=reason,
        operator_id=str(current_user.id),
    )
    
    return BaseResponse(
        data=PaymentRecordResponse(
            id=str(payment.id),
            payment_no=payment.payment_no,
            order_no=payment.order_no,
            package_name=payment.package_name or "",
            amount=float(payment.amount),
            payment_method=payment.payment_method or "",
            status=payment.status,
            pay_time=payment.pay_time,
            created_at=payment.created_at,
        )
    )

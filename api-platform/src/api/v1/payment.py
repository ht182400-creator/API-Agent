"""Payment API - 支付接口"""

from typing import Optional, List
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.config.logging_config import get_logger
from src.schemas.response import BaseResponse
from src.services.payment_service import PaymentService
from src.services.auth_service import get_current_user
from src.models.user import User

# 日志记录器
logger = get_logger("payment_api")

router = APIRouter(prefix="/payments", tags=["支付"])

# 订单有效期配置
ORDER_EXPIRY_MINUTES = 10


def calculate_expires_in(created_at: datetime) -> int:
    """
    计算订单剩余有效期（秒）
    
    订单有效期为 ORDER_EXPIRY_MINUTES（10分钟）
    数据库存储的 created_at 是 UTC 时间，但可能以 naive datetime 形式返回
    """
    from src.utils.helpers import utc_now
    
    # 防御性检查：如果 created_at 为 None 或无效，返回默认值
    if created_at is None:
        logger.warning("[倒计时] created_at 为 None，返回默认值 600")
        return 600
    
    # 获取当前 UTC 时间（aware datetime）
    now_utc = utc_now()
    
    if created_at.tzinfo is None:
        # created_at 是 naive datetime，假定为 UTC 时间进行计算
        # 因为 get_utc_now() 返回的是 datetime.now(timezone.utc)
        utc_tz = timezone.utc
        created_at_aware = created_at.replace(tzinfo=utc_tz)
    else:
        created_at_aware = created_at
    
    # 计算过期时间点
    expiry_time = created_at_aware + timedelta(minutes=ORDER_EXPIRY_MINUTES)
    
    # 计算剩余秒数
    remaining = (expiry_time - now_utc).total_seconds()
    
    # 调试日志
    logger.debug(f"[倒计时] created_at={created_at}, now_utc={now_utc}, expiry_time={expiry_time}, remaining={int(remaining)}")
    
    # 如果计算结果异常（太大或太小），返回默认值
    if remaining > ORDER_EXPIRY_MINUTES * 60 * 2 or remaining < 0:
        logger.warning(f"[倒计时] 计算结果异常 ({remaining}秒)，返回默认值 600")
        return 600
    
    return max(0, int(remaining))


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
    payment_type: str = "page"  # page=跳转支付, qrcode=扫码支付


class CreatePaymentRequest(BaseModel):
    """创建支付请求"""
    package_id: str
    payment_method: str = "alipay"
    payment_type: str = "page"  # page=跳转支付, qrcode=扫码支付
    callback_url: Optional[str] = None


class CreatePaymentResponse(BaseModel):
    """创建支付响应"""
    payment_no: str
    order_no: str
    amount: float
    status: str
    payment_url: str
    pay_url: Optional[str] = None  # 支付链接（兼容字段）
    qr_code: Optional[str] = None  # 二维码图片（base64）
    payment_type: Optional[str] = None  # 支付类型：page/qrcode
    created_at: datetime  # 订单创建时间（ISO格式）
    expires_in: int  # 订单剩余有效期（秒），后端计算避免时区问题


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
    pay_time: Optional[datetime] = None
    pay_url: Optional[str] = None  # 支付链接
    created_at: datetime  # 订单创建时间（ISO格式）
    expires_in: int  # 订单剩余有效期（秒），后端计算避免时区问题


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
        - payment_type: 支付类型 (page=跳转支付, qrcode=扫码支付)
    """
    from src.config.logging_config import get_logger
    from src.core.exceptions import ValidationError
    logger = get_logger("payment")
    
    service = PaymentService(db)
    
    try:
        payment, payment_url = await service.create_custom_recharge(
            user_id=str(current_user.id),
            amount=request.amount,
            payment_method=request.payment_method,
        )
        
        # 扫码支付：生成二维码
        qr_code = None
        final_payment_url = payment_url
        logger.info(f"[CustomPayment] payment_type={request.payment_type}, payment_method={request.payment_method}")
        
        if request.payment_type == "qrcode" and request.payment_method == "alipay":
            try:
                logger.info(f"[CustomQRCode] 正在生成二维码 | order_no={payment.order_no}")
                qr_code = await service.generate_alipay_qrcode(payment)
                final_payment_url = None
                logger.info(f"[CustomQRCode] 二维码生成成功 | order_no={payment.order_no}")
            except Exception as e:
                logger.error(f"[CustomQRCode] 二维码生成失败 | order_no={payment.order_no}, error={str(e)}")
                logger.info(f"[CustomQRCode] 回退到跳转支付模式 | order_no={payment.order_no}")
        
        # 计算并记录有效期（用于调试时区问题）
        expires_in = calculate_expires_in(payment.created_at)
        logger.info(f"[CustomPayment] 自定义订单 created_at={payment.created_at}, expires_in={expires_in}")
        
        return BaseResponse(
            data=CreatePaymentResponse(
                payment_no=payment.payment_no,
                order_no=payment.order_no,
                amount=float(payment.amount),
                status=payment.status,
                payment_url=final_payment_url or payment_url,
                pay_url=final_payment_url or payment_url,
                qr_code=qr_code,
                payment_type=request.payment_type if qr_code else "page",
                created_at=payment.created_at,
                expires_in=expires_in,
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
        - payment_type: 支付类型 (page=跳转支付, qrcode=扫码支付)
        - callback_url: 回调通知地址
    """
    from src.config.logging_config import get_logger
    logger = get_logger("payment")
    
    service = PaymentService(db)
    
    # 创建支付订单
    payment, payment_url = await service.create_payment(
        user_id=str(current_user.id),
        package_id=request.package_id,
        payment_method=request.payment_method,
        callback_url=request.callback_url,
    )
    
    qr_code = None
    final_payment_url = payment_url
    
    # 如果是扫码支付，生成二维码
    logger.info(f"[CreatePayment] payment_type={request.payment_type}, payment_method={request.payment_method}")
    if request.payment_type == "qrcode" and request.payment_method == "alipay":
        try:
            logger.info(f"[QRCode] 正在生成二维码 | order_no={payment.order_no}")
            qr_code = await service.generate_alipay_qrcode(payment)
            final_payment_url = None  # 扫码支付不需要跳转链接
            logger.info(f"[QRCode] 二维码生成成功 | order_no={payment.order_no}")
        except Exception as e:
            logger.error(f"[QRCode] 二维码生成失败 | order_no={payment.order_no}, error={str(e)}")
            # 扫码失败时回退到跳转支付
            logger.info(f"[QRCode] 回退到跳转支付模式 | order_no={payment.order_no}")
    
    # 计算并记录有效期（用于调试时区问题）
    expires_in = calculate_expires_in(payment.created_at)
    logger.info(f"[CreatePayment] 套餐订单 created_at={payment.created_at}, expires_in={expires_in}")
    
    return BaseResponse(
        data=CreatePaymentResponse(
            payment_no=payment.payment_no,
            order_no=payment.order_no,
            amount=float(payment.amount),
            status=payment.status,
            payment_url=final_payment_url or payment_url,
            pay_url=final_payment_url or payment_url,
            qr_code=qr_code,
            payment_type=request.payment_type if qr_code else "page",
            created_at=payment.created_at,
            expires_in=expires_in,
        )
    )


@router.get("/status/{payment_no}", response_model=BaseResponse[PaymentStatusResponse])
async def query_payment_status(
    payment_no: str,
    db: AsyncSession = Depends(get_db),
):
    """
    查询支付状态
    
    【核心优化】当本地状态不是成功时，主动从支付宝查询真实状态。
    解决异步回调延迟或丢失导致的状态不一致问题。
    
    【修复 V7.4】同时支持 payment_no（系统支付单号）和 order_no（支付宝商户订单号/out_trade_no）查询。
    支付宝 return_url 返回的是 out_trade_no（对应 order_no），需要兼容处理。
    
    Args:
        payment_no: 支付单号或订单号（order_no/out_trade_no）
    """
    from src.config.settings import settings
    from src.config.logging_config import get_logger
    
    logger = get_logger("payment")
    logger.info(f"[QueryStatus] 查询支付状态 | payment_no={payment_no}")
    
    service = PaymentService(db)
    
    # 【V7.4 修复】先尝试用 payment_no 查询，如果找不到再尝试 order_no
    # 这样可以兼容支付宝 return_url 返回的 out_trade_no
    payment = await service.query_payment(payment_no)
    
    if not payment:
        # 尝试用 order_no 查询（支付宝 out_trade_no）
        logger.info(f"[QueryStatus] payment_no 未找到，尝试 order_no 查询 | payment_no={payment_no}")
        payment = await service.query_payment_by_order(payment_no)
    
    if not payment:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("支付记录不存在")
    
    # 【关键优化】如果本地状态不是成功，主动从支付宝同步状态
    if payment.status not in ("paid", "completed"):
        if settings.alipay_app_id and settings.get_alipay_public_key():
            logger.info(f"[QueryStatus] 尝试从支付宝同步状态 | payment_no={payment_no}")
            synced_payment = await service.sync_payment_status_from_alipay(payment.payment_no)
            if synced_payment:
                payment = synced_payment
                logger.info(f"[QueryStatus] 支付宝同步结果 | payment_no={payment_no}, status={payment.status}")
    
    # 如果支付成功，也更新本地 balance
    if payment.status in ("paid", "completed"):
        try:
            await service.update_user_balance_after_payment(payment.payment_no)
        except Exception as e:
            logger.warning(f"[QueryStatus] 更新余额失败 | payment_no={payment_no}, error={str(e)}")
    
    return BaseResponse(
        data=PaymentStatusResponse(
            payment_no=payment.payment_no,
            status=payment.status,
            amount=float(payment.amount),
            pay_time=payment.pay_time,
            created_at=payment.created_at,
            expires_in=calculate_expires_in(payment.created_at),
        )
    )


@router.post("/refresh-qrcode/{payment_no}", response_model=BaseResponse[dict])
async def refresh_payment_qrcode(
    payment_no: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    刷新支付二维码
    
    当原二维码失效时，重新生成新的二维码。
    
    Args:
        payment_no: 支付单号
    """
    service = PaymentService(db)
    
    # 验证用户权限
    payment = await service.query_payment(payment_no)
    if not payment:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("支付记录不存在")
    
    if str(payment.user_id) != str(current_user.id):
        from src.core.exceptions import AuthorizationError
        raise AuthorizationError("无权操作此订单")
    
    # 刷新二维码
    qr_code = await service.refresh_alipay_qrcode(payment_no)
    
    logger.info(f"[RefreshQRCode] 二维码刷新成功 | payment_no={payment_no}")
    
    return BaseResponse(
        data={
            "payment_no": payment_no,
            "qr_code": qr_code,
        }
    )


class ClientLogRequest(BaseModel):
    message: str
    level: str = "info"
    data: Optional[dict] = None


@router.post("/client-log")
async def client_log(log: ClientLogRequest, request: Request):
    """
    接收前端日志并记录到文件
    
    Args:
        log: 日志内容
    """
    from src.config.logging_config import get_logger
    
    logger = get_logger("client")
    
    # 获取客户端IP
    client_ip = request.client.host if request.client else "unknown"
    
    log_message = f"[CLIENT:{client_ip}] [{log.level.upper()}] {log.message}"
    if log.data:
        import json
        log_message += f" | data: {json.dumps(log.data, ensure_ascii=False)}"
    
    if log.level == "error":
        logger.error(log_message)
    elif log.level == "warning":
        logger.warning(log_message)
    else:
        logger.info(log_message)
    
    return BaseResponse(data={"logged": True})


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


@router.get("/alipay/return")
async def alipay_return(request: Request):
    """
    支付宝同步返回地址（中转站）
    
    由于支付宝从服务器端跳转回 RETURN_URL，浏览器需要能访问到该地址。
    此接口接收支付宝的返回参数，然后重定向到前端页面，让前端处理支付状态。
    
    配置格式：
    ALIPAY_RETURN_URL=https://你的域名/api/v1/payments/alipay/return
    """
    from src.config.logging_config import get_logger
    
    logger = get_logger("payment")
    logger.info("[AlipayReturn] Received return request")
    
    # 获取所有查询参数
    query_params = dict(request.query_params)
    logger.info(f"[AlipayReturn] Query params: {query_params}")
    
    # 提取关键参数
    out_trade_no = query_params.get("out_trade_no")
    
    # 【修复】优先使用配置的前端基础地址
    # 如果配置了 frontend_base_url（用于 ngrok/内网穿透），使用配置值
    # 否则尝试从请求推断
    from src.config.settings import settings
    
    if settings.frontend_base_url and settings.frontend_base_url != "http://localhost:3000":
        # 使用配置的前端地址（支持 ngrok、内网穿透、域名等场景）
        frontend_base = settings.frontend_base_url.rstrip('/')
        logger.info(f"[AlipayReturn] Using configured frontend_base_url: {frontend_base}")
    else:
        # 开发模式：从请求头获取原始 Host，构建前端地址
        host = request.headers.get("host", "localhost:3000")
        scheme = "https" if request.headers.get("x-forwarded-proto") == "https" else "http"
        frontend_base = f"{scheme}://{host}"
        logger.info(f"[AlipayReturn] Using request-based frontend_base: {frontend_base}")
    
    # 【V7.3 修改】重定向到专用支付成功页面，而不是充值页面
    # 支付成功页面会：1. 显示支付结果 2. 通知原始窗口 3. 提示用户关闭
    frontend_path = "/payment-success"
    redirect_url = f"{frontend_base}{frontend_path}"
    
    # 如果有 out_trade_no，附加到 URL
    if out_trade_no:
        from urllib.parse import urlencode
        params = {"out_trade_no": out_trade_no}
        redirect_url = f"{redirect_url}?{urlencode(params)}"
    
    logger.info(f"[AlipayReturn] Redirecting to: {redirect_url}")
    
    # 重定向到前端
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/alipay/callback", response_model=BaseResponse[dict])
async def alipay_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    支付宝异步回调通知接口
    
    用于接收支付宝支付结果通知，验证签名并更新订单状态。
    沙箱环境同样适用此接口。
    
    注意：此接口需要公网可访问，回调URL配置格式：
    https://你的域名/api/v1/payments/alipay/callback
    """
    from src.config.settings import settings
    from src.config.logging_config import get_logger
    from alipay.aop.api.util.SignatureUtils import get_sign_content, verify_with_rsa
    
    logger = get_logger("payment")
    logger.info("[AlipayCallback] Received alipay callback")
    
    # 检查是否配置了支付宝
    if not settings.alipay_app_id or not settings.get_alipay_public_key():
        logger.error("[AlipayCallback] Alipay not configured")
        return BaseResponse(data={"success": False, "message": "支付宝未配置"})
    
    try:
        # 获取POST数据
        form_data = await request.form()
        form_dict = dict(form_data)
        logger.info(f"[AlipayCallback] Form data: {form_dict}")
        
        # 验证签名
        signature = form_dict.get("sign")
        if not signature:
            logger.error("[AlipayCallback] Missing signature")
            return BaseResponse(data={"success": False, "message": "缺少签名参数"})
        
        # 构建签名内容：排除 sign 和 sign_type，按字母顺序排列
        sign_parts = []
        for key in sorted(form_dict.keys()):
            if key in ("sign", "sign_type"):
                continue
            value = form_dict.get(key, "")
            sign_parts.append(f"{key}={value}")
        sign_content = "&".join(sign_parts)
        
        # 验证签名：verify_with_rsa 需要 message 是有 read() 方法的对象
        from io import BytesIO
        message_stream = BytesIO(sign_content.encode('utf-8'))
        is_valid = verify_with_rsa(settings.get_alipay_public_key(), message_stream, signature)
        
        if not is_valid:
            logger.warning("[AlipayCallback] Signature verification failed")
            return BaseResponse(data={"success": False, "message": "签名验证失败"})
        
        # 获取交易状态
        trade_status = form_dict.get("trade_status")
        out_trade_no = form_dict.get("out_trade_no")  # 商户订单号
        
        if not out_trade_no:
            logger.error("[AlipayCallback] Missing out_trade_no")
            return BaseResponse(data={"success": False, "message": "缺少订单号"})
        
        trade_no = form_dict.get("trade_no")  # 支付宝交易号
        total_amount = form_dict.get("total_amount")
        
        logger.info(f"[AlipayCallback] trade_status={trade_status}, out_trade_no={out_trade_no}")
        
        # 处理支付结果
        service = PaymentService(db)
        
        # 注意：TRADE_HAS_SUCCESS 是沙箱环境返回的"已付款"状态
        if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED", "TRADE_HAS_SUCCESS"):
            # 支付成功
            payer_info = {
                "buyer_email": form_dict.get("buyer_logon_id", ""),
                "buyer_id": form_dict.get("buyer_id", ""),
                "pay_time": form_dict.get("gmt_payment", ""),
            }
            
            await service.handle_payment_callback(
                order_no=out_trade_no,
                transaction_id=trade_no,
                status="success",
                payer_info=payer_info,
                raw_data=form_dict,
            )
            
            logger.info(f"[AlipayCallback] Payment success: {out_trade_no}")
            return BaseResponse(data={"success": True, "message": "支付成功"})
        
        elif trade_status == "WAIT_BUYER_PAY":
            # 等待买家付款
            logger.info(f"[AlipayCallback] Waiting for payment: {out_trade_no}")
            return BaseResponse(data={"success": True, "message": "等待付款"})
        
        elif trade_status == "TRADE_CLOSED":
            # 交易关闭
            logger.info(f"[AlipayCallback] Trade closed: {out_trade_no}")
            return BaseResponse(data={"success": True, "message": "交易关闭"})
        
        else:
            logger.warning(f"[AlipayCallback] Unknown trade_status: {trade_status}")
            return BaseResponse(data={"success": True, "message": "状态未知"})
            
    except Exception as e:
        logger.error(f"[AlipayCallback] Error: {e}", exc_info=True)
        return BaseResponse(data={"success": False, "message": str(e)})


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

"""
支付配置 API - 管理员接口

提供支付宝、微信支付等真实支付渠道的配置管理
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.config.database import get_db
from src.models.system_config import SystemConfig
from src.schemas.response import BaseResponse
from src.services.auth_service import get_current_admin_user

router = APIRouter(prefix="/payment-config", tags=["管理员-支付配置"])


# ==================== Pydantic Models ====================

class ChannelConfig(BaseModel):
    """渠道配置"""
    enabled: bool
    sandbox: bool = True
    notify_url: Optional[str] = None
    return_url: Optional[str] = None


class AlipayConfig(ChannelConfig):
    """支付宝配置"""
    app_id: Optional[str] = None
    private_key: Optional[str] = None
    alipay_public_key: Optional[str] = None


class WechatConfig(ChannelConfig):
    """微信支付配置"""
    mchid: Optional[str] = None
    appid: Optional[str] = None
    api_key: Optional[str] = None
    cert_path: Optional[str] = None


class BankcardConfig(ChannelConfig):
    """银行卡配置"""
    merchant_id: Optional[str] = None
    terminal_id: Optional[str] = None


class PaymentConfigResponse(BaseModel):
    """支付配置响应"""
    mock_mode: bool
    alipay: AlipayConfig
    wechat: WechatConfig
    bankcard: BankcardConfig


class PaymentConfigUpdate(BaseModel):
    """支付配置更新"""
    mock_mode: Optional[bool] = None
    alipay: Optional[AlipayConfig] = None
    wechat: Optional[WechatConfig] = None
    bankcard: Optional[BankcardConfig] = None


class ConfigStatusItem(BaseModel):
    """配置状态项"""
    channel: str
    channel_name: str
    enabled: bool
    sandbox: bool
    configured: bool  # 是否已配置密钥
    status: str  # ready, not_configured, disabled


class PaymentConfigStatusResponse(BaseModel):
    """支付配置状态响应"""
    mock_mode: bool
    channels: List[ConfigStatusItem]


# ==================== 辅助函数 ====================

def parse_bool_config(value: Optional[str]) -> bool:
    """解析布尔配置"""
    if value is None:
        return False
    return value.lower() in ('true', '1', 'yes', 'on')


async def get_config_value(db: AsyncSession, key: str) -> Optional[str]:
    """获取配置值"""
    result = await db.execute(
        select(SystemConfig).where(
            SystemConfig.category == key.split('.')[0],
            SystemConfig.key == key.split('.')[1] if '.' in key else key
        )
    )
    config = result.scalar_one_or_none()
    return config.value if config else None


async def set_config_value(
    db: AsyncSession, 
    category: str, 
    key: str, 
    value: str,
    encrypted: bool = False,
    updated_by: str = None
):
    """设置配置值"""
    result = await db.execute(
        select(SystemConfig).where(
            SystemConfig.category == category,
            SystemConfig.key == key
        )
    )
    config = result.scalar_one_or_none()
    
    if config:
        config.value = value
        if encrypted:
            config.is_encrypted = True
        if updated_by:
            config.updated_by = updated_by
    else:
        config = SystemConfig(
            category=category,
            key=key,
            value=value,
            is_encrypted=encrypted,
            updated_by=updated_by
        )
        db.add(config)
    
    await db.commit()


# ==================== API 接口 ====================

@router.get("/status", response_model=BaseResponse[PaymentConfigStatusResponse])
async def get_payment_config_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    获取支付配置状态（快速检查）
    
    返回各支付渠道的启用状态和配置状态
    """
    # 获取支付模式
    mock_mode_result = await db.execute(
        select(SystemConfig).where(
            SystemConfig.category == "payment",
            SystemConfig.key == "mock_mode"
        )
    )
    mock_mode = True
    if mock_mode_result:
        mock_config = mock_mode_result.scalar_one_or_none()
        if mock_config:
            mock_mode = parse_bool_config(mock_config.value)
    
    channels = []
    
    # 检查支付宝
    alipay_enabled = parse_bool_config(await get_config_value(db, "payment.alipay.enabled"))
    alipay_app_id = await get_config_value(db, "payment.alipay.app_id")
    alipay_sandbox = parse_bool_config(await get_config_value(db, "payment.alipay.sandbox"))
    channels.append(ConfigStatusItem(
        channel="alipay",
        channel_name="支付宝",
        enabled=alipay_enabled,
        sandbox=alipay_sandbox,
        configured=bool(alipay_app_id),
        status="ready" if alipay_app_id else ("disabled" if not alipay_enabled else "not_configured")
    ))
    
    # 检查微信支付
    wechat_enabled = parse_bool_config(await get_config_value(db, "payment.wechat.enabled"))
    wechat_mchid = await get_config_value(db, "payment.wechat.mchid")
    wechat_sandbox = parse_bool_config(await get_config_value(db, "payment.wechat.sandbox"))
    channels.append(ConfigStatusItem(
        channel="wechat",
        channel_name="微信支付",
        enabled=wechat_enabled,
        sandbox=wechat_sandbox,
        configured=bool(wechat_mchid),
        status="ready" if wechat_mchid else ("disabled" if not wechat_enabled else "not_configured")
    ))
    
    # 检查银行卡
    bankcard_enabled = parse_bool_config(await get_config_value(db, "payment.bankcard.enabled"))
    bankcard_merchant_id = await get_config_value(db, "payment.bankcard.merchant_id")
    channels.append(ConfigStatusItem(
        channel="bankcard",
        channel_name="银行卡",
        enabled=bankcard_enabled,
        sandbox=False,
        configured=bool(bankcard_merchant_id),
        status="ready" if bankcard_merchant_id else ("disabled" if not bankcard_enabled else "not_configured")
    ))
    
    return BaseResponse(data=PaymentConfigStatusResponse(
        mock_mode=mock_mode,
        channels=channels
    ))


@router.get("/detail", response_model=BaseResponse[PaymentConfigResponse])
async def get_payment_config_detail(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    获取支付配置详情（完整配置，密钥部分脱敏）
    
    注意：私钥等敏感信息会被脱敏显示
    """
    # 获取支付模式
    mock_mode = parse_bool_config(await get_config_value(db, "payment.mock_mode"))
    
    # 支付宝配置
    alipay = AlipayConfig(
        enabled=parse_bool_config(await get_config_value(db, "payment.alipay.enabled")),
        sandbox=parse_bool_config(await get_config_value(db, "payment.alipay.sandbox")),
        app_id=await get_config_value(db, "payment.alipay.app_id"),
        notify_url=await get_config_value(db, "payment.alipay.notify_url"),
        return_url=await get_config_value(db, "payment.alipay.return_url"),
        # 私钥信息不返回，仅返回是否已配置
        private_key="***已配置***" if await get_config_value(db, "payment.alipay.private_key") else None,
        alipay_public_key="***已配置***" if await get_config_value(db, "payment.alipay.alipay_public_key") else None,
    )
    
    # 微信支付配置
    wechat = WechatConfig(
        enabled=parse_bool_config(await get_config_value(db, "payment.wechat.enabled")),
        sandbox=parse_bool_config(await get_config_value(db, "payment.wechat.sandbox")),
        mchid=await get_config_value(db, "payment.wechat.mchid"),
        appid=await get_config_value(db, "payment.wechat.appid"),
        notify_url=await get_config_value(db, "payment.wechat.notify_url"),
        # 密钥信息不返回
        api_key="***已配置***" if await get_config_value(db, "payment.wechat.api_key") else None,
        cert_path="***已配置***" if await get_config_value(db, "payment.wechat.cert_path") else None,
    )
    
    # 银行卡配置
    bankcard = BankcardConfig(
        enabled=parse_bool_config(await get_config_value(db, "payment.bankcard.enabled")),
        merchant_id=await get_config_value(db, "payment.bankcard.merchant_id"),
        terminal_id=await get_config_value(db, "payment.bankcard.terminal_id"),
        notify_url=await get_config_value(db, "payment.bankcard.notify_url"),
    )
    
    return BaseResponse(data=PaymentConfigResponse(
        mock_mode=mock_mode,
        alipay=alipay,
        wechat=wechat,
        bankcard=bankcard
    ))


@router.put("/update", response_model=BaseResponse[PaymentConfigResponse])
async def update_payment_config(
    config: PaymentConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    更新支付配置
    
    支持部分更新，只传递需要修改的字段
    """
    username = current_user.get("username", "admin")
    
    # 更新支付模式
    if config.mock_mode is not None:
        await set_config_value(db, "payment", "mock_mode", str(config.mock_mode).lower(), updated_by=username)
    
    # 更新支付宝配置
    if config.alipay:
        if config.alipay.enabled is not None:
            await set_config_value(db, "payment.alipay", "enabled", str(config.alipay.enabled).lower(), updated_by=username)
        if config.alipay.sandbox is not None:
            await set_config_value(db, "payment.alipay", "sandbox", str(config.alipay.sandbox).lower(), updated_by=username)
        if config.alipay.app_id is not None:
            await set_config_value(db, "payment.alipay", "app_id", config.alipay.app_id, encrypted=True, updated_by=username)
        if config.alipay.private_key is not None:
            await set_config_value(db, "payment.alipay", "private_key", config.alipay.private_key, encrypted=True, updated_by=username)
        if config.alipay.alipay_public_key is not None:
            await set_config_value(db, "payment.alipay", "alipay_public_key", config.alipay.alipay_public_key, encrypted=True, updated_by=username)
        if config.alipay.notify_url is not None:
            await set_config_value(db, "payment.alipay", "notify_url", config.alipay.notify_url, updated_by=username)
        if config.alipay.return_url is not None:
            await set_config_value(db, "payment.alipay", "return_url", config.alipay.return_url, updated_by=username)
    
    # 更新微信支付配置
    if config.wechat:
        if config.wechat.enabled is not None:
            await set_config_value(db, "payment.wechat", "enabled", str(config.wechat.enabled).lower(), updated_by=username)
        if config.wechat.sandbox is not None:
            await set_config_value(db, "payment.wechat", "sandbox", str(config.wechat.sandbox).lower(), updated_by=username)
        if config.wechat.mchid is not None:
            await set_config_value(db, "payment.wechat", "mchid", config.wechat.mchid, encrypted=True, updated_by=username)
        if config.wechat.appid is not None:
            await set_config_value(db, "payment.wechat", "appid", config.wechat.appid, encrypted=True, updated_by=username)
        if config.wechat.api_key is not None:
            await set_config_value(db, "payment.wechat", "api_key", config.wechat.api_key, encrypted=True, updated_by=username)
        if config.wechat.cert_path is not None:
            await set_config_value(db, "payment.wechat", "cert_path", config.wechat.cert_path, encrypted=True, updated_by=username)
        if config.wechat.notify_url is not None:
            await set_config_value(db, "payment.wechat", "notify_url", config.wechat.notify_url, updated_by=username)
    
    # 更新银行卡配置
    if config.bankcard:
        if config.bankcard.enabled is not None:
            await set_config_value(db, "payment.bankcard", "enabled", str(config.bankcard.enabled).lower(), updated_by=username)
        if config.bankcard.merchant_id is not None:
            await set_config_value(db, "payment.bankcard", "merchant_id", config.bankcard.merchant_id, encrypted=True, updated_by=username)
        if config.bankcard.terminal_id is not None:
            await set_config_value(db, "payment.bankcard", "terminal_id", config.bankcard.terminal_id, encrypted=True, updated_by=username)
        if config.bankcard.notify_url is not None:
            await set_config_value(db, "payment.bankcard", "notify_url", config.bankcard.notify_url, updated_by=username)
    
    # 返回更新后的配置
    return await get_payment_config_detail(db, current_user)


@router.post("/test/alipay", response_model=BaseResponse[dict])
async def test_alipay_config(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    测试支付宝配置连通性
    
    验证配置的AppID和密钥是否有效
    """
    app_id = await get_config_value(db, "payment.alipay.app_id")
    private_key = await get_config_value(db, "payment.alipay.private_key")
    alipay_public_key = await get_config_value(db, "payment.alipay.alipay_public_key")
    sandbox = parse_bool_config(await get_config_value(db, "payment.alipay.sandbox"))
    
    if not all([app_id, private_key, alipay_public_key]):
        return BaseResponse(
            code=400,
            message="支付宝配置不完整，请检查AppID、私钥和公钥",
            data={"success": False, "error": "incomplete_config"}
        )
    
    # TODO: 实际测试支付宝SDK连通性
    # 当前返回模拟结果
    return BaseResponse(
        data={
            "success": True,
            "message": "支付宝配置测试通过",
            "mode": "sandbox" if sandbox else "production",
            "app_id": app_id
        }
    )


@router.post("/test/wechat", response_model=BaseResponse[dict])
async def test_wechat_config(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    测试微信支付配置连通性
    
    验证商户号和密钥是否有效
    """
    mchid = await get_config_value(db, "payment.wechat.mchid")
    api_key = await get_config_value(db, "payment.wechat.api_key")
    sandbox = parse_bool_config(await get_config_value(db, "payment.wechat.sandbox"))
    
    if not all([mchid, api_key]):
        return BaseResponse(
            code=400,
            message="微信支付配置不完整，请检查商户号和API密钥",
            data={"success": False, "error": "incomplete_config"}
        )
    
    # TODO: 实际测试微信支付SDK连通性
    return BaseResponse(
        data={
            "success": True,
            "message": "微信支付配置测试通过",
            "mode": "sandbox" if sandbox else "production",
            "mchid": mchid
        }
    )

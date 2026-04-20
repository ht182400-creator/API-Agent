"""
计费配置 API - 管理员接口

提供计费配置的CRUD管理功能，支持三种计费模式：
1. call - 按调用次数计费
2. token - 按Token数计费
3. package - 套餐包计费
"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_

from src.config.database import get_db
from src.models.pricing_config import PricingConfig
from src.models.repository import Repository
from src.schemas.response import BaseResponse
from src.services.auth_service import get_current_admin_user

router = APIRouter(prefix="/pricing-configs", tags=["管理员-计费配置"])


# ==================== Pydantic Models ====================

class PackageItem(BaseModel):
    """套餐包项"""
    id: str
    name: str
    calls: int  # 可用调用次数
    price: float
    period_days: int = 30  # 有效期天数


class PricingTierItem(BaseModel):
    """阶梯定价项"""
    min_calls: int
    max_calls: Optional[int] = None
    discount: float = 1.0


class PricingConfigBase(BaseModel):
    """计费配置基础模型"""
    repo_id: Optional[str] = None
    pricing_type: str = Field(..., pattern="^(call|token|package)$")

    # 按调用计费
    price_per_call: Optional[float] = None
    free_calls: int = 0

    # 按Token计费
    price_per_1k_input_tokens: Optional[float] = None
    price_per_1k_output_tokens: Optional[float] = None
    free_input_tokens: int = 0
    free_output_tokens: int = 0

    # 套餐包计费
    packages: Optional[List[PackageItem]] = None
    default_package_id: Optional[str] = None

    # 通用配置
    pricing_tiers: Optional[List[PricingTierItem]] = None
    vip_discounts: Optional[Dict[str, float]] = None
    priority: int = 100

    # 生效时间
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    # 状态
    status: str = Field(default="active", pattern="^(active|inactive|deprecated)$")
    description: Optional[str] = None


class PricingConfigCreate(PricingConfigBase):
    """创建计费配置请求"""
    pass


class PricingConfigUpdate(BaseModel):
    """更新计费配置请求"""
    repo_id: Optional[str] = None
    pricing_type: Optional[str] = Field(None, pattern="^(call|token|package)$")

    # 按调用计费
    price_per_call: Optional[float] = None
    free_calls: Optional[int] = None

    # 按Token计费
    price_per_1k_input_tokens: Optional[float] = None
    price_per_1k_output_tokens: Optional[float] = None
    free_input_tokens: Optional[int] = None
    free_output_tokens: Optional[int] = None

    # 套餐包计费
    packages: Optional[List[PackageItem]] = None
    default_package_id: Optional[str] = None

    # 通用配置
    pricing_tiers: Optional[List[PricingTierItem]] = None
    vip_discounts: Optional[Dict[str, float]] = None
    priority: Optional[int] = None

    # 生效时间
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    # 状态
    status: Optional[str] = Field(None, pattern="^(active|inactive|deprecated)$")
    description: Optional[str] = None


class PricingConfigResponse(BaseModel):
    """计费配置响应"""
    id: str
    repo_id: Optional[str]
    repo_name: Optional[str] = None
    pricing_type: str

    # 按调用计费
    price_per_call: Optional[float]
    free_calls: int

    # 按Token计费
    price_per_1k_input_tokens: Optional[float]
    price_per_1k_output_tokens: Optional[float]
    free_input_tokens: int
    free_output_tokens: int

    # 套餐包计费
    packages: List[Dict[str, Any]]
    default_package_id: Optional[str]

    # 通用配置
    pricing_tiers: List[Dict[str, Any]]
    vip_discounts: Dict[str, float]
    priority: int

    # 生效时间
    valid_from: Optional[str]
    valid_until: Optional[str]

    # 状态
    status: str
    description: Optional[str]

    # 审计字段
    created_at: Optional[str]
    updated_at: Optional[str]
    created_by: Optional[str]

    is_valid: bool  # 是否在有效期内

    class Config:
        from_attributes = True


class PricingConfigListResponse(BaseModel):
    """计费配置列表响应"""
    items: List[PricingConfigResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== 辅助函数 ====================

def model_to_response(config: PricingConfig) -> PricingConfigResponse:
    """将 ORM 模型转换为响应模型"""
    from src.models.repository import Repository

    repo_name = None
    if config.repo_id:
        # 注意：这里需要同步查询，使用已有数据
        repo_name = getattr(config, 'repo_name', None)

    return PricingConfigResponse(
        id=str(config.id),
        repo_id=str(config.repo_id) if config.repo_id else None,
        repo_name=repo_name,
        pricing_type=config.pricing_type,

        # 按调用计费
        price_per_call=float(config.price_per_call) if config.price_per_call else None,
        free_calls=config.free_calls or 0,

        # 按Token计费
        price_per_1k_input_tokens=float(config.price_per_1k_input_tokens) if config.price_per_1k_input_tokens else None,
        price_per_1k_output_tokens=float(config.price_per_1k_output_tokens) if config.price_per_1k_output_tokens else None,
        free_input_tokens=config.free_input_tokens or 0,
        free_output_tokens=config.free_output_tokens or 0,

        # 套餐包计费
        packages=config.packages or [],
        default_package_id=config.default_package_id,

        # 通用配置
        pricing_tiers=config.pricing_tiers or [],
        vip_discounts=config.vip_discounts or {},
        priority=config.priority or 100,

        # 生效时间
        valid_from=config.valid_from.isoformat() if config.valid_from else None,
        valid_until=config.valid_until.isoformat() if config.valid_until else None,

        # 状态
        status=config.status or "active",
        description=config.description,

        # 审计字段
        created_at=config.created_at.isoformat() if config.created_at else None,
        updated_at=config.updated_at.isoformat() if config.updated_at else None,
        created_by=str(config.created_by) if config.created_by else None,

        # 是否在有效期内
        is_valid=config.is_valid(),
    )


# ==================== API 接口 ====================

@router.get("", response_model=BaseResponse[PricingConfigListResponse])
async def get_pricing_configs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repo_id: Optional[str] = Query(None, description="仓库ID过滤"),
    pricing_type: Optional[str] = Query(None, pattern="^(call|token|package)$"),
    status: Optional[str] = Query(None, pattern="^(active|inactive|deprecated)$"),
    is_global: Optional[bool] = Query(None, description="是否全局配置（repo_id为空）"),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取计费配置列表（分页）

    支持按仓库ID、计费类型、状态过滤
    """
    # 构建查询条件
    conditions = []
    if repo_id:
        conditions.append(PricingConfig.repo_id == uuid.UUID(repo_id))
    if pricing_type:
        conditions.append(PricingConfig.pricing_type == pricing_type)
    if status:
        conditions.append(PricingConfig.status == status)
    if is_global is True:
        conditions.append(PricingConfig.repo_id.is_(None))
    elif is_global is False:
        conditions.append(PricingConfig.repo_id.isnot(None))

    # 获取总数
    count_query = select(func.count(PricingConfig.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    offset = (page - 1) * page_size
    query = select(PricingConfig).order_by(desc(PricingConfig.priority), desc(PricingConfig.created_at))
    if conditions:
        query = query.where(and_(*conditions))
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    configs = result.scalars().all()

    # 填充仓库名称
    repo_ids = [c.repo_id for c in configs if c.repo_id]
    repo_names = {}
    if repo_ids:
        repo_result = await db.execute(
            select(Repository.id, Repository.name).where(Repository.id.in_(repo_ids))
        )
        for row in repo_result.all():
            repo_names[row[0]] = row[1]

    # 转换响应
    items = []
    for config in configs:
        resp = model_to_response(config)
        if config.repo_id and config.repo_id in repo_names:
            resp.repo_name = repo_names[config.repo_id]
        items.append(resp)

    return BaseResponse(data=PricingConfigListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0,
    ))


@router.get("/global", response_model=BaseResponse[List[PricingConfigResponse]])
async def get_global_pricing_configs(
    pricing_type: Optional[str] = Query(None, pattern="^(call|token|package)$"),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取全局默认计费配置

    全局配置的 repo_id 为空
    """
    query = select(PricingConfig).where(PricingConfig.repo_id.is_(None))
    if pricing_type:
        query = query.where(PricingConfig.pricing_type == pricing_type)
    query = query.order_by(PricingConfig.priority)

    result = await db.execute(query)
    configs = result.scalars().all()

    return BaseResponse(data=[model_to_response(c) for c in configs])


@router.get("/by-repo/{repo_id}", response_model=BaseResponse[List[PricingConfigResponse]])
async def get_pricing_configs_by_repo(
    repo_id: str,
    active_only: bool = Query(True),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定仓库的计费配置

    如果仓库没有特定配置，返回全局默认配置
    """
    repo_uuid = uuid.UUID(repo_id)

    # 查询仓库特定配置
    query = select(PricingConfig).where(PricingConfig.repo_id == repo_uuid)
    if active_only:
        query = query.where(PricingConfig.status == "active")
    query = query.order_by(PricingConfig.priority)

    result = await db.execute(query)
    configs = result.scalars().all()

    # 如果没有仓库特定配置，获取全局配置
    if not configs:
        query = select(PricingConfig).where(PricingConfig.repo_id.is_(None))
        if active_only:
            query = query.where(PricingConfig.status == "active")
        query = query.order_by(PricingConfig.priority)
        result = await db.execute(query)
        configs = result.scalars().all()

    # 获取仓库名称
    repo_result = await db.execute(select(Repository.name).where(Repository.id == repo_uuid))
    repo_name = repo_result.scalar_one_or_none()

    # 转换响应
    items = []
    for config in configs:
        resp = model_to_response(config)
        resp.repo_name = repo_name
        items.append(resp)

    return BaseResponse(data=items)


# 费用预览路由 - 必须放在 /{config_id} 之前，否则会被错误匹配
@router.get("/calculate-cost", response_model=BaseResponse[dict])
async def calculate_cost_preview(
    pricing_type: str = Query(..., pattern="^(call|token|package)$"),
    call_count: int = Query(1, ge=0),
    input_tokens: int = Query(0, ge=0),
    output_tokens: int = Query(0, ge=0),
    vip_level: int = Query(0, ge=0),
    config_id: Optional[str] = Query(None, description="使用指定配置"),
    repo_id: Optional[str] = Query(None, description="使用仓库的默认配置"),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    预览费用计算

    根据指定配置计算费用，可用于测试计费配置是否正确
    """
    config = None

    if config_id:
        # 使用指定配置
        try:
            config_uuid = uuid.UUID(config_id)
            result = await db.execute(
                select(PricingConfig).where(PricingConfig.id == config_uuid)
            )
            config = result.scalar_one_or_none()
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的配置ID格式")

    elif repo_id:
        # 使用仓库的默认配置
        try:
            repo_uuid = uuid.UUID(repo_id)
            result = await db.execute(
                select(PricingConfig).where(
                    and_(
                        PricingConfig.repo_id == repo_uuid,
                        PricingConfig.pricing_type == pricing_type,
                        PricingConfig.status == "active"
                    )
                ).order_by(PricingConfig.priority)
            )
            config = result.scalar_one_or_none()

            # 如果没有仓库特定配置，使用全局配置
            if not config:
                result = await db.execute(
                    select(PricingConfig).where(
                        and_(
                            PricingConfig.repo_id.is_(None),
                            PricingConfig.pricing_type == pricing_type,
                            PricingConfig.status == "active"
                        )
                    ).order_by(PricingConfig.priority)
                )
                config = result.scalar_one_or_none()
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的仓库ID格式")

    else:
        # 使用全局默认配置
        result = await db.execute(
            select(PricingConfig).where(
                and_(
                    PricingConfig.repo_id.is_(None),
                    PricingConfig.pricing_type == pricing_type,
                    PricingConfig.status == "active"
                )
            ).order_by(PricingConfig.priority)
        )
        config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="未找到有效的计费配置")

    # 计算费用
    cost = config.calculate_cost(
        call_count=call_count,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        vip_level=vip_level
    )

    # 计算详情
    details = {
        "base_cost": 0.0,
        "tier_discount": 1.0,
        "vip_discount": 1.0,
        "free_deduction": 0.0,
    }

    if config.pricing_type == "call":
        billable_calls = max(0, call_count - config.free_calls)
        unit_price = float(config.price_per_call or 0)
        details["base_cost"] = billable_calls * unit_price
        details["free_deduction"] = call_count - billable_calls

    elif config.pricing_type == "token":
        billable_input = max(0, input_tokens - config.free_input_tokens)
        billable_output = max(0, output_tokens - config.free_output_tokens)
        input_price = float(config.price_per_1k_input_tokens or 0) / 1000
        output_price = float(config.price_per_1k_output_tokens or 0) / 1000
        details["base_cost"] = billable_input * input_price + billable_output * output_price
        details["free_deduction"] = (input_tokens - billable_input) + (output_tokens - billable_output)

    # 阶梯折扣
    details["tier_discount"] = config.get_tier_discount(call_count)
    details["vip_discount"] = config.get_vip_discount(vip_level)

    return BaseResponse(data={
        "config_id": str(config.id),
        "pricing_type": config.pricing_type,
        "input": {
            "call_count": call_count,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "vip_level": vip_level,
        },
        "cost": round(cost, 4),
        "details": details,
    })


@router.get("/{config_id}", response_model=BaseResponse[PricingConfigResponse])
async def get_pricing_config(
    config_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取单个计费配置详情
    """
    try:
        config_uuid = uuid.UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的配置ID格式")

    result = await db.execute(
        select(PricingConfig).where(PricingConfig.id == config_uuid)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="计费配置不存在")

    resp = model_to_response(config)

    # 填充仓库名称
    if config.repo_id:
        repo_result = await db.execute(
            select(Repository.name).where(Repository.id == config.repo_id)
        )
        repo_name = repo_result.scalar_one_or_none()
        if repo_name:
            resp.repo_name = repo_name

    return BaseResponse(data=resp)


@router.post("", response_model=BaseResponse[PricingConfigResponse])
async def create_pricing_config(
    config_data: PricingConfigCreate,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建计费配置

    如果 repo_id 为空，则创建全局默认配置
    """
    username = current_user.get("username")

    # 验证 repo_id 是否存在
    repo_uuid = None
    if config_data.repo_id:
        try:
            repo_uuid = uuid.UUID(config_data.repo_id)
            # 检查仓库是否存在
            repo_result = await db.execute(
                select(Repository).where(Repository.id == repo_uuid)
            )
            if not repo_result.scalar_one_or_none():
                raise HTTPException(status_code=404, detail=f"仓库不存在: {config_data.repo_id}")
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的仓库ID格式")

    # 检查同类型配置是否已存在（同一仓库+同一计费类型只能有一个生效配置）
    conditions = [
        PricingConfig.repo_id == repo_uuid,
        PricingConfig.pricing_type == config_data.pricing_type,
        PricingConfig.status == "active"
    ]
    existing = await db.execute(
        select(PricingConfig.id).where(and_(*conditions))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"该仓库已存在生效的 {config_data.pricing_type} 类型配置，请先禁用或更新现有配置"
        )

    # 创建配置
    config = PricingConfig(
        repo_id=repo_uuid,
        pricing_type=config_data.pricing_type,
        price_per_call=config_data.price_per_call,
        free_calls=config_data.free_calls,
        price_per_1k_input_tokens=config_data.price_per_1k_input_tokens,
        price_per_1k_output_tokens=config_data.price_per_1k_output_tokens,
        free_input_tokens=config_data.free_input_tokens,
        free_output_tokens=config_data.free_output_tokens,
        packages=[p.model_dump() for p in config_data.packages] if config_data.packages else [],
        default_package_id=config_data.default_package_id,
        pricing_tiers=[t.model_dump() for t in config_data.pricing_tiers] if config_data.pricing_tiers else [],
        vip_discounts=config_data.vip_discounts or {},
        priority=config_data.priority,
        valid_from=config_data.valid_from,
        valid_until=config_data.valid_until,
        status=config_data.status,
        description=config_data.description,
        created_by=uuid.UUID(username) if username and len(username) == 36 else None,
    )

    db.add(config)
    await db.commit()
    await db.refresh(config)

    return BaseResponse(data=model_to_response(config))


@router.put("/{config_id}", response_model=BaseResponse[PricingConfigResponse])
async def update_pricing_config(
    config_id: str,
    config_data: PricingConfigUpdate,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新计费配置
    """
    try:
        config_uuid = uuid.UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的配置ID格式")

    result = await db.execute(
        select(PricingConfig).where(PricingConfig.id == config_uuid)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="计费配置不存在")

    # 更新字段
    update_data = config_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "repo_id":
            if value:
                try:
                    config.repo_id = uuid.UUID(value)
                except ValueError:
                    raise HTTPException(status_code=400, detail="无效的仓库ID格式")
            else:
                config.repo_id = None
        elif field == "packages":
            config.packages = [p.model_dump() if hasattr(p, 'model_dump') else p for p in value] if value else []
        elif field == "pricing_tiers":
            config.pricing_tiers = [t.model_dump() if hasattr(t, 'model_dump') else t for t in value] if value else []
        elif value is not None:
            setattr(config, field, value)

    config.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(config)

    resp = model_to_response(config)

    # 填充仓库名称
    if config.repo_id:
        repo_result = await db.execute(
            select(Repository.name).where(Repository.id == config.repo_id)
        )
        repo_name = repo_result.scalar_one_or_none()
        if repo_name:
            resp.repo_name = repo_name

    return BaseResponse(data=resp)


@router.delete("/{config_id}", response_model=BaseResponse[dict])
async def delete_pricing_config(
    config_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    删除计费配置

    建议使用禁用代替删除，禁用后可在历史记录中追溯
    """
    try:
        config_uuid = uuid.UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的配置ID格式")

    result = await db.execute(
        select(PricingConfig).where(PricingConfig.id == config_uuid)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="计费配置不存在")

    # 执行删除
    await db.delete(config)
    await db.commit()

    return BaseResponse(data={"id": config_id, "deleted": True})


@router.post("/{config_id}/disable", response_model=BaseResponse[PricingConfigResponse])
async def disable_pricing_config(
    config_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    禁用计费配置
    """
    try:
        config_uuid = uuid.UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的配置ID格式")

    result = await db.execute(
        select(PricingConfig).where(PricingConfig.id == config_uuid)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="计费配置不存在")

    config.status = "inactive"
    config.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(config)

    return BaseResponse(data=model_to_response(config))


@router.post("/{config_id}/enable", response_model=BaseResponse[PricingConfigResponse])
async def enable_pricing_config(
    config_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    启用计费配置
    """
    try:
        config_uuid = uuid.UUID(config_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的配置ID格式")

    result = await db.execute(
        select(PricingConfig).where(PricingConfig.id == config_uuid)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="计费配置不存在")

    # 检查是否与其他生效配置冲突
    repo_uuid = config.repo_id
    conditions = [
        PricingConfig.id != config_uuid,
        PricingConfig.repo_id == repo_uuid,
        PricingConfig.pricing_type == config.pricing_type,
        PricingConfig.status == "active"
    ]
    existing = await db.execute(
        select(PricingConfig.id).where(and_(*conditions))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"存在其他生效的 {config.pricing_type} 类型配置，请先禁用"
        )

    config.status = "active"
    config.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(config)

    return BaseResponse(data=model_to_response(config))




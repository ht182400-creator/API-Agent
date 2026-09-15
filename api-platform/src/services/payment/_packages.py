"""
充值套餐管理：套餐查询/创建、充值金额校验、默认套餐初始化

由 `scripts/dev/split_payment_service.py` 从 `payment_service.py` 精确搬移生成，
方法体与原实现逐字一致（仅移动位置）。

⚠️ 依赖宿主类提供 ``self.db``（由 :class:`PaymentService` 组合）。
"""

from typing import Optional, List, Tuple
from sqlalchemy import select
from src.models.payment import RechargePackage
from src.config.logging_config import get_logger

logger = get_logger("payment")


class PaymentPackagesMixin:
    """充值套餐管理：套餐查询/创建、充值金额校验、默认套餐初始化"""

    
    # ==================== 充值套餐管理 ====================
    
    async def list_packages(self, is_active: bool = True) -> List[RechargePackage]:
        """
        获取可用充值套餐列表
        
        Args:
            is_active: 是否只显示启用状态
            
        Returns:
            套餐列表
        """
        query = select(RechargePackage)
        
        if is_active:
            query = query.where(RechargePackage.is_active == "true")
        
        query = query.order_by(RechargePackage.sort_order.asc())
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_package(self, package_id: str) -> Optional[RechargePackage]:
        """
        获取套餐详情
        
        Args:
            package_id: 套餐ID
            
        Returns:
            套餐信息
        """
        result = await self.db.execute(
            select(RechargePackage).where(RechargePackage.id == package_id)
        )
        return result.scalar_one_or_none()
    
    async def create_package(
        self,
        name: str,
        price: float,
        original_amount: float = None,
        bonus_amount: str = "0",
        bonus_ratio: str = None,
        validity_days: int = None,
        description: str = None,
        is_featured: bool = False,
    ) -> RechargePackage:
        """
        创建充值套餐
        
        Args:
            name: 套餐名称
            price: 售价
            original_amount: 原价
            bonus_amount: 赠送金额
            bonus_ratio: 赠送比例
            validity_days: 有效期天数
            description: 描述
            is_featured: 是否推荐
            
        Returns:
            创建的套餐
        """
        package = RechargePackage(
            name=name,
            original_amount=str(original_amount or price),
            price=str(price),
            bonus_amount=bonus_amount,
            bonus_ratio=bonus_ratio,
            validity_days=validity_days,
            description=description,
            is_featured="true" if is_featured else "false",
        )
        
        self.db.add(package)
        await self.db.commit()
        await self.db.refresh(package)
        
        return package
    
    # ==================== 充值配置验证 ====================
    
    async def validate_recharge_amount(self, amount: float, package_id: str = None) -> Tuple[bool, str]:
        """
        验证充值金额是否合法
        
        Args:
            amount: 充值金额
            package_id: 套餐ID（可选）
            
        Returns:
            (是否合法, 错误消息)
        """
        from src.config.settings import settings
        
        # 全局最小/最大金额限制
        if amount < settings.recharge_min_amount:
            return False, f"充值金额不能低于 {settings.recharge_min_amount} 元"
        
        if amount > settings.recharge_max_amount:
            return False, f"充值金额不能超过 {settings.recharge_max_amount} 元"
        
        # 如果指定了套餐，检查套餐的金额限制
        if package_id:
            package = await self.get_package(package_id)
            if package:
                if package.min_amount and amount < float(package.min_amount):
                    return False, f"该套餐最低充值 {package.min_amount} 元"
                if package.max_amount and amount > float(package.max_amount):
                    return False, f"该套餐最高充值 {package.max_amount} 元"
        
        return True, ""
    
    # ==================== 初始化默认套餐 ====================
    
    async def init_default_packages(self) -> List[RechargePackage]:
        """
        初始化默认充值套餐
        
        Returns:
            创建的套餐列表
        """
        packages = [
            {
                "name": "基础套餐",
                "price": 10.0,
                "bonus_amount": "0",
                "description": "10元 = 100次调用额度",
                "included_calls": 100,
                "is_featured": False,
            },
            {
                "name": "标准套餐",
                "price": 50.0,
                "bonus_amount": "5",
                "description": "50元 = 550次调用额度（送10%）",
                "included_calls": 500,
                "bonus_ratio": "0.1",
                "is_featured": True,
            },
            {
                "name": "高级套餐",
                "price": 100.0,
                "bonus_amount": "15",
                "description": "100元 = 1200次调用额度（送15%）",
                "included_calls": 1000,
                "bonus_ratio": "0.15",
                "is_featured": False,
            },
            {
                "name": "企业套餐",
                "price": 500.0,
                "bonus_amount": "100",
                "description": "500元 = 7000次调用额度（送20%）",
                "included_calls": 5000,
                "bonus_ratio": "0.2",
                "validity_days": 365,
                "is_featured": False,
            },
        ]
        
        created_packages = []
        for i, pkg_data in enumerate(packages):
            pkg = await self.create_package(
                **pkg_data,
                sort_order=i,
            )
            created_packages.append(pkg)
        
        return created_packages

"""
测试计费配置API

使用方法:
    python scripts/test_pricing_config_api.py
"""

import asyncio
import sys
sys.path.insert(0, ".")

from src.config.database import async_engine, AsyncSessionLocal
from src.models.pricing_config import PricingConfig
from sqlalchemy import select, func, text


async def test_pricing_config_api():
    """测试计费配置表操作"""
    print("=" * 60)
    print("测试计费配置 API 功能")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # 1. 测试查询所有配置
        print("\n1. 查询所有计费配置:")
        result = await db.execute(select(PricingConfig))
        configs = result.scalars().all()
        print(f"   找到 {len(configs)} 条配置")

        for config in configs:
            print(f"   - {config.id}: {config.pricing_type} (status={config.status})")

        # 2. 测试按类型查询
        print("\n2. 查询按调用计费配置:")
        result = await db.execute(
            select(PricingConfig).where(PricingConfig.pricing_type == "call")
        )
        configs = result.scalars().all()
        for config in configs:
            print(f"   - {config.pricing_type}: 价格={config.price_per_call}/次, 免费={config.free_calls}次")

        # 3. 测试按Token计费配置
        print("\n3. 查询按Token计费配置:")
        result = await db.execute(
            select(PricingConfig).where(PricingConfig.pricing_type == "token")
        )
        configs = result.scalars().all()
        for config in configs:
            print(f"   - {config.pricing_type}: 输入={config.price_per_1k_input_tokens}/1K, 输出={config.price_per_1k_output_tokens}/1K")

        # 4. 测试套餐包配置
        print("\n4. 查询套餐包计费配置:")
        result = await db.execute(
            select(PricingConfig).where(PricingConfig.pricing_type == "package")
        )
        configs = result.scalars().all()
        for config in configs:
            print(f"   - {config.pricing_type}: {len(config.packages)} packages")
            for pkg in config.packages:
                print(f"     - {pkg.get('name')}: {pkg.get('calls')} calls, ${pkg.get('price')}")

        # 5. 测试费用计算
        print("\n5. 测试费用计算:")
        result = await db.execute(
            select(PricingConfig).where(
                PricingConfig.pricing_type == "call",
                PricingConfig.repo_id.is_(None)
            )
        )
        config = result.scalar_one_or_none()
        if config:
            cost = config.calculate_cost(call_count=100)
            print(f"   - Per-call pricing: 100 calls = ${cost}")

        result = await db.execute(
            select(PricingConfig).where(
                PricingConfig.pricing_type == "token",
                PricingConfig.repo_id.is_(None)
            )
        )
        config = result.scalar_one_or_none()
        if config:
            cost = config.calculate_cost(input_tokens=10000, output_tokens=5000)
            print(f"   - Per-token pricing: 10K input + 5K output = ${cost}")

        # 6. 测试VIP折扣
        print("\n6. Test VIP discounts:")
        result = await db.execute(
            select(PricingConfig).where(PricingConfig.pricing_type == "call")
        )
        config = result.scalar_one_or_none()
        if config:
            for vip_level in [0, 1, 2, 3]:
                cost = config.calculate_cost(call_count=100, vip_level=vip_level)
                discount = config.get_vip_discount(vip_level)
                print(f"   - VIP{vip_level}: discount={discount}, 100 calls=${cost}")

        # 7. 统计
        print("\n7. 统计信息:")
        result = await db.execute(
            select(
                PricingConfig.pricing_type,
                func.count(PricingConfig.id).label("count")
            ).group_by(PricingConfig.pricing_type)
        )
        for row in result.all():
            print(f"   - {row[0]}: {row[1]} 条")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_pricing_config_api())

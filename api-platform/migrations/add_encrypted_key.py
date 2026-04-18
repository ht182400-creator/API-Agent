"""
迁移脚本：为 api_keys 表添加 encrypted_key 列并填充数据

功能：
1. 添加 encrypted_key 列
2. 为现有数据生成加密的 key（如果已知原始 key）
3. 标记不支持查看的 key

使用方法：
    python migrations/add_encrypted_key.py              # 添加列并迁移数据
    python migrations/add_encrypted_key.py --dry-run   # 仅显示将要执行的操作
    python migrations/add_encrypted_key.py --fill=FULL_KEY  # 为指定 key 填充数据
"""

import asyncio
import sys
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import async_engine, AsyncSessionLocal
from src.utils.crypto import encrypt_api_key


# 已知的前端创建生成的 key 模式（用于识别）
# 注意：这些是示例，实际需要根据用户需求填充
KNOWN_KEY_PATTERNS = {
    # key_prefix: original_key
    # 如果用户在界面创建了 key，可以在这里添加映射
}

# 测试数据中的 key（用于演示）
TEST_KEYS = {
    "sk_test_a": "sk_test_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "sk_live_A": "sk_live_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "sk_test_b": "sk_test_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
}


async def check_column_exists(conn) -> bool:
    """检查列是否存在"""
    result = await conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'api_keys' AND column_name = 'encrypted_key'
    """))
    return result.fetchone() is not None


async def get_keys_without_encrypted(conn) -> list:
    """获取没有 encrypted_key 的记录"""
    result = await conn.execute(text("""
        SELECT id, key_prefix, key_name 
        FROM api_keys 
        WHERE encrypted_key IS NULL
    """))
    return result.fetchall()


async def migrate(dry_run: bool = False, fill_keys: dict = None):
    """执行迁移"""
    fill_keys = fill_keys or {}
    
    async with async_engine.begin() as conn:
        # 1. 检查列是否存在
        column_exists = await check_column_exists(conn)
        
        if not column_exists:
            print("📝 添加列 encrypted_key...")
            if not dry_run:
                await conn.execute(text("""
                    ALTER TABLE api_keys 
                    ADD COLUMN encrypted_key TEXT
                """))
            print("✅ 列 encrypted_key 已添加")
        else:
            print("✅ 列 encrypted_key 已存在")
        
        # 2. 获取需要填充的数据
        keys_to_fill = await get_keys_without_encrypted(conn)
        
        if not keys_to_fill:
            print("✅ 所有 API Keys 都已填充 encrypted_key")
            return
        
        print(f"\n📊 发现 {len(keys_to_fill)} 条记录需要填充 encrypted_key:")
        for row in keys_to_fill:
            print(f"   - ID: {row.id}, Prefix: {row.key_prefix}, Name: {row.key_name}")
        
        # 3. 尝试填充已知的数据
        filled_count = 0
        unknown_count = 0
        
        for row in keys_to_fill:
            key_prefix = row.key_prefix
            
            # 尝试从测试数据填充
            if key_prefix in TEST_KEYS:
                original_key = TEST_KEYS[key_prefix]
                encrypted = encrypt_api_key(original_key)
                print(f"\n🔐 填充 Key: {key_prefix} -> {original_key[:20]}...")
                if not dry_run:
                    await conn.execute(
                        text("UPDATE api_keys SET encrypted_key = :encrypted WHERE id = :id"),
                        {"encrypted": encrypted, "id": str(row.id)}
                    )
                filled_count += 1
            elif key_prefix in fill_keys:
                # 从命令行参数填充
                original_key = fill_keys[key_prefix]
                encrypted = encrypt_api_key(original_key)
                print(f"\n🔐 填充 Key: {key_prefix} (命令行指定)")
                if not dry_run:
                    await conn.execute(
                        text("UPDATE api_keys SET encrypted_key = :encrypted WHERE id = :id"),
                        {"encrypted": encrypted, "id": str(row.id)}
                    )
                filled_count += 1
            else:
                print(f"\n⚠️  未知 Key: {key_prefix}，无法填充（需要删除后重新创建）")
                unknown_count += 1
        
        print(f"\n📈 迁移完成:")
        print(f"   - 成功填充: {filled_count} 条")
        print(f"   - 无法填充: {unknown_count} 条（建议删除重新创建）")
        
        if unknown_count > 0:
            print("\n💡 提示: 如果知道这些 Key 的原始值，可以使用以下命令填充:")
            print("   python migrations/add_encrypted_key.py --fill-prefix=sk_xxx:sk_full_key_here")


async def main():
    parser = argparse.ArgumentParser(description="迁移 api_keys 表，添加 encrypted_key 列")
    parser.add_argument("--dry-run", action="store_true", help="仅显示将要执行的操作")
    parser.add_argument("--fill", type=str, help="填充指定的 key，格式: prefix:full_key")
    parser.add_argument("--test-data", action="store_true", help="填充测试数据中的 key")
    args = parser.parse_args()
    
    fill_keys = {}
    if args.fill:
        parts = args.fill.split(":", 1)
        if len(parts) == 2:
            fill_keys[parts[0]] = parts[1]
    
    print("=" * 60)
    print("API Keys encrypted_key 字段迁移脚本")
    print("=" * 60)
    
    await migrate(dry_run=args.dry_run, fill_keys=fill_keys)


if __name__ == "__main__":
    asyncio.run(main())

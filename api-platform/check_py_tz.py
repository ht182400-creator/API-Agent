import asyncio
from datetime import datetime, timezone, timedelta

# 检查 Python 环境时区
print(f"Python 时区: {datetime.now().astimezone().tzinfo}")
print(f"当前时间: {datetime.now()}")
print(f"UTC 时间: {datetime.utcnow()}")

# 模拟 datetime.now() 生成的时间
now_china = datetime.now()  # 假设这是北京时间
print(f"\ndatetime.now() = {now_china}")

# 如果直接存入 PostgreSQL，PostgreSQL 会怎么处理？
# PostgreSQL 的 TIMESTAMP WITH TIME ZONE 会将输入的时间转换为 UTC 存储
# 所以 16:46 (北京时间) 会被存储为 08:46 (UTC)
print(f"\n如果 datetime.now() 直接存入数据库:")
print(f"  存入的值: {now_china}")
print(f"  数据库会存为 UTC: {now_china - timedelta(hours=8)}")
print(f"  取出时显示为 Asia/Shanghai: {now_china}")

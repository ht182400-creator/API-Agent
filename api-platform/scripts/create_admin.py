#!/usr/bin/env python
"""
创建管理员 / 超级管理员账号（生产安全版）

为什么要有它：
    `init_db_with_data.py` 把 super123456 / admin123 等**明文默认口令**写进脚本并入库，
    生产环境不可用（该脚本已加生产守卫）。本脚本提供正规的管理员创建途径：

    - 口令**不回显**输入（getpass）并做强度校验；
    - 支持 `--random-password` 生成强随机口令（仅打印一次）；
    - 生产环境**禁止弱口令 / 已知默认口令**；
    - 幂等：账号已存在时默认报错，`--reset-password` 可重置口令；
    - 高权限角色（admin / super_admin）**只能由本脚本或现有超管授予**，注册接口不可申请
      （见 UserCreate.SELF_REGISTER_ROLES 白名单）。

用法：
    python scripts/create_admin.py                       # 交互式创建 super_admin
    python scripts/create_admin.py --user-type admin      # 创建普通管理员
    python scripts/create_admin.py --email a@b.com --random-password
    python scripts/create_admin.py --email a@b.com --reset-password

注意：
    会先确保表结构存在（调用 init_db_with_data.init_db）。
"""
import argparse
import asyncio
import getpass
import os
import re
import secrets
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select  # noqa: E402

from src.config.database import AsyncSessionLocal  # noqa: E402
from src.config.settings import settings  # noqa: E402
from src.core.security import hash_password  # noqa: E402
from src.models.user import User  # noqa: E402

# ⚠️ 已知默认口令 / 弱口令黑名单：生产环境一律拒绝
BANNED_PASSWORDS = {
    "admin123", "super123456", "owner123", "dev123456", "test123",
    "password", "password123", "12345678", "admin123456", "root", "changeme",
}

ALLOWED_TYPES = ("super_admin", "admin")


def generate_password(length: int = 20) -> str:
    """生成强随机口令（含大小写字母、数字、符号）"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(not c.isalnum() for c in pwd)
        ):
            return pwd


def validate_password(pwd: str) -> None:
    """口令强度校验（生产环境更严格）"""
    problems = []
    if len(pwd) < (12 if settings.is_production() else 8):
        problems.append(f"长度至少 {12 if settings.is_production() else 8} 位")
    if not any(c.islower() for c in pwd) or not any(c.isupper() for c in pwd):
        problems.append("需同时包含大小写字母")
    if not any(c.isdigit() for c in pwd):
        problems.append("需包含数字")

    if pwd.lower() in BANNED_PASSWORDS:
        problems.append("禁止使用已知默认口令/弱口令")

    if problems:
        raise ValueError("；".join(problems))


def prompt_password() -> str:
    """交互式输入口令（不回显 + 二次确认）"""
    while True:
        pwd = getpass.getpass("请输入口令（不回显）: ")
        try:
            validate_password(pwd)
        except ValueError as e:
            print(f"[X] 口令不满足要求：{e}")
            continue
        if pwd != getpass.getpass("请再次输入以确认: "):
            print("[X] 两次输入不一致，请重新输入。")
            continue
        return pwd


async def ensure_schema() -> None:
    """确保表结构存在（复用初始化脚本的建表逻辑）"""
    from scripts.init_db_with_data import init_db

    await init_db()


async def main() -> None:
    parser = argparse.ArgumentParser(description="创建管理员/超级管理员账号")
    parser.add_argument("--email", help="登录邮箱（必填，或交互式输入）")
    parser.add_argument("--username", help="用户名（可选，默认取邮箱前缀）")
    parser.add_argument("--user-type", choices=ALLOWED_TYPES, default="super_admin",
                        help="创建的管理员类型（默认 super_admin）")
    parser.add_argument("--password", help="口令（不建议在命令行传入，会留在 shell 历史）")
    parser.add_argument("--random-password", action="store_true", help="生成强随机口令并打印一次")
    parser.add_argument("--reset-password", action="store_true",
                        help="账号已存在时重置其口令（默认报错退出）")
    args = parser.parse_args()

    print("\n[Create Admin]")
    print("=" * 50)
    print(f"环境: {settings.environment}"
          + ("（生产环境：启用严格口令策略）" if settings.is_production() else ""))

    email = args.email or input("邮箱: ").strip()
    if not email or "@" not in email:
        print("[X] 邮箱格式不正确。")
        raise SystemExit(1)

    username = args.username or email.split("@")[0]

    if args.random_password:
        password = generate_password()
    elif args.password:
        password = args.password
        try:
            validate_password(password)
        except ValueError as e:
            print(f"[X] 口令不满足要求：{e}")
            raise SystemExit(1)
    elif os.getenv("ADMIN_PASSWORD"):
        # 便于自动化（CI/容器首次初始化）：从环境变量读取
        password = os.environ["ADMIN_PASSWORD"]
        try:
            validate_password(password)
        except ValueError as e:
            print(f"[X] 口令不满足要求：{e}")
            raise SystemExit(1)
    else:
        password = prompt_password()

    await ensure_schema()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            if not args.reset_password:
                print(f"[X] 账号已存在（id={user.id}, user_type={user.user_type}）。"
                      f"如需重置口令请加 --reset-password。")
                raise SystemExit(2)
            user.password_hash = hash_password(password)
            user.user_type = args.user_type
            user.role = args.user_type
            user.email_verified = True
            action = "重置口令并更新角色"
        else:
            user = User(
                username=username,
                email=email,
                password_hash=hash_password(password),
                user_type=args.user_type,
                role=args.user_type,
                email_verified=True,
            )
            session.add(user)
            action = "创建"

        await session.commit()
        await session.refresh(user)

    print(f"[OK] {action}成功：")
    print(f"     id        : {user.id}")
    print(f"     email     : {user.email}")
    print(f"     username  : {user.username}")
    print(f"     user_type : {user.user_type}")
    if args.random_password:
        print(f"     password  : {password}   ← 仅显示一次，请妥善保存")
    print("\n[SEC] 高权限账号创建后请确认：口令已存入密码管理器，且不要提交进代码库。")


if __name__ == "__main__":
    asyncio.run(main())

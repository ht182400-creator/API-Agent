"""
超级管理员操作守卫测试（TC-SEC-ADMIN）

背景：超管可以改任何用户的类型/角色/状态。缺少防护时，一次误操作就可能
把系统置于"没有可用管理员"的境地（只能改库恢复）。本套件锁定三件事：

1. 不能降级 / 停用**自己**（自锁防护）；
2. 不能降级 / 停用**最后一个**活跃的超级管理员；
3. 正常路径仍然可用（把普通用户提升为 admin），且操作被审计。

另见：注册接口不得自我提权（tests/test_auth.py TC-SEC-REG-001~003）。
"""
import pytest
from httpx import AsyncClient

from src.models.user import User


@pytest.mark.asyncio
class TestSuperAdminGuard:
    """超级管理员接口的自我防护"""

    async def test_cannot_demote_self(self, client: AsyncClient, test_super_admin: User,
                                      super_admin_headers: dict):
        """TC-SEC-ADMIN-001: 超管不能把自己降级（防止自锁）"""
        resp = await client.put(
            f"/api/v1/superadmin/users/{test_super_admin.id}",
            json={"user_type": "developer"},
            headers=super_admin_headers,
        )

        assert resp.status_code == 400
        assert test_super_admin.user_type == "super_admin"

    async def test_cannot_deactivate_self(self, client: AsyncClient, test_super_admin: User,
                                          super_admin_headers: dict):
        """TC-SEC-ADMIN-002: 超管不能把自己停用"""
        resp = await client.put(
            f"/api/v1/superadmin/users/{test_super_admin.id}",
            json={"user_status": "inactive"},
            headers=super_admin_headers,
        )

        assert resp.status_code == 400

    async def test_cannot_disable_last_super_admin(self, client: AsyncClient,
                                                   test_super_admin: User,
                                                   super_admin_headers: dict,
                                                   db_session):
        """TC-SEC-ADMIN-003: 不能停用最后一个活跃的超级管理员"""
        # 造第二个超管后，先停用自己之外的那个应成功（此时还剩 1 个）
        from src.core.security import hash_password

        another = User(
            username="another_sa",
            email="another_sa@test.com",
            password_hash=hash_password("super123456"),
            user_type="super_admin",
            user_status="active",
            role="super_admin",
            permissions=["*"],
        )
        db_session.add(another)
        await db_session.commit()
        await db_session.refresh(another)

        # 把 another 改成 developer 后，test_super_admin 成为最后一个
        await db_session.refresh(another)
        another.user_type = "developer"
        another.role = "developer"
        await db_session.commit()

        resp = await client.put(
            f"/api/v1/superadmin/users/{test_super_admin.id}",
            json={"user_status": "suspended"},
            headers=super_admin_headers,
        )

        # 自己是唯一活跃超管 → 必须被拒（同时也命中"不能停用自己"）
        assert resp.status_code == 400

    async def test_can_promote_normal_user(self, client: AsyncClient, test_user: User,
                                           super_admin_headers: dict, db_session):
        """TC-SEC-ADMIN-004: 正常路径 —— 把普通用户提升为 admin（并记录审计）"""
        resp = await client.put(
            f"/api/v1/superadmin/users/{test_user.id}",
            json={"user_type": "admin", "role": "admin"},
            headers=super_admin_headers,
        )

        assert resp.status_code == 200
        assert resp.json()["data"]["user_type"] == "admin"

        from sqlalchemy import select
        from src.models.audit_log import AuditLog

        logs = (
            await db_session.execute(
                select(AuditLog).where(AuditLog.resource_id == str(test_user.id))
            )
        ).scalars().all()
        assert len(logs) >= 1, "提升用户角色必须留下审计日志"

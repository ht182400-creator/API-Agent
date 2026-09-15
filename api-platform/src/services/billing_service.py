"""
Billing Service - 账单号生成（轻模块）

⚠️ 历史说明（2026-09-15 清理）：
    本模块原含 ``BillingService`` 类（约 600 行完整计费逻辑）。
    经排查，该类**在生产代码中 0 处实例化**（实际计费统一由
    ``AccountService`` 负责），属于早期实现被取代后残留的死代码，
    且其内部 6 处 ``Bill(...)`` 构造与现行模型字段不匹配（缺
    ``balance_before`` / ``balance_after`` 等 NOT NULL 字段），
    一旦误用必然抛错。

    已删除该类及其专属测试（tests/test_billing.py）。
    仅保留仍被活代码引用的 :func:`generate_bill_no`：

        - ``api/v1/user.py``（用户升级扣费 ×2）

    计费/扣费/充值请使用 ``src/services/account_service.AccountService``。
"""

from datetime import datetime, timezone


def generate_bill_no() -> str:
    """生成账单号：BILL + UTC 时间戳（14 位）+ 6 位随机数字"""
    import random
    import string

    prefix = "BILL"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.digits, k=6))
    return f"{prefix}{timestamp}{random_str}"

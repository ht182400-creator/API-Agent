#!/usr/bin/env python
"""
向「API 仓库市场」批量写入大模型仓库（国外 + 国内）

用途：让仓库市场页（/developer/repos）直接展示这些可调用的模型仓库。

包含：
    国外：GPT-6 / Fable 5.0 / Gemini
    国内：Hy4 preview / Hy3 / DeepSeek-V4.1-Flash / DeepSeek-V4-Pro /
          GLM-5.3 / GLM-5.3-Flash / GLM-5.2 / GLM-5.1 / GLM-5v-Turbo /
          Kimi-K3 / Kimi-K2.7-Code

⚠️ 说明：
    - `price_per_token` 按用户提供的**倍率表近似换算**（基准 0.01 元/千 token × 倍率），
      仅用于演示与排序，**上线前请在管理端按真实商务价调整**；
    - `endpoint_url` 为占位网关地址（与其它种子仓库一致的风格），
      真正接入时替换为你的模型网关；
    - 脚本**幂等**：同 slug 已存在则更新展示字段（不重复插入）。

用法：
    python scripts/seed_ai_models.py            # 写入/更新
    python scripts/seed_ai_models.py --dry-run  # 只打印将要写入的内容
"""
import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select  # noqa: E402

from src.config.database import AsyncSessionLocal  # noqa: E402
from src.models.repository import Repository, RepoEndpoint, RepoLimits, RepoPricing  # noqa: E402
from src.models.user import User  # noqa: E402

GATEWAY = "http://model-gateway:8000"

# 通用端点（每个模型仓库都有：对话 / 向量 / 模型列表）
def default_endpoints() -> list:
    return [
        {"path": "/v1/chat/completions", "method": "POST", "description": "对话补全（Chat Completions）",
         "category": "chat", "display_order": 1},
        {"path": "/v1/embeddings", "method": "POST", "description": "文本向量化",
         "category": "embedding", "display_order": 2},
        {"path": "/v1/models", "method": "GET", "description": "列出可用模型",
         "category": "meta", "display_order": 3},
    ]


def default_limits(timeout: int = 60) -> dict:
    return {
        "rpm": 1000, "rph": 10000, "rpd": 100000,
        "burst_limit": 50, "concurrent_limit": 10,
        "daily_quota": 50000, "monthly_quota": 1000000,
        "request_timeout": timeout, "connect_timeout": 15,
    }


# ⚠️ price_per_token = 0.01 × 倍率（倍率取自用户提供的价目表；上线前按真实商务价调整）
MODELS = [
    # ---------------- 国外 ----------------
    {
        "slug": "gpt-6", "name": "GPT-6", "display_name": "GPT-6 API",
        "description": "OpenAI 最新一代旗舰模型：超长上下文、强推理与原生多模态，适合复杂 agent 与代码任务。",
        "multiple": 1.0, "type": "ai",
    },
    {
        "slug": "fable-5", "name": "Fable 5.0", "display_name": "Fable 5.0 API",
        "description": "Fable 5.0：面向长篇创作与角色扮演的创意大模型，风格一致性与叙事连贯性突出。",
        "multiple": 0.8, "type": "ai",
    },
    {
        "slug": "gemini", "name": "Gemini", "display_name": "Gemini API",
        "description": "Google Gemini 系列最新多模态模型：图文音视频统一理解，长文档与视频检索场景表现优异。",
        "multiple": 0.6, "type": "ai",
    },
    # ---------------- 国内 ----------------
    {
        "slug": "hy4-preview", "name": "Hy4 preview", "display_name": "Hy4 preview",
        "description": "混元 Hy4 preview（限时免费）：新一代稀疏 MoE 架构，通用对话与工具调用能力大幅提升。",
        "multiple": 0.0, "type": "ai",
    },
    {
        "slug": "hy3", "name": "Hy3", "display_name": "Hy3",
        "description": "混元 Hy3：稳定版通用大模型，中文理解与代码生成均衡，适合生产环境长期使用。",
        "multiple": 0.05, "type": "ai",
    },
    {
        "slug": "deepseek-v4-1-flash", "name": "DeepSeek-V4.1-Flash", "display_name": "DeepSeek-V4.1-Flash",
        "description": "DeepSeek-V4.1-Flash（独家优惠）：高吞吐低延迟，适合大规模批处理与实时对话。",
        "multiple": 0.03, "type": "ai",
    },
    {
        "slug": "deepseek-v4-pro", "name": "DeepSeek-V4-Pro", "display_name": "DeepSeek-V4-Pro",
        "description": "DeepSeek-V4-Pro（建议错峰使用）：深度推理与数学编程能力突出，适合复杂分析任务。",
        "multiple": 0.51, "type": "ai",
    },
    {
        "slug": "glm-5-3", "name": "GLM-5.3", "display_name": "GLM-5.3",
        "description": "智谱 GLM-5.3：通用能力全面升级，中文写作、代码与工具调用表现稳定。",
        "multiple": 0.79, "type": "ai",
    },
    {
        "slug": "glm-5-3-flash", "name": "GLM-5.3-Flash", "display_name": "GLM-5.3-Flash",
        "description": "GLM-5.3-Flash（订阅用户优先）：轻量高速版本，适合高并发在线服务。",
        "multiple": 0.06, "type": "ai",
    },
    {
        "slug": "glm-5-2", "name": "GLM-5.2", "display_name": "GLM-5.2",
        "description": "GLM-5.2（夜间折扣）：成熟稳定版本，夜间时段享有额外折扣。",
        "multiple": 0.5, "type": "ai",
    },
    {
        "slug": "glm-5-1", "name": "GLM-5.1", "display_name": "GLM-5.1",
        "description": "GLM-5.1：上一代主力版本，兼容性好，适合存量业务平滑迁移。",
        "multiple": 0.79, "type": "ai",
    },
    {
        "slug": "glm-5v-turbo", "name": "GLM-5v-Turbo", "display_name": "GLM-5v-Turbo",
        "description": "GLM-5v-Turbo：视觉理解加速版，图像问答与文档解析延迟更低。",
        "multiple": 0.71, "type": "vision",
    },
    {
        "slug": "kimi-k3", "name": "Kimi-K3", "display_name": "Kimi-K3",
        "description": "月之暗面 Kimi-K3：超长上下文（百万级 token）与强检索能力，适合长文档与研报分析。",
        "multiple": 1.62, "type": "ai",
    },
    {
        "slug": "kimi-k2-7-code", "name": "Kimi-K2.7-Code", "display_name": "Kimi-K2.7-Code",
        "description": "Kimi-K2.7-Code：代码专精模型，仓库级理解与多文件重构场景优化。",
        "multiple": 0.57, "type": "ai",
    },
]


async def find_owner(db):
    """优先用 owner 用户作为仓库所有者，退化为 superadmin/admin"""
    for username in ("owner", "superadmin", "admin"):
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user:
            return user
    return None


async def main(dry_run: bool = False) -> None:
    print("\n[Seed AI Model Repos]")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        owner = await find_owner(db)
        if not owner:
            print("[X] 未找到可用的所有者账号（owner/superadmin/admin），请先初始化数据库。")
            raise SystemExit(1)
        print(f"所有者: {owner.username} ({owner.id})")

        created, updated = 0, 0
        for m in MODELS:
            price_per_token = f"{0.01 * m['multiple']:.4f}"
            result = await db.execute(select(Repository).where(Repository.slug == m["slug"]))
            repo = result.scalar_one_or_none()

            if dry_run:
                action = "更新" if repo else "新建"
                print(f"  [{action}] {m['display_name']:<24} 倍率 {m['multiple']:<5} "
                      f"价 {price_per_token}/token")
                continue

            if repo:
                repo.display_name = m["display_name"]
                repo.description = m["description"]
                repo.repo_type = m["type"]
                repo.endpoint_url = GATEWAY
                # ⚠️ api_docs_url 也必须一起更新：否则改了 GATEWAY 后重跑，
                #    endpoint_url 变成新网关，而文档链接仍指向旧地址（曾遗漏，实测确认）
                repo.api_docs_url = f"{GATEWAY}/docs"
                repo.status = "online"
                updated += 1
            else:
                repo = Repository(
                    owner_id=owner.id,
                    owner_type="internal",
                    name=m["name"],
                    slug=m["slug"],
                    display_name=m["display_name"],
                    description=m["description"],
                    repo_type=m["type"],
                    protocol="http",
                    endpoint_url=GATEWAY,
                    api_docs_url=f"{GATEWAY}/docs",
                    status="online",
                    online_at=datetime.now(timezone.utc),
                    sla_uptime="99.9",
                    sla_latency_p99=800,
                )
                db.add(repo)
                await db.flush()

                db.add(RepoPricing(
                    repo_id=repo.id,
                    pricing_type="token",
                    price_per_call="0.01",
                    price_per_token=price_per_token,
                    free_calls=100,
                    free_tokens=10000,
                    free_quota_days=7,
                ))
                for ep in default_endpoints():
                    db.add(RepoEndpoint(
                        repo_id=repo.id,
                        path=ep["path"], method=ep["method"],
                        description=ep["description"], category=ep["category"],
                        display_order=ep["display_order"],
                        enabled=True, is_deprecated=False,
                    ))
                lim = default_limits()
                db.add(RepoLimits(
                    repo_id=repo.id,
                    rpm=lim["rpm"], rph=lim["rph"], rpd=lim["rpd"],
                    burst_limit=lim["burst_limit"], concurrent_limit=lim["concurrent_limit"],
                    daily_quota=lim["daily_quota"], monthly_quota=lim["monthly_quota"],
                    request_timeout=lim["request_timeout"], connect_timeout=lim["connect_timeout"],
                    enabled=True,
                ))
                created += 1

        if not dry_run:
            await db.commit()

        print("-" * 60)
        if dry_run:
            print(f"[DRY-RUN] 共 {len(MODELS)} 个模型仓库（未写入）。")
        else:
            print(f"[OK] 新建 {created} 个，更新 {updated} 个，共 {len(MODELS)} 个模型仓库。")
            print("     打开 /developer/repos 查看（需刷新浏览器）。")
            print("[NOTE] 价格为演示占位（按倍率近似），请在管理端按真实商务价调整。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="写入大模型仓库到仓库市场")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不写库")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))

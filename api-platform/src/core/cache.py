"""
缓存工具（Redis，评审项 P1-5）

背景：
    平台存在大量"读多写少"的热点数据（仓库详情、系统配置、套餐列表等），
    每次请求都查库会放大数据库压力。本模块提供统一的缓存读写能力。

设计要点：
    1. 优雅降级：Redis 不可用或缓存未启用时，读返回 None、写静默跳过，
       业务逻辑自动回落数据库，不会因为缓存故障导致接口报错；
    2. 命名空间：key 统一加前缀，便于按业务批量失效（cache_delete_prefix）；
    3. 序列化：统一 JSON，兼容 dict / list / 基本类型；
    4. 明确 TTL：所有写入必须显式或隐式带过期时间，避免脏数据长期驻留。

使用方式：
    from src.core.cache import cache_get_json, cache_set_json, make_key, invalidate_prefix

    key = make_key("system_configs", category or "all")
    cached = await cache_get_json(key)
    if cached is not None:
        return cached
    data = await load_from_db()
    await cache_set_json(key, data, ttl=300)
    return data
"""

import json
from typing import Any, List, Optional

from src.config.logging_config import get_logger

logger = get_logger("cache")

# 缓存 key 扫描批量大小（SCAN 游标）
_SCAN_COUNT = 500


def make_key(*parts: Any) -> str:
    """构造带全局前缀的缓存 key"""
    from src.config.settings import settings

    segments = [settings.cache_key_prefix.strip(":")]
    segments.extend(str(p) for p in parts if p is not None)
    return ":".join(segments)


def _is_enabled() -> bool:
    from src.config.settings import settings

    return bool(settings.cache_enabled)


async def cache_get(key: str) -> Optional[str]:
    """
    读取字符串缓存。

    Returns:
        缓存值；未命中 / Redis 不可用 / 未启用缓存时返回 None
    """
    if not _is_enabled():
        return None

    from src.core.redis_manager import RedisManager

    client = await RedisManager.get_client()
    if client is None:
        return None
    try:
        return await client.get(key)
    except Exception as exc:
        RedisManager.mark_unavailable(exc)
        return None


async def cache_set(key: str, value: str, ttl: Optional[int] = None) -> bool:
    """写入字符串缓存（带 TTL）"""
    if not _is_enabled():
        return False

    from src.config.settings import settings
    from src.core.redis_manager import RedisManager

    client = await RedisManager.get_client()
    if client is None:
        return False

    ttl = ttl if ttl is not None else settings.cache_default_ttl
    try:
        await client.set(key, value, ex=max(1, int(ttl)))
        return True
    except Exception as exc:
        RedisManager.mark_unavailable(exc)
        return False


async def cache_get_json(key: str) -> Optional[Any]:
    """读取 JSON 缓存，失败时返回 None（视为未命中）"""
    raw = await cache_get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        # 缓存内容损坏：删除并视为未命中
        logger.warning("[Cache] 缓存内容解析失败，已删除: %s", key)
        await cache_delete(key)
        return None


async def cache_set_json(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """写入 JSON 缓存"""
    try:
        payload = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError) as exc:  # pragma: no cover
        logger.warning("[Cache] 序列化失败，跳过缓存: %s (%s)", key, exc)
        return False
    return await cache_set(key, payload, ttl=ttl)


async def cache_delete(*keys: str) -> int:
    """删除指定缓存 key"""
    if not _is_enabled():
        return 0

    from src.core.redis_manager import RedisManager

    client = await RedisManager.get_client()
    if client is None or not keys:
        return 0
    try:
        return int(await client.delete(*keys))
    except Exception as exc:
        RedisManager.mark_unavailable(exc)
        return 0


async def cache_delete_prefix(prefix: str) -> int:
    """
    按前缀批量失效缓存（使用 SCAN，避免 KEYS 阻塞 Redis）。

    Args:
        prefix: key 前缀，建议使用 make_key("system_configs") 生成

    Returns:
        删除数量；Redis 不可用时返回 0
    """
    if not _is_enabled():
        return 0

    from src.core.redis_manager import RedisManager

    client = await RedisManager.get_client()
    if client is None:
        return 0

    deleted = 0
    try:
        cursor = 0
        batch: List[str] = []
        while True:
            cursor, keys = await client.scan(cursor=cursor, match=f"{prefix}*", count=_SCAN_COUNT)
            batch.extend(keys)
            if cursor == 0:
                break
            if len(batch) >= _SCAN_COUNT:
                deleted += int(await client.delete(*batch))
                batch = []
        if batch:
            deleted += int(await client.delete(*batch))
    except Exception as exc:
        RedisManager.mark_unavailable(exc)
        return 0

    if deleted:
        logger.info("[Cache] 前缀失效 %s* 共 %s 个 key", prefix, deleted)
    return deleted

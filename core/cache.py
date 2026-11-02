import json
from typing import Optional, Any
from core.redis_client import redis_client


async def get(key: str) -> Optional[Any]:
    """Cache'dan ma'lumot olish"""
    client = await redis_client.get_client()
    value = await client.get(key)
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


async def set(key: str, value: Any, expire_seconds: int = 3600) -> bool:
    """Cache'ga ma'lumot yozish"""
    client = await redis_client.get_client()
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    return await client.set(key, value, ex=expire_seconds)


async def delete(key: str) -> bool:
    """Cache'dan ma'lumot o'chirish"""
    client = await redis_client.get_client()
    return await client.delete(key) > 0


async def exists(key: str) -> bool:
    """Cache'da ma'lumot mavjudligini tekshirish"""
    client = await redis_client.get_client()
    return await client.exists(key) > 0


async def clear_pattern(pattern: str) -> int:
    """Pattern bo'yicha cache tozalash"""
    client = await redis_client.get_client()
    keys = await client.keys(pattern)
    if keys:
        return await client.delete(*keys)
    return 0

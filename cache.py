import json
import os
from typing import Any

try:
    import redis
except ImportError:
    redis = None


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))


def get_redis_client():
    if redis is None:
        return None

    try:
        client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def cache_available() -> bool:
    return get_redis_client() is not None


def get_json(key: str):
    client = get_redis_client()
    if client is None:
        return None

    value = client.get(key)
    if value is None:
        return None

    return json.loads(value)


def set_json(key: str, value: Any, ttl: int = CACHE_TTL_SECONDS):
    client = get_redis_client()
    if client is None:
        return

    client.setex(key, ttl, json.dumps(value))


def delete_key(key: str):
    client = get_redis_client()
    if client is not None:
        client.delete(key)


def delete_by_prefix(prefix: str):
    client = get_redis_client()
    if client is None:
        return

    for key in client.scan_iter(f"{prefix}*"):
        client.delete(key)


def cache_info():
    client = get_redis_client()
    if client is None:
        return {
            "connected": False,
            "redis_url": REDIS_URL,
            "total_cached_keys": 0,
            "keys": [],
        }

    keys = []
    for key in client.scan_iter("*"):
        keys.append({
            "key": key,
            "ttl_seconds": client.ttl(key),
        })

    return {
        "connected": True,
        "redis_url": REDIS_URL,
        "total_cached_keys": len(keys),
        "keys": keys,
    }

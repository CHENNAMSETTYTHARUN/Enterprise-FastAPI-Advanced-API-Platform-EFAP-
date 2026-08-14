import json
import time
from typing import Optional, Any

_in_memory_cache = {}

class CacheService:
    @staticmethod
    def get(key: str) -> Optional[Any]:
        if key in _in_memory_cache:
            data, expires_at = _in_memory_cache[key]
            if expires_at is None or expires_at > time.time():
                return data
            else:
                del _in_memory_cache[key]
        return None

    @staticmethod
    def set(key: str, value: Any, ttl_seconds: Optional[int] = 300):
        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        _in_memory_cache[key] = (value, expires_at)

    @staticmethod
    def delete(key: str):
        if key in _in_memory_cache:
            del _in_memory_cache[key]

    @staticmethod
    def clear():
        _in_memory_cache.clear()

cache_service = CacheService()

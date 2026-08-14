import json
from typing import Optional, Dict, Any, Tuple
from app.services.cache_service import cache_service

class IdempotencyService:
    @staticmethod
    def get_record(key: str) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        cache_key = f"idempotency:{key}"
        cached = cache_service.get(cache_key)
        if cached:
            data = json.loads(cached)
            if isinstance(data, dict) and "result" in data and "payload" in data:
                return data["payload"], data["result"]
            elif isinstance(data, dict):
                # Fallback for old cache format
                return None, data
        return None

    @staticmethod
    def get_response(key: str) -> Optional[Dict[str, Any]]:
        record = IdempotencyService.get_record(key)
        if record:
            return record[1]
        return None

    @staticmethod
    def save_response(key: str, payload_data: Dict[str, Any], response_data: Dict[str, Any], ttl_seconds: int = 86400):
        cache_key = f"idempotency:{key}"
        wrapper = {
            "payload": payload_data,
            "result": response_data
        }
        cache_service.set(cache_key, json.dumps(wrapper), ttl_seconds=ttl_seconds)

idempotency_service = IdempotencyService()


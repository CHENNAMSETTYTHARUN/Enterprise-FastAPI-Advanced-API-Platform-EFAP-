import httpx
from typing import Dict, Any
from app.core.config import settings

async def fetch_external_data() -> Dict[str, Any]:
    url = settings.EXTERNAL_API_URL
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                raw_data = response.json()
                return {
                    "source": "JSONPlaceholder",
                    "id": raw_data.get("id"),
                    "title": raw_data.get("title"),
                    "content": raw_data.get("body"),
                    "status": "success"
                }
            return {
                "status": "error",
                "message": f"External API returned status code {response.status_code}"
            }
    except Exception as exc:
        return {
            "status": "fallback",
            "message": f"External service unavailable: {str(exc)}",
            "data": {
                "id": 1,
                "title": "Fallback Static Title",
                "content": "Fallback static content provided due to network timeout or offline mode."
            }
        }

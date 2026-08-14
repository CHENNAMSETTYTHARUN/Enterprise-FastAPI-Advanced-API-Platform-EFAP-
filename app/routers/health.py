from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.services.cache_service import cache_service

router = APIRouter(tags=["Health Monitoring"])

@router.get("/health")
def health_check(response: Response, db: Session = Depends(get_db)):
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    cache_status = "healthy"
    try:
        cache_service.set("health_test", "ok", ttl_seconds=5)
        if cache_service.get("health_test") != "ok":
            cache_status = "unhealthy"
    except Exception:
        cache_status = "unhealthy"

    ext_status = "healthy"
    is_healthy = (db_status == "healthy")

    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    overall = "healthy" if (is_healthy and cache_status == "healthy" and ext_status == "healthy") else "unhealthy"

    return {
        "status": overall,
        "database": {"status": db_status},
        "cache": {"status": cache_status},
        "external_service": {"status": ext_status},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }



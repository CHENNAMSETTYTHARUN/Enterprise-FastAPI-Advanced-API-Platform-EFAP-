import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.audit import AuditLog

SECRET_KEYS = {"password", "hashed_password", "otp", "otp_code", "token", "access_token", "secret", "api_key"}

def mask_secrets(data: Any) -> Any:
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            if k.lower() in SECRET_KEYS:
                masked[k] = "***MASKED***"
            else:
                masked[k] = mask_secrets(v)
        return masked
    elif isinstance(data, list):
        return [mask_secrets(item) for item in data]
    return data

def log_audit(
    db: Session,
    action: str,
    entity: str,
    entity_id: Optional[Any] = None,
    user_id: Optional[Any] = None,
    tenant_id: Optional[Any] = None,
    request_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    status: str = "SUCCESS",
    details: Optional[str] = None
):
    try:
        masked_old = json.dumps(mask_secrets(old_values)) if old_values else None
        masked_new = json.dumps(mask_secrets(new_values)) if new_values else None

        log_entry = AuditLog(
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            user_id=int(user_id) if isinstance(user_id, int) or (isinstance(user_id, str) and user_id.isdigit()) else None,
            tenant_id=int(tenant_id) if isinstance(tenant_id, int) or (isinstance(tenant_id, str) and tenant_id.isdigit()) else None,
            request_id=request_id,
            ip_address=ip_address,
            old_values=masked_old,
            new_values=masked_new,
            status=status,
            details=details
        )
        db.add(log_entry)
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.dependencies import get_current_user, require_permission

router = APIRouter(prefix="/api/audit-logs", tags=["Audit Logging"])

@router.get("")
def get_audit_logs(
    action: Optional[str] = Query(None),
    entity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit:read"))
):
    query = db.query(AuditLog)
    if current_user.tenant_id:
        query = query.filter((AuditLog.tenant_id == current_user.tenant_id) | (AuditLog.tenant_id == None))
    if action:
        query = query.filter(AuditLog.action == action)
    if entity:
        query = query.filter(AuditLog.entity == entity)
        
    logs = query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return [
        {
            "id": l.id,
            "action": l.action,
            "entity": l.entity,
            "resource_type": l.entity,
            "entity_id": l.entity_id,
            "resource_id": l.entity_id,
            "user_id": l.user_id,
            "tenant_id": l.tenant_id,
            "request_id": l.request_id,
            "ip_address": l.ip_address,
            "old_values": l.old_values,
            "new_values": l.new_values,
            "status": l.status or "SUCCESS",
            "details": l.details,
            "created_at": l.created_at,
            "timestamp": l.created_at
        } for l in logs
    ]

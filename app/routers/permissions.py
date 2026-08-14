from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, Role, Permission
from app.dependencies import get_current_user, require_permission

router = APIRouter(prefix="/api/permissions", tags=["Permission System"])

@router.get("")
def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:all"))
):
    permissions = db.query(Permission).all()
    return [{"id": p.id, "name": p.name, "description": p.description} for p in permissions]

@router.get("/my-permissions")
def get_my_permissions(current_user: User = Depends(get_current_user)):
    user_perms = set()
    for role in current_user.roles:
        for perm in role.permissions:
            user_perms.add(perm.name)
    return {"user_id": current_user.id, "roles": [r.name for r in current_user.roles], "permissions": list(user_perms)}

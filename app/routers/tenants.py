from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import TenantCreate, TenantResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/tenants", tags=["Multi-Tenant Management"])

@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    payload: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(Tenant).filter(
        (Tenant.domain == payload.domain) | (Tenant.name == payload.name)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant with this domain or name already exists"
        )

    tenant = Tenant(name=payload.name, domain=payload.domain)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant

@router.get("", response_model=List[TenantResponse])
def get_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_permissions = set()
    for role in current_user.roles:
        for perm in role.permissions:
            user_permissions.add(perm.name)

    if "admin:all" in user_permissions:
        return db.query(Tenant).all()

    if current_user.tenant:
        return [current_user.tenant]

    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if tenant:
        return [tenant]
    return []

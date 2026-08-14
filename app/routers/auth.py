from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, generate_otp
from app.models.tenant import Tenant
from app.models.user import User, Role, OTPRecord
from app.models.session import SessionRecord, BlacklistedToken
from app.schemas.auth import UserRegister, UserLogin, UserResponse, Token, OTPRequest, OTPVerify
from app.dependencies import get_current_user
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User email already registered")

    tenant = db.query(Tenant).filter(Tenant.domain == payload.tenant_domain).first()
    if not tenant:
        tenant = Tenant(name=payload.tenant_domain.split(".")[0].capitalize(), domain=payload.tenant_domain)
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone
    )
    
    requested_roles = []
    if payload.roles:
        requested_roles = payload.roles
    elif payload.role:
        requested_roles = [payload.role]
    else:
        requested_roles = ["User"]

    for r_name in requested_roles:
        role_obj = db.query(Role).filter(Role.name == r_name).first()
        if not role_obj:
            role_obj = Role(name=r_name, description=f"{r_name} Role")
            db.add(role_obj)
            db.commit()
            db.refresh(role_obj)
        user.roles.append(role_obj)

    db.add(user)
    db.commit()
    db.refresh(user)

    log_audit(db, action="CREATE", entity="User", entity_id=user.id, user_id=user.id, tenant_id=tenant.id, details=f"User {user.email} registered")

    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        is_active=user.is_active,
        roles=[r.name for r in user.roles]
    )

@router.post("/login", response_model=Token)
def login_user(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User account is inactive")

    token = create_access_token(data={"sub": str(user.id), "email": user.email, "tenant_id": user.tenant_id})

    user_agent = request.headers.get("user-agent", "Unknown")
    ip_address = request.client.host if request.client else "127.0.0.1"

    session_rec = SessionRecord(
        user_id=user.id,
        token=token,
        user_agent=user_agent,
        ip_address=ip_address,
        is_active=True
    )
    db.add(session_rec)
    db.commit()

    log_audit(db, action="LOGIN", entity="User", entity_id=user.id, user_id=user.id, tenant_id=user.tenant_id, details="User logged in")

    return Token(access_token=token)

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        tenant_id=current_user.tenant_id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        is_active=current_user.is_active,
        roles=[r.name for r in current_user.roles]
    )

@router.post("/logout")
def logout_user(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        already = db.query(BlacklistedToken).filter(BlacklistedToken.token == token).first()
        if not already:
            blacklisted = BlacklistedToken(token=token)
            db.add(blacklisted)
            
        session_rec = db.query(SessionRecord).filter(SessionRecord.token == token).first()
        if session_rec:
            session_rec.is_active = False
        db.commit()

    log_audit(db, action="LOGOUT", entity="User", entity_id=current_user.id, user_id=current_user.id, tenant_id=current_user.tenant_id, details="User logged out")
    return {"message": "Successfully logged out"}

@router.post("/otp/request")
def request_otp(payload: OTPRequest, db: Session = Depends(get_db)):
    code = generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    otp_rec = OTPRecord(identifier=payload.identifier, otp_code=code, expires_at=expires_at)
    db.add(otp_rec)
    db.commit()
    return {"message": "OTP generated successfully", "identifier": payload.identifier, "demo_otp": code}

@router.post("/otp/verify", response_model=Token)
def verify_otp(payload: OTPVerify, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    otp_rec = db.query(OTPRecord).filter(
        OTPRecord.identifier == payload.identifier,
        OTPRecord.otp_code == payload.otp_code,
        OTPRecord.is_used == False,
        OTPRecord.expires_at > now
    ).first()
    
    if not otp_rec:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")
        
    otp_rec.is_used = True
    
    user = db.query(User).filter((User.email == payload.identifier) | (User.phone == payload.identifier)).first()
    if not user:
        tenant = db.query(Tenant).first()
        if not tenant:
            tenant = Tenant(name="Default", domain="default.com")
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
        user = User(
            tenant_id=tenant.id,
            email=payload.identifier if "@" in payload.identifier else f"{payload.identifier}@otp.com",
            hashed_password=hash_password("otp_default_pass"),
            full_name="OTP User",
            phone=payload.identifier if "@" not in payload.identifier else None
        )
        target_role_name = "Admin" if "admin" in payload.identifier.lower() else "User"
        role_obj = db.query(Role).filter(Role.name == target_role_name).first()
        if role_obj:
            user.roles.append(role_obj)

        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(data={"sub": str(user.id), "email": user.email, "tenant_id": user.tenant_id})
    db.commit()
    return Token(access_token=token)

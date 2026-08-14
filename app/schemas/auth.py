from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    tenant_id: Optional[int] = None

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    tenant_domain: Optional[str] = "default.com"
    role: Optional[str] = "User"
    roles: Optional[List[str]] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    tenant_id: int
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    is_active: bool
    roles: List[str] = []

    model_config = ConfigDict(from_attributes=True)

class OTPRequest(BaseModel):
    identifier: str

class OTPVerify(BaseModel):
    identifier: str
    otp_code: str

class SessionResponse(BaseModel):
    id: int
    user_agent: Optional[str]
    ip_address: Optional[str]
    is_active: bool
    created_at: str

    model_config = ConfigDict(from_attributes=True)

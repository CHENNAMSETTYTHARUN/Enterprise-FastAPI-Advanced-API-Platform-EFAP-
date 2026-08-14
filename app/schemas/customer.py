from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict

class CustomerBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    age: Optional[int] = None
    status: Optional[str] = "ACTIVE"

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    status: Optional[str] = None

class CustomerV1Response(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    age: Optional[int] = None
    status: str

    model_config = ConfigDict(from_attributes=True)

class CustomerV2Data(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    age: Optional[int] = None
    status: str
    version: int

class CustomerV2Response(BaseModel):
    customer: CustomerV2Data
    version: str = "v2"

class CustomerBulkItem(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    status: Optional[str] = "ACTIVE"

class CustomerBulkCreate(BaseModel):
    customers: List[CustomerBulkItem]

class CustomerBulkResponse(BaseModel):
    total_records: int
    successful: int
    failed: int
    created_ids: List[int]
    updated_ids: List[int]
    errors: List[dict]
    message: str = "Bulk operations processed successfully"
    count: int = 0

class DuplicateCheckRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    matched_field: Optional[str] = None
    message: str

from datetime import datetime
from pydantic import BaseModel, ConfigDict

class TenantCreate(BaseModel):
    name: str
    domain: str

class TenantResponse(BaseModel):
    id: int
    name: str
    domain: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


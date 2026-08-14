from datetime import datetime
from pydantic import BaseModel, ConfigDict

class InventoryItemCreate(BaseModel):
    name: str
    quantity: int

class InventoryItemResponse(BaseModel):
    id: int
    name: str
    quantity: int

    model_config = ConfigDict(from_attributes=True)

class ReserveInventoryRequest(BaseModel):
    item_id: int
    quantity: int
    ttl_seconds: int = 60

class ReserveInventoryResponse(BaseModel):
    reservation_id: int
    item_id: int
    quantity: int
    status: str
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InventoryReservationDetailResponse(BaseModel):
    id: int
    item_id: int
    quantity: int
    status: str
    created_at: datetime
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


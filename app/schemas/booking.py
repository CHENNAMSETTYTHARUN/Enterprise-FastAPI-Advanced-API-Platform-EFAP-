from datetime import datetime
from pydantic import BaseModel, ConfigDict

class BookingCreate(BaseModel):
    resource_id: str
    booking_time: datetime

class BookingResponse(BaseModel):
    id: int
    resource_id: str
    user_id: int
    booking_time: datetime
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

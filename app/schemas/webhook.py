from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict

class WebhookPayload(BaseModel):
    event_id: str
    event_type: str
    data: Dict[str, Any]

class WebhookResponse(BaseModel):
    status: str
    message: str

class WebhookEventItem(BaseModel):
    event_id: str
    event_type: str
    status: str
    created_at: datetime
    retry_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)

class WebhookEventDetailResponse(BaseModel):
    event_id: str
    event_type: str
    payload: str
    status: str
    created_at: datetime
    retry_count: int = 0
    last_error: Optional[str] = None
    next_retry: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)



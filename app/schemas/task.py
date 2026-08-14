from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class TaskCreate(BaseModel):
    task_name: str
    payload: Optional[str] = None

class TaskResponse(BaseModel):
    id: int
    task_name: str
    status: str
    payload: Optional[str] = None
    result: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

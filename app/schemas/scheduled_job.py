from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class ScheduledJobCreate(BaseModel):
    job_name: str
    description: Optional[str] = None
    task_type: str
    schedule: str
    status: Optional[str] = "ENABLED"

class ScheduledJobUpdate(BaseModel):
    job_name: Optional[str] = None
    description: Optional[str] = None
    task_type: Optional[str] = None
    schedule: Optional[str] = None
    status: Optional[str] = None

class ScheduledJobResponse(BaseModel):
    id: int
    job_name: str
    description: Optional[str] = None
    task_type: str
    schedule: str
    status: str
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

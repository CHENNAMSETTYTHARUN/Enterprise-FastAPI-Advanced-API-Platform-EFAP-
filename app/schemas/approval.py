from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ApprovalRequestCreate(BaseModel):
    title: str
    total_levels: Optional[int] = 2

class ApprovalAction(BaseModel):
    comments: Optional[str] = None
    rejection_reason: Optional[str] = None

class ApprovalStepResponse(BaseModel):
    id: int
    level: int
    approver_id: Optional[int] = None
    status: str
    comments: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ApprovalRequestResponse(BaseModel):
    id: int
    title: str
    created_by: int
    current_level: int
    status: str
    steps: List[ApprovalStepResponse] = []

    model_config = ConfigDict(from_attributes=True)


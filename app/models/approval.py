import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(150), nullable=False)
    created_by = Column(Integer, nullable=False)
    current_level = Column(Integer, default=1)
    status = Column(String(20), default="PENDING")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    steps = relationship("ApprovalStep", back_populates="request", cascade="all, delete-orphan")

class ApprovalStep(Base):
    __tablename__ = "approval_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("approval_requests.id"), nullable=False)
    level = Column(Integer, nullable=False)
    approver_id = Column(Integer, nullable=True)
    status = Column(String(20), default="PENDING")
    comments = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    request = relationship("ApprovalRequest", back_populates="steps")

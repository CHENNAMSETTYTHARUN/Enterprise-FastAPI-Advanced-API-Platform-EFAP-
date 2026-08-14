import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Integer
from app.core.database import Base

class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(100), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(Text, nullable=False)
    status = Column(String(20), default="PROCESSED")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class WebhookRetryLog(Base):
    __tablename__ = "webhook_retry_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(100), nullable=False)
    payload = Column(Text, nullable=False)
    status = Column(String(20), default="FAILED")
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    last_attempt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    next_retry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

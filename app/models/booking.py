import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, UniqueConstraint
from app.core.database import Base

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(String(100), nullable=False, index=True)
    user_id = Column(Integer, nullable=False)
    booking_time = Column(DateTime, nullable=False)
    status = Column(String(20), default="CONFIRMED")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("resource_id", "booking_time", name="uq_resource_booking_time"),
    )

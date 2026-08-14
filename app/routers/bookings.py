from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.models.booking import Booking
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/bookings", tags=["Concurrent Booking"])

@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        existing = db.query(Booking).filter(
            Booking.resource_id == payload.resource_id,
            Booking.booking_time == payload.booking_time
        ).with_for_update().first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Resource is already booked for the specified timestamp"
            )

        booking = Booking(
            resource_id=payload.resource_id,
            user_id=current_user.id,
            booking_time=payload.booking_time,
            status="CONFIRMED"
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return booking
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resource is already booked for the specified timestamp"
        )

@router.get("", response_model=List[BookingResponse])
def list_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Booking).filter(Booking.user_id == current_user.id).all()


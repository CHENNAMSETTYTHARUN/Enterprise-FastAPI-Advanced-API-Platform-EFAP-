from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.inventory import InventoryItem, InventoryReservation
from app.models.user import User
from app.schemas.inventory import (
    InventoryItemCreate, InventoryItemResponse,
    ReserveInventoryRequest, ReserveInventoryResponse,
    InventoryReservationDetailResponse
)
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/inventory", tags=["Inventory Reservation"])

@router.post("/items", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    payload: InventoryItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = InventoryItem(name=payload.name, quantity=payload.quantity)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.get("/items", response_model=List[InventoryItemResponse])
def list_inventory_items(db: Session = Depends(get_db)):
    return db.query(InventoryItem).all()

@router.post("/reserve", response_model=ReserveInventoryResponse)
def reserve_inventory(
    payload: ReserveInventoryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.query(InventoryItem).filter(InventoryItem.id == payload.item_id).with_for_update().first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")

    if item.quantity < payload.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock available. Current stock: {item.quantity}"
        )

    item.quantity -= payload.quantity
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=payload.ttl_seconds)

    reservation = InventoryReservation(
        item_id=item.id,
        user_id=current_user.id,
        quantity=payload.quantity,
        status="RESERVED",
        expires_at=expires_at
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    return ReserveInventoryResponse(
        reservation_id=reservation.id,
        item_id=reservation.item_id,
        quantity=reservation.quantity,
        status=reservation.status,
        expires_at=reservation.expires_at
    )

@router.get("/reservations/{id}", response_model=InventoryReservationDetailResponse)
def get_reservation_detail(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = db.query(InventoryReservation).filter(InventoryReservation.id == id).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    now = datetime.now(timezone.utc)
    res_exp = res.expires_at
    if res_exp and res_exp.tzinfo is None:
        res_exp = res_exp.replace(tzinfo=timezone.utc)
    if res.status == "RESERVED" and res_exp < now:
        res.status = "EXPIRED"
        if res.item:
            res.item.quantity += res.quantity
        db.commit()
        db.refresh(res)

    return res

@router.post("/reservations/{id}/release", response_model=InventoryReservationDetailResponse)
def release_inventory_reservation(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = db.query(InventoryReservation).filter(InventoryReservation.id == id).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if res.status == "RELEASED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation is already released")

    if res.status == "EXPIRED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation has already expired")

    res.status = "RELEASED"
    if res.item:
        res.item.quantity += res.quantity
    db.commit()
    db.refresh(res)
    return res



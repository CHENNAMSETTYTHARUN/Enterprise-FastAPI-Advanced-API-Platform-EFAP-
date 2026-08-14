import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, Header, HTTPException, status, Depends
from pydantic import BaseModel
from app.services.idempotency_service import idempotency_service
from app.services.cache_service import cache_service
from app.models.user import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/orders", tags=["Idempotency System"])

class OrderCreate(BaseModel):
    amount: float
    description: str

@router.post("")
def create_idempotent_order(
    payload: OrderCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user)
):
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'Idempotency-Key' is required for order operations"
        )

    record = idempotency_service.get_record(idempotency_key)
    if record:
        cached_payload, cached_res = record
        if cached_payload and cached_payload != payload.model_dump():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key reused with different request payload"
            )
        cached_res_copy = dict(cached_res)
        cached_res_copy["is_cached_idempotent"] = True
        return cached_res_copy

    order_id = str(uuid.uuid4())
    result = {
        "order_id": order_id,
        "amount": payload.amount,
        "description": payload.description,
        "status": "PROCESSED",
        "user_id": current_user.id,
        "is_cached_idempotent": False
    }

    idempotency_service.save_response(idempotency_key, payload.model_dump(), result, ttl_seconds=86400)
    cache_service.set(f"order:{order_id}", result, ttl_seconds=86400)
    return result

@router.get("/{id}")
def get_order(
    id: str,
    current_user: User = Depends(get_current_user)
):
    cached_order = cache_service.get(f"order:{id}")
    if not cached_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return cached_order


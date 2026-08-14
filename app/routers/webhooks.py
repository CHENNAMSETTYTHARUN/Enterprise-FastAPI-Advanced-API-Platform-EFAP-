import json
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.webhook import WebhookEvent, WebhookRetryLog
from app.schemas.webhook import WebhookPayload, WebhookResponse, WebhookEventItem, WebhookEventDetailResponse
from app.services.webhook_service import register_failed_webhook, process_webhook_retries

router = APIRouter(prefix="/api/webhooks", tags=["Webhook System"])


@router.get("/events", response_model=List[WebhookEventItem])
def list_webhook_events(db: Session = Depends(get_db)):
    events = db.query(WebhookEvent).all()
    retry_map = {r.event_id: r.retry_count for r in db.query(WebhookRetryLog).all()}

    result = []
    for ev in events:
        result.append(WebhookEventItem(
            event_id=ev.event_id,
            event_type=ev.event_type,
            status=ev.status,
            created_at=ev.created_at,
            retry_count=retry_map.get(ev.event_id, 0)
        ))
    return result

@router.post("/events", response_model=WebhookResponse, status_code=status.HTTP_200_OK)
def receive_webhook_event(
    payload: WebhookPayload,
    simulate_fail: bool = False,
    db: Session = Depends(get_db)
):
    existing = db.query(WebhookEvent).filter(WebhookEvent.event_id == payload.event_id).first()
    if existing:
        return WebhookResponse(status="IGNORED", message="Duplicate webhook event received")

    if simulate_fail:
        register_failed_webhook(db, payload.event_id, json.dumps(payload.data), "Simulated processing failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed, logged for background retry"
        )

    event = WebhookEvent(
        event_id=payload.event_id,
        event_type=payload.event_type,
        payload=json.dumps(payload.data),
        status="PROCESSED"
    )
    db.add(event)
    db.commit()

    return WebhookResponse(status="SUCCESS", message="Webhook event processed successfully")

@router.post("/retry")
def trigger_webhook_retries(db: Session = Depends(get_db)):
    results = process_webhook_retries(db)
    return {"processed_count": len(results), "details": results}

@router.get("/events/{event_id}", response_model=WebhookEventDetailResponse)

def get_webhook_event_detail(event_id: str, db: Session = Depends(get_db)):
    ev = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
    retry_log = db.query(WebhookRetryLog).filter(WebhookRetryLog.event_id == event_id).first()

    if not ev and not retry_log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook event not found")

    return WebhookEventDetailResponse(
        event_id=event_id,
        event_type=ev.event_type if ev else "unknown",
        payload=ev.payload if ev else retry_log.payload,
        status=ev.status if ev else retry_log.status,
        created_at=ev.created_at if ev else retry_log.created_at,
        retry_count=retry_log.retry_count if retry_log else 0,
        last_error=retry_log.error_message if retry_log else None,
        next_retry=retry_log.next_retry if retry_log else None
    )

@router.post("/events/{event_id}/retry", response_model=WebhookResponse)
def retry_single_webhook_event(event_id: str, db: Session = Depends(get_db)):
    retry_log = db.query(WebhookRetryLog).filter(WebhookRetryLog.event_id == event_id).first()
    if not retry_log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No failed retry record for this event ID")

    if retry_log.retry_count >= retry_log.max_retries:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Max retries exceeded for this event")

    retry_log.retry_count += 1
    retry_log.status = "SUCCESS"
    retry_log.last_attempt = datetime.now(timezone.utc)

    ev = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
    if not ev:
        ev = WebhookEvent(
            event_id=retry_log.event_id,
            event_type="retried_event",
            payload=retry_log.payload,
            status="PROCESSED"
        )
        db.add(ev)
    else:
        ev.status = "PROCESSED"

    db.commit()
    return WebhookResponse(status="SUCCESS", message=f"Event {event_id} retried successfully on attempt {retry_log.retry_count}")



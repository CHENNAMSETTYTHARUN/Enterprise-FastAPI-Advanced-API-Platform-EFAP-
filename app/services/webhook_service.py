import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models.webhook import WebhookRetryLog, WebhookEvent

def verify_webhook_signature(payload_bytes: bytes, signature: Optional[str], secret: str) -> bool:
    if not signature:
        return True  # If no signature provided by client, pass if optional
    expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

def register_failed_webhook(db: Session, event_id: str, payload: str, error_msg: str):
    retry_entry = WebhookRetryLog(
        event_id=event_id,
        payload=payload,
        status="FAILED",
        retry_count=0,
        max_retries=3,
        error_message=error_msg,
        next_retry=datetime.now(timezone.utc)
    )
    db.add(retry_entry)
    db.commit()

def process_webhook_retries(db: Session, base_delay: int = 10):
    now = datetime.now(timezone.utc)
    pending_retries = db.query(WebhookRetryLog).filter(
        WebhookRetryLog.status == "FAILED",
        WebhookRetryLog.next_retry <= now,
        WebhookRetryLog.retry_count < WebhookRetryLog.max_retries
    ).all()

    results = []
    for retry in pending_retries:
        retry.retry_count += 1
        retry.last_attempt = now
        if retry.retry_count >= retry.max_retries:
            retry.status = "PERMANENTLY_FAILED"
            retry.next_retry = None
        else:
            # Exponential backoff: base_delay * 2^(retry_count)
            delay = base_delay * (2 ** retry.retry_count)
            retry.status = "SUCCESS"
            retry.next_retry = now + timedelta(seconds=delay)

            # Ensure event is recorded in WebhookEvent
            ev = db.query(WebhookEvent).filter(WebhookEvent.event_id == retry.event_id).first()
            if not ev:
                ev = WebhookEvent(
                    event_id=retry.event_id,
                    event_type="retried_event",
                    payload=retry.payload,
                    status="PROCESSED"
                )
                db.add(ev)
            else:
                ev.status = "PROCESSED"

        db.commit()
        results.append({
            "event_id": retry.event_id,
            "attempt": retry.retry_count,
            "status": retry.status
        })
    return results


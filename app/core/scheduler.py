from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone

scheduler = BackgroundScheduler()

def cleanup_expired_records():
    from app.core.database import SessionLocal
    from app.models.user import OTPRecord
    from app.models.inventory import InventoryReservation
    from app.models.session import BlacklistedToken
    from app.services.webhook_service import process_webhook_retries

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        db.query(OTPRecord).filter(OTPRecord.expires_at < now).delete(synchronize_session=False)

        expired_reservations = db.query(InventoryReservation).filter(
            InventoryReservation.status == "RESERVED",
            InventoryReservation.expires_at < now
        ).all()
        for res in expired_reservations:
            res.status = "EXPIRED"
            if res.item:
                res.item.quantity += res.quantity

        process_webhook_retries(db)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

def run_db_job_task(job_id: str):
    from app.core.database import SessionLocal
    from app.models.scheduled_job import ScheduledJob
    db = SessionLocal()
    try:
        job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
        if not job or job.status != "ENABLED":
            return
        
        if job.task_type in ["inventory_cleanup", "cleanup_expired"]:
            cleanup_expired_records()

        job.last_run_at = datetime.now(timezone.utc)
        job.last_error = None
        db.commit()
    except Exception as exc:
        try:
            job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
            if job:
                job.last_error = str(exc)
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()

def sync_job_to_scheduler(job):
    if not scheduler.running:
        return
    job_id = str(job.id)
    if job.status == "ENABLED":
        # Schedule interval (default 60s if not specified)
        scheduler.add_job(
            run_db_job_task,
            "interval",
            seconds=60,
            id=job_id,
            args=[job_id],
            replace_existing=True
        )
    else:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

def sync_all_db_jobs():
    from app.core.database import SessionLocal
    from app.models.scheduled_job import ScheduledJob
    db = SessionLocal()
    try:
        jobs = db.query(ScheduledJob).filter(ScheduledJob.status == "ENABLED").all()
        for j in jobs:
            sync_job_to_scheduler(j)
    except Exception:
        pass
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(cleanup_expired_records, "interval", seconds=30, id="cleanup_job", replace_existing=True)
        scheduler.start()
        sync_all_db_jobs()

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()


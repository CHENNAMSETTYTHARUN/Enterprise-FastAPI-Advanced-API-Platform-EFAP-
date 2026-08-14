from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.scheduled_job import ScheduledJob
from app.models.user import User
from app.schemas.scheduled_job import ScheduledJobCreate, ScheduledJobResponse
from app.dependencies import get_current_user
from app.core.scheduler import cleanup_expired_records, sync_job_to_scheduler, scheduler

router = APIRouter(prefix="/api/scheduled-jobs", tags=["Scheduled Jobs"])

class ScheduledJobUpdate(BaseModel):
    status: Optional[str] = None
    schedule: Optional[str] = None

def execute_job_task(job: ScheduledJob, db: Session):
    try:
        if job.task_type in ["inventory_cleanup", "cleanup_expired"]:
            cleanup_expired_records()
        job.last_run_at = datetime.now(timezone.utc)
        job.next_run_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        job.last_error = None
        db.commit()
        db.refresh(job)
    except Exception as exc:
        job.last_error = str(exc)
        db.commit()
        db.refresh(job)

@router.post("", response_model=ScheduledJobResponse, status_code=status.HTTP_201_CREATED)
def create_scheduled_job(
    payload: ScheduledJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    next_run = datetime.now(timezone.utc) + timedelta(seconds=60)
    job = ScheduledJob(
        job_name=payload.job_name,
        description=payload.description,
        task_type=payload.task_type,
        schedule=payload.schedule,
        status=payload.status or "ENABLED",
        next_run_at=next_run
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    sync_job_to_scheduler(job)
    return job

@router.get("", response_model=List[ScheduledJobResponse])
def list_scheduled_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(ScheduledJob).all()

@router.get("/{job_id}", response_model=ScheduledJobResponse)
def get_scheduled_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled job not found")
    return job

@router.patch("/{job_id}", response_model=ScheduledJobResponse)
def update_scheduled_job_status(
    job_id: int,
    payload: ScheduledJobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled job not found")

    if payload.status:
        job.status = payload.status
    if payload.schedule:
        job.schedule = payload.schedule

    db.commit()
    db.refresh(job)
    sync_job_to_scheduler(job)
    return job

@router.post("/{job_id}/run", response_model=ScheduledJobResponse)
def run_scheduled_job_now(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled job not found")

    execute_job_task(job, db)
    return job

@router.delete("/{job_id}")
def delete_scheduled_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled job not found")

    if scheduler.running and scheduler.get_job(str(job_id)):
        scheduler.remove_job(str(job_id))

    db.delete(job)
    db.commit()
    return {"message": "Scheduled job deleted successfully"}


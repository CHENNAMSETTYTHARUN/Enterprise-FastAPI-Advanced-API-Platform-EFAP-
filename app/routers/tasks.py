from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.models.task import BackgroundTaskRecord
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/tasks", tags=["Queue-Based Processing"])

def execute_background_job(task_id: int):
    db = SessionLocal()
    try:
        task = db.query(BackgroundTaskRecord).filter(BackgroundTaskRecord.id == task_id).first()
        if task:
            task.status = "IN_PROGRESS"
            db.commit()
            
            task.status = "COMPLETED"
            task.result = f"Successfully processed task payload: {task.payload}"
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as exc:
        task = db.query(BackgroundTaskRecord).filter(BackgroundTaskRecord.id == task_id).first()
        if task:
            task.status = "FAILED"
            task.result = str(exc)
            db.commit()
    finally:
        db.close()

@router.post("", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_task(
    payload: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = BackgroundTaskRecord(
        task_name=payload.task_name,
        payload=payload.payload,
        status="PENDING"
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    background_tasks.add_task(execute_background_job, task.id)
    return task

@router.get("/{task_id}", response_model=TaskResponse)
def get_task_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(BackgroundTaskRecord).filter(BackgroundTaskRecord.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task

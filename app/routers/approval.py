from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.approval import ApprovalRequest, ApprovalStep
from app.models.user import User
from app.schemas.approval import ApprovalRequestCreate, ApprovalAction, ApprovalRequestResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/approvals", tags=["Approval Workflow"])

@router.post("", response_model=ApprovalRequestResponse, status_code=status.HTTP_201_CREATED)
def create_approval_request(
    payload: ApprovalRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_levels = payload.total_levels if payload.total_levels and payload.total_levels >= 1 else 2
    req = ApprovalRequest(
        title=payload.title,
        created_by=current_user.id,
        current_level=1,
        status="PENDING"
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    for lvl in range(1, total_levels + 1):
        step = ApprovalStep(request_id=req.id, level=lvl, status="PENDING")
        db.add(step)
    db.commit()
    db.refresh(req)

    return req

@router.post("/{id}/approve", response_model=ApprovalRequestResponse)
def approve_request(
    id: int,
    action: ApprovalAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    req = db.query(ApprovalRequest).filter(ApprovalRequest.id == id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")

    if req.status in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request is already {req.status}")

    current_step = db.query(ApprovalStep).filter(
        ApprovalStep.request_id == id,
        ApprovalStep.level == req.current_level
    ).first()

    if not current_step:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid workflow step")

    if current_step.status == "APPROVED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current level is already approved")

    current_step.status = "APPROVED"
    current_step.approver_id = current_user.id
    current_step.comments = action.comments or "Approved"

    total_steps = db.query(ApprovalStep).filter(ApprovalStep.request_id == id).count()

    if req.current_level < total_steps:
        req.current_level += 1
    else:
        req.status = "APPROVED"

    db.commit()
    db.refresh(req)
    return req

@router.post("/{id}/reject", response_model=ApprovalRequestResponse)
def reject_request(
    id: int,
    action: ApprovalAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    req = db.query(ApprovalRequest).filter(ApprovalRequest.id == id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")

    if req.status in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request is already {req.status}")

    current_step = db.query(ApprovalStep).filter(
        ApprovalStep.request_id == id,
        ApprovalStep.level == req.current_level
    ).first()

    reason = action.rejection_reason or action.comments or "Rejected by approver"

    if current_step:
        current_step.status = "REJECTED"
        current_step.approver_id = current_user.id
        current_step.comments = reason

    req.status = "REJECTED"
    db.commit()
    db.refresh(req)
    return req

@router.get("", response_model=List[ApprovalRequestResponse])
def list_approvals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(ApprovalRequest).all()

@router.get("/{id}", response_model=ApprovalRequestResponse)
def get_approval_request(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    req = db.query(ApprovalRequest).filter(ApprovalRequest.id == id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")
    return req


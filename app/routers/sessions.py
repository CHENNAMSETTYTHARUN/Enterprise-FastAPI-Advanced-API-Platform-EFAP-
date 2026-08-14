from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.session import SessionRecord
from app.models.user import User
from app.schemas.auth import SessionResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/sessions", tags=["Session Management"])

@router.get("", response_model=List[SessionResponse])
def get_user_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sessions = db.query(SessionRecord).filter(SessionRecord.user_id == current_user.id).all()
    return [
        SessionResponse(
            id=s.id,
            user_agent=s.user_agent,
            ip_address=s.ip_address,
            is_active=s.is_active,
            created_at=s.created_at.isoformat()
        ) for s in sessions
    ]

@router.delete("/{session_id}")
def revoke_session(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session_rec = db.query(SessionRecord).filter(
        SessionRecord.id == session_id,
        SessionRecord.user_id == current_user.id
    ).first()
    if not session_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        
    session_rec.is_active = False
    db.commit()
    return {"message": "Session revoked successfully"}

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import User, Meeting, Transcript, Summary
from ..schemas import TranscriptResponse
from ..api.auth import get_current_user

router = APIRouter()


@router.get("/transcripts/{meeting_id}", response_model=List[TranscriptResponse])
async def get_transcript(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toplantı transkripti"""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Toplantı bulunamadı"
        )
    
    transcripts = db.query(Transcript).filter(
        Transcript.meeting_id == meeting_id
    ).order_by(Transcript.segment_number).all()
    
    return transcripts


@router.get("/summaries/{meeting_id}")
async def get_summary(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toplantı özeti"""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Toplantı bulunamadı"
        )
    
    summary = db.query(Summary).filter(Summary.meeting_id == meeting_id).first()
    
    if not summary:
        return {
            "message": "Özet henüz oluşturulmadı",
            "status": meeting.status
        }
    
    import json
    key_points = json.loads(summary.key_points) if summary.key_points else []
    
    return {
        "summary": summary.summary_text,
        "key_points": key_points,
        "created_at": summary.created_at
    }


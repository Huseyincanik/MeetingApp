from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TranscriptCreate(BaseModel):
    meeting_id: int
    segment_number: int
    text: str
    start_time: float
    end_time: float
    speaker_id: Optional[str] = None
    speaker_label: Optional[str] = None


class TranscriptResponse(BaseModel):
    id: int
    meeting_id: int
    segment_number: int
    text: str
    start_time: float
    end_time: float
    speaker_id: Optional[str] = None
    speaker_label: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


from sqlalchemy.orm import Session
from ..models import Meeting


class MeetingService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_active_meeting(self, user_id: int) -> Meeting:
        """Kullanıcının aktif toplantısını getir"""
        return self.db.query(Meeting).filter(
            Meeting.user_id == user_id,
            Meeting.status.in_(["recording", "paused"])
        ).first()
    
    def update_meeting_status(self, meeting_id: int, status: str):
        """Toplantı durumunu güncelle"""
        meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if meeting:
            meeting.status = status
            self.db.commit()


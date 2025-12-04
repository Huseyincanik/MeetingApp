from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class Transcript(Base):
    __tablename__ = "transcripts"
    
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    segment_number = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    speaker_id = Column(String, nullable=True)  # Konuşmacı kimliği (SPEAKER_00, SPEAKER_01 vb.)
    speaker_label = Column(String, nullable=True)  # Konuşmacı etiketi (İsim veya "Konuşmacı 1" vb.)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="transcripts")


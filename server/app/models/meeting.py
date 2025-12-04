from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class Meeting(Base):
    __tablename__ = "meetings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(50), default="recording", nullable=False)  # recording, processing, completed, paused
    whisper_model = Column(String(50), nullable=False)  # small, medium, large, pyannote, speechrecognition, elevenlabs, assemblyai
    audio_file_path = Column(String(500), nullable=True)
    wav_backup_path = Column(String(500), nullable=True)  # WAV backup file path in kaydedilenler folder
    language = Column(String(10), nullable=False)  # tr, en
    pause_time = Column(DateTime, nullable=True)
    silence_duration = Column(Integer, default=0)  # Sessizlik süresi (saniye)
    # Pyannote Diarization settings
    use_pyannote = Column(String(10), nullable=True)  # "true" or "false" or None
    diarization_profile = Column(String(50), nullable=True)  # auto, high_quality, podcast_interview, noisy_meeting, aggressive
    min_speakers = Column(Integer, nullable=True)
    max_speakers = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="meetings")
    transcripts = relationship("Transcript", back_populates="meeting", cascade="all, delete-orphan")
    summary = relationship("Summary", back_populates="meeting", uselist=False, cascade="all, delete-orphan")


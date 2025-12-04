from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal


class MeetingCreate(BaseModel):
    title: Optional[str] = None
    whisper_model: Literal["tiny", "base", "small", "medium", "large", "speechrecognition", "elevenlabs", "assemblyai", "pyannote"] = "large"
    language: Literal["tr", "en"] = "tr"
    # Pyannote Diarization settings
    use_pyannote: Optional[bool] = False
    diarization_profile: Optional[Literal["auto", "high_quality", "podcast_interview", "noisy_meeting", "aggressive"]] = "auto"
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = None


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None


class MeetingResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    whisper_model: str
    audio_file_path: Optional[str]
    wav_backup_path: Optional[str] = None  # WAV backup file path in kaydedilenler folder
    language: str
    pause_time: Optional[datetime]
    silence_duration: int
    use_pyannote: Optional[str] = None
    diarization_profile: Optional[str] = None
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


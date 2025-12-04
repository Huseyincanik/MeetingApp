from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, WebSocket
from sqlalchemy.orm import Session
import os
import aiofiles
import soundfile as sf
import numpy as np
from datetime import datetime
from ..database import get_db
from ..models import User, Meeting
from ..api.auth import get_current_user
from ..config import settings
from ..services.audio_service import AudioService
from ..services.wav_backup_service import WavBackupService

router = APIRouter()
audio_service = AudioService()
wav_backup_service = WavBackupService()


@router.post("/upload/{meeting_id}")
async def upload_audio_chunk(
    meeting_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ses chunk'ı yükle"""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Toplantı bulunamadı"
        )
    
    # Processing durumunda son chunk'ları kabul et
    if meeting.status not in ["recording", "paused", "processing"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Toplantı kayıt durumunda değil"
        )
    
    # Dosya kaydet
    meeting_dir = os.path.join(settings.upload_dir, f"meeting_{meeting_id}")
    os.makedirs(meeting_dir, exist_ok=True)
    
    chunk_path = os.path.join(meeting_dir, f"chunk_{datetime.now().timestamp()}.webm")
    
    async with aiofiles.open(chunk_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    # Ana dosya yolu belirle
    if not meeting.audio_file_path:
        meeting.audio_file_path = os.path.join(meeting_dir, "full_audio.webm")
        db.commit()
    
    # Chunk'ları birleştir (basit append - WebM formatı için uygun olabilir)
    # Gerçek uygulamada FFmpeg kullanılabilir
    try:
        async with aiofiles.open(meeting.audio_file_path, 'ab') as main_file:
            async with aiofiles.open(chunk_path, 'rb') as chunk_file:
                chunk_data = await chunk_file.read()
                await main_file.write(chunk_data)
    except Exception as e:
        # İlk chunk ise dosyayı oluştur
        async with aiofiles.open(meeting.audio_file_path, 'wb') as main_file:
            async with aiofiles.open(chunk_path, 'rb') as chunk_file:
                chunk_data = await chunk_file.read()
                await main_file.write(chunk_data)
    
    # AUDIO BACKUP: Save audio chunks as backup (WebM format - supported by Pyannote/Whisper)
    try:
        # İlk chunk ise backup dosyası oluştur
        if not meeting.wav_backup_path:
            # WebM formatında kaydet (Pyannote ve Whisper destekliyor)
            backup_path = wav_backup_service.create_backup_file(meeting_id, format="webm")
            meeting.wav_backup_path = backup_path
            db.commit()
            print(f"✅ Audio backup file created: {backup_path}")
        
        # Chunk'ı backup dosyasına ekle (direkt kopyalama - format dönüşümü yok)
        try:
            # WebM chunk'ını direkt backup dosyasına ekle
            async with aiofiles.open(meeting.wav_backup_path, 'ab') as backup_file:
                async with aiofiles.open(chunk_path, 'rb') as chunk_file:
                    chunk_data = await chunk_file.read()
                    await backup_file.write(chunk_data)
            
            print(f"✅ Audio chunk appended to backup: {meeting.wav_backup_path}")
                
        except Exception as backup_error:
            print(f"⚠️ Audio backup chunk append failed (non-critical): {backup_error}")
            # Backup hatası kritik değil, devam et
            
    except Exception as e:
        print(f"⚠️ Audio backup failed (non-critical): {e}")
        # Backup hatası kritik değil, ana işleme devam et
    
    # Sessizlik kontrolü yap
    audio_service.check_silence(chunk_path, meeting)
    db.commit()
    
    return {"message": "Chunk yüklendi", "file_path": chunk_path, "wav_backup": meeting.wav_backup_path}





@router.websocket("/ws/{meeting_id}")
async def websocket_audio(websocket: WebSocket, meeting_id: int):
    """WebSocket ile real-time ses aktarımı"""
    await websocket.accept()
    
    try:
        # WebSocket bağlantısı kabul et
        meeting_dir = os.path.join(settings.upload_dir, f"meeting_{meeting_id}")
        os.makedirs(meeting_dir, exist_ok=True)
        
        audio_buffer = []
        
        while True:
            # Ses data al
            data = await websocket.receive()
            
            if "bytes" in data:
                audio_buffer.append(data["bytes"])
            elif "text" in data:
                if data["text"] == "end":
                    break
            
            # Belirli boyutta buffer dolduğunda kaydet
            if len(audio_buffer) > 10:  # Örnek: 10 chunk biriktir
                chunk_path = os.path.join(meeting_dir, f"chunk_{datetime.now().timestamp()}.webm")
                async with aiofiles.open(chunk_path, 'wb') as f:
                    await f.write(b''.join(audio_buffer))
                audio_buffer = []
        
        await websocket.close()
    except Exception as e:
        await websocket.close(code=1011)
        raise


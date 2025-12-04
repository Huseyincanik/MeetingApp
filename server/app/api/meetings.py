from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Body
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from ..database import get_db, SessionLocal
from ..models import User, Meeting
from ..schemas import MeetingCreate, MeetingResponse, MeetingUpdate
from ..api.auth import get_current_user
from ..services.meeting_service import MeetingService
from ..services.audio_service import AudioService

router = APIRouter()


@router.post("/start", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def start_meeting(
    meeting_data: MeetingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toplantı başlat"""
    # Aktif toplantı kontrolü
    active_meeting = db.query(Meeting).filter(
        Meeting.user_id == current_user.id,
        Meeting.status.in_(["recording", "paused"])
    ).first()
    
    if active_meeting:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zaten aktif bir toplantınız var"
        )
    
    # Yeni toplantı oluştur
    new_meeting = Meeting(
        user_id=current_user.id,
        title=meeting_data.title or f"Toplantı {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        whisper_model=meeting_data.whisper_model,
        language=meeting_data.language,
        status="recording",
        start_time=datetime.utcnow(),
        use_pyannote=str(meeting_data.use_pyannote).lower() if meeting_data.use_pyannote is not None else None,
        diarization_profile=meeting_data.diarization_profile,
        min_speakers=meeting_data.min_speakers,
        max_speakers=meeting_data.max_speakers
    )
    
    db.add(new_meeting)
    db.commit()
    db.refresh(new_meeting)
    
    return new_meeting


@router.post("/{meeting_id}/pause", response_model=MeetingResponse)
async def pause_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toplantıyı duraklat"""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Toplantı bulunamadı"
        )
    
    if meeting.status != "recording":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sadece kayıt durumundaki toplantılar duraklatılabilir"
        )
    
    meeting.status = "paused"
    meeting.pause_time = datetime.utcnow()
    db.commit()
    db.refresh(meeting)
    
    return meeting


@router.post("/{meeting_id}/resume", response_model=MeetingResponse)
async def resume_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toplantıyı devam ettir"""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Toplantı bulunamadı"
        )
    
    if meeting.status != "paused":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sadece duraklatılmış toplantılar devam ettirilebilir"
        )
    
    meeting.status = "recording"
    meeting.pause_time = None
    meeting.silence_duration = 0
    db.commit()
    db.refresh(meeting)
    
    return meeting


@router.post("/{meeting_id}/end", response_model=MeetingResponse)
async def end_meeting(
    meeting_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toplantıyı bitir"""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Toplantı bulunamadı"
        )
    
    if meeting.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Toplantı zaten tamamlanmış"
        )
    
    meeting.status = "processing"
    meeting.end_time = datetime.utcnow()
    db.commit()
    
    # Background task ile transkript ve özet oluştur
    from ..services.whisper_service import WhisperService
    from ..services.openai_service import OpenAIService
    import asyncio
    
    def process_meeting():
        if meeting.audio_file_path:
            # Audio preprocessing servisi
            from ..services.audio_preprocessing_service import AudioPreprocessingService
            from ..services.whisper_service import WhisperService
            from ..services.speaker_diarization_service import SpeakerDiarizationService
            
            preprocessing_service = AudioPreprocessingService()
            whisper_service = WhisperService()
            diarization_service = SpeakerDiarizationService()
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                print(f"🔊 Audio preprocessing başlatılıyor: {meeting.audio_file_path}")
                
                # 1. Audio preprocessing (gürültü engelleme, normalizasyon)
                # SpeechRecognition, ElevenLabs ve AssemblyAI için preprocessing'i atlayabiliriz (API'ler kendi işlemlerini yapıyor)
                if meeting.whisper_model == "speechrecognition":
                    print("⚠️  SpeechRecognition için preprocessing atlanıyor (Google API kendi işlemlerini yapıyor)")
                    processed_audio_path = meeting.audio_file_path
                elif meeting.whisper_model == "elevenlabs":
                    print("⚠️  ElevenLabs için preprocessing atlanıyor (ElevenLabs API kendi işlemlerini yapıyor)")
                    processed_audio_path = meeting.audio_file_path
                elif meeting.whisper_model == "assemblyai":
                    print("⚠️  AssemblyAI için preprocessing atlanıyor (AssemblyAI API kendi işlemlerini yapıyor)")
                    processed_audio_path = meeting.audio_file_path
                else:
                    processed_audio_path = preprocessing_service.preprocess_audio(meeting.audio_file_path)
                    print(f"✅ Audio preprocessing tamamlandı: {processed_audio_path}")
                
                # 2. Speaker diarization (konuşmacı ayırt etme) - Pyannote seçeneği
                speaker_segments = []
                use_pyannote_diarization = (
                    meeting.use_pyannote == "true" or 
                    meeting.whisper_model == "pyannote"
                )
                
                # Pyannote diarization kullanılıyorsa
                if use_pyannote_diarization or meeting.whisper_model == "pyannote":
                    print("🎤 Pyannote Diarization başlatılıyor...")
                    try:
                        from ..services.pyannote_diarization_service import PyannoteDiarizationService
                        pyannote_service = PyannoteDiarizationService()
                        
                        # Pyannote ile transkript ve diarization
                        transcripts = pyannote_service.process_with_speakers(
                            processed_audio_path,
                            min_speakers=meeting.min_speakers,
                            max_speakers=meeting.max_speakers,
                            profile=meeting.diarization_profile or "auto"
                        )
                        
                        print(f"✅ {len(transcripts)} transkript segmenti oluşturuldu (Pyannote)")
                        
                        # Veritabanına kaydet
                        db_session = SessionLocal()
                        try:
                            from ..models import Transcript
                            for i, segment in enumerate(transcripts):
                                transcript = Transcript(
                                    meeting_id=meeting.id,
                                    segment_number=i + 1,
                                    text=segment["text"],
                                    start_time=segment["start"],
                                    end_time=segment["end"],
                                    speaker_id=segment.get("speaker_id"),
                                    speaker_label=segment.get("speaker_label")
                                )
                                db_session.add(transcript)
                            
                            updated_meeting = db_session.query(Meeting).filter(Meeting.id == meeting.id).first()
                            if updated_meeting:
                                updated_meeting.status = "completed"
                            db_session.commit()
                            print("✅ Transkriptler veritabanına kaydedildi")
                        finally:
                            db_session.close()
                        
                        return  # Pyannote işlemi tamamlandı, çık
                        
                    except Exception as e:
                        print(f"❌ Pyannote diarization hatası: {e}")
                        import traceback
                        traceback.print_exc()
                        raise
                else:
                    # Normal speaker diarization (eski yöntem)
                    try:
                        print("🎤 Speaker diarization başlatılıyor...")
                        speaker_segments = diarization_service.diarize(processed_audio_path)
                        if speaker_segments:
                            print(f"✅ {len(speaker_segments)} speaker segmenti bulundu")
                        else:
                            print("⚠️  Speaker diarization sonuç vermedi (devam ediliyor)")
                    except Exception as e:
                        print(f"⚠️  Speaker diarization hatası: {e} (devam ediliyor)")
                
                # 3. Transkript oluştur (model tipine göre)
                print(f"📝 Transkript oluşturuluyor (Model: {meeting.whisper_model})...")
                
                # Model tipine göre doğru servisi kullan
                if meeting.whisper_model == "elevenlabs":
                    # ElevenLabs servisi kullan - Kişi ayrımı destekli
                    from ..services.elevenlabs_service import ElevenLabsService
                    elevenlabs_service = ElevenLabsService()
                    # ElevenLabs için speaker diarization her zaman aktif
                    transcripts = loop.run_until_complete(
                        elevenlabs_service.transcribe_audio(
                            processed_audio_path,
                            model_name="elevenlabs",
                            language=meeting.language,
                            enable_speaker_diarization=True,  # ElevenLabs için her zaman aktif
                            speaker_segments=speaker_segments  # Harici diarization sonuçları ile birleştir
                        )
                    )
                elif meeting.whisper_model == "assemblyai":
                    # AssemblyAI servisi kullan - Kişi ayrımı destekli
                    from ..services.assemblyai_service import AssemblyAIService
                    assemblyai_service = AssemblyAIService()
                    # AssemblyAI için speaker diarization aktif
                    transcripts = loop.run_until_complete(
                        assemblyai_service.transcribe_audio(
                            processed_audio_path,
                            model_name="assemblyai",
                            language=meeting.language,
                            enable_speaker_diarization=True,  # AssemblyAI için aktif
                            speaker_segments=speaker_segments  # Harici diarization sonuçları ile birleştir
                        )
                    )
                elif meeting.whisper_model == "speechrecognition":
                    from ..services.speechrecognition_service import SpeechRecognitionService
                    sr_service = SpeechRecognitionService()
                    transcripts = loop.run_until_complete(
                        sr_service.transcribe_audio(
                            processed_audio_path,
                            model_name="google",
                            language=meeting.language,
                            enable_speaker_diarization=len(speaker_segments) > 0,
                            speaker_segments=speaker_segments
                        )
                    )
                else:
                    # Whisper modeli kullan
                    transcripts = loop.run_until_complete(
                        whisper_service.transcribe_audio(
                            processed_audio_path,
                            meeting.whisper_model,
                            meeting.language,
                            enable_speaker_diarization=len(speaker_segments) > 0,
                            speaker_segments=speaker_segments
                        )
                    )
                print(f"✅ {len(transcripts)} transkript segmenti oluşturuldu")
                
                # 4. Veritabanına kaydet
                db_session = SessionLocal()
                try:
                    from ..models import Transcript
                    for i, segment in enumerate(transcripts):
                        print(f"💾 Transkript kaydediliyor - Segment {i+1}: '{segment['text'][:100]}...' ({len(segment['text'])} karakter)")
                        transcript = Transcript(
                            meeting_id=meeting.id,
                            segment_number=i + 1,
                            text=segment["text"],
                            start_time=segment["start"],
                            end_time=segment["end"],
                            speaker_id=segment.get("speaker_id"),
                            speaker_label=segment.get("speaker_label")
                        )
                        db_session.add(transcript)
                    
                    # Toplantıyı tamamla
                    updated_meeting = db_session.query(Meeting).filter(Meeting.id == meeting.id).first()
                    if updated_meeting:
                        updated_meeting.status = "completed"
                    db_session.commit()
                    print("✅ Transkriptler veritabanına kaydedildi")
                finally:
                    db_session.close()
                
                # Temizlik: İşlenmiş audio dosyasını sil (opsiyonel)
                # if processed_audio_path != meeting.audio_file_path:
                #     try:
                #         os.remove(processed_audio_path)
                #     except:
                #         pass
                    
            except Exception as e:
                print(f"❌ Toplantı işleme hatası: {e}")
                import traceback
                traceback.print_exc()
                
                # Hata durumunda meeting'i hata durumuna al
                db_session = SessionLocal()
                try:
                    error_meeting = db_session.query(Meeting).filter(Meeting.id == meeting.id).first()
                    if error_meeting:
                        error_meeting.status = "error"
                    db_session.commit()
                finally:
                    db_session.close()
            finally:
                loop.close()
    
    background_tasks.add_task(process_meeting)
    db.refresh(meeting)
    
    return meeting


@router.get("/", response_model=List[MeetingResponse])
async def get_meetings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kullanıcının toplantılarını listele"""
    meetings = db.query(Meeting).filter(
        Meeting.user_id == current_user.id
    ).order_by(Meeting.created_at.desc()).all()
    
    return meetings


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toplantı detayı"""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Toplantı bulunamadı"
        )
    
    return meeting


@router.post("/{meeting_id}/generate-summary")
async def generate_summary(
    meeting_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toplantı için özet oluştur (manuel)"""
    from ..models import Transcript, Summary
    from ..services.openai_service import OpenAIService
    import asyncio
    
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Toplantı bulunamadı"
        )
    
    # Toplantı tamamlanmış mı kontrol et
    if meeting.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sadece tamamlanmış toplantılar için özet oluşturulabilir"
        )
    
    # Zaten özet var mı kontrol et
    existing_summary = db.query(Summary).filter(Summary.meeting_id == meeting_id).first()
    if existing_summary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu toplantı için zaten özet oluşturulmuş"
        )
    
    # Transkriptleri al
    transcripts = db.query(Transcript).filter(
        Transcript.meeting_id == meeting_id
    ).order_by(Transcript.segment_number).all()
    
    if not transcripts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Toplantı için transkript bulunamadı"
        )
    
    def create_summary():
        """Background task ile özet oluştur"""
        db_session = SessionLocal()
        try:
            full_text = " ".join([t.text for t in transcripts])
            openai_service = OpenAIService()
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                summary_result = loop.run_until_complete(
                    openai_service.summarize_transcript(full_text, meeting.language)
                )
                
                summary = Summary(
                    meeting_id=meeting_id,
                    summary_text=summary_result["summary"],
                    key_points=summary_result["key_points"]
                )
                db_session.add(summary)
                db_session.commit()
            finally:
                loop.close()
        except Exception as e:
            print(f"Özet oluşturma hatası: {str(e)}")
        finally:
            db_session.close()
    
    background_tasks.add_task(create_summary)
    
    return {"message": "Özet oluşturuluyor, lütfen bekleyin..."}


@router.post("/{meeting_id}/cancel")
async def cancel_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """İşlenmekte olan toplantıyı iptal et"""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Toplantı bulunamadı"
        )
    
    # Sadece işlenmekte olan toplantılar iptal edilebilir
    if meeting.status not in ["processing", "recording", "paused"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bu durumda olan toplantılar iptal edilemez: {meeting.status}"
        )
    
    # Toplantıyı iptal et
    meeting.status = "cancelled"
    meeting.end_time = datetime.utcnow()
    db.commit()
    db.refresh(meeting)
    
    return {
        "message": "Toplantı iptal edildi",
        "meeting_id": meeting.id,
        "status": meeting.status
    }



class ProcessFileRequest(BaseModel):
    audio_file_path: str
    whisper_model: str = "small"  # tiny, base, small, medium, large, speechrecognition, elevenlabs, assemblyai, pyannote
    language: str = "tr"
    use_pyannote: bool = False  # Deprecated: use whisper_model="pyannote" instead
    diarization_profile: str = "auto"
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = None
    use_streaming: bool = False  # AssemblyAI için streaming audio kullan (sadece assemblyai modeli için geçerli)


@router.post("/process-file")
async def process_audio_file(
    file_data: ProcessFileRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Dosya yolu ile ses dosyasını işle (Pyannote destekli)"""
    import os
    
    audio_file_path = file_data.audio_file_path
    whisper_model = file_data.whisper_model
    language = file_data.language
    use_pyannote = file_data.use_pyannote
    diarization_profile = file_data.diarization_profile
    min_speakers = file_data.min_speakers
    max_speakers = file_data.max_speakers
    
    # Dosya varlığını kontrol et
    if not os.path.exists(audio_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ses dosyası bulunamadı: {audio_file_path}"
        )
    
    # Yeni toplantı oluştur
    new_meeting = Meeting(
        user_id=current_user.id,
        title=f"Dosya İşleme - {os.path.basename(audio_file_path)}",
        whisper_model="pyannote" if use_pyannote else whisper_model,
        language=language,
        status="processing",
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        audio_file_path=audio_file_path,
        use_pyannote=str(use_pyannote).lower() if use_pyannote else None,
        diarization_profile=diarization_profile,
        min_speakers=min_speakers,
        max_speakers=max_speakers
    )
    
    db.add(new_meeting)
    db.commit()
    db.refresh(new_meeting)
    
    # Background task ile işle
    def process_file():
        import asyncio
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        db_session = SessionLocal()
        
        try:
            # Model tipine göre işleme yap
            model_type = whisper_model if not use_pyannote else "pyannote"
            print(f"🎯 Dosya işleme başlatılıyor - Model: {model_type}, Dosya: {audio_file_path}")
            
            # Pyannote modeli
            if use_pyannote or model_type == "pyannote":
                print(f"🎤 Pyannote ile dosya işleniyor: {audio_file_path}")
                from ..services.pyannote_diarization_service import PyannoteDiarizationService
                pyannote_service = PyannoteDiarizationService()
                
                transcripts = pyannote_service.process_with_speakers(
                    audio_file_path,
                    min_speakers=min_speakers,
                    max_speakers=max_speakers,
                    profile=diarization_profile
                )
                
            # ElevenLabs modeli
            elif model_type == "elevenlabs":
                print(f"🎙️ ElevenLabs ile dosya işleniyor: {audio_file_path}")
                from ..services.elevenlabs_service import ElevenLabsService
                elevenlabs_service = ElevenLabsService()
                
                transcripts = loop.run_until_complete(
                    elevenlabs_service.transcribe_audio(
                        audio_file_path,
                        model_name="elevenlabs",
                        language=language,
                        enable_speaker_diarization=True
                    )
                )
                
            # AssemblyAI modeli
            elif model_type == "assemblyai":
                print(f"🌐 AssemblyAI ile dosya işleniyor: {audio_file_path}")
                from ..services.assemblyai_service import AssemblyAIService
                assemblyai_service = AssemblyAIService()
                
                transcripts = loop.run_until_complete(
                    assemblyai_service.transcribe_audio(
                        audio_file_path,
                        model_name="assemblyai",
                        language=language,
                        enable_speaker_diarization=True
                    )
                )
                
            # SpeechRecognition modeli
            elif model_type == "speechrecognition":
                print(f"🗣️ SpeechRecognition ile dosya işleniyor: {audio_file_path}")
                from ..services.speechrecognition_service import SpeechRecognitionService
                sr_service = SpeechRecognitionService()
                
                transcripts = loop.run_until_complete(
                    sr_service.transcribe_audio(
                        audio_file_path,
                        model_name="google",
                        language=language,
                        enable_speaker_diarization=False
                    )
                )
                
            # Whisper modelleri (tiny, base, small, medium, large)
            else:
                print(f"🎧 Whisper ({model_type}) ile dosya işleniyor: {audio_file_path}")
                from ..services.whisper_service import WhisperService
                whisper_service = WhisperService()
                
                transcripts = loop.run_until_complete(
                    whisper_service.transcribe_audio(
                        audio_file_path,
                        model_type,
                        language
                    )
                )
            
            # Veritabanına kaydet
            from ..models import Transcript
            print(f"💾 {len(transcripts)} transkript segmenti veritabanına kaydediliyor...")
            
            for i, segment in enumerate(transcripts):
                transcript = Transcript(
                    meeting_id=new_meeting.id,
                    segment_number=i + 1,
                    text=segment["text"],
                    start_time=segment["start"],
                    end_time=segment["end"],
                    speaker_id=segment.get("speaker_id"),
                    speaker_label=segment.get("speaker_label")
                )
                db_session.add(transcript)
            
            updated_meeting = db_session.query(Meeting).filter(Meeting.id == new_meeting.id).first()
            if updated_meeting:
                updated_meeting.status = "completed"
            db_session.commit()
            print(f"✅ Dosya işlendi ve kaydedildi - Model: {model_type}")
                
        except Exception as e:
            print(f"❌ Dosya işleme hatası: {e}")
            import traceback
            traceback.print_exc()
            updated_meeting = db_session.query(Meeting).filter(Meeting.id == new_meeting.id).first()
            if updated_meeting:
                updated_meeting.status = "error"
            db_session.commit()
        finally:
            db_session.close()
            loop.close()
    
    background_tasks.add_task(process_file)
    
    return {
        "message": "Dosya işleniyor...",
        "meeting_id": new_meeting.id
    }


class StreamAudioRequest(BaseModel):
    meeting_id: Optional[int] = None  # Mevcut bir meeting'e bağla (opsiyonel)
    duration_seconds: Optional[int] = None  # Maksimum süre (saniye), None ise manuel durdurma
    save_wav: bool = True  # WAV dosyası kaydet
    language: str = "tr"


@router.post("/stream-audio")
async def stream_audio(
    stream_data: StreamAudioRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AssemblyAI Streaming Audio - Gerçek zamanlı ses transkripsiyon
    
    NOT: Bu endpoint streaming başlatır ve hemen döner.
    Transkriptler gerçek zamanlı olarak veritabanına kaydedilir.
    """
    import os
    
    # Meeting kontrolü veya yeni meeting oluştur
    if stream_data.meeting_id:
        meeting = db.query(Meeting).filter(
            Meeting.id == stream_data.meeting_id,
            Meeting.user_id == current_user.id
        ).first()
        
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Toplantı bulunamadı"
            )
        
        if meeting.status not in ["recording", "paused"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sadece kayıt durumundaki toplantılara streaming eklenebilir"
            )
    else:
        # Yeni meeting oluştur
        meeting = Meeting(
            user_id=current_user.id,
            title=f"Streaming Audio - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            whisper_model="assemblyai",
            language=stream_data.language,
            status="recording",
            start_time=datetime.utcnow()
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
    
    # Background task ile streaming başlat
    def start_streaming():
        from ..services.assemblyai_streaming_service import AssemblyAIStreamingService
        from ..models import Transcript
        import asyncio
        
        db_session = SessionLocal()
        transcripts_buffer = []
        segment_counter = 0
        
        try:
            print(f"🎙️ AssemblyAI Streaming başlatılıyor - Meeting ID: {meeting.id}")
            service = AssemblyAIStreamingService()
            
            # Transcript callback'i
            def on_transcript(text: str, is_formatted: bool):
                nonlocal segment_counter
                if is_formatted and text.strip():
                    segment_counter += 1
                    print(f"📝 Transkript alındı (Segment {segment_counter}): {text[:100]}...")
                    
                    # Veritabanına kaydet
                    try:
                        transcript = Transcript(
                            meeting_id=meeting.id,
                            segment_number=segment_counter,
                            text=text,
                            start_time=0.0,  # Streaming'de zaman damgası yok
                            end_time=0.0,
                            speaker_id=None,  # Streaming API'de speaker ID farklı formatta gelebilir
                            speaker_label=None
                        )
                        db_session.add(transcript)
                        db_session.commit()
                        print(f"✅ Transkript kaydedildi (Segment {segment_counter})")
                    except Exception as e:
                        print(f"❌ Transkript kaydetme hatası: {e}")
                        db_session.rollback()
            
            # Session callback'leri
            def on_session_begin(session_id: str, expires_at: int):
                print(f"🟢 Session başladı: {session_id}")
            
            def on_session_end(audio_duration: float, session_duration: float):
                print(f"🔴 Session bitti: {audio_duration}s audio, {session_duration}s toplam")
                
                # Meeting'i tamamla
                try:
                    updated_meeting = db_session.query(Meeting).filter(Meeting.id == meeting.id).first()
                    if updated_meeting:
                        updated_meeting.status = "completed"
                        updated_meeting.end_time = datetime.utcnow()
                    db_session.commit()
                    print(f"✅ Meeting tamamlandı (ID: {meeting.id})")
                except Exception as e:
                    print(f"❌ Meeting güncelleme hatası: {e}")
                    db_session.rollback()
            
            # Callback'leri ayarla
            service.set_transcript_callback(on_transcript)
            service.set_session_callbacks(on_session_begin, on_session_end)
            
            # Streaming'i başlat
            service.start_streaming(duration_seconds=stream_data.duration_seconds)
            
            # WAV dosyasını kaydet
            if stream_data.save_wav:
                # Meeting dizinini oluştur
                meeting_dir = os.path.join("uploads", str(current_user.id), str(meeting.id))
                os.makedirs(meeting_dir, exist_ok=True)
                
                wav_path = os.path.join(meeting_dir, "streaming_audio.wav")
                saved_path = service.save_wav_file(wav_path)
                
                if saved_path:
                    # Meeting'e audio path'i ekle
                    try:
                        updated_meeting = db_session.query(Meeting).filter(Meeting.id == meeting.id).first()
                        if updated_meeting:
                            updated_meeting.audio_file_path = saved_path
                        db_session.commit()
                        print(f"✅ WAV dosyası kaydedildi: {saved_path}")
                    except Exception as e:
                        print(f"❌ Audio path güncelleme hatası: {e}")
                        db_session.rollback()
            
            print(f"✅ Streaming tamamlandı - Meeting ID: {meeting.id}")
            
        except Exception as e:
            print(f"❌ Streaming hatası: {e}")
            import traceback
            traceback.print_exc()
            
            # Hata durumunda meeting'i hata durumuna al
            try:
                error_meeting = db_session.query(Meeting).filter(Meeting.id == meeting.id).first()
                if error_meeting:
                    error_meeting.status = "error"
                db_session.commit()
            except:
                pass
        finally:
            db_session.close()
    
    # Background task'i başlat
    background_tasks.add_task(start_streaming)
    
    return {
        "message": "Streaming başlatılıyor...",
        "meeting_id": meeting.id,
        "info": "Mikrofona konuşun. Transkriptler gerçek zamanlı olarak kaydedilecek."
    }



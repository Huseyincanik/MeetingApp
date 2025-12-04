import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models import Meeting


class AudioService:
    SILENCE_THRESHOLD = 500  # Ses seviyesi eşiği
    SILENCE_DURATION_SECONDS = 15 * 60  # 15 dakika (saniye)
    PAUSE_DURATION_SECONDS = 15 * 60  # 15 dakika pause sonrası
    
    def check_silence(self, audio_path: str, meeting: Meeting):
        """Ses dosyasında sessizlik kontrolü yap"""
        try:
            # WebM dosyasını işle (basit bir kontrol)
            # Gerçek uygulamada daha gelişmiş VAD kullanılabilir
            file_size = os.path.getsize(audio_path)
            
            # Eğer dosya çok küçükse sessizlik olabilir
            if file_size < 1000:  # 1KB altı
                meeting.silence_duration += 20  # Örnek: 20 saniye ekle
            else:
                meeting.silence_duration = 0  # Ses varsa sıfırla
            
            # Eğer 15 dakika sessizlik varsa pause yap
            if meeting.silence_duration >= self.SILENCE_DURATION_SECONDS:
                if meeting.status == "recording":
                    meeting.status = "paused"
                    meeting.pause_time = datetime.utcnow()
            
            # Eğer pause'dan sonra 15 dakika geçtiyse bitir
            if meeting.status == "paused" and meeting.pause_time:
                pause_duration = (datetime.utcnow() - meeting.pause_time).total_seconds()
                if pause_duration >= self.PAUSE_DURATION_SECONDS:
                    meeting.status = "processing"
                    meeting.end_time = datetime.utcnow()
        
        except Exception as e:
            # Hata durumunda sessizlik kontrolünü atla
            print(f"Sessizlik kontrolü hatası: {e}")
    
    def detect_voice_activity(self, audio_data: bytes) -> bool:
        """Ses aktivitesi tespiti (VAD)"""
        try:
            # Basit bir RMS (Root Mean Square) hesaplama
            rms = audioop.rms(audio_data, 2)  # 16-bit sample
            return rms > self.SILENCE_THRESHOLD
        except:
            return False


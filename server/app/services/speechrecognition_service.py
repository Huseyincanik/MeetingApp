import os
import speech_recognition as sr
from typing import List, Dict, Optional
import subprocess
import tempfile
import shutil
import asyncio


class SpeechRecognitionService:
    """Python SpeechRecognition servisi - Google Speech Recognition API kullanır"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        # Ses kalitesi ayarları
        self.recognizer.energy_threshold = 300  # Minimum ses enerjisi
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8  # Duraklama eşiği (saniye)
        self.recognizer.operation_timeout = None  # Timeout yok
    
    def convert_to_wav(self, audio_path: str, output_path: Optional[str] = None) -> str:
        """FFmpeg ile ses dosyasını WAV formatına çevir (SpeechRecognition için)"""
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, 
                         check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("FFmpeg kurulu değil. SpeechRecognition için FFmpeg gerekli.")
        
        if output_path is None:
            output_path = audio_path.rsplit('.', 1)[0] + '_sr.wav'
        
        # FFmpeg ile format dönüşümü - SpeechRecognition için optimize edilmiş
        cmd = [
            'ffmpeg',
            '-i', audio_path,
            '-ar', '16000',  # 16kHz sample rate (SpeechRecognition için önerilen)
            '-ac', '1',  # Mono (tek kanal)
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            '-y',  # Overwrite
            output_path
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    
    async def transcribe_audio(
        self,
        audio_path: str,
        model_name: str = "google",  # SpeechRecognition için model adı (google, sphinx, etc.)
        language: str = "tr-TR",
        enable_speaker_diarization: bool = False,
        speaker_segments: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """Ses dosyasını transkript et - SpeechRecognition kullanarak
        
        Not: Bu fonksiyon async olarak tanımlanmıştır ancak SpeechRecognition
        senkron bir kütüphanedir. Async interface uyumluluğu için async olarak bırakılmıştır.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Ses dosyası bulunamadı: {audio_path}")
        
        # Dosya bilgilerini kontrol et
        file_size = os.path.getsize(audio_path)
        print(f"📊 SpeechRecognition: Dosya boyutu: {file_size} bytes ({file_size / 1024:.2f} KB)")
        
        if file_size < 1000:  # 1KB'dan küçükse
            print("⚠️  SpeechRecognition: Dosya çok küçük, muhtemelen boş")
            return [{
                "text": "",
                "start": 0.0,
                "end": 0.0,
                "speaker_id": None,
                "speaker_label": None
            }]
        
        # Dil kodunu SpeechRecognition formatına çevir
        language_map = {
            "tr": "tr-TR",
            "en": "en-US"
        }
        recognition_language = language_map.get(language, "tr-TR")
        print(f"🌐 SpeechRecognition: Dil: {recognition_language}")
        
        # Geçici WAV dosyası oluştur
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            temp_wav_path = tmp_file.name
        
        try:
            # Ses dosyasını WAV formatına çevir
            print(f"🔄 SpeechRecognition: WAV formatına dönüştürülüyor...")
            if not audio_path.endswith('.wav'):
                wav_path = self.convert_to_wav(audio_path, temp_wav_path)
                print(f"✅ SpeechRecognition: WAV dönüşümü tamamlandı: {wav_path}")
            else:
                # Zaten WAV ise, sample rate'i kontrol et ve optimize et
                wav_path = temp_wav_path
                try:
                    self.convert_to_wav(audio_path, temp_wav_path)
                    print(f"✅ SpeechRecognition: WAV optimize edildi: {wav_path}")
                except Exception as e:
                    print(f"⚠️  SpeechRecognition: WAV optimize hatası: {e}, orijinal dosya kullanılıyor")
                    # Dönüşüm başarısız olursa orijinal dosyayı kopyala
                    shutil.copy(audio_path, temp_wav_path)
            
            # WAV dosya boyutunu kontrol et
            wav_size = os.path.getsize(wav_path)
            print(f"📊 SpeechRecognition: WAV dosya boyutu: {wav_size} bytes ({wav_size / 1024:.2f} KB)")
            
            # AudioFile ile ses dosyasını yükle (async executor'da çalıştır)
            def _load_and_recognize():
                print(f"🎤 SpeechRecognition: Ses dosyası yükleniyor ve işleniyor...")
                with sr.AudioFile(wav_path) as source:
                    # Dosya süresini al
                    duration = source.DURATION
                    print(f"⏱️  SpeechRecognition: Ses süresi: {duration:.2f} saniye")
                    
                    if duration < 0.1:  # 100ms'den kısa ses
                        print("⚠️  SpeechRecognition: Ses çok kısa (< 0.1 saniye)")
                        return None, duration
                    
                    # Gürültü ayarlaması (daha kısa süre, daha az agresif)
                    try:
                        self.recognizer.adjust_for_ambient_noise(source, duration=min(0.5, duration / 2))
                        print(f"🔧 SpeechRecognition: Gürültü ayarlaması yapıldı")
                    except Exception as e:
                        print(f"⚠️  SpeechRecognition: Gürültü ayarlaması hatası: {e}")
                    
                    # Ses dosyasını oku
                    audio_data = self.recognizer.record(source)
                    print(f"✅ SpeechRecognition: Ses verisi okundu")
                
                # Google Speech Recognition kullan (ücretsiz, internet gerekli)
                print(f"🌐 SpeechRecognition: Google API'ye istek gönderiliyor...")
                try:
                    text = self.recognizer.recognize_google(
                        audio_data,
                        language=recognition_language
                    )
                    print(f"✅ SpeechRecognition: Transkript alındı: {len(text)} karakter")
                    print(f"📝 SpeechRecognition: Transkript içeriği: '{text[:200]}...' (ilk 200 karakter)")
                    return text, duration  # Hem text hem de duration döndür
                except sr.UnknownValueError as e:
                    print(f"⚠️  SpeechRecognition: Google API sesi anlayamadı: {e}")
                    raise
                except sr.RequestError as e:
                    print(f"❌ SpeechRecognition: Google API hatası: {e}")
                    raise
            
            # Senkron işlemi async executor'da çalıştır
            audio_duration = 0.0  # Ses süresini sakla
            try:
                try:
                    result = await asyncio.to_thread(_load_and_recognize)
                except AttributeError:
                    # Python < 3.9 için alternatif
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, _load_and_recognize)
                
                # Result None ise veya tuple ise
                if result is None:
                    text = None
                    audio_duration = 0.0
                elif isinstance(result, tuple):
                    text, audio_duration = result
                else:
                    text = result
                    audio_duration = 0.0
                
                # Eğer text None ise (çok kısa ses)
                if text is None:
                    print("⚠️  SpeechRecognition: Ses çok kısa, transkript oluşturulamadı")
                    return [{
                        "text": "",
                        "start": 0.0,
                        "end": 0.0,
                        "speaker_id": None,
                        "speaker_label": None
                    }]
                    
            except sr.UnknownValueError as e:
                # Ses anlaşılamadı
                print(f"⚠️  SpeechRecognition: Ses anlaşılamadı - {e}")
                print("💡 İpucu: Ses kalitesi düşük olabilir veya dosya boş olabilir")
                return [{
                    "text": "",
                    "start": 0.0,
                    "end": 0.0,
                    "speaker_id": None,
                    "speaker_label": None
                }]
            except sr.RequestError as e:
                # API hatası
                error_msg = f"SpeechRecognition API hatası: {e}"
                print(f"❌ {error_msg}")
                print("💡 İpucu: Internet bağlantınızı kontrol edin veya Google API erişim sorununu kontrol edin")
                raise RuntimeError(error_msg)
            except Exception as e:
                print(f"❌ SpeechRecognition: Beklenmeyen hata: {e}")
                import traceback
                traceback.print_exc()
                raise
            
            # Transkript oluştur
            # Tek bir segment olarak döndür (SpeechRecognition tüm dosyayı tek seferde işler)
            # Eğer audio_duration bilinmiyorsa, metin uzunluğundan tahmin et
            if audio_duration <= 0:
                # Tahmini: Türkçe için ortalama 10 karakter/saniye konuşma hızı
                estimated_duration = len(text) / 10.0 if text else 0.0
                audio_duration = estimated_duration
                print(f"⏱️  SpeechRecognition: Ses süresi tahmin edildi: {audio_duration:.2f} saniye")
            
            segments = [{
                "text": text,
                "start": 0.0,
                "end": audio_duration,  # Gerçek veya tahmin edilmiş süre
                "speaker_id": None,
                "speaker_label": None
            }]
            
            print(f"📊 SpeechRecognition: Transkript segmenti oluşturuldu - Başlangıç: 0.0s, Bitiş: {audio_duration:.2f}s")
            
            # Eğer metin uzunsa, cümlelere böl (daha iyi segmentasyon için)
            if len(text) > 100:
                sentences = text.split('. ')
                segments = []
                current_time = 0.0
                estimated_duration_per_char = 0.05  # Tahmini karakter başına süre (saniye)
                
                for i, sentence in enumerate(sentences):
                    if sentence.strip():
                        sentence_duration = len(sentence) * estimated_duration_per_char
                        segments.append({
                            "text": sentence.strip() + ('.' if i < len(sentences) - 1 else ''),
                            "start": current_time,
                            "end": current_time + sentence_duration,
                            "speaker_id": None,
                            "speaker_label": None
                        })
                        current_time += sentence_duration
            
            # Speaker diarization varsa eşleştir
            if enable_speaker_diarization and speaker_segments:
                for segment in segments:
                    for speaker_seg in speaker_segments:
                        if (segment["start"] >= speaker_seg["start"] and 
                            segment["end"] <= speaker_seg["end"]):
                            segment["speaker_id"] = speaker_seg.get("speaker_id")
                            segment["speaker_label"] = speaker_seg.get("speaker_label")
                            break
            
            return segments
                
        finally:
            # Geçici dosyayı temizle
            try:
                if os.path.exists(temp_wav_path):
                    os.remove(temp_wav_path)
            except:
                pass


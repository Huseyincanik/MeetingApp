"""
AssemblyAI Speech-to-Text Service
AssemblyAI Python SDK kullanarak konuşma tanıma ve transkript oluşturma servisi
Kişi ayrımı (speaker diarization) desteği ile profesyonel toplantı transkriptleri

KURULUM:
1. .env dosyasına ASSEMBLYAI_API_KEY ekleyin
2. pip install assemblyai
3. Speech Model: "universal" (varsayılan, diğer modeller de desteklenir)

KİŞİ AYRIMI (SPEAKER DIARIZATION):
- AssemblyAI için speaker diarization otomatik desteklenir (enable_speaker_labels=True)
- API kendi diarization sağlıyor, harici pyannote sonuçları ile birleştirilebilir
"""
import os
import asyncio
from typing import List, Dict, Optional
import assemblyai as aai
from ..config import settings


class AssemblyAIService:
    """AssemblyAI Speech-to-Text servisi - Kişi ayrımı destekli"""
    
    def __init__(self):
        # AssemblyAI API key - config'den veya environment variable'dan alınacak
        self.api_key = settings.assemblyai_api_key or os.getenv("ASSEMBLYAI_API_KEY", "")
        
        if not self.api_key:
            raise RuntimeError("AssemblyAI API key bulunamadı. Lütfen .env dosyasına ASSEMBLYAI_API_KEY ekleyin.")
        
        # AssemblyAI API key'i ayarla
        aai.settings.api_key = self.api_key
        print(f"✅ AssemblyAI client oluşturuldu")
    
    async def transcribe_audio(
        self,
        audio_path: str,
        model_name: str = "assemblyai",
        language: str = "tr",
        enable_speaker_diarization: bool = True,
        speaker_segments: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Ses dosyasını AssemblyAI SDK kullanarak transkript et
        
        Args:
            audio_path: İşlenecek ses dosyası yolu
            model_name: Model adı (assemblyai)
            language: Dil kodu (tr, en) - AssemblyAI otomatik algılar
            enable_speaker_diarization: Kişi ayrımı aktif mi
            speaker_segments: Önceden hesaplanmış konuşmacı segmentleri (opsiyonel)
        
        Returns:
            Transkript segmentleri listesi (speaker bilgisi ile)
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Ses dosyası bulunamadı: {audio_path}")
        
        # Dosya bilgilerini kontrol et
        file_size = os.path.getsize(audio_path)
        print(f"📊 AssemblyAI: Dosya boyutu: {file_size} bytes ({file_size / 1024:.2f} KB)")
        
        if file_size < 1000:  # 1KB'dan küçükse
            print("⚠️  AssemblyAI: Dosya çok küçük, muhtemelen boş")
            return [{
                "text": "",
                "start": 0.0,
                "end": 0.0,
                "speaker_id": None,
                "speaker_label": None
            }]
        
        print(f"🌐 AssemblyAI: Dil: {language} (otomatik algılama)")
        
        try:
            # TranscriptionConfig oluştur
            print(f"📂 AssemblyAI: Ses dosyası okunuyor: {audio_path}")
            print(f"📋 AssemblyAI: Speaker Diarization: {enable_speaker_diarization}")
            
            config = aai.TranscriptionConfig(
                speech_model=aai.SpeechModel.best,  # En iyi kalite için 'best' modeli
                speaker_labels=enable_speaker_diarization,  # Kişi ayrımı
                language_code=language if language in ["tr", "en"] else None,  # Otomatik algılama için None
                punctuate=True,  # Noktalama işaretleri ekle
                format_text=True,  # Metni formatla (büyük harf, vb.)
                language_detection=True,  # Otomatik dil algılama
                # Türkçe için özel ayarlar
                speech_threshold=0.5,  # Konuşma algılama eşiği (0.0-1.0, düşük = daha hassas)
            )
            
            # SDK metodunu async executor'da çalıştır
            def _transcribe():
                transcriber = aai.Transcriber(config=config)
                return transcriber.transcribe(audio_path)
            
            # Senkron SDK metodunu async executor'da çalıştır
            try:
                transcript = await asyncio.to_thread(_transcribe)
            except AttributeError:
                # Python < 3.9 için alternatif
                loop = asyncio.get_event_loop()
                transcript = await loop.run_in_executor(None, _transcribe)
            
            # Hata kontrolü
            if transcript.status == "error":
                error_msg = f"AssemblyAI transcription failed: {transcript.error}"
                print(f"❌ {error_msg}")
                raise RuntimeError(error_msg)
            
            print(f"✅ AssemblyAI: Transkript alındı (Status: {transcript.status})")
            
            # Debug: Transcript objesinin yapısını kontrol et
            print(f"🔍 Debug: Transcript objesi tipi: {type(transcript)}")
            print(f"🔍 Debug: Transcript attributes: {dir(transcript)}")
            print(f"🔍 Debug: Has utterances: {hasattr(transcript, 'utterances')}")
            if hasattr(transcript, 'utterances'):
                print(f"🔍 Debug: Utterances var mı: {transcript.utterances is not None}")
                print(f"🔍 Debug: Utterances tipi: {type(transcript.utterances)}")
                if transcript.utterances:
                    print(f"🔍 Debug: Utterances sayısı: {len(transcript.utterances)}")
                    if len(transcript.utterances) > 0:
                        print(f"🔍 Debug: İlk utterance: {transcript.utterances[0]}")
                        print(f"🔍 Debug: İlk utterance attributes: {dir(transcript.utterances[0]) if hasattr(transcript.utterances[0], '__dict__') else 'N/A'}")
            print(f"🔍 Debug: Has words: {hasattr(transcript, 'words')}")
            if hasattr(transcript, 'words') and transcript.words:
                print(f"🔍 Debug: Words sayısı: {len(transcript.words)}")
                if len(transcript.words) > 0:
                    print(f"🔍 Debug: İlk word: {transcript.words[0]}")
            
            # API yanıtını işle
            segments = self._process_api_response(
                transcript,
                enable_speaker_diarization,
                speaker_segments
            )
            
            return segments
        
        except Exception as e:
            error_msg = f"AssemblyAI işleme hatası: {e}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(error_msg)
    
    def _process_api_response(
        self,
        transcript,
        enable_speaker_diarization: bool,
        speaker_segments: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        AssemblyAI transcript objesini işle ve segmentlere dönüştür
        
        AssemblyAI transcript objesi şu özelliklere sahiptir:
        - transcript.text: Tam metin
        - transcript.utterances: Konuşmacı bazlı segmentler (speaker_labels=True ise)
        - transcript.words: Kelime bazlı zaman damgaları
        """
        segments = []
        
        # Utterances varsa (speaker diarization aktifse) onları kullan
        if enable_speaker_diarization and hasattr(transcript, 'utterances') and transcript.utterances:
            print(f"🎤 AssemblyAI: {len(transcript.utterances)} utterance bulundu")
            for utterance in transcript.utterances:
                # Utterance'dan bilgileri al (dict veya obje olabilir)
                if isinstance(utterance, dict):
                    utterance_text = utterance.get('text', '')
                    utterance_start = utterance.get('start', 0)
                    utterance_end = utterance.get('end', 0)
                    utterance_speaker = utterance.get('speaker', None)
                else:
                    utterance_text = getattr(utterance, 'text', '')
                    utterance_start = getattr(utterance, 'start', 0)
                    utterance_end = getattr(utterance, 'end', 0)
                    # Speaker bilgisi farklı attribute'larda olabilir
                    utterance_speaker = getattr(utterance, 'speaker', None) or getattr(utterance, 'speaker_label', None)
                
                # AssemblyAI utterances için zaman damgaları genelde saniye cinsindendir (milisaniye değil)
                # Ama 100000'den büyükse milisaniye olabilir
                if utterance_start > 100000:
                    start_sec = utterance_start / 1000.0  # Milisaniyeden saniyeye
                else:
                    start_sec = utterance_start
                
                if utterance_end > 100000:
                    end_sec = utterance_end / 1000.0  # Milisaniyeden saniyeye
                else:
                    end_sec = utterance_end
                
                # Speaker ID'yi düzenle - AssemblyAI "A", "B" veya "SPEAKER_00", "SPEAKER_01" formatında olabilir
                if utterance_speaker is not None:
                    speaker_str = str(utterance_speaker)
                    # Eğer "A", "B" gibi harf formatındaysa
                    if len(speaker_str) == 1 and speaker_str.isalpha():
                        speaker_id = f"speaker_{ord(speaker_str) - ord('A')}"
                    # Eğer "SPEAKER_00" formatındaysa
                    elif speaker_str.startswith('SPEAKER_'):
                        speaker_num = speaker_str.replace('SPEAKER_', '').strip()
                        speaker_id = f"speaker_{speaker_num}"
                    # Eğer zaten "speaker_" ile başlıyorsa
                    elif speaker_str.startswith('speaker_'):
                        speaker_id = speaker_str
                    # Diğer durumlar
                    else:
                        speaker_id = f"speaker_{speaker_str}"
                else:
                    speaker_id = None
                
                print(f"🔍 Debug utterance: text='{utterance_text[:50]}...', start={start_sec}, end={end_sec}, speaker={utterance_speaker}, speaker_id={speaker_id}")
                
                segments.append({
                    'text': utterance_text,
                    'start': start_sec,
                    'end': end_sec,
                    'speaker_id': speaker_id,
                    'speaker_label': self._get_speaker_label(speaker_id) if speaker_id else None
                })
        # Utterances yoksa ama words varsa, words'den segment oluştur (speaker bilgisi ile)
        elif hasattr(transcript, 'words') and transcript.words:
            print(f"📝 AssemblyAI: Words'den segment oluşturuluyor ({len(transcript.words)} kelime)")
            # Kelimeleri zaman damgasına göre sırala
            words_list = list(transcript.words)
            
            def get_word_start(w):
                if isinstance(w, dict):
                    return w.get('start', 0)
                return getattr(w, 'start', 0)
            
            words_list.sort(key=get_word_start)
            
            if not words_list:
                # Eğer kelime yoksa ama text varsa, tek segment oluştur
                transcript_text = transcript.text if hasattr(transcript, 'text') else ""
                if transcript_text:
                    segments.append({
                        'text': transcript_text,
                        'start': 0.0,
                        'end': 0.0,
                        'speaker_id': None,
                        'speaker_label': None
                    })
                return segments
            
            # Words'den speaker bilgisi var mı kontrol et
            first_word = words_list[0]
            has_speaker_in_words = False
            if isinstance(first_word, dict):
                has_speaker_in_words = 'speaker' in first_word or 'speaker_label' in first_word
            else:
                has_speaker_in_words = hasattr(first_word, 'speaker') or hasattr(first_word, 'speaker_label')
            
            # Eğer words'de speaker bilgisi varsa, speaker'a göre grupla
            if enable_speaker_diarization and has_speaker_in_words:
                print(f"🎤 AssemblyAI: Words'de speaker bilgisi bulundu, gruplandırılıyor...")
                current_speaker = None
                current_text = []
                current_start = 0.0
                current_end = 0.0
                
                for word in words_list:
                    # Word'dan bilgileri al
                    if isinstance(word, dict):
                        word_text = word.get('text', '')
                        word_start = word.get('start', 0)
                        word_end = word.get('end', 0)
                        word_speaker = word.get('speaker') or word.get('speaker_label')
                    else:
                        word_text = getattr(word, 'text', '')
                        word_start = getattr(word, 'start', 0)
                        word_end = getattr(word, 'end', 0)
                        word_speaker = getattr(word, 'speaker', None) or getattr(word, 'speaker_label', None)
                    
                    # Zaman damgalarını saniyeye çevir (gerekirse)
                    if word_start > 100000:
                        word_start = word_start / 1000.0
                    if word_end > 100000:
                        word_end = word_end / 1000.0
                    
                    # Speaker ID'yi düzenle
                    if word_speaker is not None:
                        speaker_str = str(word_speaker)
                        if len(speaker_str) == 1 and speaker_str.isalpha():
                            speaker_id = f"speaker_{ord(speaker_str) - ord('A')}"
                        elif speaker_str.startswith('SPEAKER_'):
                            speaker_num = speaker_str.replace('SPEAKER_', '').strip()
                            speaker_id = f"speaker_{speaker_num}"
                        elif speaker_str.startswith('speaker_'):
                            speaker_id = speaker_str
                        else:
                            speaker_id = f"speaker_{speaker_str}"
                    else:
                        speaker_id = None
                    
                    # Speaker değişti mi?
                    if speaker_id != current_speaker:
                        # Önceki speaker'ın segmentini kaydet
                        if current_text:
                            segments.append({
                                'text': ' '.join(current_text),
                                'start': current_start,
                                'end': current_end,
                                'speaker_id': current_speaker,
                                'speaker_label': self._get_speaker_label(current_speaker) if current_speaker else None
                            })
                        # Yeni speaker başlat
                        current_speaker = speaker_id
                        current_text = [word_text] if word_text else []
                        current_start = word_start
                        current_end = word_end
                    else:
                        # Aynı speaker devam ediyor
                        if word_text:
                            current_text.append(word_text)
                        current_end = word_end
                
                # Son segmenti ekle
                if current_text:
                    segments.append({
                        'text': ' '.join(current_text),
                        'start': current_start,
                        'end': current_end,
                        'speaker_id': current_speaker,
                        'speaker_label': self._get_speaker_label(current_speaker) if current_speaker else None
                    })
            else:
                # Speaker bilgisi yok, tüm kelimeleri birleştir
                first_word = words_list[0]
                last_word = words_list[-1]
                
                # Zaman damgalarını al
                if isinstance(first_word, dict):
                    first_start = first_word.get('start', 0)
                    last_end = last_word.get('end', 0)
                else:
                    first_start = getattr(first_word, 'start', 0)
                    last_end = getattr(last_word, 'end', 0)
                
                # Milisaniye ise saniyeye çevir
                start_time = first_start / 1000.0 if first_start > 100000 else first_start
                end_time = last_end / 1000.0 if last_end > 100000 else (last_end if last_end > 0 else start_time + 1.0)
                
                # Tüm kelimeleri birleştir
                text_parts = []
                for word in words_list:
                    word_text = word.get('text', '') if isinstance(word, dict) else getattr(word, 'text', '')
                    if word_text:
                        text_parts.append(word_text)
                
                transcript_text = transcript.text if hasattr(transcript, 'text') else ""
                full_text = ' '.join(text_parts) if text_parts else transcript_text
                
                segments.append({
                    'text': full_text,
                    'start': start_time,
                    'end': end_time,
                    'speaker_id': None,
                    'speaker_label': None
                })
        # Hiçbiri yoksa ama text varsa
        elif hasattr(transcript, 'text') and transcript.text:
            print(f"📄 AssemblyAI: Tek metin segmenti oluşturuluyor")
            segments.append({
                'text': transcript.text,
                'start': 0.0,
                'end': 0.0,
                'speaker_id': None,
                'speaker_label': None
            })
        else:
            print("⚠️  AssemblyAI: Hiç transkript verisi bulunamadı")
            return []
        
        # Eğer speaker_segments varsa ve API'den speaker bilgisi gelmemişse, eşleştir
        if enable_speaker_diarization and speaker_segments and not any(seg.get("speaker_id") for seg in segments):
            print("🔄 AssemblyAI: Harici speaker diarization sonuçları ile eşleştiriliyor...")
            for segment in segments:
                for speaker_seg in speaker_segments:
                    if (segment["start"] >= speaker_seg["start"] and 
                        segment["end"] <= speaker_seg["end"]):
                        segment["speaker_id"] = speaker_seg.get("speaker_id")
                        segment["speaker_label"] = speaker_seg.get("speaker_label")
                        break
        
        # Speaker bilgisi yoksa ve diarization aktifse, label'ları oluştur
        if enable_speaker_diarization:
            for segment in segments:
                if segment.get("speaker_id") and not segment.get("speaker_label"):
                    segment["speaker_label"] = self._get_speaker_label(segment["speaker_id"])
        
        print(f"✅ AssemblyAI: {len(segments)} transkript segmenti oluşturuldu")
        return segments
    
    def _get_speaker_label(self, speaker_id: str) -> str:
        """Speaker ID'yi okunabilir etikete çevir"""
        if not speaker_id or speaker_id == 'speaker_unknown':
            return None
        
        try:
            # speaker_0, speaker_1 formatı
            if speaker_id.startswith('speaker_'):
                speaker_num = int(speaker_id.split('_')[1])
                return f"Konuşmacı {speaker_num + 1}"
            # Direkt sayı
            elif speaker_id.isdigit():
                return f"Konuşmacı {int(speaker_id) + 1}"
            else:
                return speaker_id
        except:
            return speaker_id


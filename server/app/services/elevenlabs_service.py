"""
ElevenLabs Speech-to-Text Service
ElevenLabs Python SDK kullanarak konuşma tanıma ve transkript oluşturma servisi
Kişi ayrımı (speaker diarization) desteği ile profesyonel toplantı transkriptleri

KURULUM:
1. .env dosyasına ELEVENLABS_API_KEY ekleyin
2. pip install elevenlabs
3. Model ID: "scribe_v1" (şu an için tek desteklenen model)

KİŞİ AYRIMI (SPEAKER DIARIZATION):
- ElevenLabs için speaker diarization varsayılan olarak aktif (diarize=True)
- Multi-channel modunda diarize=False olmalı (her kanal zaten bir konuşmacı)
- API kendi diarization sağlıyor, harici pyannote sonuçları ile birleştirilebilir
"""
import os
import asyncio
from io import BytesIO
from typing import List, Dict, Optional
from elevenlabs.client import ElevenLabs
from ..config import settings


class ElevenLabsService:
    """ElevenLabs Speech-to-Text servisi - Kişi ayrımı destekli"""
    
    def __init__(self):
        # ElevenLabs API key - config'den veya environment variable'dan alınacak
        self.api_key = settings.elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY", "")
        self.model_id = settings.elevenlabs_model_id or os.getenv("ELEVENLABS_MODEL_ID", "scribe_v1")
        
        if not self.api_key:
            raise RuntimeError("ElevenLabs API key bulunamadı. Lütfen .env dosyasına ELEVENLABS_API_KEY ekleyin.")
        
        # ElevenLabs client oluştur
        self.client = ElevenLabs(api_key=self.api_key)
        print(f"✅ ElevenLabs client oluşturuldu (Model: {self.model_id})")
    
    def _get_language_code(self, language: str) -> Optional[str]:
        """Dil kodunu ElevenLabs formatına çevir"""
        language_map = {
            "tr": "tur",  # Türkçe
            "en": "eng",  # İngilizce
        }
        return language_map.get(language, None)  # None = otomatik algılama
    
    async def transcribe_audio(
        self,
        audio_path: str,
        model_name: str = "elevenlabs",
        language: str = "tr",
        enable_speaker_diarization: bool = True,  # ElevenLabs için varsayılan olarak aktif
        speaker_segments: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Ses dosyasını ElevenLabs SDK kullanarak transkript et
        
        Args:
            audio_path: İşlenecek ses dosyası yolu
            model_name: Model adı (elevenlabs)
            language: Dil kodu (tr, en)
            enable_speaker_diarization: Kişi ayrımı aktif mi
            speaker_segments: Önceden hesaplanmış konuşmacı segmentleri (opsiyonel)
        
        Returns:
            Transkript segmentleri listesi (speaker bilgisi ile)
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Ses dosyası bulunamadı: {audio_path}")
        
        # Dosya bilgilerini kontrol et
        file_size = os.path.getsize(audio_path)
        print(f"📊 ElevenLabs: Dosya boyutu: {file_size} bytes ({file_size / 1024:.2f} KB)")
        
        if file_size < 1000:  # 1KB'dan küçükse
            print("⚠️  ElevenLabs: Dosya çok küçük, muhtemelen boş")
            return [{
                "text": "",
                "start": 0.0,
                "end": 0.0,
                "speaker_id": None,
                "speaker_label": None
            }]
        
        # Dil kodunu ElevenLabs formatına çevir
        language_code = self._get_language_code(language)
        print(f"🌐 ElevenLabs: Dil: {language} -> {language_code or 'otomatik algılama'}")
        
        try:
            # Ses dosyasını oku
            print(f"📂 ElevenLabs: Ses dosyası okunuyor: {audio_path}")
            with open(audio_path, 'rb') as audio_file:
                audio_data = BytesIO(audio_file.read())
            
            # ElevenLabs API'ye istek gönder
            print(f"🌐 ElevenLabs: API'ye istek gönderiliyor...")
            print(f"📋 ElevenLabs: Model ID: {self.model_id}, Diarization: {enable_speaker_diarization}")
            
            # SDK metodunu async executor'da çalıştır
            def _transcribe():
                return self.client.speech_to_text.convert(
                    file=audio_data,
                    model_id=self.model_id,
                    tag_audio_events=True,  # Ses olaylarını etiketle (gülme, alkış vb.)
                    language_code=language_code,  # None ise otomatik algılama
                    diarize=enable_speaker_diarization,  # Kişi ayrımı
                    timestamps_granularity='word'  # Kelime bazlı zaman damgaları
                )
            
            # Senkron SDK metodunu async executor'da çalıştır
            try:
                transcription = await asyncio.to_thread(_transcribe)
            except AttributeError:
                # Python < 3.9 için alternatif
                loop = asyncio.get_event_loop()
                transcription = await loop.run_in_executor(None, _transcribe)
            
            print(f"✅ ElevenLabs: Transkript alındı")
            
            # API yanıtını işle
            segments = self._process_api_response(
                transcription, 
                enable_speaker_diarization,
                speaker_segments
            )
            
            return segments
        
        except Exception as e:
            error_msg = f"ElevenLabs işleme hatası: {e}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(error_msg)
    
    def _process_api_response(
        self,
        transcription_response,
        enable_speaker_diarization: bool,
        speaker_segments: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        ElevenLabs API yanıtını işle ve segmentlere dönüştür
        
        ElevenLabs API'si SpeechToTextChunkResponseModel döndürür:
        - transcription.text: Tam metin
        - transcription.words: Kelime listesi (word objeleri)
        - transcription.channel_index: Kanal index'i (multi-channel için)
        - Her word: text, start, end, speaker_id (varsa), type
        """
        all_words = []
        
        # Result formatını kontrol et
        # ElevenLabs API'si farklı formatlar döndürebilir:
        # 1. Tek bir SpeechToTextChunkResponseModel objesi (text, words direkt)
        # 2. Dict formatında {'transcripts': [...]}
        # 3. Liste formatında [transcript1, transcript2, ...]
        
        transcripts = []
        
        if isinstance(transcription_response, list):
            # Liste formatında
            transcripts = transcription_response
        elif isinstance(transcription_response, dict):
            # Dict formatında
            if 'transcripts' in transcription_response:
                transcripts = transcription_response['transcripts']
            elif 'words' in transcription_response:
                # Tek bir transcript dict formatında
                transcripts = [transcription_response]
            else:
                transcripts = []
        else:
            # Obje formatında (SpeechToTextChunkResponseModel)
            # Eğer 'transcripts' attribute'u varsa kullan
            if hasattr(transcription_response, 'transcripts') and transcription_response.transcripts:
                transcripts = transcription_response.transcripts
            elif hasattr(transcription_response, 'words') or hasattr(transcription_response, 'text'):
                # Tek bir transcript objesi - direkt kullan
                transcripts = [transcription_response]
            else:
                transcripts = []
        
        # Eğer transcripts boşsa, hata mesajı ver
        if not transcripts:
            print("⚠️  Transcripts boş! Result yapısını kontrol ediyorum...")
            print(f"   Result tipi: {type(transcription_response)}")
            if hasattr(transcription_response, '__dict__'):
                print(f"   Result attributes: {transcription_response.__dict__.keys()}")
            return []
        
        # Tüm kanallardan kelimeleri topla
        for transcript in transcripts:
            # Transcript dict veya obje olabilir
            if isinstance(transcript, dict):
                channel_index = transcript.get('channel_index', 0)
                words = transcript.get('words', [])
            else:
                channel_index = getattr(transcript, 'channel_index', 0)
                words = getattr(transcript, 'words', []) or []
            
            if not words:
                print(f"⚠️  Transcript'te kelime bulunamadı (channel: {channel_index})")
                continue
            
            for word in words:
                # Word dict veya obje olabilir
                if isinstance(word, dict):
                    word_type = word.get('type', 'word')
                    word_text = word.get('text', '')
                    word_start = word.get('start', 0)
                    word_end = word.get('end', 0)
                    word_speaker_id = word.get('speaker_id', None)
                else:
                    word_type = getattr(word, 'type', 'word')
                    word_text = getattr(word, 'text', '')
                    word_start = getattr(word, 'start', 0)
                    word_end = getattr(word, 'end', 0)
                    word_speaker_id = getattr(word, 'speaker_id', None)
                
                # Sadece 'word' tipinde olanları al
                if word_type == 'word' and word_text:
                    # Multi-channel modunda speaker_id kanal index'ine göre atanır
                    speaker_id = word_speaker_id
                    # Eğer speaker_id yoksa ama channel varsa, channel'ı speaker olarak kullan
                    if speaker_id is None and channel_index is not None:
                        speaker_id = f"channel_{channel_index}"
                    # Eğer hala speaker_id yoksa, varsayılan speaker kullan
                    if speaker_id is None:
                        speaker_id = "speaker_0"
                    
                    all_words.append({
                        'text': word_text,
                        'start': word_start,
                        'end': word_end,
                        'speaker_id': speaker_id,
                        'channel': channel_index
                    })
        
        if not all_words:
            print("⚠️  Hiç kelime bulunamadı! Transkript boş olabilir.")
            return []
        
        # Zaman damgasına göre sırala
        all_words.sort(key=lambda w: w['start'])
        
        # Konuşmacıya göre ardışık kelimeleri grupla (segmentlere dönüştür)
        segments = []
        current_speaker = None
        current_text = []
        current_start_time = 0.0
        current_end_time = 0.0
        
        for word in all_words:
            speaker = word['speaker_id'] if word['speaker_id'] is not None else 'speaker_unknown'
            
            # Konuşmacı değişti mi?
            if speaker != current_speaker:
                # Önceki konuşmacının segmentini kaydet
                if current_text:
                    segments.append({
                        'text': ' '.join(current_text),
                        'start': current_start_time,
                        'end': current_end_time,
                        'speaker_id': current_speaker,
                        'speaker_label': self._get_speaker_label(current_speaker)
                    })
                # Yeni konuşmacı başlat
                current_speaker = speaker
                current_text = [word['text']]
                current_start_time = word['start']
                current_end_time = word['end']
            else:
                # Aynı konuşmacı devam ediyor
                current_text.append(word['text'])
                current_end_time = word['end']  # Son kelimenin bitiş zamanını güncelle
        
        # Son konuşmacının segmentini ekle
        if current_text:
            segments.append({
                'text': ' '.join(current_text),
                'start': current_start_time,
                'end': current_end_time,
                'speaker_id': current_speaker,
                'speaker_label': self._get_speaker_label(current_speaker)
            })
        
        # Eğer speaker_segments varsa ve API'den speaker bilgisi gelmemişse, eşleştir
        if enable_speaker_diarization and speaker_segments and not any(seg.get("speaker_id") for seg in segments):
            print("🔄 ElevenLabs: Harici speaker diarization sonuçları ile eşleştiriliyor...")
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
        
        print(f"✅ ElevenLabs: {len(segments)} transkript segmenti oluşturuldu")
        return segments
    
    def _get_speaker_label(self, speaker_id: str) -> str:
        """Speaker ID'yi okunabilir etikete çevir"""
        if not speaker_id or speaker_id == 'speaker_unknown':
            return None
        
        try:
            # channel_0, channel_1 formatı
            if speaker_id.startswith('channel_'):
                channel_num = int(speaker_id.split('_')[1])
                return f"Konuşmacı {channel_num + 1}"
            # speaker_0, speaker_1 formatı
            elif speaker_id.startswith('speaker_'):
                speaker_num = int(speaker_id.split('_')[1])
                return f"Konuşmacı {speaker_num + 1}"
            # Direkt sayı
            elif speaker_id.isdigit():
                return f"Konuşmacı {int(speaker_id) + 1}"
            else:
                return speaker_id
        except:
            return speaker_id

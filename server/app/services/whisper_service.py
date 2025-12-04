import whisper
import os
import torch
import numpy as np
from typing import List, Dict, Optional
from ..config import settings


class WhisperService:
    def __init__(self):
        self.models_cache = {}
        # GPU kullanılabilirliğini kontrol et
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Whisper device: {self.device}")
    
    def load_model(self, model_name: str = "small"):
        """Whisper modelini yükle veya cache'den al"""
        if model_name not in self.models_cache:
            # Model dosyasının varlığını kontrol et
            model_file = os.path.join(settings.models_dir, f"{model_name}.pt")
            
            if os.path.exists(model_file):
                # Model zaten indirilmiş, dosyadan yükle
                print(f"Model yükleniyor: {model_file} (Device: {self.device})")
                model = whisper.load_model(model_name, device=self.device, download_root=settings.models_dir)
            else:
                # Model yok, indir
                print(f"Model indiriliyor: {model_name} (Device: {self.device})")
                os.makedirs(settings.models_dir, exist_ok=True)
                model = whisper.load_model(model_name, device=self.device, download_root=settings.models_dir)
            
            self.models_cache[model_name] = model
        return self.models_cache[model_name]
    
    async def transcribe_audio(
        self,
        audio_path: str,
        model_name: str = "small",
        language: str = "tr",
        enable_speaker_diarization: bool = False,
        speaker_segments: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """Ses dosyasını transkript et - Optimize edilmiş parametrelerle"""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Ses dosyası bulunamadı: {audio_path}")
        
        # Model yükle
        model = self.load_model(model_name)
        
        # Optimize edilmiş transkript parametreleri
        transcribe_options = {
            "language": language if language != "tr" else None,  # Whisper otomatik TR algılar
            "verbose": False,
            "fp16": torch.cuda.is_available(),  # GPU varsa FP16 kullan (daha hızlı)
            "beam_size": 5,  # Beam search boyutu (daha hızlı için düşürülebilir)
            "best_of": 5,  # Best of sayısı
            "temperature": 0.0,  # Deterministik çıktı için 0
            "compression_ratio_threshold": 2.4,  # Kompresyon oranı eşiği
            "logprob_threshold": -1.0,  # Log probability eşiği
            "no_speech_threshold": 0.6,  # Sessizlik eşiği
            "condition_on_previous_text": True,  # Önceki metni kullan
            "initial_prompt": "Bu bir toplantı kaydıdır. Konuşmacılar Türkçe konuşmaktadır." if language == "tr" else None,
        }
        
        # Transkript oluştur
        result = model.transcribe(audio_path, **transcribe_options)
        
        # Segmentleri döndür ve speaker bilgisi ekle
        segments = []
        for i, segment in enumerate(result["segments"]):
            segment_data = {
                "text": segment["text"].strip(),
                "start": segment["start"],
                "end": segment["end"],
                "speaker_id": None,
                "speaker_label": None
            }
            
            # Speaker diarization varsa eşleştir
            if enable_speaker_diarization and speaker_segments:
                # Bu segmentin hangi konuşmacıya ait olduğunu bul
                for speaker_seg in speaker_segments:
                    if (segment["start"] >= speaker_seg["start"] and 
                        segment["end"] <= speaker_seg["end"]):
                        segment_data["speaker_id"] = speaker_seg.get("speaker_id")
                        segment_data["speaker_label"] = speaker_seg.get("speaker_label")
                        break
            
            segments.append(segment_data)
        
        return segments

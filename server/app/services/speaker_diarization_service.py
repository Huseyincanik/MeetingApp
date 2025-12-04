import os
from typing import List, Dict, Optional
from pyannote.audio import Pipeline
import torch
import torchaudio
from ..config import settings


class SpeakerDiarizationService:
    """Konuşmacı diarization servisi - kim konuşuyor?"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipeline = None
        self.hf_token = os.getenv("HF_TOKEN", "")  # HuggingFace token
        
        # Model cache klasörü
        self.model_cache_dir = os.path.join(settings.models_dir, "pyannote")
        os.makedirs(self.model_cache_dir, exist_ok=True)
    
    def load_pipeline(self):
        """Speaker diarization pipeline'ını yükle"""
        if self.pipeline is None:
            try:
                # Pyannote.audio pipeline'ını yükle
                # Not: HuggingFace token gerekebilir (ücretsiz kayıt olabilirsiniz)
                if self.hf_token:
                    self.pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        use_auth_token=self.hf_token,
                        cache_dir=self.model_cache_dir
                    )
                else:
                    # Alternatif: Yerel model kullan (eğer varsa)
                    model_path = os.path.join(self.model_cache_dir, "speaker-diarization")
                    if os.path.exists(model_path):
                        self.pipeline = Pipeline.from_pretrained(model_path)
                    else:
                        print("⚠️  HuggingFace token bulunamadı. Speaker diarization devre dışı.")
                        print("    Ücretsiz token almak için: https://huggingface.co/settings/tokens")
                        return None
                
                self.pipeline.to(torch.device(self.device))
                print(f"Speaker diarization pipeline yüklendi (Device: {self.device})")
                
            except Exception as e:
                print(f"Speaker diarization pipeline yükleme hatası: {e}")
                print("⚠️  Speaker diarization devre dışı bırakıldı.")
                return None
        
        return self.pipeline
    
    def diarize(self, audio_path: str) -> List[Dict]:
        """Ses dosyasında konuşmacı diarization yap"""
        pipeline = self.load_pipeline()
        
        if pipeline is None:
            return []
        
        try:
            # Diarization yap
            diarization = pipeline(audio_path)
            
            # Sonuçları formatla
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker_id": speaker,
                    "speaker_label": self._get_speaker_label(speaker)
                })
            
            return segments
            
        except Exception as e:
            print(f"Speaker diarization hatası: {e}")
            return []
    
    def _get_speaker_label(self, speaker_id: str) -> str:
        """Speaker ID'yi okunabilir etikete çevir"""
        # SPEAKER_00 -> Konuşmacı 1, SPEAKER_01 -> Konuşmacı 2 vb.
        try:
            speaker_num = int(speaker_id.split("_")[-1])
            return f"Konuşmacı {speaker_num + 1}"
        except:
            return speaker_id
    
    def merge_with_transcripts(self, 
                              transcript_segments: List[Dict],
                              speaker_segments: List[Dict]) -> List[Dict]:
        """Transkript segmentlerini konuşmacı segmentleriyle birleştir"""
        merged_segments = []
        
        for transcript_seg in transcript_segments:
            # Bu transkript segmentinin hangi konuşmacıya ait olduğunu bul
            speaker_info = self._find_speaker_for_segment(
                transcript_seg["start"],
                transcript_seg["end"],
                speaker_segments
            )
            
            transcript_seg["speaker_id"] = speaker_info.get("speaker_id")
            transcript_seg["speaker_label"] = speaker_info.get("speaker_label")
            merged_segments.append(transcript_seg)
        
        return merged_segments
    
    def _find_speaker_for_segment(self, 
                                  start: float, 
                                  end: float,
                                  speaker_segments: List[Dict]) -> Dict:
        """Belirli bir zaman aralığı için konuşmacı bilgisini bul"""
        # En fazla örtüşen konuşmacı segmentini bul
        best_match = None
        max_overlap = 0
        
        for speaker_seg in speaker_segments:
            # Örtüşme hesapla
            overlap_start = max(start, speaker_seg["start"])
            overlap_end = min(end, speaker_seg["end"])
            overlap_duration = max(0, overlap_end - overlap_start)
            
            if overlap_duration > max_overlap:
                max_overlap = overlap_duration
                best_match = speaker_seg
        
        if best_match:
            return {
                "speaker_id": best_match["speaker_id"],
                "speaker_label": best_match["speaker_label"]
            }
        
        return {"speaker_id": None, "speaker_label": None}


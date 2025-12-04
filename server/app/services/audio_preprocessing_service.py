import os
import numpy as np
import librosa
import soundfile as sf
import noisereduce as nr
from typing import Optional, Tuple
import subprocess
import tempfile
import shutil


class AudioPreprocessingService:
    """Audio preprocessing servisi - gürültü engelleme ve ses iyileştirme"""
    
    def __init__(self):
        self.sample_rate = 16000  # Whisper için önerilen sample rate
    
    def check_ffmpeg(self) -> bool:
        """FFmpeg'in kurulu olup olmadığını kontrol et"""
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, 
                         check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def convert_to_wav(self, input_path: str, output_path: Optional[str] = None) -> str:
        """FFmpeg ile ses dosyasını WAV formatına çevir"""
        if not self.check_ffmpeg():
            raise RuntimeError("FFmpeg kurulu değil. Lütfen FFmpeg'i kurun.")
        
        if output_path is None:
            output_path = input_path.rsplit('.', 1)[0] + '.wav'
        
        # FFmpeg ile format dönüşümü ve optimize etme
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-ar', str(self.sample_rate),  # Sample rate
            '-ac', '1',  # Mono (tek kanal)
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            '-y',  # Overwrite
            output_path
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    
    def reduce_noise(self, audio_path: str, output_path: Optional[str] = None) -> str:
        """Gürültü engelleme (noise reduction)"""
        try:
            # Ses dosyasını yükle
            audio, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # Gürültü engelleme uygula
            # Stationary noise reduction (arka plan gürültüsü)
            reduced_noise = nr.reduce_noise(
                y=audio,
                sr=sr,
                stationary=True,
                prop_decrease=0.8  # Gürültüyü %80 azalt
            )
            
            # Non-stationary noise reduction (geçici gürültüler)
            reduced_noise = nr.reduce_noise(
                y=reduced_noise,
                sr=sr,
                stationary=False,
                prop_decrease=0.6
            )
            
            # Çıktı dosyasını kaydet
            if output_path is None:
                output_path = audio_path.rsplit('.', 1)[0] + '_denoised.wav'
            
            sf.write(output_path, reduced_noise, sr)
            return output_path
            
        except Exception as e:
            print(f"Gürültü engelleme hatası: {e}")
            # Hata durumunda orijinal dosyayı döndür
            return audio_path
    
    def normalize_audio(self, audio_path: str, output_path: Optional[str] = None) -> str:
        """Ses normalizasyonu - ses seviyesini optimize et"""
        try:
            # Ses dosyasını yükle
            audio, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # Normalize et (peak normalization)
            audio_normalized = librosa.util.normalize(audio)
            
            # Çıktı dosyasını kaydet
            if output_path is None:
                output_path = audio_path.rsplit('.', 1)[0] + '_normalized.wav'
            
            sf.write(output_path, audio_normalized, sr)
            return output_path
            
        except Exception as e:
            print(f"Ses normalizasyonu hatası: {e}")
            return audio_path
    
    def remove_silence(self, audio_path: str, output_path: Optional[str] = None) -> str:
        """Sessizlik bölümlerini kaldır"""
        try:
            # Ses dosyasını yükle
            audio, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # Trim silence (başındaki ve sonundaki sessizliği kaldır)
            audio_trimmed, _ = librosa.effects.trim(
                audio,
                top_db=20,  # 20 dB altındaki sesleri sessizlik kabul et
                frame_length=2048,
                hop_length=512
            )
            
            # Çıktı dosyasını kaydet
            if output_path is None:
                output_path = audio_path.rsplit('.', 1)[0] + '_trimmed.wav'
            
            sf.write(output_path, audio_trimmed, sr)
            return output_path
            
        except Exception as e:
            print(f"Sessizlik kaldırma hatası: {e}")
            return audio_path
    
    def preprocess_audio(self, audio_path: str, output_path: Optional[str] = None) -> str:
        """Tüm preprocessing işlemlerini uygula"""
        try:
            # Geçici dosya için tempfile kullan
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                temp_path = tmp_file.name
            
            # 1. Format dönüşümü (FFmpeg ile)
            if not audio_path.endswith('.wav'):
                temp_path = self.convert_to_wav(audio_path, temp_path)
            else:
                # Eğer zaten WAV ise, sample rate'i kontrol et ve gerekirse dönüştür
                audio, sr = librosa.load(audio_path, sr=None)
                if sr != self.sample_rate:
                    temp_path = self.convert_to_wav(audio_path, temp_path)
                else:
                    import shutil
                    shutil.copy(audio_path, temp_path)
            
            # 2. Ses normalizasyonu
            temp_path = self.normalize_audio(temp_path, temp_path)
            
            # 3. Gürültü engelleme
            temp_path = self.reduce_noise(temp_path, temp_path)
            
            # 4. Sessizlik kaldırma (opsiyonel - çok agresif olabilir)
            # temp_path = self.remove_silence(temp_path, temp_path)
            
            # Final çıktı dosyası
            if output_path is None:
                output_path = audio_path.rsplit('.', 1)[0] + '_processed.wav'
            
            import shutil
            shutil.move(temp_path, output_path)
            
            return output_path
            
        except Exception as e:
            print(f"Audio preprocessing hatası: {e}")
            # Hata durumunda orijinal dosyayı döndür
            return audio_path


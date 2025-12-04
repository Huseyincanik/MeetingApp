"""
AssemblyAI Streaming Audio Service
Gerçek zamanlı ses transkripsiyon servisi - WebSocket kullanarak

KURULUM:
1. pip install websocket-client pyaudio
2. .env dosyasında ASSEMBLYAI_API_KEY tanımlı olmalı

KULLANIM:
- Gerçek zamanlı mikrofon transkripsiyon
- WebSocket üzerinden audio streaming
- Konuşmacı ayrımı desteği (format_turns=True)
- Otomatik WAV dosyası kaydetme
"""
import os
import json
import threading
import time
import wave
from typing import Optional, Callable, List
from urllib.parse import urlencode
from datetime import datetime
import pyaudio
import websocket

from ..config import settings


class AssemblyAIStreamingService:
    """AssemblyAI Streaming Audio servisi - Gerçek zamanlı transkripsiyon"""
    
    # Audio Configuration
    FRAMES_PER_BUFFER = 800  # 50ms of audio (0.05s * 16000Hz)
    SAMPLE_RATE = 16000
    CHANNELS = 1
    FORMAT = pyaudio.paInt16
    
    def __init__(self):
        # AssemblyAI API key
        self.api_key = settings.assemblyai_api_key or os.getenv("ASSEMBLYAI_API_KEY", "")
        
        if not self.api_key:
            raise RuntimeError("AssemblyAI API key bulunamadı. Lütfen .env dosyasına ASSEMBLYAI_API_KEY ekleyin.")
        
        # Connection parameters
        self.connection_params = {
            "sample_rate": self.SAMPLE_RATE,
            "format_turns": True  # Konuşmacı ayrımı için
        }
        
        # API endpoint
        api_endpoint_base_url = "wss://streaming.assemblyai.com/v3/ws"
        self.api_endpoint = f"{api_endpoint_base_url}?{urlencode(self.connection_params)}"
        
        # Global variables
        self.audio = None
        self.stream = None
        self.ws_app = None
        self.audio_thread = None
        self.stop_event = threading.Event()
        
        # WAV recording
        self.recorded_frames = []
        self.recording_lock = threading.Lock()
        
        # Callbacks
        self.on_transcript_callback: Optional[Callable] = None
        self.on_session_begin_callback: Optional[Callable] = None
        self.on_session_end_callback: Optional[Callable] = None
        
        print("✅ AssemblyAI Streaming Service oluşturuldu")
    
    def set_transcript_callback(self, callback: Callable[[str, bool], None]):
        """
        Transkript callback'i ayarla
        
        Args:
            callback: (transcript_text: str, is_formatted: bool) -> None
        """
        self.on_transcript_callback = callback
    
    def set_session_callbacks(
        self,
        on_begin: Optional[Callable[[str, int], None]] = None,
        on_end: Optional[Callable[[float, float], None]] = None
    ):
        """
        Session callback'lerini ayarla
        
        Args:
            on_begin: (session_id: str, expires_at: int) -> None
            on_end: (audio_duration: float, session_duration: float) -> None
        """
        self.on_session_begin_callback = on_begin
        self.on_session_end_callback = on_end
    
    def _on_open(self, ws):
        """WebSocket bağlantısı açıldığında"""
        print("WebSocket connection opened.")
        print(f"Connected to: {self.api_endpoint}")
        
        # Audio streaming thread'i başlat
        def stream_audio():
            print("Starting audio streaming...")
            while not self.stop_event.is_set():
                try:
                    audio_data = self.stream.read(self.FRAMES_PER_BUFFER, exception_on_overflow=False)
                    
                    # Audio data'yı kaydet
                    with self.recording_lock:
                        self.recorded_frames.append(audio_data)
                    
                    # WebSocket üzerinden gönder
                    ws.send(audio_data, websocket.ABNF.OPCODE_BINARY)
                except Exception as e:
                    print(f"Error streaming audio: {e}")
                    break
            print("Audio streaming stopped.")
        
        self.audio_thread = threading.Thread(target=stream_audio)
        self.audio_thread.daemon = True
        self.audio_thread.start()
    
    def _on_message(self, ws, message):
        """WebSocket mesajı alındığında"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == "Begin":
                session_id = data.get('id')
                expires_at = data.get('expires_at')
                print(f"\nSession began: ID={session_id}, ExpiresAt={datetime.fromtimestamp(expires_at)}")
                
                if self.on_session_begin_callback:
                    self.on_session_begin_callback(session_id, expires_at)
                    
            elif msg_type == "Turn":
                transcript = data.get('transcript', '')
                formatted = data.get('turn_is_formatted', False)
                
                # Callback'i çağır
                if self.on_transcript_callback:
                    self.on_transcript_callback(transcript, formatted)
                
                # Console'a yazdır
                if formatted:
                    print('\r' + ' ' * 80 + '\r', end='')
                    print(transcript)
                else:
                    print(f"{transcript}", end='', flush=True)
                    
            elif msg_type == "Termination":
                audio_duration = data.get('audio_duration_seconds', 0)
                session_duration = data.get('session_duration_seconds', 0)
                print(f"\nSession Terminated: Audio Duration={audio_duration}s, Session Duration={session_duration}s")
                
                if self.on_session_end_callback:
                    self.on_session_end_callback(audio_duration, session_duration)
                    
        except json.JSONDecodeError as e:
            print(f"Error decoding message: {e}")
        except Exception as e:
            print(f"Error handling message: {e}")
    
    def _on_error(self, ws, error):
        """WebSocket hatası oluştuğunda"""
        print(f"\nWebSocket Error: {error}")
        self.stop_event.set()
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket bağlantısı kapandığında"""
        print(f"\nWebSocket Disconnected: Status={close_status_code}, Msg={close_msg}")
        
        # WAV dosyasını kaydet
        self.save_wav_file()
        
        # Cleanup
        self.stop_event.set()
        
        if self.stream:
            if self.stream.is_active():
                self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
        if self.audio:
            self.audio.terminate()
            self.audio = None
            
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=1.0)
    
    def save_wav_file(self, output_path: Optional[str] = None) -> Optional[str]:
        """
        Kaydedilen audio'yu WAV dosyası olarak kaydet
        
        Args:
            output_path: Çıktı dosya yolu (opsiyonel, otomatik oluşturulur)
            
        Returns:
            Kaydedilen dosya yolu veya None
        """
        if not self.recorded_frames:
            print("No audio data recorded.")
            return None
        
        # Dosya adı oluştur
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"recorded_audio_{timestamp}.wav"
        
        try:
            with wave.open(output_path, 'wb') as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(2)  # 16-bit = 2 bytes
                wf.setframerate(self.SAMPLE_RATE)
                
                # Tüm frame'leri yaz
                with self.recording_lock:
                    wf.writeframes(b''.join(self.recorded_frames))
            
            duration = len(self.recorded_frames) * self.FRAMES_PER_BUFFER / self.SAMPLE_RATE
            print(f"Audio saved to: {output_path}")
            print(f"Duration: {duration:.2f} seconds")
            
            return output_path
            
        except Exception as e:
            print(f"Error saving WAV file: {e}")
            return None
    
    def start_streaming(self, duration_seconds: Optional[int] = None):
        """
        Streaming'i başlat
        
        Args:
            duration_seconds: Maksimum süre (saniye), None ise sonsuz
        """
        # PyAudio'yu başlat
        self.audio = pyaudio.PyAudio()
        
        # Mikrofon stream'ini aç
        try:
            self.stream = self.audio.open(
                input=True,
                frames_per_buffer=self.FRAMES_PER_BUFFER,
                channels=self.CHANNELS,
                format=self.FORMAT,
                rate=self.SAMPLE_RATE,
            )
            print("Microphone stream opened successfully.")
            print("Speak into your microphone. Press Ctrl+C to stop.")
            print("Audio will be saved to a WAV file when the session ends.")
        except Exception as e:
            print(f"Error opening microphone stream: {e}")
            if self.audio:
                self.audio.terminate()
            raise
        
        # WebSocketApp oluştur
        self.ws_app = websocket.WebSocketApp(
            self.api_endpoint,
            header={"Authorization": self.api_key},
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        
        # WebSocket'i ayrı thread'de çalıştır
        ws_thread = threading.Thread(target=self.ws_app.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        try:
            # Belirtilen süre kadar bekle veya sonsuz
            if duration_seconds:
                time.sleep(duration_seconds)
                self.stop_streaming()
            else:
                # Ctrl+C ile durdurmayı bekle
                while ws_thread.is_alive():
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nCtrl+C received. Stopping...")
            self.stop_streaming()
        
        # Thread'in bitmesini bekle
        ws_thread.join(timeout=2.0)
    
    def stop_streaming(self):
        """Streaming'i durdur"""
        print("\nStopping streaming...")
        self.stop_event.set()
        
        # Termination mesajı gönder
        if self.ws_app and self.ws_app.sock and self.ws_app.sock.connected:
            try:
                terminate_message = {"type": "Terminate"}
                print(f"Sending termination message: {json.dumps(terminate_message)}")
                self.ws_app.send(json.dumps(terminate_message))
                time.sleep(0.5)  # Mesajın gönderilmesi için kısa bir bekleme
            except Exception as e:
                print(f"Error sending termination message: {e}")
        
        # WebSocket'i kapat
        if self.ws_app:
            self.ws_app.close()
        
        print("Streaming stopped.")
    
    def get_recorded_frames(self) -> List[bytes]:
        """Kaydedilen audio frame'lerini al"""
        with self.recording_lock:
            return self.recorded_frames.copy()
    
    def clear_recorded_frames(self):
        """Kaydedilen audio frame'lerini temizle"""
        with self.recording_lock:
            self.recorded_frames.clear()


# Test için standalone kullanım
if __name__ == "__main__":
    service = AssemblyAIStreamingService()
    
    # Callback'leri ayarla
    def on_transcript(text, is_formatted):
        if is_formatted:
            print(f"\n[FORMATTED] {text}")
    
    def on_session_begin(session_id, expires_at):
        print(f"Session started: {session_id}")
    
    def on_session_end(audio_duration, session_duration):
        print(f"Session ended: {audio_duration}s audio, {session_duration}s total")
    
    service.set_transcript_callback(on_transcript)
    service.set_session_callbacks(on_session_begin, on_session_end)
    
    # Streaming'i başlat
    service.start_streaming()

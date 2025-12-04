from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database
    database_url: str
    
    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # OpenAI
    openai_api_key: str
    
    # ElevenLabs
    elevenlabs_api_key: str = ""  # ElevenLabs API key (opsiyonel)
    elevenlabs_model_id: str = "scribe_v1"  # ElevenLabs model ID (şu an için sadece "scribe_v1" destekleniyor)
    
    # AssemblyAI
    assemblyai_api_key: str = ""  # AssemblyAI API key (environment variable'dan alınacak)
    
    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    
    # File Storage
    upload_dir: str = "./uploads"
    models_dir: str = "./models"
    
    # Whisper
    default_whisper_model: str = "large-v3-turbo"
    enable_gpu: bool = True  # GPU kullanımını etkinleştir
    enable_speaker_diarization: bool = True  # Konuşmacı ayırt etmeyi etkinleştir
    enable_noise_reduction: bool = True  # Gürültü engellemeyi etkinleştir
    
    # HuggingFace (Speaker diarization için)
    hf_token: str = ""  # HuggingFace token (opsiyonel, .env'den alınır)
    
    # Pyannote Diarization
    whisper_model_path: str = "./models/whisper-large-v3-turbo"  # Whisper model yolu (relative path)
    enable_pyannote: bool = True  # Pyannote diarization'ı etkinleştir
    default_diarization_profile: str = "auto"  # auto, high_quality, podcast_interview, noisy_meeting, aggressive
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Settings instance
settings = Settings()

# Create directories if they don't exist
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.models_dir, exist_ok=True)


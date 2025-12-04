import os
import wave
import soundfile as sf
import numpy as np
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class WavBackupService:
    """Service for backing up audio recordings as WAV files"""
    
    def __init__(self, backup_dir: str = None):
        """Initialize WAV backup service
        
        Args:
            backup_dir: Directory to save WAV backups (default: kaydedilenler)
        """
        if backup_dir is None:
            # Default to kaydedilenler folder in project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            self.backup_dir = os.path.join(project_root, "kaydedilenler")
        else:
            self.backup_dir = backup_dir
            
        # Create backup directory if it doesn't exist
        os.makedirs(self.backup_dir, exist_ok=True)
        logger.info(f"WAV Backup Service initialized - Directory: {self.backup_dir}")
    
    def create_wav_file(self, meeting_id: int, sample_rate: int = 16000, channels: int = 1) -> str:
        """Create a new WAV file for recording
        
        Args:
            meeting_id: Meeting ID
            sample_rate: Audio sample rate (default: 16000 Hz)
            channels: Number of audio channels (default: 1 for mono)
            
        Returns:
            Path to created WAV file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"meeting_{meeting_id}_{timestamp}.wav"
        wav_path = os.path.join(self.backup_dir, filename)
        
        # Create empty WAV file with proper headers
        with wave.open(wav_path, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)  # 16-bit audio
            wav_file.setframerate(sample_rate)
        
        logger.info(f"Created WAV file: {wav_path}")
        return wav_path
    
    def create_backup_file(self, meeting_id: int, format: str = "webm") -> str:
        """Create a new backup file for audio recording
        
        Args:
            meeting_id: Meeting ID
            format: File format (webm, wav, mp3)
            
        Returns:
            Path to created backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"meeting_{meeting_id}_{timestamp}.{format}"
        backup_path = os.path.join(self.backup_dir, filename)
        
        # Create empty file
        with open(backup_path, 'wb') as f:
            pass  # Empty file
        
        logger.info(f"Created {format.upper()} backup file: {backup_path}")
        return backup_path
    
    def append_audio_chunk(self, wav_path: str, audio_data: bytes, 
                          sample_rate: int = 16000, channels: int = 1):
        """Append audio chunk to existing WAV file
        
        Args:
            wav_path: Path to WAV file
            audio_data: Raw audio data bytes
            sample_rate: Audio sample rate
            channels: Number of audio channels
        """
        try:
            if not os.path.exists(wav_path):
                logger.warning(f"WAV file not found, creating new: {wav_path}")
                self.create_wav_file(os.path.basename(wav_path).split('_')[1], sample_rate, channels)
            
            # Open WAV file in append mode
            with wave.open(wav_path, 'rb') as existing:
                params = existing.getparams()
                existing_frames = existing.readframes(existing.getnframes())
            
            # Combine existing and new audio data
            combined_data = existing_frames + audio_data
            
            # Write combined data back to file
            with wave.open(wav_path, 'wb') as wav_file:
                wav_file.setparams(params)
                wav_file.writeframes(combined_data)
            
            logger.debug(f"Appended {len(audio_data)} bytes to {wav_path}")
            
        except Exception as e:
            logger.error(f"Error appending audio chunk to WAV: {e}")
            raise
    
    def append_audio_array(self, wav_path: str, audio_array: np.ndarray, sample_rate: int = 16000):
        """Append audio array to existing WAV file using soundfile
        
        Args:
            wav_path: Path to WAV file
            audio_array: Audio data as numpy array
            sample_rate: Audio sample rate
        """
        try:
            if not os.path.exists(wav_path):
                # Create new file
                sf.write(wav_path, audio_array, sample_rate, subtype='PCM_16')
                logger.info(f"Created new WAV file: {wav_path}")
            else:
                # Read existing data
                existing_data, existing_sr = sf.read(wav_path)
                
                # Ensure sample rates match
                if existing_sr != sample_rate:
                    logger.warning(f"Sample rate mismatch: {existing_sr} vs {sample_rate}")
                
                # Combine audio data
                combined_data = np.concatenate([existing_data, audio_array])
                
                # Write back to file
                sf.write(wav_path, combined_data, sample_rate, subtype='PCM_16')
                logger.debug(f"Appended {len(audio_array)} samples to {wav_path}")
                
        except Exception as e:
            logger.error(f"Error appending audio array to WAV: {e}")
            raise
    
    def convert_webm_to_wav(self, webm_path: str, meeting_id: int) -> Optional[str]:
        """Convert WebM file to WAV format (fallback method)
        
        Args:
            webm_path: Path to WebM file
            meeting_id: Meeting ID
            
        Returns:
            Path to converted WAV file or None if conversion fails
        """
        try:
            # Read WebM file using soundfile
            audio_data, sample_rate = sf.read(webm_path)
            
            # Create WAV file path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"meeting_{meeting_id}_{timestamp}.wav"
            wav_path = os.path.join(self.backup_dir, filename)
            
            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            # Resample to 16kHz if needed
            if sample_rate != 16000:
                from scipy import signal
                num_samples = int(len(audio_data) * 16000 / sample_rate)
                audio_data = signal.resample(audio_data, num_samples)
                sample_rate = 16000
            
            # Save as WAV
            sf.write(wav_path, audio_data, sample_rate, subtype='PCM_16')
            
            logger.info(f"Converted WebM to WAV: {wav_path}")
            return wav_path
            
        except Exception as e:
            logger.error(f"Error converting WebM to WAV: {e}")
            return None
    
    def finalize_wav_file(self, wav_path: str) -> bool:
        """Finalize WAV file after recording ends
        
        Args:
            wav_path: Path to WAV file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(wav_path):
                logger.error(f"WAV file not found: {wav_path}")
                return False
            
            # Verify WAV file is valid
            with wave.open(wav_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                duration = frames / wav_file.getframerate()
                
            logger.info(f"Finalized WAV file: {wav_path} ({duration:.2f} seconds, {frames} frames)")
            return True
            
        except Exception as e:
            logger.error(f"Error finalizing WAV file: {e}")
            return False
    
    def get_wav_info(self, wav_path: str) -> dict:
        """Get information about WAV file
        
        Args:
            wav_path: Path to WAV file
            
        Returns:
            Dictionary with WAV file information
        """
        try:
            with wave.open(wav_path, 'rb') as wav_file:
                info = {
                    'path': wav_path,
                    'filename': os.path.basename(wav_path),
                    'channels': wav_file.getnchannels(),
                    'sample_width': wav_file.getsampwidth(),
                    'sample_rate': wav_file.getframerate(),
                    'frames': wav_file.getnframes(),
                    'duration': wav_file.getnframes() / wav_file.getframerate(),
                    'size_bytes': os.path.getsize(wav_path)
                }
                return info
        except Exception as e:
            logger.error(f"Error getting WAV info: {e}")
            return {}

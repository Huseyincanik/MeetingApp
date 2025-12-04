import os
import torch
import soundfile as sf
import noisereduce as nr
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
from pyannote.audio import Pipeline
import numpy as np
import psutil
from scipy import signal
import warnings
import logging
from typing import List, Dict, Optional
from ..config import settings

warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import transformers
transformers.logging.set_verbosity_error()

logging.getLogger('pyannote.audio.core.io').setLevel(logging.ERROR)
logging.getLogger('transformers').setLevel(logging.ERROR)


class PyannoteDiarizationService:
    """Pyannote ile gelişmiş konuşmacı diarization ve STT servisi"""
    
    def __init__(self, whisper_model_path: Optional[str] = None, hf_token: Optional[str] = None):
        """Pyannote diarization servisi başlat"""
        self.whisper_model_path = whisper_model_path or settings.whisper_model_path
        self.hf_token = hf_token or settings.hf_token
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        
        # Whisper chunk parametreleri
        self.chunk_length_s = 20
        self.stride_length_s = 4
        
        print(f"Pyannote Diarization Service - Device: {self.device}")
        
        # Diarization profilleri
        self.diarization_profiles = {
            'high_quality': {
                'segmentation': {
                    'min_duration_off': 0.1,
                    'threshold': 0.45,
                },
                'clustering': {
                    'method': 'centroid',
                    'min_cluster_size': 13,
                    'threshold': 0.45,
                }
            },
            'podcast_interview': {
                'segmentation': {
                    'min_duration_off': 0.15,
                    'threshold': 0.50,
                },
                'clustering': {
                    'method': 'centroid',
                    'min_cluster_size': 15,
                    'threshold': 0.35,
                }
            },
            'noisy_meeting': {
                'segmentation': {
                    'min_duration_off': 0.15,
                    'threshold': 0.50,
                },
                'clustering': {
                    'method': 'centroid',
                    'min_cluster_size': 16,
                    'threshold': 0.35,
                }
            },
            'aggressive': {
                'segmentation': {
                    'min_duration_off': 0.15,
                    'threshold': 0.50,
                },
                'clustering': {
                    'method': 'centroid',
                    'min_cluster_size': 17,
                    'threshold': 0.35,
                }
            }
        }
        
        self.whisper_model = None
        self.whisper_processor = None
        self.diarization_pipeline = None
        
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"GPU: {gpu_name}")
            print(f"GPU Memory: {gpu_memory:.2f} GB")
    
    def _apply_ai_noise_reduction(self, audio_array, sample_rate):
        """
        🔥 UPDATED: FFT-based Spectral Gating (noisereduce) instead of classic Bandpass.
        Removes stationary noise like fans, AC, hum.
        """
        print("   ...Extracting noise profile and cleaning (Stationary Noise Reduction)...")
        
        try:
            # 1. Extract noise profile from very quiet parts
            # stationary=True: Cleans constant sounds like fans, AC, hum
            # prop_decrease=0.90: Remove 90% of noise (not 100% to avoid robotic sound)
            cleaned_audio = nr.reduce_noise(
                y=audio_array, 
                sr=sample_rate, 
                stationary=True, 
                prop_decrease=0.90,
                n_fft=2048,
                hop_length=512
            )
            
            # 2. Normalize (prevent clipping)
            max_val = np.max(np.abs(cleaned_audio))
            if max_val > 0:
                cleaned_audio = cleaned_audio / max_val
                
            return cleaned_audio

        except Exception as e:
            print(f"⚠️ Noise reduction warning: {e}")
            return audio_array  # Return original audio if error occurs
    
    def analyze_audio_quality(self, audio_path):
        """Ses kalitesini analiz et ve uygun profil öner"""
        audio_array, sample_rate = sf.read(audio_path, dtype='float32')
        
        if len(audio_array.shape) > 1:
            audio_array = np.mean(audio_array, axis=1)
        
        window_size = int(0.1 * sample_rate)
        energy = np.array([
            np.sum(audio_array[i:i+window_size]**2) 
            for i in range(0, len(audio_array)-window_size, window_size)
        ])
        
        noise_energy = np.percentile(energy, 10)
        signal_energy = np.mean(energy)
        
        snr = 10 * np.log10(signal_energy / (noise_energy + 1e-10))
        speech_ratio = np.sum(energy > np.percentile(energy, 30)) / len(energy)
        
        print(f"\n🔊 Audio Analysis:")
        print(f"  SNR: {snr:.2f} dB")
        print(f"  Speech density: {speech_ratio*100:.1f}%")
        
        if snr > 20 and speech_ratio > 0.6:
            profile = 'high_quality'
            print(f"  ✅ Recommended profile: HIGH QUALITY")
        elif snr > 15 and speech_ratio < 0.4:
            profile = 'podcast_interview'
            print(f"  ✅ Recommended profile: PODCAST/INTERVIEW")
        elif speech_ratio > 0.7:
            profile = 'aggressive'
            print(f"  ✅ Recommended profile: AGGRESSIVE")
        else:
            profile = 'noisy_meeting'
            print(f"  ✅ Recommended profile: NOISY MEETING")
        
        return profile, snr, speech_ratio
    
    def _load_models(self):
        """Whisper ve Pyannote modellerini yükle"""
        if self.whisper_model is None:
            print("Loading Whisper model...")
            
            self.whisper_model = AutoModelForSpeechSeq2Seq.from_pretrained(
                self.whisper_model_path,
                torch_dtype=self.dtype,
                low_cpu_mem_usage=True,
                use_safetensors=True
            )
            self.whisper_model.to(self.device)
            
            self.whisper_processor = AutoProcessor.from_pretrained(self.whisper_model_path)
            
            print("✓ Whisper model loaded")
        
        if self.diarization_pipeline is None:
            print("Loading Pyannote diarization model...")
            try:
                self.diarization_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    token=self.hf_token
                )
                if torch.cuda.is_available():
                    self.diarization_pipeline.to(torch.device("cuda"))
                print("✓ Pyannote model loaded")
            except Exception as e:
                print(f"❌ Pyannote model loading error: {e}")
                raise e
    
    def _load_audio(self, audio_path, target_sr=16000):
        """Ses dosyasını yükle ve normalize et"""
        try:
            audio_array, sample_rate = sf.read(audio_path, dtype='float32')
            
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
            
            if sample_rate != target_sr:
                num_samples = int(len(audio_array) * target_sr / sample_rate)
                audio_array = signal.resample(audio_array, num_samples)
                sample_rate = target_sr
            
            if np.abs(audio_array).max() > 0:
                audio_array = audio_array / np.abs(audio_array).max()
            
            return audio_array, sample_rate
            
        except Exception as e:
            print(f"❌ Audio loading error: {e}")
            raise
    
    def diarize_audio(self, audio_path, min_speakers=None, max_speakers=None, profile='auto'):
        """Konuşmacı ayrımı"""
        print("\n🔍 Starting speaker diarization...")
        
        if profile == 'auto':
            profile, snr, speech_ratio = self.analyze_audio_quality(audio_path)
        
        params = self.diarization_profiles.get(profile, self.diarization_profiles['high_quality'])
        
        print(f"📋 Using parameters ({profile}):")
        print(f"  Segmentation: {params['segmentation']}")
        print(f"  Clustering: {params['clustering']}")
        
        try:
            audio_array, sample_rate = sf.read(audio_path, dtype='float32')
            
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
            
            print("🔊 Cleaning audio (AI Noise Reduction)...")
            audio_array = self._apply_ai_noise_reduction(audio_array, sample_rate)
            waveform = torch.from_numpy(audio_array).float()
            
            if waveform.dim() == 1:
                waveform = waveform.unsqueeze(0)
            
            audio_dict = {
                "waveform": waveform,
                "sample_rate": sample_rate
            }
            
            if min_speakers and max_speakers:
                diarization = self.diarization_pipeline(
                    audio_dict, 
                    min_speakers=min_speakers, 
                    max_speakers=max_speakers,
                    **params
                )
            else:
                diarization = self.diarization_pipeline(audio_dict, **params)
            
            if torch.cuda.is_available():
                gpu_after = torch.cuda.memory_allocated(0) / 1024**3
                gpu_peak = torch.cuda.max_memory_allocated(0) / 1024**3
                print(f"GPU usage: {gpu_after:.2f} GB | Peak: {gpu_peak:.2f} GB")
            
            print("✓ Speaker diarization completed")
            return diarization
            
        except Exception as e:
            print(f"❌ Diarization error: {e}")
            raise
    
    def transcribe_audio_chunked(self, audio_path):
        """Uzun ses dosyalarını chunk'lara bölerek transkript et"""
        print("\n📝 Creating transcript (chunk-based)...")
        
        try:
            audio_array, sample_rate = self._load_audio(audio_path, target_sr=16000)
            total_duration = len(audio_array) / sample_rate
            
            print(f"Total duration: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
            
            chunk_samples = int(self.chunk_length_s * sample_rate)
            stride_samples = int(self.stride_length_s * sample_rate)
            
            all_chunks = []
            offset = 0
            chunk_idx = 0
            
            while offset < len(audio_array):
                end = min(offset + chunk_samples, len(audio_array))
                chunk = audio_array[offset:end]
                
                if len(chunk) < sample_rate:
                    break
                
                chunk_idx += 1
                chunk_start_time = offset / sample_rate
                
                if torch.cuda.is_available():
                    gpu_used = torch.cuda.memory_allocated(0) / 1024**3
                    print(f"  Chunk {chunk_idx}: {chunk_start_time:.1f}s - {chunk_start_time + len(chunk)/sample_rate:.1f}s | GPU: {gpu_used:.2f}GB")
                else:
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    ram_used = psutil.virtual_memory().used / 1024**3
                    print(f"  Chunk {chunk_idx}: {chunk_start_time:.1f}s | CPU: {cpu_percent}% | RAM: {ram_used:.2f}GB")
                
                input_features = self.whisper_processor(
                    chunk,
                    sampling_rate=16000,
                    return_tensors="pt",
                    return_attention_mask=True
                ).input_features
                
                input_features = input_features.to(self.device, dtype=self.dtype)
                
                with torch.no_grad():
                    # 🔥 FIXED: condition_on_previous_text removed to prevent context bleeding
                    predicted_ids = self.whisper_model.generate(
                        input_features,
                        language="tr",
                        task="transcribe",
                        return_timestamps=True,
                        do_sample=False,

                        # Repetition prevention parameters
                        repetition_penalty=1.2,
                        no_repeat_ngram_size=3,  # Prevent 3-gram repetition
                        temperature=0.0,

                        # Hallucination reduction
                        compression_ratio_threshold=2.4,  # Stop at high compression ratios
                        logprob_threshold=-1.0,           # Stop at low log probabilities
                    )
                
                transcription = self.whisper_processor.batch_decode(
                    predicted_ids,
                    skip_special_tokens=False,
                    decode_with_timestamps=True
                )
                
                chunk_result = self._parse_whisper_output(transcription[0])
                
                for sub_chunk in chunk_result['chunks']:
                    if sub_chunk['timestamp'][0] is not None:
                        adjusted_start = chunk_start_time + sub_chunk['timestamp'][0]
                        adjusted_end = chunk_start_time + sub_chunk['timestamp'][1]
                        
                        all_chunks.append({
                            'timestamp': (adjusted_start, adjusted_end),
                            'text': sub_chunk['text']
                        })
                
                offset += chunk_samples - stride_samples
            
            print(f"✓ Total {len(all_chunks)} segments transcribed")
            
            all_chunks = self._merge_overlapping_chunks(all_chunks)
            
            return {'chunks': all_chunks, 'text': ' '.join([c['text'] for c in all_chunks])}
            
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _merge_overlapping_chunks(self, chunks):
        """Overlap bölgelerindeki tekrarlanan metinleri temizle"""
        if not chunks:
            return chunks
        
        merged = [chunks[0]]
        
        for current in chunks[1:]:
            prev = merged[-1]
            
            if current['timestamp'][0] < prev['timestamp'][1]:
                overlap_duration = prev['timestamp'][1] - current['timestamp'][0]
                
                if overlap_duration > (prev['timestamp'][1] - prev['timestamp'][0]) * 0.5:
                    prev_words = prev['text'].split()
                    current_words = current['text'].split()
                    
                    overlap_words = min(5, len(prev_words))
                    if prev_words[-overlap_words:] == current_words[:overlap_words]:
                        merged[-1]['text'] = prev['text'] + ' ' + ' '.join(current_words[overlap_words:])
                        merged[-1]['timestamp'] = (prev['timestamp'][0], current['timestamp'][1])
                    else:
                        merged.append(current)
                else:
                    merged.append(current)
            else:
                merged.append(current)
        
        return merged
    
    def _parse_whisper_output(self, text):
        """
        Parse Whisper output into timestamped chunks
        🔥 UPDATED: Filters hallucinations (loops) and zero-duration errors
        """
        import re
        
        # Detect if text is a "repetition loop" (e.g., "This this this this...")
        # Simple heuristic: Same word appears more than 10 times
        words = text.split()
        if len(words) > 10:
            unique_words = set(words)
            # If word diversity is less than 10% (constantly repeating same thing)
            if len(unique_words) / len(words) < 0.1:
                print(f"⚠️ Hallucination detected and removed: {text[:50]}...")
                return {'chunks': [], 'text': ''}

        timestamp_pattern = r'<\|(\d+\.\d+)\|>'
        parts = re.split(timestamp_pattern, text)
        
        chunks = []
        
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                try:
                    start_time = float(parts[i])
                    chunk_text = parts[i + 1].strip()
                    
                    if i + 2 < len(parts):
                        end_time = float(parts[i + 2])
                    else:
                        end_time = start_time + 2.0
                    
                    # 🔥 FIX 2: Filter invalid time ranges
                    # 1. Start time >= end time
                    # 2. Duration is 0 (434.00 - 434.00 error)
                    # 3. Text is only punctuation
                    if end_time <= start_time:
                        continue
                        
                    if not chunk_text or chunk_text in ".,?!:":
                        continue

                    # Repetition check: If chunk text is like "This this this", skip it
                    if len(chunk_text.split()) > 4 and len(set(chunk_text.split())) == 1:
                        continue

                    chunks.append({
                        'timestamp': (start_time, end_time),
                        'text': chunk_text
                    })
                except:
                    continue
        
        # If chunks is empty but text exists (timestamps couldn't be generated)
        if not chunks:
            clean_text = re.sub(r'<\|.*?\|>', '', text).strip()
            # Loop check here too
            if clean_text and len(clean_text) < 200:  # Don't take very long loop texts
                chunks.append({
                    'timestamp': (0.0, 2.0),
                    'text': clean_text
                })
        
        return {'chunks': chunks, 'text': text}
    
    def _post_process_diarization(self, diarization):
        """Pyannote çıktısındaki gereksiz boşlukları temizler"""
        from pyannote.core import Annotation
        
        new_annotation = Annotation()
        
        sorted_segments = sorted(
            [(s, t, l) for s, t, l in diarization.itertracks(yield_label=True)],
            key=lambda x: x[0].start
        )
        
        if not sorted_segments:
            return diarization

        current_segment, _, current_label = sorted_segments[0]
        
        for next_segment, _, next_label in sorted_segments[1:]:
            gap = next_segment.start - current_segment.end
            
            if next_label == current_label and gap < 1.0:
                from pyannote.core import Segment
                current_segment = Segment(current_segment.start, next_segment.end)
            else:
                new_annotation[current_segment] = current_label
                current_segment = next_segment
                current_label = next_label
        
        new_annotation[current_segment] = current_label
        
        return new_annotation
    
    def _remove_redundant_segments(self, segments):
        """
        🔥 NEW: Cleans timeline errors and duplicates (Deduplication).
        Example Problem:
        1. [43.90 - 48.68] ...what will happen?
        2. [48.00 - 50.00] what will happen (UNNECESSARY DUPLICATE)
        """
        if not segments:
            return []
            
        cleaned = [segments[0]]
        
        for i in range(1, len(segments)):
            current = segments[i]
            prev = cleaned[-1]
            
            # Calculate time overlap
            overlap_start = max(prev['start'], current['start'])
            overlap_end = min(prev['end'], current['end'])
            overlap_duration = max(0, overlap_end - overlap_start)
            
            current_duration = current['end'] - current['start']
            
            # RULE 1: Delete fully contained small segments
            # If 80%+ of new segment is already in previous segment and text is short
            if current_duration > 0 and (overlap_duration / current_duration) > 0.8:
                # Check text similarity (Simple word matching)
                prev_words = set(prev['text'].lower().split())
                curr_words = set(current['text'].lower().split())
                
                # If new segment's words are already in previous segment, skip
                if curr_words.issubset(prev_words):
                    continue  # Skip (don't add)
            
            # RULE 2: Fix time drift
            # If a segment starts before the previous one ends, shift its start
            if current['start'] < prev['end']:
                # If there's too much overlap (e.g., not 2 people talking simultaneously)
                # Pull new segment's start to previous segment's end
                if overlap_duration < 1.0:
                    current['start'] = prev['end']
            
            # Don't add segments with no remaining duration
            if current['end'] - current['start'] > 0.1:
                cleaned.append(current)
                
        return cleaned
    
    def _align_whisper_with_diarization(self, whisper_chunks, speaker_segments):
        """Dominant Speaker mantığı ile eşleştirme"""
        results = []
        
        for chunk in whisper_chunks:
            w_start = chunk['timestamp'][0]
            w_end = chunk['timestamp'][1]
            w_text = chunk['text']
            w_duration = w_end - w_start
            
            if w_duration <= 0:
                continue

            overlap_stats = {}
            
            for spk_seg in speaker_segments:
                overlap_start = max(w_start, spk_seg['start'])
                overlap_end = min(w_end, spk_seg['end'])
                overlap_dur = max(0, overlap_end - overlap_start)
                
                if overlap_dur > 0:
                    speaker = spk_seg['speaker']
                    overlap_stats[speaker] = overlap_stats.get(speaker, 0) + overlap_dur
            
            if not overlap_stats:
                nearest_speaker = self._find_nearest_speaker(w_start, w_end, speaker_segments)
                results.append({
                    'start': w_start,
                    'end': w_end,
                    'speaker': nearest_speaker,
                    'text': w_text
                })
            else:
                dominant_speaker = max(overlap_stats, key=overlap_stats.get)
                
                results.append({
                    'start': w_start,
                    'end': w_end,
                    'speaker': dominant_speaker,
                    'text': w_text
                })
                
        return results
    
    def _find_nearest_speaker(self, start, end, speaker_segments):
        """En yakın konuşmacıyı bul"""
        mid_point = (start + end) / 2
        min_distance = float('inf')
        best_speaker = "SPEAKER_00"
        
        for segment in speaker_segments:
            segment_mid = (segment['start'] + segment['end']) / 2
            distance = abs(mid_point - segment_mid)
            
            if distance < min_distance:
                min_distance = distance
                best_speaker = segment['speaker']
        
        return best_speaker
    
    def _merge_consecutive_speakers(self, results):
        """Smartly merge consecutive segments from same speaker"""
        if not results:
            return results
        
        merged = []
        current = results[0].copy()
        
        for next_seg in results[1:]:
            # Same speaker?
            if current['speaker'] == next_seg['speaker']:
                
                # Gap between segments
                gap = next_seg['start'] - current['end']
                
                # MERGE CONDITIONS:
                # 1. Gap is less than 2 seconds (Natural pause)
                # 2. Or gap is negative (Time overlap correction)
                if gap < 2.0:
                    # Merge text
                    current['text'] += " " + next_seg['text']
                    # Update end time (Take the furthest time)
                    current['end'] = max(current['end'], next_seg['end'])
                    continue
            
            # Otherwise, save current and move to next
            merged.append(current)
            current = next_seg.copy()
        
        merged.append(current)
        return merged
    
    def get_speaker_overlap(self, diarization) -> List[Dict]:
        """Detect and return overlapping speech segments
        
        Args:
            diarization: Pyannote diarization output
            
        Returns:
            List of overlap segments with timestamps
        """
        try:
            overlap = diarization.get_overlap()
            overlap_segments = []
            
            for segment in overlap:
                overlap_segments.append({
                    'start': segment.start,
                    'end': segment.end,
                    'duration': segment.duration
                })
            
            print(f"📊 Found {len(overlap_segments)} overlapping speech regions")
            return overlap_segments
            
        except Exception as e:
            print(f"⚠️ Error detecting overlap: {e}")
            return []
    
    def calculate_speaker_statistics(self, diarization) -> Dict:
        """Calculate speaking time and statistics per speaker
        
        Args:
            diarization: Pyannote diarization output
            
        Returns:
            Dictionary with speaker statistics
        """
        try:
            stats = {}
            
            # Get all unique speakers
            speakers = diarization.labels()
            
            for speaker in speakers:
                # Calculate total speaking time for this speaker
                speaking_time = diarization.label_duration(speaker)
                
                # Get all segments for this speaker
                speaker_timeline = diarization.label_timeline(speaker)
                num_segments = len(list(speaker_timeline))
                
                stats[speaker] = {
                    'total_speaking_time': speaking_time,
                    'num_segments': num_segments,
                    'speaker_label': speaker
                }
            
            print(f"📊 Speaker Statistics:")
            for speaker, data in stats.items():
                print(f"  {speaker}: {data['total_speaking_time']:.2f}s ({data['num_segments']} segments)")
            
            return stats
            
        except Exception as e:
            print(f"⚠️ Error calculating speaker statistics: {e}")
            return {}
    
    def filter_by_speaker(self, diarization, speaker_id: str) -> List[Dict]:
        """Filter segments by specific speaker
        
        Args:
            diarization: Pyannote diarization output
            speaker_id: Speaker ID to filter (e.g., "SPEAKER_00")
            
        Returns:
            List of segments for the specified speaker
        """
        try:
            speaker_timeline = diarization.label_timeline(speaker_id)
            segments = []
            
            for segment in speaker_timeline:
                segments.append({
                    'start': segment.start,
                    'end': segment.end,
                    'duration': segment.duration,
                    'speaker': speaker_id
                })
            
            print(f"📊 Speaker {speaker_id} has {len(segments)} segments")
            return segments
            
        except Exception as e:
            print(f"⚠️ Error filtering by speaker: {e}")
            return []
    
    def process_with_speakers(
        self, 
        audio_path, 
        min_speakers=None, 
        max_speakers=None, 
        profile='auto'
    ) -> List[Dict]:
        """
        Pyannote ile konuşmacı ayrımı ve transkript oluştur
        Returns: List of transcript segments with speaker info
        """
        # Modelleri yükle
        self._load_models()
        
        # 1. Diarization İşlemi
        diarization_output = self.diarize_audio(audio_path, min_speakers, max_speakers, profile)
        
        # Diarization output'u düzelt
        if hasattr(diarization_output, 'speaker_diarization'):
            raw_annotation = diarization_output.speaker_diarization
        else:
            raw_annotation = diarization_output
        
        # 2. Diarization İyileştirme
        clean_diarization = self._post_process_diarization(raw_annotation)
        
        # 3. Overlap Detection (NEW)
        overlap_segments = self.get_speaker_overlap(clean_diarization)
        
        # 4. Speaker Statistics (NEW)
        speaker_stats = self.calculate_speaker_statistics(clean_diarization)
        
        # 5. Transkript
        transcription = self.transcribe_audio_chunked(audio_path)
        
        # Diarization segmentlerini listeye çevir
        speaker_segments = []
        for segment, _, speaker in clean_diarization.itertracks(yield_label=True):
            speaker_segments.append({
                'start': segment.start,
                'end': segment.end,
                'speaker': speaker
            })
        
        print(f"Total {len(speaker_segments)} speaker segments (Improved)")
        
        # 6. Alignment (Dominant Speaker Logic)
        results = self._align_whisper_with_diarization(
            transcription['chunks'], 
            speaker_segments
        )
        
        # 🔥 NEW STEP 1: Sort by time (Fixes time travel issues)
        results = sorted(results, key=lambda x: x['start'])
        
        # 🔥 NEW STEP 2: Remove overlapping and duplicate ghost sentences
        results = self._remove_redundant_segments(results)
        
        # 7. Merge consecutive same speakers
        results = self._merge_consecutive_speakers(results)
        
        # 8. Format çıktıyı
        formatted_results = []
        for result in results:
            speaker_id = result['speaker']
            # SPEAKER_00 -> Konuşmacı 1 formatına çevir
            try:
                speaker_num = int(speaker_id.split("_")[-1])
                speaker_label = f"Konuşmacı {speaker_num + 1}"
            except:
                speaker_label = speaker_id
            
            # Check if this segment overlaps with any overlap region
            is_overlap = False
            for overlap in overlap_segments:
                if (result['start'] < overlap['end'] and result['end'] > overlap['start']):
                    is_overlap = True
                    break
            
            formatted_results.append({
                'text': result['text'],
                'start': result['start'],
                'end': result['end'],
                'speaker_id': speaker_id,
                'speaker_label': speaker_label,
                'is_overlap': is_overlap  # Mark segments with speaker overlap
            })
        
        print("\n📊 Process Summary:")
        print(f"  - Total segments: {len(formatted_results)}")
        print(f"  - Number of speakers: {len(set([r['speaker_id'] for r in formatted_results]))}")
        print(f"  - Overlap regions: {len(overlap_segments)}")
        print(f"  - Segments with overlap: {sum(1 for r in formatted_results if r['is_overlap'])}")
        
        # Add speaker statistics to results metadata
        for result in formatted_results:
            if result['speaker_id'] in speaker_stats:
                result['speaker_total_time'] = speaker_stats[result['speaker_id']]['total_speaking_time']
        
        if torch.cuda.is_available():
            gpu_final = torch.cuda.memory_allocated(0) / 1024**3
            gpu_max = torch.cuda.max_memory_allocated(0) / 1024**3
            print(f"  - GPU usage: {gpu_final:.2f} GB (max: {gpu_max:.2f} GB)")
        else:
            ram_used = psutil.virtual_memory().used / 1024**3
            print(f"  - RAM usage: {ram_used:.2f} GB")
        
        return formatted_results


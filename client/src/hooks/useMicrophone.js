import { useState, useRef, useCallback } from 'react';

export const useMicrophone = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [captureSystemAudio, setCaptureSystemAudio] = useState(false);
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const systemStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);

  const startRecording = useCallback(async (onChunkReady, includeSystemAudio = false) => {
    try {
      // 1. Get microphone stream
      const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = micStream;

      let finalStream = micStream;
      let audioContext = null;

      // 2. If system audio is requested, capture and mix it
      if (includeSystemAudio) {
        try {
          console.log('🎙️ Requesting system audio capture...');

          // Request screen/tab sharing with audio
          // IMPORTANT: video must be true for audio to work in some browsers
          const displayStream = await navigator.mediaDevices.getDisplayMedia({
            video: {
              displaySurface: "browser",  // Prefer browser tab
            },
            audio: {
              echoCancellation: false,
              noiseSuppression: false,
              autoGainControl: false,
              suppressLocalAudioPlayback: false
            }
          });

          console.log('📺 Display stream obtained:', {
            videoTracks: displayStream.getVideoTracks().length,
            audioTracks: displayStream.getAudioTracks().length
          });

          // Check if audio track exists
          const audioTracks = displayStream.getAudioTracks();
          if (audioTracks.length === 0) {
            console.warn('⚠️ No audio track in display stream - user may not have shared tab audio');
            throw new Error('No audio track available. Please select "Share tab audio" when sharing.');
          }

          console.log('✅ Audio track found:', audioTracks[0].label);

          // Remove video track (we only need audio)
          displayStream.getVideoTracks().forEach(track => {
            track.stop();
            displayStream.removeTrack(track);
          });

          systemStreamRef.current = displayStream;

          // Create audio context for mixing
          audioContext = new (window.AudioContext || window.webkitAudioContext)();
          audioContextRef.current = audioContext;

          console.log('🎵 Creating audio sources...');

          // Create sources
          const micSource = audioContext.createMediaStreamSource(micStream);
          const systemSource = audioContext.createMediaStreamSource(displayStream);

          // Create destination
          const destination = audioContext.createMediaStreamDestination();

          // Create gain nodes for volume control
          const micGain = audioContext.createGain();
          const systemGain = audioContext.createGain();

          // Set gain values (adjust as needed)
          micGain.gain.value = 1.0;  // Microphone volume
          systemGain.gain.value = 1.5;  // System audio volume (slightly boosted)

          // Connect: mic -> gain -> destination
          micSource.connect(micGain);
          micGain.connect(destination);

          // Connect: system -> gain -> destination
          systemSource.connect(systemGain);
          systemGain.connect(destination);

          // Use mixed stream
          finalStream = destination.stream;

          console.log('✅ System audio capture enabled - both mic and speaker will be recorded');
          console.log('🎚️ Mixed stream tracks:', finalStream.getTracks().map(t => t.label));
        } catch (displayError) {
          console.error('❌ System audio capture failed:', displayError);
          console.warn('⚠️ Falling back to microphone only');
          alert('Sistem sesi yakalanamadı. Lütfen ekran paylaşımında "Sekme sesini paylaş" seçeneğini işaretlediğinizden emin olun.\n\nSadece mikrofon ile devam ediliyor.');
          // Fall back to microphone only
          finalStream = micStream;
        }
      }

      // Audio context for level monitoring (separate from mixing)
      const monitorContext = new (window.AudioContext || window.webkitAudioContext)();
      const analyser = monitorContext.createAnalyser();
      const source = monitorContext.createMediaStreamSource(finalStream);
      source.connect(analyser);
      analyser.fftSize = 256;

      analyserRef.current = analyser;

      // Audio level monitoring
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const updateLevel = () => {
        if (analyserRef.current) {
          analyserRef.current.getByteFrequencyData(dataArray);
          const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
          setAudioLevel(average);
          requestAnimationFrame(updateLevel);
        }
      };
      updateLevel();

      // MediaRecorder setup with final stream (mic only or mixed)
      const mediaRecorder = new MediaRecorder(finalStream, {
        mimeType: 'audio/webm;codecs=opus',
      });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && onChunkReady) {
          onChunkReady(event.data);
        }
      };

      mediaRecorder.start(5000); // 5 saniyede bir chunk
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
    } catch (error) {
      console.error('Mikrofon erişim hatası:', error);
      throw error;
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }

    // Stop system audio stream if exists
    if (systemStreamRef.current) {
      systemStreamRef.current.getTracks().forEach(track => track.stop());
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
    }

    if (analyserRef.current) {
      analyserRef.current = null;
    }

    setIsRecording(false);
    setAudioLevel(0);
    mediaRecorderRef.current = null;
    streamRef.current = null;
    systemStreamRef.current = null;
    audioContextRef.current = null;
  }, []);

  return {
    isRecording,
    audioLevel,
    captureSystemAudio,
    setCaptureSystemAudio,
    startRecording,
    stopRecording,
  };
};

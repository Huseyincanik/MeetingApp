import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Container, Card, Form, Button, Alert, Spinner, Row, Col, Badge } from 'react-bootstrap';
import { FiMic, FiArrowLeft, FiCpu, FiGlobe, FiLoader, FiAlertCircle } from 'react-icons/fi';
import { useMicrophone } from '../hooks/useMicrophone';
import { meetingsAPI, audioAPI } from '../services/api';
import MeetingControl from '../components/Meeting/MeetingControl';
import RecordingStatus from '../components/Meeting/RecordingStatus';
import TranscriptView from '../components/Meeting/TranscriptView';
import SummaryView from '../components/Meeting/SummaryView';

const Dashboard = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [whisperModel, setWhisperModel] = useState('tiny');
  const [language, setLanguage] = useState('tr');
  const [activeMeeting, setActiveMeeting] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [micPermission, setMicPermission] = useState(null);
  const [viewMode, setViewMode] = useState('new'); // 'new' veya 'view'
  // Pyannote Diarization settings
  const [usePyannote, setUsePyannote] = useState(false);
  const [diarizationProfile, setDiarizationProfile] = useState('auto');
  const [minSpeakers, setMinSpeakers] = useState('');
  const [maxSpeakers, setMaxSpeakers] = useState('');
  const [filePath, setFilePath] = useState('');
  const [processFileMode, setProcessFileMode] = useState(false);

  const { isRecording, audioLevel, captureSystemAudio, setCaptureSystemAudio, startRecording, stopRecording } = useMicrophone();
  const [recordingInterval, setRecordingInterval] = useState(null);

  useEffect(() => {
    // Mikrofon izni kontrolü
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(() => {
        setMicPermission(true);
      })
      .catch(() => {
        setMicPermission(false);
      });
  }, []);

  // URL'den meeting ID'sini kontrol et ve yükle
  useEffect(() => {
    const meetingId = searchParams.get('meeting');
    if (meetingId) {
      const id = parseInt(meetingId);
      // Eğer aynı meeting zaten yüklenmişse tekrar yükleme
      if (activeMeeting?.id === id) {
        return;
      }
      setLoading(true);
      setViewMode('view');
      meetingsAPI.getMeeting(id)
        .then((meeting) => {
          setActiveMeeting(meeting);
        })
        .catch((err) => {
          setError('Toplantı yüklenemedi');
          console.error('Toplantı yükleme hatası:', err);
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      // URL'de meeting yoksa activeMeeting'i temizle
      if (viewMode === 'view') {
        setActiveMeeting(null);
        setViewMode('new');
      }
    }
  }, [searchParams]);

  // Processing durumundaki toplantıları otomatik yenile
  useEffect(() => {
    if (activeMeeting && viewMode === 'view' && activeMeeting.status === 'processing') {
      let interval = setInterval(async () => {
        try {
          const updatedMeeting = await meetingsAPI.getMeeting(activeMeeting.id);
          setActiveMeeting(updatedMeeting);
          if (updatedMeeting.status === 'completed') {
            clearInterval(interval);
            interval = null;
          }
        } catch (err) {
          console.error('Meeting güncelleme hatası:', err);
          clearInterval(interval);
          interval = null;
        }
      }, 5000);

      return () => {
        if (interval) {
          clearInterval(interval);
        }
      };
    }
  }, [activeMeeting?.id, activeMeeting?.status, viewMode]);

  const handleStartMeeting = async () => {
    if (!micPermission) {
      setError('Mikrofon izni gerekli');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Normal meeting başlatma (streaming değilse)
      const meeting = await meetingsAPI.startMeeting({
        whisper_model: whisperModel,
        language: language,
        use_pyannote: whisperModel === 'pyannote' || usePyannote,
        diarization_profile: diarizationProfile,
        min_speakers: minSpeakers ? parseInt(minSpeakers) : null,
        max_speakers: maxSpeakers ? parseInt(maxSpeakers) : null,
      });

      setActiveMeeting(meeting);

      await startRecording(async (chunk) => {
        try {
          await audioAPI.uploadChunk(meeting.id, chunk);
        } catch (err) {
          console.error('Chunk upload hatası:', err);
        }
      }, captureSystemAudio);  // Pass system audio capture flag


      // Recording sırasında sadece status değişikliklerini kontrol et
      const interval = setInterval(async () => {
        try {
          const updatedMeeting = await meetingsAPI.getMeeting(meeting.id);
          // Sadece status değiştiyse güncelle
          if (updatedMeeting.status !== activeMeeting.status) {
            setActiveMeeting(updatedMeeting);
          }

          if (updatedMeeting.status === 'completed' || updatedMeeting.status === 'processing') {
            clearInterval(interval);
            stopRecording();
            setRecordingInterval(null);
          }
        } catch (err) {
          console.error('Meeting durum kontrolü hatası:', err);
        }
      }, 10000);

      setRecordingInterval(interval);
    } catch (err) {
      // Pydantic validation hatası bir array olabilir, string'e çevir
      const errorDetail = err.response?.data?.detail;
      let errorMessage = 'Toplantı başlatılamadı';

      if (errorDetail) {
        if (Array.isArray(errorDetail)) {
          // Validation hatası array formatında
          errorMessage = errorDetail.map(e => e.msg || JSON.stringify(e)).join(', ');
        } else if (typeof errorDetail === 'string') {
          errorMessage = errorDetail;
        } else {
          errorMessage = JSON.stringify(errorDetail);
        }
      }

      setError(errorMessage);
      if (isRecording) {
        stopRecording();
      }
    } finally {
      setLoading(false);
    }
  };

  const handlePauseMeeting = async () => {
    if (!activeMeeting) return;

    try {
      const meeting = await meetingsAPI.pauseMeeting(activeMeeting.id);
      setActiveMeeting(meeting);
      stopRecording();
      if (recordingInterval) {
        clearInterval(recordingInterval);
        setRecordingInterval(null);
      }
    } catch (err) {
      const errorDetail = err.response?.data?.detail;
      const errorMessage = Array.isArray(errorDetail)
        ? errorDetail.map(e => e.msg || JSON.stringify(e)).join(', ')
        : (typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail)) || 'Toplantı duraklatılamadı';
      setError(errorMessage);
    }
  };

  const handleResumeMeeting = async () => {
    if (!activeMeeting) return;

    try {
      const meeting = await meetingsAPI.resumeMeeting(activeMeeting.id);
      setActiveMeeting(meeting);

      await startRecording(async (chunk) => {
        try {
          await audioAPI.uploadChunk(meeting.id, chunk);
        } catch (err) {
          console.error('Chunk upload hatası:', err);
        }
      });

      // Recording sırasında sadece status değişikliklerini kontrol et
      const interval = setInterval(async () => {
        try {
          const updatedMeeting = await meetingsAPI.getMeeting(meeting.id);
          // Sadece status değiştiyse güncelle
          if (updatedMeeting.status !== meeting.status) {
            setActiveMeeting(updatedMeeting);
          }

          if (updatedMeeting.status === 'completed' || updatedMeeting.status === 'processing') {
            clearInterval(interval);
            stopRecording();
            setRecordingInterval(null);
          }
        } catch (err) {
          console.error('Meeting durum kontrolü hatası:', err);
        }
      }, 10000);

      setRecordingInterval(interval);
    } catch (err) {
      const errorDetail = err.response?.data?.detail;
      const errorMessage = Array.isArray(errorDetail)
        ? errorDetail.map(e => e.msg || JSON.stringify(e)).join(', ')
        : (typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail)) || 'Toplantı devam ettirilemedi';
      setError(errorMessage);
    }
  };

  const handleEndMeeting = async () => {
    if (!activeMeeting) return;

    try {
      // Önce kaydı durdur
      stopRecording();

      // Interval'ı temizle
      if (recordingInterval) {
        clearInterval(recordingInterval);
        setRecordingInterval(null);
      }

      // Kısa bir süre bekle (son chunk'ların gönderilmesi için)
      await new Promise(resolve => setTimeout(resolve, 500));

      // Toplantıyı bitir
      const meeting = await meetingsAPI.endMeeting(activeMeeting.id);
      setActiveMeeting(meeting);

      // Processing durumundaysa polling başlat
      if (meeting.status === 'processing') {
        const processingInterval = setInterval(async () => {
          try {
            const updatedMeeting = await meetingsAPI.getMeeting(meeting.id);
            setActiveMeeting(updatedMeeting);

            if (updatedMeeting.status === 'completed') {
              clearInterval(processingInterval);
              setRecordingInterval(null);
            }
          } catch (err) {
            console.error('Meeting durum kontrolü hatası:', err);
            clearInterval(processingInterval);
            setRecordingInterval(null);
          }
        }, 5000);

        // Cleanup için interval'ı sakla
        setRecordingInterval(processingInterval);
      }
    } catch (err) {
      const errorDetail = err.response?.data?.detail;
      const errorMessage = Array.isArray(errorDetail)
        ? errorDetail.map(e => e.msg || JSON.stringify(e)).join(', ')
        : (typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail)) || 'Toplantı bitirilemedi';
      setError(errorMessage);
    }
  };

  const handleCancelMeeting = async () => {
    if (!activeMeeting) return;

    if (!window.confirm('Toplantıyı iptal etmek istediğinizden emin misiniz?')) {
      return;
    }

    try {
      const response = await meetingsAPI.cancelMeeting(activeMeeting.id);
      setActiveMeeting(prev => ({ ...prev, status: 'cancelled' }));

      // Interval'ı temizle
      if (recordingInterval) {
        clearInterval(recordingInterval);
        setRecordingInterval(null);
      }

      alert('Toplantı iptal edildi');

      // Ana sayfaya dön
      setActiveMeeting(null);
      setViewMode('new');
      navigate('/', { replace: true });
    } catch (err) {
      const errorDetail = err.response?.data?.detail;
      const errorMessage = Array.isArray(errorDetail)
        ? errorDetail.map(e => e.msg || JSON.stringify(e)).join(', ')
        : (typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail)) || 'Toplantı iptal edilemedi';
      setError(errorMessage);
    }
  };

  return (
    <div className="min-vh-100 bg-light py-4">
      <Container>
        {error && (
          <Alert
            variant="danger"
            className="mb-3"
            dismissible
            onClose={() => setError('')}
          >
            {error}
          </Alert>
        )}

        {!activeMeeting ? (
          <div>
            {/* Hero Section */}
            <Card
              className="mb-4 border-0 fade-in"
              style={{
                background: 'linear-gradient(135deg, #2563eb 0%, #1e40af 100%)',
                color: 'white',
              }}
            >
              <Card.Body className="p-5">
                <div className="d-flex align-items-center gap-3 mb-3">
                  <div
                    className="bg-white rounded-circle d-flex align-items-center justify-content-center"
                    style={{ width: '64px', height: '64px', backgroundColor: 'rgba(255, 255, 255, 0.2)' }}
                  >
                    <FiMic size={32} color="white" />
                  </div>
                  <div>
                    <h1 className="mb-2 fw-bold" style={{ fontSize: '2rem' }}>Toplantı Kaydı Başlat</h1>
                    <p className="mb-0 opacity-90" style={{ fontSize: '1.1rem' }}>
                      Whisper AI ile profesyonel toplantı transkriptleri ve OpenAI ile akıllı özetler
                    </p>
                  </div>
                </div>
              </Card.Body>
            </Card>

            {micPermission === false && (
              <Alert variant="warning" className="mb-3 d-flex align-items-center gap-2">
                <FiAlertCircle size={20} />
                <span>Mikrofon izni verilmedi. Lütfen tarayıcı ayarlarından mikrofon izni verin.</span>
              </Alert>
            )}

            {/* Settings Grid */}
            <Row className="mb-4 g-3">
              <Col xs={12} md={6}>
                <Card className="shadow-sm border-0 fade-in">
                  <Card.Body className="p-4">
                    <h5 className="mb-2 fw-semibold d-flex align-items-center gap-2">
                      <FiCpu size={20} className="text-primary" />
                      <span>Model Seçimi</span>
                    </h5>
                    <p className="text-muted small mb-3">Transkript kalitesi ve hızı</p>
                    <Form.Select
                      value={whisperModel}
                      onChange={(e) => {
                        setWhisperModel(e.target.value);
                        if (e.target.value === 'pyannote') {
                          setUsePyannote(true);
                        }
                      }}
                      className="form-select-lg"
                    >
                      <optgroup label="Whisper Modelleri">
                        <option value="tiny">Tiny - En hızlı (~75 MB)</option>
                        <option value="base">Base - Hızlı (~142 MB)</option>
                        <option value="small">Small - Hızlı ve dengeli (~466 MB)</option>
                        <option value="medium">Medium - Daha yüksek doğruluk (~1.5 GB)</option>
                        <option value="large">Large - En yüksek kalite (~2.9 GB)</option>
                      </optgroup>
                      <optgroup label="Diğer Modeller">
                        <option value="speechrecognition">Python SpeechRecognition - Google API (İnternet gerekli)</option>
                        <option value="elevenlabs">ElevenLabs - Konuşma Tanıma (Kişi Ayrımı Destekli)</option>
                        <option value="assemblyai">AssemblyAI - Konuşma Tanıma (Kişi Ayrımı Destekli)</option>
                        <option value="pyannote">Pyannote Diarization - Gelişmiş Konuşmacı Ayrımı</option>
                      </optgroup>
                    </Form.Select>
                  </Card.Body>
                </Card>
              </Col>

              <Col xs={12} md={6}>
                <Card className="shadow-sm border-0 fade-in">
                  <Card.Body className="p-4">
                    <h5 className="mb-2 fw-semibold d-flex align-items-center gap-2">
                      <FiGlobe size={20} className="text-primary" />
                      <span>Dil Seçimi</span>
                    </h5>
                    <p className="text-muted small mb-3">Transkript dili</p>
                    <Form.Select
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="form-select-lg"
                    >
                      <option value="tr">Türkçe</option>
                      <option value="en">English</option>
                    </Form.Select>
                  </Card.Body>
                </Card>
              </Col>
            </Row>

            {/* System Audio Capture */}
            <Row className="mb-4 g-3">
              <Col xs={12}>
                <Card className="shadow-sm border-0 fade-in" style={{ borderLeft: '4px solid #10b981' }}>
                  <Card.Body className="p-4">
                    <div className="d-flex align-items-center justify-content-between mb-2">
                      <h5 className="mb-0 fw-semibold d-flex align-items-center gap-2">
                        <FiMic size={20} className="text-success" />
                        <span>Sistem Sesi Kaydı</span>
                      </h5>
                      <Form.Check
                        type="switch"
                        id="system-audio-switch"
                        checked={captureSystemAudio}
                        onChange={(e) => setCaptureSystemAudio(e.target.checked)}
                        className="form-switch-lg"
                      />
                    </div>
                    <p className="text-muted small mb-0">
                      <strong>Online toplantılar için:</strong> Hem mikrofonunuzu hem de hoparlörden çıkan sesi (karşı tarafın sesini) kaydetmek için aktif edin.
                      Tarayıcı ekran paylaşımı izni isteyecektir - toplantı sekmesini seçip "Sekme sesini paylaş" kutucuğunu işaretleyin.
                    </p>
                  </Card.Body>
                </Card>
              </Col>
            </Row>


            {/* Pyannote Diarization Settings */}
            {(whisperModel === 'pyannote' || usePyannote) && (
              <Row className="mb-4 g-3">
                <Col xs={12}>
                  <Card className="shadow-sm border-0 fade-in" style={{ borderLeft: '4px solid #2563eb' }}>
                    <Card.Body className="p-4">
                      <h5 className="mb-3 fw-semibold d-flex align-items-center gap-2">
                        <FiLoader size={20} className="text-primary" />
                        <span>Pyannote Diarization Ayarları</span>
                      </h5>

                      <Row className="g-3">
                        <Col xs={12} md={6}>
                          <Form.Label>Konuşma Ortamı Profili</Form.Label>
                          <Form.Select
                            value={diarizationProfile}
                            onChange={(e) => setDiarizationProfile(e.target.value)}
                          >
                            <option value="auto">Otomatik (Önerilen)</option>
                            <option value="high_quality">Yüksek Kalite - Temiz Ses</option>
                            <option value="podcast_interview">Podcast/İnterview - Az Konuşmacı</option>
                            <option value="noisy_meeting">Gürültülü Toplantı</option>
                            <option value="aggressive">Agresif - Yoğun Konuşma</option>
                          </Form.Select>
                          <Form.Text className="text-muted">
                            Ses kalitesine göre uygun profil otomatik seçilir
                          </Form.Text>
                        </Col>

                        <Col xs={12} md={3}>
                          <Form.Label>Minimum Konuşmacı</Form.Label>
                          <Form.Control
                            type="number"
                            min="1"
                            max="10"
                            value={minSpeakers}
                            onChange={(e) => setMinSpeakers(e.target.value)}
                            placeholder="Otomatik"
                          />
                          <Form.Text className="text-muted">
                            Boş bırakılırsa otomatik
                          </Form.Text>
                        </Col>

                        <Col xs={12} md={3}>
                          <Form.Label>Maksimum Konuşmacı</Form.Label>
                          <Form.Control
                            type="number"
                            min="1"
                            max="20"
                            value={maxSpeakers}
                            onChange={(e) => setMaxSpeakers(e.target.value)}
                            placeholder="Otomatik"
                          />
                          <Form.Text className="text-muted">
                            Boş bırakılırsa otomatik
                          </Form.Text>
                        </Col>
                      </Row>
                    </Card.Body>
                  </Card>
                </Col>
              </Row>
            )}

            {/* File Path Processing */}
            <Row className="mb-4 g-3">
              <Col xs={12}>
                <Card className="shadow-sm border-0 fade-in">
                  <Card.Body className="p-4">
                    <div className="d-flex align-items-center justify-content-between mb-3">
                      <h5 className="mb-0 fw-semibold">Dosya Yolu ile İşleme</h5>
                      <Form.Check
                        type="switch"
                        id="process-file-switch"
                        label="Aktif Et"
                        checked={processFileMode}
                        onChange={(e) => setProcessFileMode(e.target.checked)}
                      />
                    </div>
                    {processFileMode && (
                      <div className="mt-3">
                        <Form.Label>Ses Dosyası Yolu</Form.Label>
                        <Form.Control
                          type="text"
                          placeholder="C:\path\to\audio.wav veya /path/to/audio.wav"
                          value={filePath}
                          onChange={(e) => setFilePath(e.target.value)}
                          className="mb-2"
                        />
                        <Form.Text className="text-muted">
                          Sistemdeki ses dosyasının tam yolu
                        </Form.Text>
                        <div className="mt-3">
                          <Button
                            variant="secondary"
                            onClick={async () => {
                              if (!filePath) {
                                setError('Lütfen dosya yolu girin');
                                return;
                              }
                              setLoading(true);
                              setError('');
                              try {
                                const result = await meetingsAPI.processFile({
                                  audio_file_path: filePath,
                                  whisper_model: whisperModel === 'pyannote' ? 'small' : whisperModel,
                                  language: language,
                                  use_pyannote: whisperModel === 'pyannote' || usePyannote,
                                  diarization_profile: diarizationProfile,
                                  min_speakers: minSpeakers ? parseInt(minSpeakers) : null,
                                  max_speakers: maxSpeakers ? parseInt(maxSpeakers) : null,
                                });
                                setError('');
                                alert(`Dosya işleniyor. Meeting ID: ${result.meeting_id}`);
                                navigate(`/dashboard?meeting=${result.meeting_id}`);
                              } catch (err) {
                                setError(err.response?.data?.detail || 'Dosya işleme hatası');
                              } finally {
                                setLoading(false);
                              }
                            }}
                            disabled={loading || !filePath}
                          >
                            {loading ? 'İşleniyor...' : 'Dosyayı İşle'}
                          </Button>
                        </div>
                      </div>
                    )}
                  </Card.Body>
                </Card>
              </Col>
            </Row>

            {/* Start Button */}
            <Card className="shadow-sm border-0 fade-in">
              <Card.Body className="p-4 text-center">
                <Button
                  variant="primary"
                  size="lg"
                  onClick={handleStartMeeting}
                  disabled={loading || !micPermission}
                  className="px-5 py-3 d-inline-flex align-items-center gap-2"
                  style={{
                    fontSize: '1.1rem',
                    fontWeight: '500'
                  }}
                >
                  {loading ? (
                    <>
                      <Spinner size="sm" className="me-2" />
                      <span>Başlatılıyor...</span>
                    </>
                  ) : (
                    <>
                      <FiMic size={20} />
                      <span>Toplantıyı Başlat</span>
                    </>
                  )}
                </Button>
              </Card.Body>
            </Card>
          </div>
        ) : viewMode === 'view' ? (
          <div>
            {/* Görüntüleme Modu - Tamamlanmış Toplantı */}
            <Card className="mb-3 shadow-sm border-0 fade-in">
              <Card.Body>
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <h3 className="mb-0 fw-semibold">{activeMeeting.title || 'Başlıksız Toplantı'}</h3>
                  <Button
                    variant="outline-primary"
                    onClick={() => {
                      setActiveMeeting(null);
                      setViewMode('new');
                      navigate('/', { replace: true });
                    }}
                    className="d-inline-flex align-items-center gap-2"
                  >
                    <FiArrowLeft size={18} />
                    <span>Yeni Toplantı</span>
                  </Button>
                </div>

                <div className="d-flex gap-2 flex-wrap mb-3">
                  <Badge
                    bg={activeMeeting.status === 'completed' ? 'success' : 'info'}
                    className="px-3 py-2"
                  >
                    {activeMeeting.status === 'completed' ? 'Tamamlandı' : activeMeeting.status === 'processing' ? 'İşleniyor' : 'Kayıt'}
                  </Badge>
                  <Badge bg="light" text="dark" className="px-3 py-2">Model: {activeMeeting.whisper_model}</Badge>
                  <Badge bg="light" text="dark" className="px-3 py-2">Dil: {activeMeeting.language === 'tr' ? 'Türkçe' : 'İngilizce'}</Badge>
                </div>

                {activeMeeting.start_time && (
                  <small className="text-muted d-block">
                    Başlangıç: {new Date(activeMeeting.start_time).toLocaleString('tr-TR')}
                    {activeMeeting.end_time && ` | Bitiş: ${new Date(activeMeeting.end_time).toLocaleString('tr-TR')}`}
                  </small>
                )}
              </Card.Body>
            </Card>

            {(activeMeeting.status === 'processing' || activeMeeting.status === 'completed') && (
              <div>
                {activeMeeting.status === 'processing' && (
                  <Card className="mb-3 shadow-sm border-0">
                    <Card.Body className="text-center p-4">
                      <Spinner className="mb-3" variant="primary" />
                      <h5 className="mb-2 fw-semibold">Transkript Oluşturuluyor</h5>
                      <p className="text-muted mb-0">Lütfen bekleyin, ses kaydınız işleniyor...</p>
                    </Card.Body>
                  </Card>
                )}
                <TranscriptView meetingId={activeMeeting.id} />
                <SummaryView meetingId={activeMeeting.id} />
              </div>
            )}
          </div>
        ) : (
          <div>
            {/* Kayıt Modu - Aktif Toplantı */}
            <RecordingStatus
              meeting={activeMeeting}
              isRecording={isRecording}
              audioLevel={audioLevel}
            />

            <MeetingControl
              meeting={activeMeeting}
              isRecording={isRecording}
              onPause={handlePauseMeeting}
              onResume={handleResumeMeeting}
              onEnd={handleEndMeeting}
              onCancel={handleCancelMeeting}
            />

            {(activeMeeting.status === 'processing' || activeMeeting.status === 'completed') && (
              <div className="mt-3">
                {activeMeeting.status === 'processing' && (
                  <Card className="mb-3 shadow-sm border-0">
                    <Card.Body className="text-center p-4">
                      <Spinner className="mb-3" variant="primary" />
                      <h5 className="mb-2 fw-semibold">Transkript Oluşturuluyor</h5>
                      <p className="text-muted mb-0">Lütfen bekleyin, ses kaydınız işleniyor...</p>
                    </Card.Body>
                  </Card>
                )}
                <TranscriptView meetingId={activeMeeting.id} />
                <SummaryView meetingId={activeMeeting.id} />
              </div>
            )}
          </div>
        )}
      </Container>
    </div>
  );
};

export default Dashboard;

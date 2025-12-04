import React from 'react';
import { Card, Badge, ProgressBar } from 'react-bootstrap';
import { FiCircle, FiPause, FiClock, FiCheckCircle, FiMic, FiGlobe, FiCalendar, FiFile } from 'react-icons/fi';

const RecordingStatus = ({ meeting, isRecording, audioLevel }) => {
  const getStatusConfig = () => {
    switch (meeting.status) {
      case 'recording':
        return {
          icon: <FiCircle className="text-danger pulse" size={16} />,
          text: 'Kayıt Yapılıyor',
          variant: 'danger',
          gradient: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
          bgColor: '#fee2e2'
        };
      case 'paused':
        return {
          icon: <FiPause className="text-warning" size={16} />,
          text: 'Duraklatıldı',
          variant: 'warning',
          gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
          bgColor: '#fef3c7'
        };
      case 'processing':
        return {
          icon: <FiClock className="text-info" size={16} />,
          text: 'İşleniyor...',
          variant: 'info',
          gradient: 'linear-gradient(135deg, #2563eb 0%, #1e40af 100%)',
          bgColor: '#dbeafe'
        };
      case 'completed':
        return {
          icon: <FiCheckCircle className="text-success" size={16} />,
          text: 'Tamamlandı',
          variant: 'success',
          gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
          bgColor: '#d1fae5'
        };
      default:
        return {
          icon: null,
          text: 'Bilinmiyor',
          variant: 'secondary',
          gradient: 'linear-gradient(135deg, #64748b 0%, #475569 100%)',
          bgColor: '#f1f5f9'
        };
    }
  };

  const statusConfig = getStatusConfig();

  return (
    <Card className="mb-3 shadow-sm border-0 fade-in" style={{ borderTop: `4px solid ${statusConfig.gradient.split(' ')[4]}` }}>
      <Card.Body className="p-4">
        <div className="d-flex justify-content-between align-items-start mb-3">
          <div>
            <h5 className="mb-2 fw-semibold text-dark">Toplantı Durumu</h5>
            <Badge 
              bg={statusConfig.variant}
              className="d-inline-flex align-items-center gap-2 px-3 py-2"
              style={{ 
                backgroundColor: statusConfig.bgColor,
                color: '#1e293b',
                border: 'none',
                fontWeight: '500'
              }}
            >
              {statusConfig.icon}
              <span>{statusConfig.text}</span>
            </Badge>
          </div>
          <div className="text-end">
            <small className="text-muted d-block mb-1" style={{ fontSize: '0.75rem' }}>Model</small>
            <Badge bg="light" text="dark" className="px-2 py-1" style={{ fontWeight: '500' }}>
              {meeting.whisper_model.toUpperCase()}
            </Badge>
          </div>
        </div>

        <div className="d-flex gap-4 mb-3 flex-wrap">
          <div>
            <small className="text-muted d-block mb-1" style={{ fontSize: '0.75rem' }}>
              <FiGlobe size={14} className="me-1" />
              Dil
            </small>
            <span className="fw-semibold text-dark">
              {meeting.language === 'tr' ? 'Türkçe' : 'English'}
            </span>
          </div>
          <div>
            <small className="text-muted d-block mb-1" style={{ fontSize: '0.75rem' }}>
              <FiCalendar size={14} className="me-1" />
              Başlangıç
            </small>
            <span className="fw-semibold text-dark">
              {new Date(meeting.start_time).toLocaleTimeString('tr-TR', { 
                hour: '2-digit', 
                minute: '2-digit' 
              })}
            </span>
          </div>
          {meeting.wav_backup_path && (
            <div className="flex-grow-1">
              <small className="text-muted d-block mb-1" style={{ fontSize: '0.75rem' }}>
                <FiFile size={14} className="me-1" />
                Kayıt Dosyası (WAV)
              </small>
              <span className="fw-semibold text-dark d-block" style={{ fontSize: '0.85rem', wordBreak: 'break-all' }}>
                {meeting.wav_backup_path.split('\\').pop() || meeting.wav_backup_path.split('/').pop()}
              </span>
              <small className="text-muted" style={{ fontSize: '0.7rem' }}>
                {meeting.wav_backup_path}
              </small>
            </div>
          )}
        </div>

        {isRecording && (
          <div className="mt-3">
            <div className="d-flex justify-content-between align-items-center mb-2">
              <small className="fw-medium text-dark d-flex align-items-center gap-2">
                <FiMic size={14} />
                Ses Seviyesi
              </small>
              <small className="text-muted fw-semibold">
                {Math.round((audioLevel / 255) * 100)}%
              </small>
            </div>
            <ProgressBar 
              now={Math.min((audioLevel / 255) * 100, 100)} 
              variant="danger"
              style={{ height: '6px', borderRadius: '3px' }}
            />
          </div>
        )}
      </Card.Body>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        .pulse {
          animation: pulse 1.5s ease-in-out infinite;
        }
      `}</style>
    </Card>
  );
};

export default RecordingStatus;

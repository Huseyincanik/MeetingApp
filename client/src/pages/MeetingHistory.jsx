import React, { useState, useEffect } from 'react';
import { Container, Card, Badge, Button, Spinner } from 'react-bootstrap';
import { FiClock, FiSearch, FiCalendar, FiCpu, FiGlobe } from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';
import { meetingsAPI } from '../services/api';

const MeetingHistory = () => {
  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchMeetings = async () => {
      try {
        const data = await meetingsAPI.getMeetings();
        setMeetings(data);
      } catch (err) {
        console.error('Toplantılar yüklenemedi:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchMeetings();
  }, []);

  const getStatusVariant = (status) => {
    switch (status) {
      case 'recording':
        return 'success';
      case 'paused':
        return 'warning';
      case 'processing':
        return 'info';
      case 'completed':
        return 'secondary';
      default:
        return 'secondary';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'recording':
        return 'Kayıt Yapılıyor';
      case 'paused':
        return 'Duraklatıldı';
      case 'processing':
        return 'İşleniyor';
      case 'completed':
        return 'Tamamlandı';
      default:
        return status;
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('tr-TR');
  };

  return (
    <Container className="mt-4 mb-4">
      <h2 className="mb-4 fw-semibold d-flex align-items-center gap-2">
        <FiClock size={28} className="text-primary" />
        <span>Toplantı Geçmişi</span>
      </h2>

      {loading ? (
        <div className="text-center py-5">
          <Spinner animation="border" role="status">
            <span className="visually-hidden">Yükleniyor...</span>
          </Spinner>
        </div>
      ) : meetings.length === 0 ? (
        <Card>
          <Card.Body>
            <p className="text-muted mb-0">Henüz toplantı bulunmamaktadır.</p>
          </Card.Body>
        </Card>
      ) : (
        <div className="d-flex flex-column gap-3">
          {meetings.map((meeting) => (
            <Card key={meeting.id} className="shadow-sm border-0 fade-in">
              <Card.Body>
                <div className="d-flex justify-content-between align-items-start">
                  <div className="flex-grow-1">
                    <h5 className="mb-2 fw-semibold">{meeting.title || 'Başlıksız Toplantı'}</h5>
                    <p className="text-muted small mb-2 d-flex align-items-center gap-2">
                      <FiCalendar size={14} />
                      <span>
                        Başlangıç: {formatDate(meeting.start_time)}
                        {meeting.end_time && ` | Bitiş: ${formatDate(meeting.end_time)}`}
                      </span>
                    </p>
                    <div className="d-flex gap-2 flex-wrap">
                      <Badge bg={getStatusVariant(meeting.status)} className="px-2 py-1">
                        {getStatusText(meeting.status)}
                      </Badge>
                      <Badge bg="light" text="dark" className="px-2 py-1 d-inline-flex align-items-center gap-1">
                        <FiCpu size={12} />
                        <span>{meeting.whisper_model}</span>
                      </Badge>
                      <Badge bg="light" text="dark" className="px-2 py-1 d-inline-flex align-items-center gap-1">
                        <FiGlobe size={12} />
                        <span>{meeting.language === 'tr' ? 'Türkçe' : 'English'}</span>
                      </Badge>
                    </div>
                  </div>
                  <Button
                    variant="outline-primary"
                    onClick={() => {
                      navigate(`/?meeting=${meeting.id}`, { replace: false });
                    }}
                    className="d-inline-flex align-items-center gap-2"
                  >
                    <FiSearch size={16} />
                    <span>Detay</span>
                  </Button>
                </div>
              </Card.Body>
            </Card>
          ))}
        </div>
      )}
    </Container>
  );
};

export default MeetingHistory;

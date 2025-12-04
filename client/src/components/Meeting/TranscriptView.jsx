import React, { useState, useEffect } from 'react';
import { Card, Spinner, Form, ListGroup, Badge } from 'react-bootstrap';
import { FiFileText, FiSearch, FiMic } from 'react-icons/fi';
import { transcriptsAPI } from '../../services/api';

const TranscriptView = ({ meetingId }) => {
  const [transcripts, setTranscripts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const fetchTranscript = async () => {
      try {
        const data = await transcriptsAPI.getTranscript(meetingId);
        setTranscripts(data);
        setLoading(false);
        return data.length > 0;
      } catch (err) {
        console.error('Transkript yüklenemedi:', err);
        setLoading(false);
        return false;
      }
    };

    if (!meetingId) return;

    let interval = null;
    
    const initialFetch = async () => {
      const hasData = await fetchTranscript();
      if (!hasData) {
        interval = setInterval(async () => {
          const hasDataAfterFetch = await fetchTranscript();
          if (hasDataAfterFetch && interval) {
            clearInterval(interval);
            interval = null;
          }
        }, 5000);
      }
    };

    initialFetch();
    
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [meetingId]);

  const filteredTranscripts = transcripts.filter((t) =>
    t.text.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Konuşmacıları renklendir - Kurumsal renkler
  const getSpeakerColor = (speakerId) => {
    if (!speakerId) return 'secondary';
    const colors = ['primary', 'info', 'success', 'warning'];
    const speakerNum = parseInt(speakerId.split('_')[1] || '0');
    return colors[speakerNum % colors.length];
  };

  if (loading && transcripts.length === 0) {
    return (
      <Card className="mb-3 shadow-sm border-0">
        <Card.Body className="text-center p-5">
          <Spinner animation="border" role="status" variant="primary">
            <span className="visually-hidden">Yükleniyor...</span>
          </Spinner>
        </Card.Body>
      </Card>
    );
  }

  if (transcripts.length === 0 && !loading) {
    return (
      <Card className="mb-3 shadow-sm border-0">
        <Card.Body>
          <p className="text-muted mb-0">Transkript henüz hazır değil...</p>
        </Card.Body>
      </Card>
    );
  }

  return (
    <Card className="mb-3 shadow-sm border-0 fade-in">
      <Card.Body>
        <Card.Title className="mb-3 d-flex align-items-center gap-2">
          <FiFileText size={20} className="text-primary" />
          <span>Transkript</span>
        </Card.Title>

        <Form.Group className="mb-3">
          <div className="position-relative">
            <FiSearch 
              className="position-absolute" 
              style={{ left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }}
              size={18}
            />
            <Form.Control
              type="text"
              placeholder="Ara..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ paddingLeft: '40px' }}
            />
          </div>
        </Form.Group>

        <ListGroup variant="flush">
          {filteredTranscripts.map((transcript) => (
            <ListGroup.Item 
              key={transcript.id} 
              className="px-0 mb-3 pb-3"
              style={{ borderBottom: '1px solid #e2e8f0' }}
            >
              <div className="d-flex justify-content-between align-items-start mb-2">
                <small className="text-muted d-flex align-items-center gap-2">
                  <span style={{ fontFamily: 'monospace' }}>
                    {Math.floor(transcript.start_time / 60)}:{(transcript.start_time % 60).toFixed(0).padStart(2, '0')} -{' '}
                    {Math.floor(transcript.end_time / 60)}:{(transcript.end_time % 60).toFixed(0).padStart(2, '0')}
                  </span>
                </small>
                {transcript.speaker_label && (
                  <Badge 
                    bg={getSpeakerColor(transcript.speaker_id)}
                    className="d-inline-flex align-items-center gap-1"
                  >
                    <FiMic size={12} />
                    <span>{transcript.speaker_label}</span>
                  </Badge>
                )}
              </div>
              <p className="mb-0" style={{ lineHeight: '1.7', color: '#475569' }}>{transcript.text}</p>
            </ListGroup.Item>
          ))}
        </ListGroup>
      </Card.Body>
    </Card>
  );
};

export default TranscriptView;

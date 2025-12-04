import React, { useState, useEffect } from 'react';
import { Card, Spinner, Button, Alert, ListGroup } from 'react-bootstrap';
import { FiFileText, FiStar, FiCheckCircle } from 'react-icons/fi';
import { transcriptsAPI, meetingsAPI } from '../../services/api';

const SummaryView = ({ meetingId }) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const data = await transcriptsAPI.getSummary(meetingId);
        if (data.summary) {
          setSummary(data);
          setGenerating(false);
          return true;
        }
        setLoading(false);
        return false;
      } catch (err) {
        console.error('Özet yüklenemedi:', err);
        setLoading(false);
        return false;
      }
    };

    if (!meetingId) return;

    let interval = null;
    
    const initialFetch = async () => {
      const hasSummary = await fetchSummary();
      if (!hasSummary && generating) {
        interval = setInterval(async () => {
          const hasSummaryAfterFetch = await fetchSummary();
          if (hasSummaryAfterFetch && interval) {
            clearInterval(interval);
            interval = null;
            setGenerating(false);
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
  }, [meetingId, generating]);

  const handleGenerateSummary = async () => {
    setGenerating(true);
    setError(null);
    try {
      await meetingsAPI.generateSummary(meetingId);
    } catch (err) {
      console.error('Özet oluşturma hatası:', err);
      setError(err.response?.data?.detail || 'Özet oluşturulurken bir hata oluştu');
      setGenerating(false);
    }
  };

  if (loading) {
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

  if (!summary || !summary.summary) {
    return (
      <Card className="mb-3 shadow-sm border-0 fade-in">
        <Card.Body>
          <Card.Title className="mb-3 d-flex align-items-center gap-2">
            <FiFileText size={20} />
            <span>Özet</span>
          </Card.Title>
          
          {error && (
            <Alert variant="danger" className="mb-3" dismissible onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          
          {generating ? (
            <div className="text-center py-4">
              <Spinner animation="border" className="mb-3" variant="primary" />
              <p className="text-muted mb-0">Özet oluşturuluyor, lütfen bekleyin...</p>
            </div>
          ) : (
            <div>
              <p className="text-muted mb-3">Bu toplantı için henüz özet oluşturulmamış.</p>
              <Button 
                variant="primary" 
                onClick={handleGenerateSummary}
                disabled={generating}
                className="d-inline-flex align-items-center gap-2"
              >
                <FiStar size={18} />
                <span>Özet Oluştur (OpenAI)</span>
              </Button>
            </div>
          )}
        </Card.Body>
      </Card>
    );
  }

  let keyPoints = [];
  try {
    if (typeof summary.key_points === 'string') {
      keyPoints = JSON.parse(summary.key_points);
    } else if (Array.isArray(summary.key_points)) {
      keyPoints = summary.key_points;
    }
  } catch (e) {
    console.error('Key points parse hatası:', e);
    keyPoints = [];
  }

  return (
    <Card className="mb-3 shadow-sm border-0 fade-in">
      <Card.Body>
        <Card.Title className="mb-3 d-flex align-items-center gap-2">
          <FiFileText size={20} />
          <span>Özet</span>
        </Card.Title>

        <div className="mb-4">
          <p className="mb-0" style={{ lineHeight: '1.7', color: '#475569' }}>{summary.summary}</p>
        </div>

        {keyPoints.length > 0 && (
          <div>
            <h6 className="mb-3 d-flex align-items-center gap-2">
              <FiCheckCircle size={18} className="text-primary" />
              <span>Anahtar Noktalar</span>
            </h6>
            <ListGroup variant="flush">
              {keyPoints.map((point, index) => (
                <ListGroup.Item 
                  key={index} 
                  className="px-0 py-2"
                  style={{ borderBottom: '1px solid #e2e8f0' }}
                >
                  <span className="text-muted me-2">•</span>
                  {point}
                </ListGroup.Item>
              ))}
            </ListGroup>
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export default SummaryView;

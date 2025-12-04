import React from 'react';
import { Card, Button, Spinner } from 'react-bootstrap';
import { FiPause, FiPlay, FiSquare, FiX } from 'react-icons/fi';

const MeetingControl = ({ meeting, isRecording, onPause, onResume, onEnd, onCancel }) => {
  return (
    <Card className="mb-3 shadow-sm border-0 fade-in">
      <Card.Body className="p-4">
        <div className="d-flex gap-2 justify-content-center flex-wrap">
          {meeting.status === 'recording' && (
            <>
              <Button
                variant="warning"
                onClick={onPause}
                size="lg"
                className="px-4 d-flex align-items-center gap-2"
                style={{ fontWeight: '500' }}
              >
                <FiPause size={20} />
                <span>Duraklat</span>
              </Button>
              <Button
                variant="danger"
                onClick={onEnd}
                size="lg"
                className="px-4 d-flex align-items-center gap-2"
                style={{ fontWeight: '500' }}
              >
                <FiSquare size={18} />
                <span>Bitir</span>
              </Button>
            </>
          )}
          
          {meeting.status === 'paused' && (
            <>
              <Button
                variant="success"
                onClick={onResume}
                size="lg"
                className="px-4 d-flex align-items-center gap-2"
                style={{ fontWeight: '500' }}
              >
                <FiPlay size={20} />
                <span>Devam Et</span>
              </Button>
              <Button
                variant="danger"
                onClick={onEnd}
                size="lg"
                className="px-4 d-flex align-items-center gap-2"
                style={{ fontWeight: '500' }}
              >
                <FiSquare size={18} />
                <span>Bitir</span>
              </Button>
            </>
          )}
          
          {meeting.status === 'processing' && (
            <>
              <Button 
                variant="outline-secondary" 
                disabled
                size="lg"
                className="px-4 d-flex align-items-center gap-2"
                style={{ fontWeight: '500' }}
              >
                <Spinner size="sm" className="me-2" />
                <span>İşleniyor...</span>
              </Button>
              {onCancel && (
                <Button
                  variant="danger"
                  onClick={onCancel}
                  size="lg"
                  className="px-4 d-flex align-items-center gap-2"
                  style={{ fontWeight: '500' }}
                >
                  <FiX size={20} />
                  <span>İptal Et</span>
                </Button>
              )}
            </>
          )}
        </div>
      </Card.Body>
    </Card>
  );
};

export default MeetingControl;

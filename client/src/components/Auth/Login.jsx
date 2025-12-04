import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Container, Card, Form, Button, Alert, Spinner } from 'react-bootstrap';
import { FiMic, FiLogIn, FiMail, FiLock } from 'react-icons/fi';
import { useAuth } from '../../context/AuthContext';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Giriş başarısız');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
      className="min-vh-100 d-flex align-items-center justify-content-center"
      style={{
        background: 'linear-gradient(135deg, #2563eb 0%, #1e40af 100%)',
        position: 'relative',
      }}
    >
      <Container className="position-relative" style={{ zIndex: 1, maxWidth: '540px' }}>
        <Card className="shadow-lg border-0" style={{ background: 'white' }}>
          <Card.Body className="p-5">
            <div className="text-center mb-4">
              <div 
                className="bg-primary rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                style={{ width: '64px', height: '64px', backgroundColor: '#2563eb' }}
              >
                <FiMic size={32} color="white" />
              </div>
              <h2 className="mb-2 fw-bold text-dark">
                Meeting Transcript
              </h2>
              <p className="text-muted mb-0">Hesabınıza giriş yapın</p>
            </div>
            
            {error && (
              <Alert variant="danger" dismissible onClose={() => setError('')}>
                {error}
              </Alert>
            )}

            <Form onSubmit={handleSubmit}>
              <Form.Group className="mb-3">
                <Form.Label className="fw-medium">Email</Form.Label>
                <div className="position-relative">
                  <FiMail 
                    className="position-absolute" 
                    style={{ left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }}
                    size={18}
                  />
                  <Form.Control
                    type="email"
                    placeholder="Email adresinizi girin"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    style={{ paddingLeft: '40px' }}
                  />
                </div>
              </Form.Group>
              <Form.Group className="mb-3">
                <Form.Label className="fw-medium">Şifre</Form.Label>
                <div className="position-relative">
                  <FiLock 
                    className="position-absolute" 
                    style={{ left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }}
                    size={18}
                  />
                  <Form.Control
                    type="password"
                    placeholder="Şifrenizi girin"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                    style={{ paddingLeft: '40px' }}
                  />
                </div>
              </Form.Group>
              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-100 mb-3 d-inline-flex align-items-center justify-content-center gap-2"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Spinner size="sm" />
                    <span>Giriş yapılıyor...</span>
                  </>
                ) : (
                  <>
                    <FiLogIn size={18} />
                    <span>Giriş Yap</span>
                  </>
                )}
              </Button>
              <Button
                variant="link"
                className="w-100"
                onClick={() => navigate('/register')}
              >
                Hesabınız yok mu? <span className="fw-bold text-primary">Kayıt olun</span>
              </Button>
            </Form>
          </Card.Body>
        </Card>
      </Container>
    </div>
  );
};

export default Login;

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Container, Card, Form, Button, Alert, Spinner } from 'react-bootstrap';
import { FiMic, FiUserPlus, FiMail, FiLock, FiUser } from 'react-icons/fi';
import { useAuth } from '../../context/AuthContext';

const Register = () => {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Şifreler eşleşmiyor');
      return;
    }

    if (password.length < 6) {
      setError('Şifre en az 6 karakter olmalıdır');
      return;
    }

    setLoading(true);

    try {
      await register(email, password, fullName);
      navigate('/login');
    } catch (err) {
      setError(err.response?.data?.detail || 'Kayıt başarısız');
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
              <p className="text-muted mb-0">Yeni hesap oluşturun</p>
            </div>
            
            {error && (
              <Alert variant="danger" dismissible onClose={() => setError('')}>
                {error}
              </Alert>
            )}

            <Form onSubmit={handleSubmit}>
              <Form.Group className="mb-3">
                <Form.Label className="fw-medium">Ad Soyad</Form.Label>
                <div className="position-relative">
                  <FiUser 
                    className="position-absolute" 
                    style={{ left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }}
                    size={18}
                  />
                  <Form.Control
                    type="text"
                    placeholder="Adınızı ve soyadınızı girin"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    style={{ paddingLeft: '40px' }}
                  />
                </div>
              </Form.Group>
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
                    placeholder="Şifrenizi girin (en az 6 karakter)"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    style={{ paddingLeft: '40px' }}
                  />
                </div>
              </Form.Group>
              <Form.Group className="mb-3">
                <Form.Label className="fw-medium">Şifre Tekrar</Form.Label>
                <div className="position-relative">
                  <FiLock 
                    className="position-absolute" 
                    style={{ left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }}
                    size={18}
                  />
                  <Form.Control
                    type="password"
                    placeholder="Şifrenizi tekrar girin"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    autoComplete="new-password"
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
                    <span>Kayıt yapılıyor...</span>
                  </>
                ) : (
                  <>
                    <FiUserPlus size={18} />
                    <span>Kayıt Ol</span>
                  </>
                )}
              </Button>
              <Button
                variant="link"
                className="w-100"
                onClick={() => navigate('/login')}
              >
                Zaten hesabınız var mı? <span className="fw-bold text-primary">Giriş yapın</span>
              </Button>
            </Form>
          </Card.Body>
        </Card>
      </Container>
    </div>
  );
};

export default Register;

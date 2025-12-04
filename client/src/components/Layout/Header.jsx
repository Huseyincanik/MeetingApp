import React from 'react';
import { Navbar, Nav, Container, Button } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { FiMic, FiHome, FiClock, FiLogOut, FiUser } from 'react-icons/fi';
import { useAuth } from '../../context/AuthContext';

const Header = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getInitials = (name) => {
    if (!name) return '?';
    const parts = name.split(' ');
    return parts.length >= 2 
      ? `${parts[0][0]}${parts[1][0]}`.toUpperCase()
      : parts[0][0].toUpperCase();
  };

  return (
    <Navbar bg="dark" variant="dark" expand="lg" className="shadow-sm" style={{ backgroundColor: '#1e293b' }}>
      <Container>
        <Navbar.Brand href="#" className="fw-bold fs-5 d-flex align-items-center gap-2">
          <FiMic size={24} />
          <span>Meeting Transcript</span>
        </Navbar.Brand>
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto">
            <Nav.Link 
              onClick={() => navigate('/')}
              className="d-flex align-items-center gap-2"
              style={{ cursor: 'pointer' }}
            >
              <FiHome size={18} />
              <span>Ana Sayfa</span>
            </Nav.Link>
            <Nav.Link 
              onClick={() => navigate('/history')}
              className="d-flex align-items-center gap-2"
              style={{ cursor: 'pointer' }}
            >
              <FiClock size={18} />
              <span>Geçmiş</span>
            </Nav.Link>
          </Nav>
          <Nav className="d-flex align-items-center gap-3">
            <div className="d-flex align-items-center gap-2">
              <div 
                className="bg-primary rounded-circle d-flex align-items-center justify-content-center"
                style={{ 
                  width: '36px', 
                  height: '36px', 
                  fontWeight: '600',
                  backgroundColor: '#2563eb',
                  color: 'white'
                }}
              >
                {getInitials(user?.full_name)}
              </div>
              <span className="text-white fw-medium">
                {user?.full_name}
              </span>
            </div>
            <Button 
              variant="outline-light" 
              size="sm"
              onClick={handleLogout}
              className="d-flex align-items-center gap-2"
            >
              <FiLogOut size={16} />
              <span>Çıkış</span>
            </Button>
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default Header;

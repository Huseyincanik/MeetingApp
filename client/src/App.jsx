import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import Dashboard from './pages/Dashboard';
import MeetingHistory from './pages/MeetingHistory';
import PrivateRoute from './components/PrivateRoute';
import Header from './components/Layout/Header';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/*"
            element={
              <PrivateRoute>
                <Header />
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/history" element={<MeetingHistory />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </PrivateRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;


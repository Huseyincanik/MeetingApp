import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Debug: API URL'yi log'la
console.log('🔗 API URL:', API_URL);

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - token ekle ve URL'yi log'la
api.interceptors.request.use(
  (config) => {
    const fullUrl = config.baseURL + config.url;
    console.log('📤 API Request:', config.method?.toUpperCase(), fullUrl);

    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    console.error('❌ API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor - 401 hatası durumunda logout
api.interceptors.response.use(
  (response) => {
    console.log('✅ API Response:', response.config.method?.toUpperCase(), response.config.url, response.status);
    return response;
  },
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url;
    console.error('❌ API Error:', status, url, error.message);

    if (status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    } else if (status === 404) {
      console.error('💡 404 Hatası: Backend çalışıyor mu kontrol edin:', error.config?.baseURL);
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (email, password) => {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    const response = await api.post('/api/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  register: async (email, password, fullName) => {
    const response = await api.post('/api/auth/register', {
      email,
      password,
      full_name: fullName,
    });
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await api.get('/api/auth/me');
    return response.data;
  },
};

// Meetings API
export const meetingsAPI = {
  startMeeting: async (meetingData) => {
    const response = await api.post('/api/meetings/start', meetingData);
    return response.data;
  },

  pauseMeeting: async (meetingId) => {
    const response = await api.post(`/api/meetings/${meetingId}/pause`);
    return response.data;
  },

  resumeMeeting: async (meetingId) => {
    const response = await api.post(`/api/meetings/${meetingId}/resume`);
    return response.data;
  },

  endMeeting: async (meetingId) => {
    const response = await api.post(`/api/meetings/${meetingId}/end`);
    return response.data;
  },

  getMeetings: async () => {
    const response = await api.get('/api/meetings');
    return response.data;
  },

  getMeeting: async (meetingId) => {
    const response = await api.get(`/api/meetings/${meetingId}`);
    return response.data;
  },

  generateSummary: async (meetingId) => {
    const response = await api.post(`/api/meetings/${meetingId}/generate-summary`);
    return response.data;
  },

  cancelMeeting: async (meetingId) => {
    const response = await api.post(`/api/meetings/${meetingId}/cancel`);
    return response.data;
  },

  startStreamingAudio: async (streamData) => {
    const response = await api.post('/api/meetings/stream-audio', streamData);
    return response.data;
  },

  processFile: async (fileData) => {
    const response = await api.post('/api/meetings/process-file', fileData);
    return response.data;
  },
};

// Audio API
export const audioAPI = {
  uploadChunk: async (meetingId, audioBlob) => {
    const formData = new FormData();
    formData.append('file', audioBlob, 'audio.webm');
    const response = await api.post(`/api/audio/upload/${meetingId}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

// Transcripts API
export const transcriptsAPI = {
  getTranscript: async (meetingId) => {
    const response = await api.get(`/api/transcripts/${meetingId}`);
    return response.data;
  },

  getSummary: async (meetingId) => {
    const response = await api.get(`/api/summaries/${meetingId}`);
    return response.data;
  },
};

export default api;

# 🎙️ MeetingApp - AI-Powered Meeting Transcription & Analysis

> Professional meeting transcription application with speaker diarization, real-time audio processing, and AI-powered summarization

![App Screenshot](./screenshots/app_screenshot.png)

## 📺 Demo Video

[![MeetingApp Demo]](./demo/meetingapp_demo.mp4)

---

## 📋 Table of Contents

- [Features](#-features)
- [Technology Stack](#-technology-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Environment Configuration](#-environment-configuration)
- [Model Setup](#-model-setup)
- [Database Setup](#-database-setup)
- [Running the Application](#-running-the-application)
- [API Integrations](#-api-integrations)
- [System Audio Recording](#-system-audio-recording)
- [File Processing](#-file-processing)
- [Backend Resource Usage](#-backend-resource-usage)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

---

## ✨ Features

### Core Capabilities
- 🎤 **Real-time Audio Recording** - Microphone and system audio capture
- 🗣️ **Speaker Diarization** - Advanced speaker identification using Pyannote.audio
- 📝 **Multi-language Transcription** - Turkish and English support via OpenAI Whisper
- 🤖 **AI Summarization** - Automatic meeting summaries using OpenAI GPT
- 🔊 **Noise Reduction** - AI-powered noise cancellation and audio enhancement
- 📊 **Meeting History** - Complete meeting archive with searchable transcripts
- 🌐 **WebSocket Streaming** - Real-time audio streaming and processing
- 💾 **File Upload Support** - Process pre-recorded audio files (WAV, MP3, WEBM)

### Advanced Features
- **Multiple Transcription Engines**:
  - OpenAI Whisper (local processing)
  - AssemblyAI (cloud-based real-time streaming)
  - ElevenLabs (alternative STT service)
- **Speaker Statistics** - Speaking time analysis per participant
- **Overlap Detection** - Identify simultaneous speech segments
- **Hallucination Prevention** - Advanced filtering for accurate transcripts
- **GPU Acceleration** - CUDA support for faster processing

---

## 🛠️ Technology Stack

### Backend
| Technology | Purpose |
|------------|---------|
| **FastAPI** | High-performance async web framework |
| **OpenAI Whisper** | Speech-to-text transcription (large-v3-turbo) |
| **Pyannote.audio** | Speaker diarization and identification |
| **SQLAlchemy** | Database ORM with MSSQL support |
| **PyTorch** | Deep learning framework (CUDA 12.8) |
| **WebSockets** | Real-time bidirectional communication |
| **OpenAI API** | GPT-powered meeting summarization |
| **AssemblyAI** | Cloud-based real-time transcription |
| **ElevenLabs** | Alternative speech-to-text service |

### Frontend
| Technology | Purpose |
|------------|---------|
| **React 18** | Modern UI library |
| **React Router** | Client-side routing |
| **Axios** | HTTP client for API calls |
| **React Bootstrap** | UI component library |
| **MediaRecorder API** | Browser audio recording |

### Database
- **Microsoft SQL Server** - Primary data storage

### Audio Processing
- **librosa** - Audio analysis and feature extraction
- **noisereduce** - Spectral noise reduction
- **soundfile** - Audio file I/O
- **pydub** - Audio manipulation
- **ffmpeg** - Audio format conversion

---

## 📦 Prerequisites

### System Requirements

#### Minimum Requirements
- **OS**: Windows 10/11, Linux, macOS
- **CPU**: 4-core processor (Intel i5 or equivalent)
- **RAM**: 8 GB
- **Storage**: 10 GB free space (for models)
- **Internet**: Stable connection for API calls

#### Recommended for GPU Acceleration
- **GPU**: NVIDIA GPU with CUDA 12.8 support
- **VRAM**: 6 GB+ (for large Whisper models)
- **CUDA Toolkit**: 12.8
- **cuDNN**: Compatible version

### Software Dependencies

#### Backend
- **Python**: 3.9 - 3.11 (3.10 recommended)
- **pip**: Latest version
- **ODBC Driver 17 for SQL Server** (Windows) or **unixODBC** (Linux/Mac)
- **FFmpeg**: For audio processing

#### Frontend
- **Node.js**: 16.x or higher
- **npm**: 8.x or higher

#### Database
- **Microsoft SQL Server**: 2017 or higher (Express edition works)

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/MeetingApp.git
cd MeetingApp
```

### 2. Backend Setup

#### Create Virtual Environment

```bash
cd server
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

#### Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Note for GPU Users**: PyTorch with CUDA support will be installed automatically. For CPU-only installation:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

#### Install FFmpeg

**Windows**:
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS**:
```bash
brew install ffmpeg
```

### 3. Frontend Setup

```bash
cd ../client
npm install
```

---

## ⚙️ Environment Configuration

### Backend Environment (.env)

Create a `.env` file in the `server` directory:

```bash
cd server
touch .env  # Linux/Mac
# or
type nul > .env  # Windows
```

Add the following configuration:

```env
# ===================================
# Database Configuration
# ===================================
DATABASE_URL=mssql+pyodbc://username:password@localhost/MeetingAppDB?driver=ODBC+Driver+17+for+SQL+Server

# ===================================
# JWT Authentication
# ===================================
SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ===================================
# OpenAI Configuration
# ===================================
OPENAI_API_KEY=sk-your-openai-api-key-here

# ===================================
# HuggingFace (Required for Pyannote)
# ===================================
# Get your token from: https://huggingface.co/settings/tokens
# Accept terms at: https://huggingface.co/pyannote/speaker-diarization-3.1
HF_TOKEN=hf_your_huggingface_token_here

# ===================================
# AssemblyAI (Optional - Real-time Transcription)
# ===================================
ASSEMBLYAI_API_KEY=your-assemblyai-api-key-here

# ===================================
# ElevenLabs (Optional - Alternative STT)
# ===================================
ELEVENLABS_API_KEY=your-elevenlabs-api-key-here
ELEVENLABS_MODEL_ID=scribe_v1

# ===================================
# Server Configuration
# ===================================
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# ===================================
# File Storage
# ===================================
UPLOAD_DIR=./uploads
MODELS_DIR=./models

# ===================================
# Whisper Configuration
# ===================================
DEFAULT_WHISPER_MODEL=large-v3-turbo
ENABLE_GPU=True
ENABLE_SPEAKER_DIARIZATION=True
ENABLE_NOISE_REDUCTION=True

# ===================================
# Pyannote Diarization
# ===================================
WHISPER_MODEL_PATH=./models/whisper-large-v3-turbo
ENABLE_PYANNOTE=True
DEFAULT_DIARIZATION_PROFILE=auto

# ===================================
# CORS Configuration
# ===================================
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Frontend Environment (.env)

Create a `.env` file in the `client` directory:

```env
REACT_APP_API_URL=http://localhost:8000
```

---

## 🤗 HuggingFace Setup for Pyannote

Pyannote.audio requires authentication with HuggingFace:

### Step 1: Create HuggingFace Account
1. Go to [https://huggingface.co/join](https://huggingface.co/join)
2. Create a free account

### Step 2: Accept Model Terms
1. Visit [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
2. Click "Agree and access repository"
3. Visit [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
4. Click "Agree and access repository"

### Step 3: Generate Access Token
1. Go to [Settings > Access Tokens](https://huggingface.co/settings/tokens)
2. Click "New token"
3. Name: `MeetingApp`
4. Type: `Read`
5. Click "Generate"
6. Copy the token (starts with `hf_`)

### Step 4: Add Token to .env
```env
HF_TOKEN=hf_your_token_here
```

---

## 📥 Model Setup

### Whisper Model Download

The application uses OpenAI Whisper models for transcription. Models are downloaded automatically on first use, but you can pre-download them:

```bash
cd server
python download_models.py
```

**Interactive Menu**:
```
📦 Mevcut Modeller:
  1. tiny      (~75 MB)    ○ Yüklenmedi
  2. base      (~142 MB)   ○ Yüklenmedi
  3. small     (~466 MB)   ○ Yüklenmedi
  4. medium    (~1.5 GB)   ○ Yüklenmedi
  5. large     (~2.9 GB)   ○ Yüklenmedi
  d. Model Sil
  0. Çıkış
```

**Recommended Models**:
- **Development/Testing**: `small` (466 MB)
- **Production**: `large-v3-turbo` (2.9 GB) - Best accuracy

**Command Line Download**:
```bash
# Download specific model
python download_models.py large

# Check download status
python check_download_status.py
```

### Whisper Model Storage

Models are stored in `server/models/`:
```
server/models/
├── whisper-large-v3-turbo/
│   ├── config.json
│   ├── model.safetensors
│   ├── preprocessor_config.json
│   └── tokenizer.json
└── large.pt  # Legacy Whisper format
```

### Pyannote Model Download

Pyannote models are downloaded automatically on first use (requires HF_TOKEN):

```bash
cd server
python migrate_pyannote.py
```

This downloads:
- `pyannote/speaker-diarization-3.1` (~1.5 GB)
- `pyannote/segmentation-3.0` (~500 MB)

---

## 🗄️ Database Setup

### 1. Install SQL Server

**Windows**:
- Download [SQL Server Express](https://www.microsoft.com/en-us/sql-server/sql-server-downloads)
- Install with default settings

**Linux (Ubuntu)**:
```bash
# Import Microsoft GPG key
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -

# Add repository
sudo add-apt-repository "$(wget -qO- https://packages.microsoft.com/config/ubuntu/20.04/mssql-server-2019.list)"

# Install SQL Server
sudo apt-get update
sudo apt-get install -y mssql-server

# Configure SQL Server
sudo /opt/mssql/bin/mssql-conf setup
```

**macOS**:
```bash
# Use Docker
docker run -e "ACCEPT_EULA=Y" -e "SA_PASSWORD=YourStrong@Passw0rd" \
   -p 1433:1433 --name sql_server \
   -d mcr.microsoft.com/mssql/server:2019-latest
```

### 2. Create Database

```sql
-- Connect to SQL Server (SSMS or Azure Data Studio)
CREATE DATABASE MeetingAppDB;
GO

-- Create login (if needed)
CREATE LOGIN meetingapp_user WITH PASSWORD = 'YourSecurePassword123!';
GO

USE MeetingAppDB;
GO

-- Create user
CREATE USER meetingapp_user FOR LOGIN meetingapp_user;
GO

-- Grant permissions
ALTER ROLE db_owner ADD MEMBER meetingapp_user;
GO
```

### 3. Run Migrations

```bash
cd server
python migrate_database.py
```

This creates the following tables:
- `users` - User accounts
- `meetings` - Meeting sessions
- `transcripts` - Transcription segments
- `summaries` - AI-generated summaries

---

## ▶️ Running the Application

### Development Mode

#### Start Backend
```bash
cd server
python start_server.py

# Or manually:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

#### Start Frontend
```bash
cd client
npm start
```

Frontend will be available at: `http://localhost:3000`

### Production Mode

#### Backend
```bash
cd server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Frontend
```bash
cd client
npm run build

# Serve with a static server
npx serve -s build -l 3000
```

---

## 🔌 API Integrations

### Free APIs

| Service | Purpose | Setup |
|---------|---------|-------|
| **HuggingFace** | Pyannote speaker diarization | [Get Token](https://huggingface.co/settings/tokens) |
| **OpenAI Whisper** | Local speech-to-text (no API key needed) | Pre-download models |

### Paid APIs (Optional)

| Service | Purpose | Pricing | Setup |
|---------|---------|---------|-------|
| **OpenAI API** | GPT-powered summarization | $0.002/1K tokens | [Get API Key](https://platform.openai.com/api-keys) |
| **AssemblyAI** | Real-time cloud transcription | $0.00025/second | [Get API Key](https://www.assemblyai.com/dashboard/signup) |
| **ElevenLabs** | Alternative STT service | $0.001/character | [Get API Key](https://elevenlabs.io/api) |

### API Usage Examples

#### OpenAI Summarization
```python
# Automatic summarization after transcription
summary = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": f"Summarize: {transcript}"}]
)
```

#### AssemblyAI Real-time
```python
# Real-time streaming transcription
service = AssemblyAIStreamingService()
service.start_streaming(duration_seconds=60)
```

---

## 🔊 System Audio Recording

### Windows Setup

#### Enable Stereo Mix
1. Right-click **Sound icon** in taskbar → **Sounds**
2. Go to **Recording** tab
3. Right-click empty area → **Show Disabled Devices**
4. Right-click **Stereo Mix** → **Enable**
5. Set as **Default Device**

#### Alternative: Virtual Audio Cable
1. Download [VB-Audio Virtual Cable](https://vb-audio.com/Cable/)
2. Install and restart
3. Set **CABLE Input** as default playback
4. Set **CABLE Output** as recording device in app

### macOS Setup

#### Using BlackHole
```bash
brew install blackhole-2ch

# Configure in Audio MIDI Setup:
# 1. Create Multi-Output Device
# 2. Add Built-in Output + BlackHole 2ch
# 3. Create Aggregate Device
# 4. Add Built-in Microphone + BlackHole 2ch
```

### Linux Setup

#### Using PulseAudio
```bash
# Load loopback module
pactl load-module module-loopback latency_msec=1

# List sources
pactl list short sources

# Record from monitor
parecord --device=alsa_output.pci-0000_00_1f.3.analog-stereo.monitor output.wav
```

### Browser-Based System Audio

The app supports **Screen Capture API** for system audio:

```javascript
// Frontend automatically requests system audio
const stream = await navigator.mediaDevices.getDisplayMedia({
  audio: {
    echoCancellation: false,
    noiseSuppression: false,
    autoGainControl: false
  },
  video: false
});
```

**Browser Support**:
- ✅ Chrome/Edge 94+
- ✅ Firefox 113+
- ❌ Safari (not supported)

---

## 📁 File Processing

### Supported Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| WAV | `.wav` | Preferred format (lossless) |
| MP3 | `.mp3` | Automatically converted to WAV |
| WEBM | `.webm` | Browser recording format |
| M4A | `.m4a` | Apple audio format |
| OGG | `.ogg` | Open format |

### Upload via API

```bash
curl -X POST "http://localhost:8000/api/audio/upload/123" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@meeting_recording.wav"
```

### Upload via Frontend

1. Go to **Dashboard**
2. Click **Upload File** button
3. Select audio file
4. Choose processing options:
   - Whisper model (small/medium/large)
   - Language (Turkish/English)
   - Enable speaker diarization
   - Enable noise reduction
5. Click **Process**

### Batch Processing

```bash
cd server
python -c "
from app.services.meeting_service import MeetingService
import asyncio

async def process_files():
    service = MeetingService()
    files = ['meeting1.wav', 'meeting2.wav', 'meeting3.wav']
    for file in files:
        await service.process_audio_file(file)

asyncio.run(process_files())
"
```

---

## 💻 Backend Resource Usage

### CPU Mode (No GPU)

| Model | RAM Usage | CPU Usage | Processing Speed |
|-------|-----------|-----------|------------------|
| tiny | 1-2 GB | 40-60% | 10x real-time |
| small | 2-4 GB | 60-80% | 5x real-time |
| medium | 4-6 GB | 80-100% | 3x real-time |
| large | 6-8 GB | 100% | 1-2x real-time |

### GPU Mode (CUDA)

| Model | VRAM Usage | GPU Usage | Processing Speed |
|-------|------------|-----------|------------------|
| tiny | 1 GB | 30-40% | 50x real-time |
| small | 2 GB | 40-60% | 30x real-time |
| medium | 3 GB | 60-80% | 20x real-time |
| large | 5-6 GB | 80-100% | 10-15x real-time |

### Optimization Tips

#### Reduce Memory Usage
```python
# In config.py
ENABLE_GPU = False  # Use CPU instead of GPU
DEFAULT_WHISPER_MODEL = "small"  # Use smaller model
```

#### Increase Processing Speed
```python
# Enable GPU acceleration
ENABLE_GPU = True

# Use faster model
DEFAULT_WHISPER_MODEL = "large-v3-turbo"  # Faster than large-v3

# Disable noise reduction for speed
ENABLE_NOISE_REDUCTION = False
```

#### Monitor Resources
```bash
# Check GPU usage
nvidia-smi -l 1

# Check CPU/RAM usage
python -c "
import psutil
print(f'CPU: {psutil.cpu_percent()}%')
print(f'RAM: {psutil.virtual_memory().percent}%')
"
```

### Concurrent Processing

The backend supports multiple simultaneous meetings:

```python
# In config.py
MAX_CONCURRENT_MEETINGS = 3  # Adjust based on resources

# Each meeting uses:
# - 1 Whisper model instance
# - 1 Pyannote pipeline instance
# - 1 WebSocket connection
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "No module named 'pyannote.audio'"

**Solution**:
```bash
pip install pyannote.audio
```

#### 2. "HuggingFace token not found"

**Solution**:
- Ensure `HF_TOKEN` is set in `.env`
- Accept terms at [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)

#### 3. "CUDA out of memory"

**Solution**:
```python
# Use smaller model
DEFAULT_WHISPER_MODEL = "small"

# Or disable GPU
ENABLE_GPU = False
```

#### 4. "Database connection failed"

**Solution**:
```bash
# Test connection
python -c "
from sqlalchemy import create_engine
engine = create_engine('your_database_url')
print(engine.connect())
"

# Check ODBC driver
odbcinst -j  # Linux
# or
Get-OdbcDriver  # Windows PowerShell
```

#### 5. "FFmpeg not found"

**Solution**:
```bash
# Windows
choco install ffmpeg

# Linux
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Verify installation
ffmpeg -version
```

#### 6. "Microphone not detected"

**Solution**:
- Grant browser microphone permissions
- Check system audio settings
- Test with: `python -c "import sounddevice; print(sounddevice.query_devices())"`

#### 7. "WebSocket connection failed"

**Solution**:
- Check firewall settings
- Ensure backend is running
- Verify CORS_ORIGINS in `.env`

### Debug Mode

Enable detailed logging:

```python
# In app/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Get Help

- **Issues**: [GitHub Issues](https://github.com/yourusername/MeetingApp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/MeetingApp/discussions)
- **Email**: support@meetingapp.com

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [Pyannote.audio](https://github.com/pyannote/pyannote-audio) - Speaker diarization
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [React](https://react.dev/) - Frontend library

---

## 📞 Contact

For questions or support, please open an issue on GitHub or contact the development team.

**Made with ❤️ by the MeetingApp Team**


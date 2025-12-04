from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import engine, Base
from .api import auth, meetings, audio, transcripts

# Import all models to ensure they are registered with SQLAlchemy
from .models import User, Meeting, Transcript, Summary

# Create tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Meeting Transcript App",
    description="Whisper ve OpenAI ile toplantı transkript ve özetleme uygulaması",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(meetings.router, prefix="/api/meetings", tags=["meetings"])
app.include_router(audio.router, prefix="/api/audio", tags=["audio"])
app.include_router(transcripts.router, prefix="/api", tags=["transcripts"])


@app.get("/")
async def root():
    return {"message": "Meeting Transcript App API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application configuration using environment variables."""
    
    # Flask
    FLASK_APP: str = os.getenv("FLASK_APP", "run.py")
    FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "development-only-change-before-deployment")
    
    # Server
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "5000"))
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///crimevision.db")
    
    # Storage
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "storage/uploads")
    EVIDENCE_FOLDER: str = os.getenv("EVIDENCE_FOLDER", "storage/evidence")
    REPORTS_FOLDER: str = os.getenv("REPORTS_FOLDER", "storage/reports")
    THUMBNAILS_FOLDER: str = os.getenv("THUMBNAILS_FOLDER", "storage/thumbnails")
    DERIVED_FOLDER: str = os.getenv("DERIVED_FOLDER", "storage/derived")
    # For production (Render), use data directory
    if os.getenv("RENDER"):
        data_dir = os.getenv("RENDER_DATA_DIR", "/opt/render/project/src")
        UPLOAD_FOLDER = os.path.join(data_dir, "storage", "uploads")
        EVIDENCE_FOLDER = os.path.join(data_dir, "storage", "evidence")
        REPORTS_FOLDER = os.path.join(data_dir, "storage", "reports")
        THUMBNAILS_FOLDER = os.path.join(data_dir, "storage", "thumbnails")
        DERIVED_FOLDER = os.path.join(data_dir, "storage", "derived")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", str(500 * 1024 * 1024)))  # 500MB
    
    # CORS
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    
    # AI Services
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "")
    
    # Object Detection
    DETECTION_MODEL: str = os.getenv("DETECTION_MODEL", "")
    DETECTION_MODEL_PATH: str = os.getenv("DETECTION_MODEL_PATH", "")
    DETECTION_CONFIDENCE_THRESHOLD: float = float(os.getenv("DETECTION_CONFIDENCE_THRESHOLD", "0.5"))
    
    # Audio Transcription
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    WHISPER_MODEL_PATH: str = os.getenv("WHISPER_MODEL_PATH", "")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "auto")
    ALLOW_MODEL_DOWNLOAD: bool = os.getenv("ALLOW_MODEL_DOWNLOAD", "false").lower() == "true"
    
    # Image Captioning
    CAPTIONING_MODEL: str = os.getenv("CAPTIONING_MODEL", "Salesforce/blip-image-captioning-base")
    CAPTION_MODEL_PATH: str = os.getenv("CAPTION_MODEL_PATH", "")
    
    # Video Processing
    VIDEO_FRAME_SAMPLE_INTERVAL: int = int(os.getenv("VIDEO_FRAME_SAMPLE_INTERVAL", "30"))  # Sample every 30 frames
    MAX_VIDEO_DURATION: int = int(os.getenv("MAX_VIDEO_DURATION", "3600"))  # 1 hour in seconds
    MAX_VIDEO_FRAMES: int = int(os.getenv("MAX_VIDEO_FRAMES", "120"))
    
    # Job Processing
    MAX_CONCURRENT_JOBS: int = int(os.getenv("MAX_CONCURRENT_JOBS", "2"))


settings = Settings()

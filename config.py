import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production-gvpcew-2026")
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'dynamic_class_track.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads
    UPLOAD_FOLDER = BASE_DIR / os.environ.get("UPLOAD_FOLDER", "uploads")
    TIMETABLE_UPLOAD_FOLDER = UPLOAD_FOLDER / "timetables"
    CSV_UPLOAD_FOLDER = UPLOAD_FOLDER / "csv"
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))  # 16 MB max
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
    ALLOWED_CSV_EXTENSIONS = {"csv"}

    # College Branding & Localization
    COLLEGE_NAME = os.environ.get("COLLEGE_NAME", "Gayatri Vidya Parishad College of Engineering for Women")
    COLLEGE_SHORT_NAME = os.environ.get("COLLEGE_SHORT_NAME", "GVPCEW")
    TIMEZONE = os.environ.get("TIMEZONE", "Asia/Kolkata")

    # OCR Settings
    TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "")

    # Web Push (VAPID) Settings
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
    VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "admin@gvpcew.ac.in")

    # Session & Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    # Rate Limiting & Reminders
    LOGIN_RATE_LIMIT_ATTEMPTS = 5
    LOGIN_RATE_LIMIT_WINDOW = 300  # 5 minutes


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class TestingConfig(Config):
    """Testing configuration with in-memory database and disabled CSRF."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"
    UPLOAD_FOLDER = BASE_DIR / "tests" / "test_uploads"
    TIMETABLE_UPLOAD_FOLDER = UPLOAD_FOLDER / "timetables"
    CSV_UPLOAD_FOLDER = UPLOAD_FOLDER / "csv"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

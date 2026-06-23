import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Database configuration
DB_PATH = os.getenv("DB_PATH", f"sqlite:///{BASE_DIR}/copilot.db")

# Directory configurations
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads"))
STATIC_DIR = Path(os.getenv("STATIC_DIR", BASE_DIR / "static"))

# Ensure paths exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Fallback models if using older library versions or specific setups
DEFAULT_TEXT_MODEL = os.getenv("DEFAULT_TEXT_MODEL", "gemini-1.5-pro")
DEFAULT_VISION_MODEL = os.getenv("DEFAULT_VISION_MODEL", "gemini-1.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")

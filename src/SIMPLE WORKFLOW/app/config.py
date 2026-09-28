import os
from pathlib import Path
import torch
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma_db"
ENV_FILE = BASE_DIR / ".env"

# Load environment variables from .env if present
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# CLIP Model Configuration
CLIP_MODEL_NAME = os.getenv("CLIP_MODEL_NAME", "openai/clip-vit-base-patch32")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

CHROMA_COLLECTION_NAME = "person_embeddings"

# Gemini Model Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

from dotenv import load_dotenv, find_dotenv
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

class EnvSettings(BaseSettings):
    GEMINI_API_KEY: str
    DATABASE_URL: str
    APP_API_TOKEN: str
    
    # Optional: Allow overriding paths via environment variables
    PROJECT_ROOT: Path | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

# --- Environment & Path Setup ---
load_dotenv(find_dotenv())
env_settings = EnvSettings()

# --- Default Path Logic ---
# If PROJECT_ROOT is not set via env var, calculate it relative to this file.
if env_settings.PROJECT_ROOT is None:
    # settings.py is in src/config/, so root is ../../
    env_settings.PROJECT_ROOT = Path(__file__).parent.parent.parent

PROJECT_ROOT = env_settings.PROJECT_ROOT

# --- Chats ---
TIMEOUT_SECONDS = 300
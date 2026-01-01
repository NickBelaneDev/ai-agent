# Load all the necessary Global Variables
from dotenv import load_dotenv, find_dotenv
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

class EnvSettings(BaseSettings):
    GEMINI_API_KEY: str
    DATABASE_URL: str = "sqlite+aiosqlite:///./chat_database.db"
    
    # Optional: Allow overriding paths via environment variables
    PROJECT_ROOT: Path | None = None
    HOME_AGENT_CONFIG_PATH: Path | None = None

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

# If HOME_AGENT_CONFIG_PATH is not set, default to the file in this directory.
if env_settings.HOME_AGENT_CONFIG_PATH is None:
    env_settings.HOME_AGENT_CONFIG_PATH = Path(__file__).parent / "llm_config.toml"

# Export for easier access
PROJECT_ROOT = env_settings.PROJECT_ROOT
CONFIG_PATH = env_settings.HOME_AGENT_CONFIG_PATH

# --- Chats ---
TIMEOUT_SECONDS = 300
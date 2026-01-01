# Load all the necessary Global Variables


import os
from dotenv import load_dotenv, find_dotenv
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

class EnvSettings(BaseSettings):
    GEMINI_API_KEY: str
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

# --- Environment & Path Setup ---
load_dotenv(find_dotenv())
env_settings = EnvSettings()

CONFIG_DIR = Path(__file__).parent
SRC_DIR = CONFIG_DIR.parent
PROJECT_ROOT = SRC_DIR.parent

# --- Chats ---
TIMEOUT_SECONDS = 300
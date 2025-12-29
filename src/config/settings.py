import os
from dotenv import load_dotenv, find_dotenv
from pathlib import Path





# --- Environment & Path Setup ---
load_dotenv(find_dotenv())
CONFIG_DIR = Path(__file__).parent
SRC_DIR = CONFIG_DIR.parent
PROJECT_ROOT = SRC_DIR.parent

# --- Secrets ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Application Configuration ---
DB_PATH = SRC_DIR / "database" / "minecraft_recipes.db"

# --- Chats ---
TIMEOUT_SECONDS = 300
import tomli
from pathlib import Path
from pydantic import BaseModel, Field
from google.genai import types

from src.config.logging_config import logger

class LLMConfigModel(BaseModel):
    model: str = "gemini-2.0-flash"
    thinking_budget: int = Field(..., ge=0)
    temperature: float = Field(..., ge=0, le=2)
    max_output_tokens: int = 100
    system_instruction: str = ("Someone forgot to add a system instruction... "
                               "Tell the user to open the config.toml and add one.")
    tools: list[types.Tool] = []

def load_config(path: Path) -> LLMConfigModel:
    """Loads and returns a BaseModel of the config.toml."""
    try:
        with open(path, "rb") as f:
            raw = tomli.load(f)
        logger.info(f"Configuration loaded from: {path}")
        return LLMConfigModel(**raw["config"])
    except FileNotFoundError:
        logger.error(f"Config file not found at {path}")
        raise
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise

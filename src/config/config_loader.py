import tomli

from pydantic import BaseModel, Field
from google.genai import types

from src.config.logging_config import logger
from src.config.settings import CONFIG_PATH

class LLMConfigModel(BaseModel):
    model: str = "gemini-flash-latest"
    thinking_budget: int = Field(..., ge=0, le=1)
    temperature: float = Field(..., ge=0, le=2)
    max_output_tokens: int = 100
    system_instruction: str = ("Someone forgot to add a system instruction... "
                               "Tell the user to open the config.toml and add one.")
    tools: list[types.Tool] = []

def load_config() -> LLMConfigModel:
    """Loads and returns a BaseModel of the config.toml."""
    with open(CONFIG_PATH, "rb") as f:
        raw = tomli.load(f)
    logger.info(f"Configuration loaded from: {CONFIG_PATH}")
    return LLMConfigModel(**raw["config"])


if __name__ == "__main__":
    config = load_config()
    print(config)
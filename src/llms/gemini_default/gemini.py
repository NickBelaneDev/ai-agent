from pathlib import Path
from llm_impl import GenericGemini, GeminiToolRegistry
from ...config.settings import env_settings
from ...config.config_loader import load_config, LLMConfigModel
from .tool_registry import tool_registry
from google import genai
from ...config.logging_config import logger

# Lazy initialization pattern
_default_gemini_llm = None

def get_default_gemini_llm() -> GenericGemini:
    """
    Returns the singleton instance of the DefaultGeminiLLM.
    Initializes it on the first call.
    """
    global _default_gemini_llm
    if _default_gemini_llm is None:
        logger.info("Initializing DefaultGeminiLLM...")
        try:
            config_path = Path(__file__).parent / "llm_config.toml"
            conf = load_config(path=config_path)
            
            _default_gemini_llm = _init_new_llm(env_settings.GEMINI_API_KEY, conf, tool_registry)
            logger.info("DefaultGeminiLLM initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize DefaultGeminiLLM: {e}")
            raise
            
    return _default_gemini_llm

def _init_new_llm(api_key: str, conf: LLMConfigModel, registry: GeminiToolRegistry):
     # Wenn wir hier den Path von einer config.toml geben, könnte man so modular LLMs erzeugen.
    _raw_client = genai.Client(api_key=api_key)

    new_llm = GenericGemini(
        client=_raw_client,
        model_name=conf.model,
        sys_instruction=conf.system_instruction,
        temp=conf.temperature,
        max_tokens=conf.max_output_tokens,
        registry=registry
    )
    return new_llm

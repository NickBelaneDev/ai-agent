import pytest
import tomli
from unittest.mock import mock_open, patch, MagicMock
from src.config.config_loader import load_config, LLMConfigModel
from src.config import settings

# Sample valid TOML content
VALID_TOML = b"""
[config]
model = "gemini-pro-test"
thinking_budget = 10
temperature = 0.5
max_output_tokens = 200
system_instruction = "Test instruction"
"""

# Sample invalid TOML (missing required field)
INVALID_TOML = b"""
[config]
model = "gemini-pro-test"
# thinking_budget missing
temperature = 0.5
"""

@pytest.fixture
def mock_config_path():
    # Since we removed CONFIG_PATH from config_loader.py and now pass path as argument
    # or rely on caller to provide it, we don't need to patch CONFIG_PATH global.
    # However, load_config signature is load_config(path: Path).
    # We will pass a dummy path in tests.
    return "dummy_path.toml"

def test_llm_config_model_validation():
    """Test Pydantic model validation."""
    # Valid data
    model = LLMConfigModel(
        model="test",
        thinking_budget=5,
        temperature=1.0,
        max_output_tokens=50,
        system_instruction="sys"
    )
    assert model.model == "test"
    assert model.temperature == 1.0

    # Invalid temperature (> 2)
    with pytest.raises(ValueError):
        LLMConfigModel(
            model="test",
            thinking_budget=5,
            temperature=2.1, # Too high
            max_output_tokens=50,
            system_instruction="sys"
        )

    # Invalid thinking_budget (< 0)
    with pytest.raises(ValueError):
        LLMConfigModel(
            model="test",
            thinking_budget=-1, # Negative
            temperature=1.0,
            max_output_tokens=50,
            system_instruction="sys"
        )

def test_load_config_success(mock_config_path):
    """Test successful loading of configuration."""
    with patch("builtins.open", mock_open(read_data=VALID_TOML)):
        config = load_config(mock_config_path)
        
        assert isinstance(config, LLMConfigModel)
        assert config.model == "gemini-pro-test"
        assert config.thinking_budget == 10
        assert config.temperature == 0.5
        assert config.max_output_tokens == 200
        assert config.system_instruction == "Test instruction"

def test_load_config_file_not_found(mock_config_path):
    """Test handling of missing config file."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            load_config(mock_config_path)

def test_load_config_invalid_toml(mock_config_path):
    """Test handling of invalid TOML structure (parsing error)."""
    with patch("builtins.open", mock_open(read_data=b"invalid toml [")):
        with pytest.raises(tomli.TOMLDecodeError):
            load_config(mock_config_path)

def test_load_config_validation_error(mock_config_path):
    """Test handling of valid TOML but invalid data for the model."""
    with patch("builtins.open", mock_open(read_data=INVALID_TOML)):
        with pytest.raises(Exception): # Pydantic validation error
            load_config(mock_config_path)

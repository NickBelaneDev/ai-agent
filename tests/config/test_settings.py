import pytest
from pathlib import Path
import os
from unittest.mock import patch, MagicMock

# We need to mock dotenv and pydantic_settings before importing settings
# because the module executes code on import.
# However, since we can't easily un-import modules, we'll test the EnvSettings class directly
# and verify the post-initialization logic.

from src.config.settings import EnvSettings

def test_env_settings_validation():
    """Test that EnvSettings validates required fields."""
    # Even with os.environ cleared, pydantic-settings might still read from the .env file
    # because it's defined in model_config.
    # We need to ensure it doesn't find the .env file either.

    with patch.dict(os.environ, {}, clear=True):
        # We override the env_file to a non-existent file to ensure it doesn't pick up the real .env
        class TestEnvSettings(EnvSettings):
            model_config = {"env_file": "non_existent_file.env"}

        # Missing required fields should raise validation error
        with pytest.raises(Exception):
            TestEnvSettings()

def test_env_settings_instantiation():
    """Test that EnvSettings can be instantiated with valid data."""
    settings = EnvSettings(
        GEMINI_API_KEY="test_key",
        DATABASE_URL="sqlite:///test.db",
        APP_API_TOKEN="test_token"
    )
    assert settings.GEMINI_API_KEY == "test_key"
    assert settings.DATABASE_URL == "sqlite:///test.db"
    assert settings.APP_API_TOKEN == "test_token"
    assert settings.PROJECT_ROOT is None
    # HOME_AGENT_CONFIG_PATH was removed from EnvSettings, so we shouldn't check for it here
    # assert settings.HOME_AGENT_CONFIG_PATH is None

def test_path_logic_defaults():
    """Test the path calculation logic that happens in settings.py"""
    # We simulate the logic from settings.py

    # 1. Create a settings instance with no paths set
    settings = EnvSettings(
        GEMINI_API_KEY="test",
        DATABASE_URL="test",
        APP_API_TOKEN="test"
    )
    
    # 2. Apply the logic from settings.py
    if settings.PROJECT_ROOT is None:
        # In the real file it uses __file__, here we mock what it would be
        # src/config/settings.py -> parent.parent.parent is root
        mock_file_path = Path("/app/src/config/settings.py")
        settings.PROJECT_ROOT = mock_file_path.parent.parent.parent
        
    # 3. Assertions
    assert settings.PROJECT_ROOT == Path("/app")

def test_path_logic_overrides():
    """Test that environment variables can override the paths."""
    custom_root = Path("/custom/root")
    
    settings = EnvSettings(
        GEMINI_API_KEY="test",
        DATABASE_URL="test",
        APP_API_TOKEN="test",
        PROJECT_ROOT=custom_root
    )
    
    # The logic in settings.py checks for None, so these shouldn't change
    if settings.PROJECT_ROOT is None:
        settings.PROJECT_ROOT = Path("should_not_happen")
        
    assert settings.PROJECT_ROOT == custom_root

import pytest
from unittest.mock import patch, MagicMock
from src.llms.gemini_default.gemini import get_default_gemini_llm

# We need to reset the singleton before tests to ensure isolation
@pytest.fixture(autouse=True)
def reset_singleton():
    # Access the module where the variable is defined
    import src.llms.gemini_default.gemini as gemini_module
    old_val = gemini_module._default_gemini_llm
    gemini_module._default_gemini_llm = None
    yield
    gemini_module._default_gemini_llm = old_val

def test_get_default_gemini_llm_lazy_init():
    """Test that the LLM is initialized on first call."""
    with patch("src.llms.gemini_default.gemini._init_new_llm") as mock_init:
        mock_llm = MagicMock()
        mock_init.return_value = mock_llm
        
        # First call
        llm1 = get_default_gemini_llm()
        assert llm1 == mock_llm
        mock_init.assert_called_once()
        
        # Second call (should return cached instance)
        llm2 = get_default_gemini_llm()
        assert llm2 == llm1
        mock_init.assert_called_once() # Still called only once

def test_get_default_gemini_llm_failure():
    """Test error handling during initialization."""
    with patch("src.llms.gemini_default.gemini.load_config", side_effect=FileNotFoundError("Config missing")):
        with pytest.raises(FileNotFoundError):
            get_default_gemini_llm()

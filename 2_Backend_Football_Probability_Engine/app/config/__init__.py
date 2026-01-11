"""
Configuration module for the Football Probability Engine.
This package contains OpenAI API key configuration.
The main settings are imported from the parent config.py module.
"""

# Import settings from the parent config.py module to maintain compatibility
# This allows both "from app.config import settings" and "from app.config.openai_keys import ..."
try:
    # Try importing from the parent config.py file using relative import
    from ..config import settings
except ImportError:
    # Fallback: use absolute import
    import sys
    from pathlib import Path
    
    parent_dir = Path(__file__).parent.parent
    config_path = parent_dir / "config.py"
    
    if config_path.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("app_config", config_path)
        app_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_config)
        settings = app_config.settings
    else:
        raise ImportError("Cannot find app/config.py file")

# Export settings for backward compatibility
__all__ = ['settings']


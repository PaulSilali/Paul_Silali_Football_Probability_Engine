"""
OpenAI API Keys Configuration
Hardcoded fallback keys that will be tried sequentially until one works.
"""

# List of OpenAI API keys to try sequentially
# NOTE: API keys should be set via environment variable OPENAI_API_KEY
# Hardcoded keys below are placeholders and should be replaced with actual keys
# or removed entirely for security
OPENAI_API_KEYS = [
    # "sk-proj-REDACTED_API_KEY_FOR_SECURITY",  # Removed for security - use environment variable instead
    "sk-abcdef1234567890abcdef1234567890abcdef12",
    "sk-1234567890abcdef1234567890abcdef12345678",
    "sk-abcdefabcdefabcdefabcdefabcdefabcdef12",
    "sk-7890abcdef7890abcdef7890abcdef7890abcd",
    "sk-1234abcd1234abcd1234abcd1234abcd1234abcd",
    "sk-abcd1234abcd1234abcd1234abcd1234abcd1234",
    "sk-5678efgh5678efgh5678efgh5678efgh5678efgh",
    "sk-efgh5678efgh5678efgh5678efgh5678efgh5678",
    "sk-ijkl1234ijkl1234ijkl1234ijkl1234ijkl1234",
    "sk-mnop5678mnop5678mnop5678mnop5678mnop5678",
    "sk-qrst1234qrst1234qrst1234qrst1234qrst1234",
    "sk-uvwx5678uvwx5678uvwx5678uvwx5678uvwx5678",
    "sk-1234ijkl1234ijkl1234ijkl1234ijkl1234ijkl",
    "sk-5678mnop5678mnop5678mnop5678mnop5678mnop",
    "sk-qrst5678qrst5678qrst5678qrst5678qrst5678",
    "sk-uvwx1234uvwx1234uvwx1234uvwx1234uvwx1234",
    "sk-1234abcd5678efgh1234abcd5678efgh1234abcd",
    "sk-5678ijkl1234mnop5678ijkl1234mnop5678ijkl",
    "sk-abcdqrstefghuvwxabcdqrstefghuvwxabcdqrst",
    "sk-ijklmnop1234qrstijklmnop1234qrstijklmnop",
    "sk-1234uvwx5678abcd1234uvwx5678abcd1234uvwx",
    "sk-efghijkl5678mnopabcd1234efghijkl5678mnop",
    "sk-mnopqrstuvwxabcdmnopqrstuvwxabcdmnopqrst",
    "sk-ijklmnopqrstuvwxijklmnopqrstuvwxijklmnop",
    "sk-abcd1234efgh5678abcd1234efgh5678abcd1234",
    "sk-1234ijklmnop5678ijklmnop1234ijklmnop5678",
    "sk-qrstefghuvwxabcdqrstefghuvwxabcdqrstefgh",
    "sk-uvwxijklmnop1234uvwxijklmnop1234uvwxijkl",
    "sk-abcd5678efgh1234abcd5678efgh1234abcd5678",
    "sk-ijklmnopqrstuvwxijklmnopqrstuvwxijklmnop",
    "sk-1234qrstuvwxabcd1234qrstuvwxabcd1234qrst",
    "sk-efghijklmnop5678efghijklmnop5678efghijkl",
    "sk-mnopabcd1234efghmnopabcd1234efghmnopabcd",
    "sk-ijklqrst5678uvwxijklqrst5678uvwxijklqrst",
    "sk-1234ijkl5678mnop1234ijkl5678mnop1234ijkl",
    "sk-abcdqrstefgh5678abcdqrstefgh5678abcdqrst",
    "sk-ijklmnopuvwx1234ijklmnopuvwx1234ijklmnop",
    "sk-efgh5678abcd1234efgh5678abcd1234efgh5678",
    "sk-mnopqrstijkl5678mnopqrstijkl5678mnopqrst",
    "sk-1234uvwxabcd5678uvwxabcd1234uvwxabcd5678",
    "sk-ijklmnop5678efghijklmnop5678efghijklmnop",
    "sk-abcd1234qrstuvwxabcd1234qrstuvwxabcd1234",
    "sk-1234efgh5678ijkl1234efgh5678ijkl1234efgh",
    "sk-5678mnopqrstuvwx5678mnopqrstuvwx5678mnop",
    "sk-abcdijkl1234uvwxabcdijkl1234uvwxabcdijkl",
    "sk-ijklmnopabcd5678ijklmnopabcd5678ijklmnop",
    "sk-1234efghqrstuvwx1234efghqrstuvwx1234efgh",
    "sk-5678ijklmnopabcd5678ijklmnopabcd5678ijkl",
    "sk-abcd1234efgh5678abcd1234efgh5678abcd1234",
    "sk-ijklmnopqrstuvwxijklmnopqrstuvwxijklmnop",
]


def get_openai_client():
    """
    Get OpenAI client by trying keys sequentially until one works.
    
    Returns:
        OpenAI client instance or None if all keys fail
    """
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Check if OpenAI package is installed
    try:
        import openai
        from openai import OpenAI
        # Verify it's a recent version
        if hasattr(openai, '__version__'):
            version = openai.__version__
            logger.debug(f"OpenAI package version: {version}")
    except ImportError as e:
        logger.error(f"OpenAI package not installed. Please install with: pip install openai>=1.12.0. Error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error importing OpenAI: {e}")
        return None
    
    # First, try environment variable
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        try:
            client = OpenAI(api_key=env_key)
            # Test the key with a simple request (timeout after 2 seconds)
            try:
                client.models.list(timeout=2.0)
                logger.info("Using OPENAI_API_KEY from environment")
                return client
            except Exception as e:
                error_str = str(e)
                # Check if it's an authentication error (401) or quota error (429)
                is_auth_error = "401" in error_str or "authentication" in error_str.lower() or "invalid_api_key" in error_str.lower()
                is_quota_error = "429" in error_str or "quota" in error_str.lower() or "insufficient_quota" in error_str.lower()
                
                if is_auth_error:
                    logger.debug(f"Environment OPENAI_API_KEY authentication failed: {error_str[:100]}")
                elif is_quota_error:
                    logger.debug(f"Environment OPENAI_API_KEY quota exceeded: {error_str[:100]}")
                else:
                    # If it's not an auth/quota error, still return client (might work for chat completions)
                    logger.info("Using OPENAI_API_KEY from environment (validation skipped)")
                    return client
        except Exception as e:
            logger.debug(f"Environment OPENAI_API_KEY failed: {str(e)[:100]}")
    
    # Try hardcoded keys sequentially
    for idx, key in enumerate(OPENAI_API_KEYS):
        try:
            client = OpenAI(api_key=key)
            # Test the key with a simple request (timeout after 2 seconds)
            try:
                client.models.list(timeout=2.0)
                logger.info(f"Using hardcoded OpenAI API key #{idx + 1}")
                return client
            except Exception as e:
                error_str = str(e)
                # Check if it's an authentication error (401) or quota error (429)
                is_auth_error = "401" in error_str or "authentication" in error_str.lower() or "invalid_api_key" in error_str.lower()
                is_quota_error = "429" in error_str or "quota" in error_str.lower() or "insufficient_quota" in error_str.lower()
                
                if is_auth_error:
                    logger.debug(f"OpenAI API key #{idx + 1} authentication failed: {error_str[:100]}")
                    continue  # Try next key
                elif is_quota_error:
                    logger.debug(f"OpenAI API key #{idx + 1} quota exceeded: {error_str[:100]}")
                    continue  # Try next key
                else:
                    # If it's not an auth/quota error, still return client (might work for chat completions)
                    logger.info(f"Using hardcoded OpenAI API key #{idx + 1} (validation skipped)")
                    return client
        except Exception as e:
            logger.debug(f"OpenAI API key #{idx + 1} failed: {str(e)[:100]}")
            continue
    
    logger.error("All OpenAI API keys failed. LLM features will be unavailable.")
    return None


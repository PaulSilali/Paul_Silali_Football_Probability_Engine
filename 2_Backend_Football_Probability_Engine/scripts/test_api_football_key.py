"""
Test script to verify API-Football API key works
Tests the API key by making a simple API call
Date: 2026-01-12
"""
import sys
import os
from pathlib import Path

# Get the absolute path to the backend directory
script_dir = Path(__file__).resolve().parent
backend_dir = script_dir.parent

# Add backend directory to Python path
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Change to backend directory for relative imports
os.chdir(str(backend_dir))

import requests
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_api_key_with_simple_call():
    """Test API key by making a simple API call to API-Football"""
    logger.info("=== API KEY VERIFICATION TEST ===")
    
    api_key = settings.API_FOOTBALL_KEY
    if not api_key or api_key.strip() == "":
        logger.error("✗ No API key configured")
        return False
    
    logger.info(f"Testing API key: {api_key[:8]}...")
    
    # Make a simple API call to verify the key works
    # Use the status endpoint which is lightweight
    url = "https://v3.football.api-sports.io/status"
    headers = {
        "x-apisports-key": api_key
    }
    
    verify_ssl = getattr(settings, 'VERIFY_SSL', True)
    
    try:
        logger.info("Making API call to verify key...")
        response = requests.get(url, headers=headers, timeout=10, verify=verify_ssl)
        
        # Check response status
        if response.status_code == 200:
            data = response.json()
            logger.info("✓ API key is valid!")
            logger.info(f"Response: {data.get('response', {}).get('account', {}).get('email', 'N/A')}")
            
            # Check rate limits
            rate_limit = response.headers.get('X-RateLimit-Limit', 'N/A')
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', 'N/A')
            logger.info(f"Rate limit: {rate_limit_remaining}/{rate_limit} requests remaining")
            
            return True
        elif response.status_code == 401:
            logger.error("✗ API key is invalid (401 Unauthorized)")
            logger.error("Response: " + response.text[:200])
            return False
        elif response.status_code == 403:
            logger.error("✗ API key is forbidden (403 Forbidden)")
            logger.error("Response: " + response.text[:200])
            return False
        else:
            logger.warning(f"⚠ Unexpected status code: {response.status_code}")
            logger.warning(f"Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("✗ API request timed out")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("✗ Could not connect to API-Football service")
        return False
    except Exception as e:
        logger.error(f"✗ Error testing API key: {e}", exc_info=True)
        return False

def test_api_key_with_fixtures_call():
    """Test API key by making a fixtures API call"""
    logger.info("\n=== API KEY FIXTURES ENDPOINT TEST ===")
    
    api_key = settings.API_FOOTBALL_KEY
    if not api_key or api_key.strip() == "":
        logger.error("✗ No API key configured")
        return False
    
    # Try to get fixtures for today (lightweight test)
    from datetime import date
    today = date.today()
    
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-apisports-key": api_key
    }
    params = {
        "date": today.strftime("%Y-%m-%d")
    }
    
    verify_ssl = getattr(settings, 'VERIFY_SSL', True)
    
    try:
        logger.info(f"Making fixtures API call for date: {today}...")
        response = requests.get(url, headers=headers, params=params, timeout=15, verify=verify_ssl)
        
        if response.status_code == 200:
            data = response.json()
            fixtures_count = len(data.get('response', []))
            logger.info(f"✓ Fixtures API call successful!")
            logger.info(f"Found {fixtures_count} fixtures for {today}")
            
            # Check rate limits
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', 'N/A')
            logger.info(f"Rate limit remaining: {rate_limit_remaining}")
            
            return True
        else:
            logger.warning(f"⚠ Fixtures API call returned status {response.status_code}")
            logger.warning(f"Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error testing fixtures API: {e}", exc_info=True)
        return False

def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("API-FOOTBALL API KEY VERIFICATION TEST")
    logger.info("=" * 60)
    
    # Test 1: Simple status call
    status_works = test_api_key_with_simple_call()
    
    # Test 2: Fixtures endpoint call
    fixtures_works = test_api_key_with_fixtures_call()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Status Endpoint: {'✓' if status_works else '✗'}")
    logger.info(f"Fixtures Endpoint: {'✓' if fixtures_works else '✗'}")
    
    if status_works and fixtures_works:
        logger.info("\n✓ API key is working correctly!")
    elif status_works:
        logger.warning("\n⚠ API key works but fixtures endpoint may have issues")
    else:
        logger.error("\n✗ API key is not working - check configuration")

if __name__ == "__main__":
    main()


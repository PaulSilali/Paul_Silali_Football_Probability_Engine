#!/usr/bin/env python3
"""
Test API-Football API key validity
"""
import requests
import sys
from pathlib import Path

def test_api_football_key(api_key: str):
    """Test if API-Football API key is valid"""
    print("=" * 60)
    print("API-Football API Key Test")
    print("=" * 60)
    print(f"Testing API Key: {api_key[:10]}...{api_key[-4:]}")
    print()
    
    # Test endpoint: Get leagues (simple endpoint to test authentication)
    url = "https://v3.football.api-sports.io/leagues"
    headers = {
        "x-apisports-key": api_key,
    }
    
    print(f"Making request to: {url}")
    print(f"Headers: x-apisports-key: {api_key[:10]}...")
    print()
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers:")
        for key, value in response.headers.items():
            if 'rate' in key.lower() or 'limit' in key.lower():
                print(f"  {key}: {value}")
        print()
        
        if response.status_code == 200:
            data = response.json()
            
            # Check response structure
            if "response" in data:
                leagues_count = len(data.get("response", []))
                print(f"✓ API Key is VALID!")
                print(f"✓ Successfully retrieved {leagues_count} leagues")
                print()
                
                # Show rate limit info if available
                rate_limit_remaining = response.headers.get("X-RateLimit-Remaining", "N/A")
                rate_limit_daily = response.headers.get("x-ratelimit-requests-remaining", "N/A")
                
                print("Rate Limit Information:")
                print(f"  Requests Remaining (per minute): {rate_limit_remaining}")
                print(f"  Requests Remaining (daily): {rate_limit_daily}")
                print()
                
                # Show first few leagues as proof
                if leagues_count > 0:
                    print("Sample Leagues Retrieved:")
                    for i, league in enumerate(data["response"][:5], 1):
                        league_info = league.get("league", {})
                        print(f"  {i}. {league_info.get('name', 'N/A')} ({league_info.get('country', 'N/A')})")
                
                return True
            else:
                print("⚠ Unexpected response format")
                print(f"Response: {data}")
                return False
                
        elif response.status_code == 401:
            print("❌ API Key is INVALID or EXPIRED")
            print("   Status: Unauthorized (401)")
            try:
                error_data = response.json()
                if "errors" in error_data:
                    print(f"   Error: {error_data['errors']}")
            except:
                pass
            return False
            
        elif response.status_code == 403:
            print("❌ API Key is FORBIDDEN")
            print("   Status: Forbidden (403)")
            print("   Possible reasons:")
            print("   - API key doesn't have access to this endpoint")
            print("   - Subscription plan doesn't include this feature")
            return False
            
        elif response.status_code == 429:
            print("⚠ Rate Limit EXCEEDED")
            print("   Status: Too Many Requests (429)")
            print("   Wait a few minutes and try again")
            return False
            
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Response: {error_data}")
            except:
                print(f"Response text: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request TIMEOUT")
        print("   The API server did not respond in time")
        return False
        
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR")
        print("   Could not connect to API-Football servers")
        print("   Check your internet connection")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}")
        print(f"   {str(e)}")
        return False

def test_fixture_endpoint(api_key: str):
    """Test fixture endpoint (more specific test)"""
    print()
    print("=" * 60)
    print("Testing Fixture Endpoint (More Specific Test)")
    print("=" * 60)
    
    # Test with a known league and date
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-apisports-key": api_key,
    }
    params = {
        "league": 39,  # Premier League
        "season": 2024,
        "last": 1  # Get last 1 fixture
    }
    
    print(f"Testing endpoint: {url}")
    print(f"Parameters: league=39 (Premier League), season=2024, last=1")
    print()
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        print(f"Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "response" in data:
                fixtures_count = len(data.get("response", []))
                print(f"✓ Fixture endpoint works! Retrieved {fixtures_count} fixture(s)")
                return True
            else:
                print("⚠ Unexpected response format")
                return False
        else:
            print(f"⚠ Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    # Get API key from command line or use default
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        # Try to get from environment or use the provided key
        api_key = "b41227796150918ad901f64b9bdf3b76"
    
    if not api_key:
        print("❌ No API key provided!")
        print("Usage: python test_api_football_key.py <API_KEY>")
        sys.exit(1)
    
    # Test the API key
    success = test_api_football_key(api_key)
    
    if success:
        # If basic test passes, test fixture endpoint
        test_fixture_endpoint(api_key)
    
    print()
    print("=" * 60)
    if success:
        print("✓ API Key Test: PASSED")
        print("  Your API key is working correctly!")
    else:
        print("❌ API Key Test: FAILED")
        print("  Please check your API key and try again")
    print("=" * 60)
    
    sys.exit(0 if success else 1)


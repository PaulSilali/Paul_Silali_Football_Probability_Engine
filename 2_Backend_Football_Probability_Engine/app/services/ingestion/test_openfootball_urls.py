"""
Test OpenFootball URLs to verify which leagues are actually available

This script tests all 17 leagues against OpenFootball repositories to determine
which ones are actually available for download.
"""
import requests
from typing import Dict, List, Tuple
from app.services.ingestion.ingest_openfootball import (
    LEAGUE_CODE_TO_OPENFOOTBALL,
    convert_season_code_to_openfootball,
    OPENFOOTBALL_BASE_URL
)

def test_openfootball_url(
    repository: str,
    country: str,
    league_file: str,
    season: str
) -> Tuple[bool, str]:
    """
    Test if an OpenFootball URL exists and is accessible
    
    Returns:
        (is_available, url_tested)
    """
    base_path = f"{repository}/master/{country}"
    
    # Try different file patterns
    file_patterns = [
        f"{season}/{league_file}.txt",
        f"{season}/{league_file}.yml",
        f"{league_file}.txt",
        f"{league_file}.yml",
        f"{season}/1-{league_file.split('-', 1)[-1]}.txt" if '-' in league_file else f"{season}/{league_file}.txt",
    ]
    
    for file_pattern in file_patterns:
        url = f"{OPENFOOTBALL_BASE_URL}/{base_path}/{file_pattern}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                content = response.text.strip()
                # Validate it's not HTML error page
                if content and not (content.startswith('<!DOCTYPE') or content.startswith('<html') or content.startswith('<HTML')):
                    return True, url
        except requests.RequestException:
            continue
    
    return False, f"{OPENFOOTBALL_BASE_URL}/{base_path}/{file_patterns[0]}"


def test_all_leagues(season: str = "2324") -> Dict[str, Dict]:
    """
    Test all 17 leagues to see which are available in OpenFootball
    
    Args:
        season: Season code (e.g., '2324' for 2023-24)
    
    Returns:
        Dictionary mapping league codes to availability status
    """
    results = {}
    openfootball_season = convert_season_code_to_openfootball(season)
    
    for league_code in LEAGUE_CODE_TO_OPENFOOTBALL.keys():
        path_info = LEAGUE_CODE_TO_OPENFOOTBALL[league_code]
        repository, country, league_file, _ = path_info
        
        is_available, url = test_openfootball_url(
            repository, country, league_file, openfootball_season
        )
        
        results[league_code] = {
            'available': is_available,
            'repository': repository,
            'country': country,
            'league_file': league_file,
            'url': url,
            'season_tested': openfootball_season
        }
    
    return results


def print_availability_report(results: Dict[str, Dict]):
    """Print a formatted report of league availability"""
    print("\n" + "="*80)
    print("OPENFOOTBALL LEAGUE AVAILABILITY REPORT")
    print("="*80)
    
    available = []
    unavailable = []
    
    for league_code, info in results.items():
        if info['available']:
            available.append((league_code, info))
        else:
            unavailable.append((league_code, info))
    
    print(f"\n✅ AVAILABLE: {len(available)}/{len(results)} leagues")
    print("-" * 80)
    for league_code, info in available:
        print(f"  ✓ {league_code:6s} | {info['repository']:15s} | {info['url']}")
    
    print(f"\n❌ UNAVAILABLE: {len(unavailable)}/{len(results)} leagues")
    print("-" * 80)
    for league_code, info in unavailable:
        print(f"  ✗ {league_code:6s} | {info['repository']:15s} | {info['url']}")
    
    print("\n" + "="*80)
    print(f"SUMMARY: {len(available)} available, {len(unavailable)} unavailable")
    print("="*80 + "\n")


if __name__ == "__main__":
    # Test with recent season
    print("Testing OpenFootball URLs for season 2023-24...")
    results = test_all_leagues("2324")
    print_availability_report(results)


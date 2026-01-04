"""
Standalone script to test OpenFootball URL availability

Run this from the project root:
    python test_openfootball_availability.py
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from typing import Dict, Tuple

# Mapping of league codes to OpenFootball repository and path structure
LEAGUE_CODE_TO_OPENFOOTBALL = {
    # Europe - from europe repository
    'SWE1': ('europe', 'sweden', '1-allsvenskan'),
    'FIN1': ('europe', 'finland', '1-veikkausliiga'),
    'RO1': ('europe', 'romania', '1-liga'),
    'RUS1': ('europe', 'russia', '1-premier'),
    'IRL1': ('europe', 'ireland', '1-premier'),
    'CZE1': ('europe', 'czech-republic', '1-liga'),
    'CRO1': ('europe', 'croatia', '1-hnl'),
    'SRB1': ('europe', 'serbia', '1-superliga'),
    'UKR1': ('europe', 'ukraine', '1-premier'),
    
    # Americas - from world repository
    'ARG1': ('south-america', 'argentina', '1-primera'),
    'BRA1': ('south-america', 'brazil', '1-serie-a'),
    'MEX1': ('world', 'mexico', '1-liga-mx'),
    'USA1': ('world', 'usa', '1-mls'),
    
    # Asia & Oceania - from world repository
    'CHN1': ('world', 'china', '1-super-league'),
    'JPN1': ('world', 'japan', '1-j1-league'),
    'KOR1': ('world', 'south-korea', '1-k-league'),
    'AUS1': ('world', 'australia', '1-a-league'),
}

OPENFOOTBALL_BASE_URL = "https://raw.githubusercontent.com/openfootball"


def convert_season_code_to_openfootball(season_code: str) -> str:
    """Convert season code (e.g., '2324') to OpenFootball format (e.g., '2023-24')"""
    if len(season_code) == 4:
        year1 = 2000 + int(season_code[:2])
        year2 = int(season_code[2:])
        return f"{year1}-{year2:02d}"
    return season_code


def test_openfootball_url(
    repository: str,
    country: str,
    league_file: str,
    season: str
) -> Tuple[bool, str]:
    """Test if an OpenFootball URL exists and is accessible"""
    base_path = f"{repository}/master/{country}"
    
    # Try different file patterns
    file_patterns = [
        f"{season}/{league_file}.txt",
        f"{season}/{league_file}.yml",
        f"{league_file}.txt",
        f"{league_file}.yml",
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
    """Test all 17 leagues to see which are available in OpenFootball"""
    results = {}
    openfootball_season = convert_season_code_to_openfootball(season)
    
    print(f"Testing OpenFootball URLs for season {openfootball_season} ({season})...")
    print("=" * 80)
    
    for league_code in LEAGUE_CODE_TO_OPENFOOTBALL.keys():
        path_info = LEAGUE_CODE_TO_OPENFOOTBALL[league_code]
        repository, country, league_file = path_info
        
        print(f"Testing {league_code}...", end=" ")
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
        
        if is_available:
            print(f"✅ FOUND: {url}")
        else:
            print(f"❌ NOT FOUND")
    
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
    results = test_all_leagues("2324")
    print_availability_report(results)


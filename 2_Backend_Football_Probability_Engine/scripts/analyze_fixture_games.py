"""
Deep analysis of how to handle different types of games from fixture list
"""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def analyze_fixture_games():
    """Analyze each game type and how to handle them"""
    
    print("=" * 80)
    print("FIXTURE GAMES ANALYSIS - HOW TO HANDLE EACH TYPE")
    print("=" * 80)
    
    # Game data from user
    games = [
        {"num": 1, "type": "International", "country": "International", "home": "Algeria", "away": "Nigeria", "date": "10/01/26"},
        {"num": 2, "type": "Club", "country": "Spain", "home": "Girona FC", "away": "CA Osasuna", "date": "10/01/26"},
        {"num": 3, "type": "Club", "country": "England", "home": "Tottenham Hotspur", "away": "Aston Villa", "date": "10/01/26"},
        {"num": 4, "type": "Club", "country": "Italy", "home": "US Lecce", "away": "Parma Calcio", "date": "11/01/26"},
        {"num": 5, "type": "Club", "country": "Spain", "home": "CD Leganes", "away": "Real Valladolid", "date": "11/01/26"},
        {"num": 6, "type": "Club", "country": "Turkey", "home": "Sivasspor", "away": "Erzurumspor FK", "date": "11/01/26"},
        {"num": 7, "type": "Club", "country": "England", "home": "Swansea City", "away": "West Bromwich Albion", "date": "11/01/26"},
        {"num": 8, "type": "Club", "country": "Spain", "home": "Unionistas de Salamanca CF", "away": "Zamora CF", "date": "11/01/26"},
        {"num": 9, "type": "Club", "country": "Spain", "home": "Granada CF", "away": "CD Castellon", "date": "11/01/26"},
        {"num": 10, "type": "Club", "country": "Spain", "home": "Levante UD", "away": "Espanyol Barcelona", "date": "11/01/26"},
        {"num": 11, "type": "Club", "country": "Greece", "home": "OFI Crete", "away": "Asteras Tripolis", "date": "11/01/26"},
        {"num": 12, "type": "Club", "country": "Portugal", "home": "GD Chaves", "away": "Maritimo Madeira", "date": "11/01/26"},
        {"num": 13, "type": "Club", "country": "Portugal", "home": "Nacional da Madeira", "away": "Santa Clara Azores", "date": "11/01/26"},
        {"num": 14, "type": "Club", "country": "Turkey", "home": "Pendikspor", "away": "Bodrum FK", "date": "11/01/26"},
        {"num": 15, "type": "Club", "country": "Italy", "home": "Hellas Verona", "away": "Lazio Rome", "date": "11/01/26"},
        {"num": 16, "type": "Club", "country": "France", "home": "FC Nantes", "away": "OGC Nice", "date": "11/01/26"},
        {"num": 17, "type": "Club", "country": "Portugal", "home": "UD Oliveirense", "away": "CD Feirense", "date": "11/01/26"},
    ]
    
    # League code mappings (from data_ingestion.py)
    country_to_league_codes = {
        "Spain": ["SP1", "SP2"],  # La Liga, Segunda Division
        "England": ["E0", "E1", "E2", "E3"],  # Premier League, Championship, League 1, League 2
        "Italy": ["I1", "I2"],  # Serie A, Serie B
        "Turkey": ["T1"],  # Super Lig
        "Greece": ["G1"],  # Super League
        "Portugal": ["P1", "P2"],  # Primeira Liga, Segunda Liga
        "France": ["F1", "F2"],  # Ligue 1, Ligue 2
        "International": ["INT"]  # Special code for international
    }
    
    print("\n1. GAME-BY-GAME ANALYSIS")
    print("-" * 80)
    
    for game in games:
        print(f"\nGame #{game['num']}: {game['home']} vs {game['away']}")
        print(f"  Type: {game['type']}")
        print(f"  Country: {game['country']}")
        print(f"  Date: {game['date']}")
        
        if game['type'] == "International":
            print(f"  ⚠️  ISSUE: International game - requires special handling")
            print(f"  ✅ SOLUTION: Assign to 'INT' league (International Matches)")
            print(f"  📋 Steps:")
            print(f"     1. Create/verify 'INT' league exists")
            print(f"     2. Create teams: 'Algeria' and 'Nigeria' in INT league")
            print(f"     3. Create fixture with league_id = INT league")
            print(f"     4. Draw structural data:")
            print(f"        - Team Form: Will work (if matches exist)")
            print(f"        - H2H Stats: Will work (if matches exist)")
            print(f"        - Elo Ratings: Will work")
            print(f"        - League Priors: Need special handling (no league priors for INT)")
            print(f"        - Weather: Will work (uses country)")
            print(f"        - Rest Days: Will work")
            print(f"        - Other: Will work")
        else:
            # Club game - need to determine league
            possible_leagues = country_to_league_codes.get(game['country'], [])
            if possible_leagues:
                print(f"  ✅ Club game - can determine league from country")
                print(f"  📋 Possible leagues: {', '.join(possible_leagues)}")
                print(f"  ⚠️  Need to determine correct league tier:")
                print(f"     - Check team names against database")
                print(f"     - Use team's existing league_id if found")
                print(f"     - Or infer from team tier (top tier = SP1/E0/I1, etc.)")
                print(f"  ✅ Draw structural data: Will work normally")
            else:
                print(f"  ⚠️  Country '{game['country']}' not in mapping")
                print(f"  📋 Need to add league code mapping")
    
    print("\n\n2. LEAGUE IDENTIFICATION STRATEGY")
    print("-" * 80)
    print("""
    For Club Games:
    
    Strategy 1: Lookup by Team Name (Best)
    ├─ Query teams table for home_team name
    ├─ Get team's league_id
    ├─ Use that league_id for fixture
    └─ ✅ Most accurate
    
    Strategy 2: Country + Tier Inference
    ├─ If team not found, infer from country
    ├─ Check team tier (top tier vs lower tier)
    ├─ Map to league code (E0 = top, E1 = second, etc.)
    └─ ⚠️ Less accurate, may need manual correction
    
    Strategy 3: Default to Top Tier
    ├─ If uncertain, default to top tier league
    ├─ E.g., Spain → SP1, England → E0
    └─ ⚠️ May be wrong for lower tier teams
    
    For International Games:
    
    Strategy: Always Use INT League
    ├─ Create/verify INT league exists
    ├─ All international teams → INT league
    └─ ✅ Consistent handling
    """)
    
    print("\n3. IMPLEMENTATION PLAN")
    print("-" * 80)
    print("""
    Step 1: Create International League (One-time)
    ┌─────────────────────────────────────────────────┐
    │ INSERT INTO leagues (code, name, country, tier,   │
    │                      is_active) VALUES           │
    │ ('INT', 'International Matches', 'World', 0,    │
    │  TRUE);                                          │
    └─────────────────────────────────────────────────┘
    
    Step 2: Modify Fixture Creation Logic
    ┌─────────────────────────────────────────────────┐
    │ IF fixture.type == "International":            │
    │     league_code = "INT"                         │
    │ ELSE:                                            │
    │     league_code = infer_from_team_or_country()  │
    └─────────────────────────────────────────────────┘
    
    Step 3: Team Resolution
    ┌─────────────────────────────────────────────────┐
    │ FOR each team in fixture:                        │
    │     team = resolve_team_safe(name, league_id)  │
    │     IF not found:                               │
    │         IF international:                        │
    │             create_team(name, INT_league_id)   │
    │         ELSE:                                   │
    │             create_team(name, inferred_league)  │
    └─────────────────────────────────────────────────┘
    
    Step 4: Draw Structural Data Handling
    ┌─────────────────────────────────────────────────┐
    │ IF league_code == "INT":                        │
    │     # Skip league priors (no league context)     │
    │     # Use default draw rate (e.g., 0.25)         │
    │     # Calculate other features normally          │
    │ ELSE:                                            │
    │     # Use normal draw structural logic           │
    └─────────────────────────────────────────────────┘
    """)
    
    print("\n4. CODE CHANGES NEEDED")
    print("-" * 80)
    print("""
    File: app/services/fixture_creation.py (or similar)
    
    1. Add league inference function:
       def infer_league_from_fixture(fixture_data):
           if fixture_data.get('type') == 'International':
               return get_or_create_league('INT')
           else:
               # Try team lookup first
               league_id = lookup_team_league(fixture_data['home_team'])
               if league_id:
                   return league_id
               # Fallback to country mapping
               return infer_league_from_country(fixture_data['country'])
    
    2. Modify team creation:
       def create_fixture_teams(fixture_data, league_id):
           home_team = resolve_or_create_team(
               fixture_data['home_team'], 
               league_id
           )
           away_team = resolve_or_create_team(
               fixture_data['away_team'], 
               league_id
           )
           return home_team, away_team
    
    3. Add INT league creation script:
       def ensure_international_league_exists(db):
           league = db.query(League).filter(League.code == 'INT').first()
           if not league:
               league = League(
                   code='INT',
                   name='International Matches',
                   country='World',
                   tier=0,
                   is_active=True
               )
               db.add(league)
               db.commit()
    """)
    
    print("\n5. DRAW STRUCTURAL DATA ADJUSTMENTS")
    print("-" * 80)
    print("""
    For INT League:
    
    ✅ Will Work (No Changes Needed):
    - Team Form: Calculates from matches (works fine)
    - H2H Stats: Calculates from matches (works fine)
    - Elo Ratings: Calculates normally (works fine)
    - Rest Days: Calculates from match dates (works fine)
    - Weather: Uses country coordinates (works fine)
    - Referee: Can assign referees (works fine)
    - Odds Movement: Tracks odds changes (works fine)
    - XG Data: Can ingest xG (works fine)
    
    ⚠️ Needs Special Handling:
    - League Priors: No league context for international
      → Use default draw rate (e.g., 0.25)
      → Or calculate from all international matches
      → Or skip league prior adjustment
    
    - League Structure: Not applicable
      → Skip league structure features
      → No relegation/promotion zones
    """)
    
    print("\n6. TESTING CHECKLIST")
    print("-" * 80)
    print("""
    ✅ Test Cases:
    
    1. International Game (Algeria vs Nigeria)
       ├─ Create INT league
       ├─ Create teams in INT league
       ├─ Create fixture
       ├─ Verify draw structural data works
       └─ Verify probability calculation works
    
    2. Club Game - Top Tier (Tottenham vs Aston Villa)
       ├─ Resolve teams (should find in E0)
       ├─ Create fixture with E0 league
       ├─ Verify all draw structural data works
       └─ Verify probability calculation works
    
    3. Club Game - Lower Tier (Swansea vs West Brom)
       ├─ Resolve teams (should find in E1 or E2)
       ├─ Create fixture with correct league
       ├─ Verify draw structural data works
       └─ Verify probability calculation works
    
    4. Club Game - Unknown League (New teams)
       ├─ Infer league from country
       ├─ Create teams in inferred league
       ├─ Create fixture
       └─ Verify system handles gracefully
    """)
    
    print("\n7. SUMMARY")
    print("-" * 80)
    print("""
    ✅ Club Games: Will work with proper league inference
    ✅ International Games: Will work with INT league creation
    ⚠️  League Inference: Need robust team lookup + country mapping
    ⚠️  League Priors: Need special handling for INT league
    
    Next Steps:
    1. Create INT league (one-time SQL script)
    2. Add league inference logic to fixture creation
    3. Add special handling for INT league in draw structural data
    4. Test with provided fixture list
    """)
    
    return True

if __name__ == "__main__":
    analyze_fixture_games()


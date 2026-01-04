"""
Comprehensive Jackpot Test Suite
Extracts jackpot data from images and tests all jackpot-related features
"""
import os
import sys
import time
import json
import requests
from datetime import datetime, date
from typing import Dict, List, Optional
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use app's database connection
from app.db.session import SessionLocal

# API base URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

# Data storage path
DATA_STORAGE_PATH = Path("data/1_data_ingestion/Historical Match_Odds_Data")
DATA_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# Extracted jackpot data from images
JACKPOT_DATA = [
    {
        "jackpot_id": "JK-2024-1129",
        "name": "15M MIDWEEK JACKPOT - 29/11",
        "kickoff_date": "2024-11-29",
        "fixtures": [
            {"order": 1, "home": "SUNDERLAND", "away": "BOURNEMOUTH", "home_odds": 3.00, "draw_odds": 3.45, "away_odds": 2.47, "result": "H", "league": "Premier League"},
            {"order": 2, "home": "LEVERKUSEN", "away": "DORTMUND", "home_odds": 2.55, "draw_odds": 3.65, "away_odds": 2.65, "result": "A", "league": "Bundesliga"},
            {"order": 3, "home": "EVERTON", "away": "NEWCASTLE", "home_odds": 2.95, "draw_odds": 3.35, "away_odds": 2.55, "result": "A", "league": "Premier League"},
            {"order": 4, "home": "LEVANTE", "away": "ATHLETIC BILBAO", "home_odds": 3.60, "draw_odds": 3.50, "away_odds": 2.14, "result": "A", "league": "LaLiga"},
            {"order": 5, "home": "TOTTENHAM", "away": "FULHAM", "home_odds": 2.09, "draw_odds": 3.65, "away_odds": 3.65, "result": "A", "league": "Premier League"},
            {"order": 6, "home": "US LECCE", "away": "TORINO FC", "home_odds": 2.85, "draw_odds": 3.00, "away_odds": 2.80, "result": "H", "league": "Serie A"},
            {"order": 7, "home": "CRYSTAL PALACE", "away": "MAN UTD", "home_odds": 2.60, "draw_odds": 3.60, "away_odds": 2.75, "result": "A", "league": "Premier League"},
            {"order": 8, "home": "REAL SOCIEDAD", "away": "VILLARREAL", "home_odds": 2.70, "draw_odds": 3.55, "away_odds": 2.70, "result": "A", "league": "LaLiga"},
            {"order": 9, "home": "NOTTINGHAM", "away": "BRIGHTON", "home_odds": 2.70, "draw_odds": 3.50, "away_odds": 2.70, "result": "A", "league": "Premier League"},
            {"order": 10, "home": "HAMBURG", "away": "STUTTGART", "home_odds": 3.05, "draw_odds": 3.80, "away_odds": 2.23, "result": "H", "league": "Bundesliga"},
            {"order": 11, "home": "SEVILLA", "away": "BETIS", "home_odds": 3.00, "draw_odds": 3.45, "away_odds": 2.46, "result": "A", "league": "LaLiga"},
            {"order": 12, "home": "LORIENT", "away": "NICE", "home_odds": 2.48, "draw_odds": 3.55, "away_odds": 2.80, "result": "H", "league": "Ligue 1"},
            {"order": 13, "home": "CHELSEA", "away": "ARSENAL", "home_odds": 3.30, "draw_odds": 3.45, "away_odds": 2.29, "result": "D", "league": "Premier League"},
            {"order": 14, "home": "FREIBURG", "away": "MAINZ", "home_odds": 2.10, "draw_odds": 3.45, "away_odds": 3.65, "result": "H", "league": "Bundesliga"},
            {"order": 15, "home": "AS ROMA", "away": "NAPOLI", "home_odds": 2.60, "draw_odds": 3.00, "away_odds": 3.10, "result": "A", "league": "Serie A"},
        ]
    },
    {
        "jackpot_id": "JK-2024-1108",
        "name": "15M MIDWEEK JACKPOT - 08/11",
        "kickoff_date": "2024-11-08",
        "fixtures": [
            {"order": 1, "home": "TOTTENHAM", "away": "MAN UTD", "home_odds": 2.70, "draw_odds": 3.75, "away_odds": 2.55, "result": "D", "league": "Premier League"},
            {"order": 2, "home": "GIRONA", "away": "ALAVES", "home_odds": 2.48, "draw_odds": 3.25, "away_odds": 3.15, "result": "H", "league": "LaLiga"},
            {"order": 3, "home": "US LECCE", "away": "HELLAS VERONA", "home_odds": 2.75, "draw_odds": 3.00, "away_odds": 2.90, "result": "D", "league": "Serie A"},
            {"order": 4, "home": "HOFFENHEIM", "away": "LEIPZIG", "home_odds": 2.75, "draw_odds": 3.95, "away_odds": 2.37, "result": "H", "league": "Bundesliga"},
            {"order": 5, "home": "ESPANYOL", "away": "VILLARREAL", "home_odds": 2.85, "draw_odds": 3.60, "away_odds": 2.50, "result": "A", "league": "LaLiga"},
            {"order": 6, "home": "BRENTFORD", "away": "NEWCASTLE", "home_odds": 3.00, "draw_odds": 3.50, "away_odds": 2.44, "result": "H", "league": "Premier League"},
            {"order": 7, "home": "NOTTINGHAM", "away": "LEEDS", "home_odds": 2.28, "draw_odds": 3.40, "away_odds": 3.40, "result": "H", "league": "Premier League"},
            {"order": 8, "home": "CRYSTAL PALACE", "away": "BRIGHTON", "home_odds": 2.35, "draw_odds": 3.60, "away_odds": 3.05, "result": "D", "league": "Premier League"},
            {"order": 9, "home": "BOLOGNA FC", "away": "NAPOLI", "home_odds": 3.00, "draw_odds": 3.15, "away_odds": 2.60, "result": "H", "league": "Serie A"},
            {"order": 10, "home": "GENOA", "away": "ACF FIORENTINA", "home_odds": 3.00, "draw_odds": 3.20, "away_odds": 2.50, "result": "D", "league": "Serie A"},
            {"order": 11, "home": "LORIENT", "away": "TOULOUSE", "home_odds": 3.10, "draw_odds": 3.30, "away_odds": 2.40, "result": "D", "league": "Ligue 1"},
            {"order": 12, "home": "ANGERS", "away": "AUXERRE", "home_odds": 2.70, "draw_odds": 3.15, "away_odds": 2.85, "result": "H", "league": "Ligue 1"},
            {"order": 13, "home": "STRASBOURG", "away": "LILLE", "home_odds": 2.85, "draw_odds": 3.45, "away_odds": 2.50, "result": "H", "league": "Ligue 1"},
            {"order": 14, "home": "VALENCIA", "away": "BETIS", "home_odds": 2.95, "draw_odds": 3.40, "away_odds": 2.50, "result": "D", "league": "LaLiga"},
            {"order": 15, "home": "MALLORCA", "away": "GETAFE", "home_odds": 2.49, "draw_odds": 3.05, "away_odds": 3.35, "result": "H", "league": "LaLiga"},
        ]
    },
    {
        "jackpot_id": "JK-2024-1122",
        "name": "15M MIDWEEK JACKPOT - 22/11",
        "kickoff_date": "2024-11-22",
        "fixtures": [
            {"order": 1, "home": "AUGSBURG", "away": "HAMBURG", "home_odds": 2.33, "draw_odds": 3.65, "away_odds": 2.95, "result": "H", "league": "Bundesliga"},
            {"order": 2, "home": "WOLFSBURG", "away": "LEVERKUSEN", "home_odds": 3.10, "draw_odds": 3.75, "away_odds": 2.22, "result": "A", "league": "Bundesliga"},
            {"order": 3, "home": "HEIDENHEIM", "away": "BORUSSIA (MG)", "home_odds": 3.25, "draw_odds": 3.70, "away_odds": 2.18, "result": "A", "league": "Bundesliga"},
            {"order": 4, "home": "FULHAM", "away": "SUNDERLAND", "home_odds": 2.12, "draw_odds": 3.40, "away_odds": 3.75, "result": "H", "league": "Premier League"},
            {"order": 5, "home": "ACF FIORENTINA", "away": "JUVENTUS", "home_odds": 3.75, "draw_odds": 3.45, "away_odds": 2.06, "result": "D", "league": "Serie A"},
            {"order": 6, "home": "1. FC COLOGNE", "away": "EINTRACHT FR", "home_odds": 2.90, "draw_odds": 3.80, "away_odds": 2.30, "result": "A", "league": "Bundesliga"},
            {"order": 7, "home": "NEWCASTLE", "away": "MAN CITY", "home_odds": 3.35, "draw_odds": 3.80, "away_odds": 2.14, "result": "A", "league": "Premier League"},
            {"order": 8, "home": "OSASUNA", "away": "REAL SOCIEDAD", "home_odds": 2.55, "draw_odds": 3.20, "away_odds": 3.05, "result": "A", "league": "LaLiga"},
            {"order": 9, "home": "RENNES", "away": "MONACO", "home_odds": 2.55, "draw_odds": 3.75, "away_odds": 2.60, "result": "H", "league": "Ligue 1"},
            {"order": 10, "home": "NAPOLI", "away": "ATALANTA BC", "home_odds": 2.16, "draw_odds": 3.40, "away_odds": 3.55, "result": "H", "league": "Serie A"},
            {"order": 11, "home": "HELLAS VERONA", "away": "PARMA", "home_odds": 2.40, "draw_odds": 3.15, "away_odds": 3.30, "result": "A", "league": "Serie A"},
            {"order": 12, "home": "OVIEDO", "away": "RAYO VALLECANO", "home_odds": 3.35, "draw_odds": 3.35, "away_odds": 2.31, "result": "D", "league": "LaLiga"},
            {"order": 13, "home": "LEEDS", "away": "ASTON VILLA", "home_odds": 3.00, "draw_odds": 3.30, "away_odds": 2.55, "result": "A", "league": "Premier League"},
            {"order": 14, "home": "NANTES", "away": "LORIENT", "home_odds": 2.45, "draw_odds": 3.40, "away_odds": 2.95, "result": "D", "league": "Ligue 1"},
            {"order": 15, "home": "ST. PAULI", "away": "UNION BERLIN", "home_odds": 2.38, "draw_odds": 3.35, "away_odds": 3.10, "result": "A", "league": "Bundesliga"},
        ]
    },
    {
        "jackpot_id": "JK-2024-1101",
        "name": "15M MIDWEEK JACKPOT - 01/11",
        "kickoff_date": "2024-11-01",
        "fixtures": [
            {"order": 1, "home": "UNION BERLIN", "away": "FREIBURG", "home_odds": 2.70, "draw_odds": 3.35, "away_odds": 2.70, "result": "D", "league": "Bundesliga"},
            {"order": 2, "home": "LEIPZIG", "away": "STUTTGART", "home_odds": 2.12, "draw_odds": 3.85, "away_odds": 3.20, "result": "H", "league": "Bundesliga"},
            {"order": 3, "home": "NOTTINGHAM", "away": "MAN UTD", "home_odds": 3.25, "draw_odds": 3.75, "away_odds": 2.20, "result": "D", "league": "Premier League"},
            {"order": 4, "home": "NORRKOPING FK", "away": "IK SIRIUS", "home_odds": 2.35, "draw_odds": 3.75, "away_odds": 2.70, "result": "A", "league": "Allsvenskan"},
            {"order": 5, "home": "TOTTENHAM", "away": "CHELSEA", "home_odds": 2.70, "draw_odds": 3.65, "away_odds": 2.60, "result": "A", "league": "Premier League"},
            {"order": 6, "home": "REAL SOCIEDAD", "away": "ATHLETIC BILBAO", "home_odds": 2.80, "draw_odds": 3.15, "away_odds": 2.80, "result": "H", "league": "LaLiga"},
            {"order": 7, "home": "NAC BREDA", "away": "GO AHEAD EAGLES", "home_odds": 2.48, "draw_odds": 3.75, "away_odds": 2.65, "result": "H", "league": "Eredivisie"},
            {"order": 8, "home": "SC TELSTAR", "away": "EXCELSIOR ROTTERDAM", "home_odds": 2.28, "draw_odds": 3.70, "away_odds": 2.95, "result": "D", "league": "Eredivisie"},
            {"order": 9, "home": "HERACLES ALMELO", "away": "PEC ZWOLLE", "home_odds": 2.46, "draw_odds": 3.50, "away_odds": 2.80, "result": "H", "league": "Eredivisie"},
            {"order": 10, "home": "LEVANTE", "away": "CELTA VIGO", "home_odds": 2.85, "draw_odds": 3.45, "away_odds": 2.55, "result": "A", "league": "LaLiga"},
            {"order": 11, "home": "FC GRONINGEN", "away": "FC TWENTE", "home_odds": 2.75, "draw_odds": 3.50, "away_odds": 2.49, "result": "D", "league": "Eredivisie"},
            {"order": 12, "home": "ALAVES", "away": "ESPANYOL", "home_odds": 2.47, "draw_odds": 3.10, "away_odds": 3.30, "result": "H", "league": "LaLiga"},
            {"order": 13, "home": "SK RAPID", "away": "SK STURM GRAZ", "home_odds": 2.30, "draw_odds": 3.45, "away_odds": 2.90, "result": "H", "league": "Bundesliga Austria"},
            {"order": 14, "home": "WOLFSBURG", "away": "HOFFENHEIM", "home_odds": 2.60, "draw_odds": 3.75, "away_odds": 2.55, "result": "A", "league": "Bundesliga"},
            {"order": 15, "home": "FK KRASNODAR", "away": "FK SPARTAK MOSCOW", "home_odds": 2.09, "draw_odds": 3.45, "away_odds": 3.55, "result": "H", "league": "Premier League Russia"},
        ]
    },
    {
        "jackpot_id": "JK-2024-1227",
        "name": "MUST BE WON RESULTS - 27/12",
        "kickoff_date": "2024-12-27",
        "fixtures": [
            {"order": 1, "home": "WEST HAM", "away": "FULHAM", "home_odds": 2.75, "draw_odds": 3.45, "away_odds": 2.65, "result": "A", "league": "Premier League"},
            {"order": 2, "home": "BRENTFORD", "away": "BOURNEMOUTH", "home_odds": 2.35, "draw_odds": 3.60, "away_odds": 3.05, "result": "H", "league": "Premier League"},
            {"order": 3, "home": "SUNDERLAND", "away": "LEEDS", "home_odds": 2.65, "draw_odds": 3.25, "away_odds": 2.90, "result": "A", "league": "Premier League"},
            {"order": 4, "home": "CRYSTAL PALACE", "away": "TOTTENHAM", "home_odds": 2.17, "draw_odds": 3.45, "away_odds": 3.60, "result": "A", "league": "Premier League"},
            {"order": 5, "home": "PARMA", "away": "ACF FIORENTINA", "home_odds": 3.45, "draw_odds": 3.15, "away_odds": 2.31, "result": "H", "league": "Serie A"},
            {"order": 6, "home": "UDINESE", "away": "LAZIO", "home_odds": 3.05, "draw_odds": 3.15, "away_odds": 2.55, "result": "D", "league": "Serie A"},
            {"order": 7, "home": "ATALANTA BC", "away": "INTER MILANO", "home_odds": 3.45, "draw_odds": 3.60, "away_odds": 2.11, "result": "A", "league": "Serie A"},
            {"order": 8, "home": "ROYAL ANTWERP FC", "away": "SV ZULTE WAREGEM", "home_odds": 2.15, "draw_odds": 3.50, "away_odds": 3.35, "result": "H", "league": "Pro League"},
            {"order": 9, "home": "RAAL LA LOUVIERE", "away": "OUD-HEVERLEE LEUVEN", "home_odds": 2.65, "draw_odds": 3.05, "away_odds": 2.90, "result": "D", "league": "Pro League"},
            {"order": 10, "home": "YELLOW-RED KV MECHELEN", "away": "FCV DENDER EH", "home_odds": 2.19, "draw_odds": 3.55, "away_odds": 3.20, "result": "D", "league": "Pro League"},
            {"order": 11, "home": "KAA GENT", "away": "KVC WESTERLO", "home_odds": 2.33, "draw_odds": 3.75, "away_odds": 2.80, "result": "H", "league": "Pro League"},
            {"order": 12, "home": "UGANDA", "away": "TANZANIA", "home_odds": 2.29, "draw_odds": 3.20, "away_odds": 3.35, "result": "D", "league": "Africa Cup of Nations"},
            {"order": 13, "home": "NIGERIA", "away": "TUNISIA", "home_odds": 2.35, "draw_odds": 3.20, "away_odds": 3.25, "result": "H", "league": "Africa Cup of Nations"},
            {"order": 14, "home": "EQUATORIAL GUINEA", "away": "SUDAN", "home_odds": 2.75, "draw_odds": 3.15, "away_odds": 2.75, "result": "A", "league": "Africa Cup of Nations"},
            {"order": 15, "home": "IVORY COAST", "away": "CAMEROON", "home_odds": 2.25, "draw_odds": 3.20, "away_odds": 3.40, "result": "A", "league": "Africa Cup of Nations"},
        ]
    }
]


class JackpotComprehensiveTest:
    def __init__(self):
        self.db = SessionLocal()
        self.results = {
            "jackpot_input": {},
            "probability_output": {},
            "sets_comparison": {},
            "ticket_construction": {},
            "jackpot_validation": {},
            "backtesting": {},
            "feature_store": {},
            "calibration": {},
            "explainability": {},
            "model_health": {}
        }
        self.test_session_folder = DATA_STORAGE_PATH / f"jackpot_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.test_session_folder.mkdir(parents=True, exist_ok=True)
        self.created_jackpot_ids = []
        
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
    
    def test_jackpot_input(self, jackpot_data: Dict) -> Dict:
        """Test Jackpot Input - Create jackpot with fixtures"""
        print(f"\n{'='*80}")
        print(f"TESTING JACKPOT INPUT: {jackpot_data['jackpot_id']}")
        print(f"{'='*80}")
        
        try:
            # Prepare fixtures
            fixtures = []
            for fix in jackpot_data['fixtures']:
                fixtures.append({
                    "homeTeam": fix['home'],
                    "awayTeam": fix['away'],
                    "homeOdds": fix['home_odds'],
                    "drawOdds": fix['draw_odds'],
                    "awayOdds": fix['away_odds']
                })
            
            # Create jackpot
            response = requests.post(
                f"{API_BASE_URL}/jackpots",
                json={
                    "jackpot_id": jackpot_data['jackpot_id'],
                    "name": jackpot_data['name'],
                    "kickoff_date": jackpot_data['kickoff_date'],
                    "fixtures": fixtures
                },
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.created_jackpot_ids.append(jackpot_data['jackpot_id'])
                
                # Verify in database
                jackpot = self.db.execute(
                    text("SELECT id, jackpot_id FROM jackpots WHERE jackpot_id = :jackpot_id"),
                    {"jackpot_id": jackpot_data['jackpot_id']}
                ).fetchone()
                
                result = {
                    "success": True,
                    "jackpot_id": jackpot_data['jackpot_id'],
                    "jackpot_db_id": jackpot.id if jackpot else None,
                    "fixtures_count": len(fixtures),
                    "response": data
                }
                print(f"  ✅ SUCCESS: Created jackpot {jackpot_data['jackpot_id']} with {len(fixtures)} fixtures")
            else:
                result = {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response": response.text
                }
                print(f"  ❌ FAILED: {result['error']}")
            
            return result
            
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(f"  ❌ ERROR: {e}")
            return result
    
    def test_probability_output(self, jackpot_id: str) -> Dict:
        """Test Probability Output - Calculate probabilities for jackpot"""
        print(f"\n{'='*80}")
        print(f"TESTING PROBABILITY OUTPUT: {jackpot_id}")
        print(f"{'='*80}")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/probabilities/calculate",
                json={"jackpot_id": jackpot_id},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if predictions were created
                jackpot = self.db.execute(
                    text("SELECT id FROM jackpots WHERE jackpot_id = :jackpot_id"),
                    {"jackpot_id": jackpot_id}
                ).fetchone()
                
                if jackpot:
                    pred_count = self.db.execute(
                        text("SELECT COUNT(*) FROM predictions WHERE fixture_id IN (SELECT id FROM jackpot_fixtures WHERE jackpot_id = :jackpot_id)"),
                        {"jackpot_id": jackpot.id}
                    ).scalar()
                    
                    result = {
                        "success": True,
                        "jackpot_id": jackpot_id,
                        "predictions_count": pred_count,
                        "response": data
                    }
                    print(f"  ✅ SUCCESS: Generated {pred_count} predictions")
                else:
                    result = {"success": False, "error": "Jackpot not found in database"}
                    print(f"  ❌ FAILED: {result['error']}")
            else:
                result = {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response": response.text
                }
                print(f"  ❌ FAILED: {result['error']}")
            
            return result
            
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(f"  ❌ ERROR: {e}")
            return result
    
    def test_sets_comparison(self, jackpot_id: str) -> Dict:
        """Test Sets Comparison - Compare probability sets"""
        print(f"\n{'='*80}")
        print(f"TESTING SETS COMPARISON: {jackpot_id}")
        print(f"{'='*80}")
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/sets/comparison",
                params={"jackpot_id": jackpot_id},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    "success": True,
                    "jackpot_id": jackpot_id,
                    "response": data
                }
                print(f"  ✅ SUCCESS: Sets comparison retrieved")
            else:
                result = {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response": response.text
                }
                print(f"  ❌ FAILED: {result['error']}")
            
            return result
            
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(f"  ❌ ERROR: {e}")
            return result
    
    def test_ticket_construction(self, jackpot_id: str) -> Dict:
        """Test Ticket Construction - Generate tickets"""
        print(f"\n{'='*80}")
        print(f"TESTING TICKET CONSTRUCTION: {jackpot_id}")
        print(f"{'='*80}")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/tickets/generate",
                json={
                    "jackpot_id": jackpot_id,
                    "max_tickets": 10,
                    "strategy": "balanced"
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    "success": True,
                    "jackpot_id": jackpot_id,
                    "tickets_generated": data.get("tickets_count", 0),
                    "response": data
                }
                print(f"  ✅ SUCCESS: Generated tickets")
            else:
                result = {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response": response.text
                }
                print(f"  ❌ FAILED: {result['error']}")
            
            return result
            
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(f"  ❌ ERROR: {e}")
            return result
    
    def test_jackpot_validation(self, jackpot_id: str, actual_results: Dict) -> Dict:
        """Test Jackpot Validation - Validate jackpot with actual results"""
        print(f"\n{'='*80}")
        print(f"TESTING JACKPOT VALIDATION: {jackpot_id}")
        print(f"{'='*80}")
        
        try:
            # Submit actual results
            response = requests.post(
                f"{API_BASE_URL}/validation/validate",
                json={
                    "jackpot_id": jackpot_id,
                    "actual_results": actual_results
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    "success": True,
                    "jackpot_id": jackpot_id,
                    "response": data
                }
                print(f"  ✅ SUCCESS: Validation completed")
            else:
                result = {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response": response.text
                }
                print(f"  ❌ FAILED: {result['error']}")
            
            return result
            
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(f"  ❌ ERROR: {e}")
            return result
    
    def test_backtesting(self, jackpot_id: str) -> Dict:
        """Test Backtesting - Run backtest on jackpot"""
        print(f"\n{'='*80}")
        print(f"TESTING BACKTESTING: {jackpot_id}")
        print(f"{'='*80}")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/backtesting/run",
                json={"jackpot_id": jackpot_id},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    "success": True,
                    "jackpot_id": jackpot_id,
                    "response": data
                }
                print(f"  ✅ SUCCESS: Backtesting completed")
            else:
                result = {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response": response.text
                }
                print(f"  ❌ FAILED: {result['error']}")
            
            return result
            
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(f"  ❌ ERROR: {e}")
            return result
    
    def test_feature_store(self) -> Dict:
        """Test Feature Store - Check feature availability"""
        print(f"\n{'='*80}")
        print("TESTING FEATURE STORE")
        print(f"{'='*80}")
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/feature-store/features",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    "success": True,
                    "features_count": len(data.get("features", [])),
                    "response": data
                }
                print(f"  ✅ SUCCESS: Feature store accessible")
            else:
                result = {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response": response.text
                }
                print(f"  ❌ FAILED: {result['error']}")
            
            return result
            
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(f"  ❌ ERROR: {e}")
            return result
    
    def test_calibration(self) -> Dict:
        """Test Calibration - Check calibration data"""
        print(f"\n{'='*80}")
        print("TESTING CALIBRATION")
        print(f"{'='*80}")
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/calibration/data",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    "success": True,
                    "response": data
                }
                print(f"  ✅ SUCCESS: Calibration data retrieved")
            else:
                result = {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response": response.text
                }
                print(f"  ❌ FAILED: {result['error']}")
            
            return result
            
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(f"  ❌ ERROR: {e}")
            return result
    
    def test_explainability(self, jackpot_id: str) -> Dict:
        """Test Explainability - Get prediction explanations"""
        print(f"\n{'='*80}")
        print(f"TESTING EXPLAINABILITY: {jackpot_id}")
        print(f"{'='*80}")
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/explainability/explanations",
                params={"jackpot_id": jackpot_id},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    "success": True,
                    "jackpot_id": jackpot_id,
                    "response": data
                }
                print(f"  ✅ SUCCESS: Explanations retrieved")
            else:
                result = {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response": response.text
                }
                print(f"  ❌ FAILED: {result['error']}")
            
            return result
            
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(f"  ❌ ERROR: {e}")
            return result
    
    def test_model_health(self) -> Dict:
        """Test Model Health - Check model status"""
        print(f"\n{'='*80}")
        print("TESTING MODEL HEALTH")
        print(f"{'='*80}")
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/model-health/status",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    "success": True,
                    "response": data
                }
                print(f"  ✅ SUCCESS: Model health retrieved")
            else:
                result = {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response": response.text
                }
                print(f"  ❌ FAILED: {result['error']}")
            
            return result
            
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(f"  ❌ ERROR: {e}")
            return result
    
    def save_results(self):
        """Save test results to JSON file"""
        results_file = self.test_session_folder / "jackpot_test_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": self.results,
                "created_jackpot_ids": self.created_jackpot_ids
            }, f, indent=2, default=str)
        print(f"\n  💾 Results saved to: {results_file}")
    
    def run_all_tests(self):
        """Run all jackpot-related tests"""
        print("\n" + "="*80)
        print("COMPREHENSIVE JACKPOT TEST SUITE")
        print("="*80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test session folder: {self.test_session_folder}")
        
        # Test each jackpot
        for jackpot_data in JACKPOT_DATA:
            print(f"\n{'='*80}")
            print(f"PROCESSING JACKPOT: {jackpot_data['jackpot_id']}")
            print(f"{'='*80}")
            
            # 1. Test Jackpot Input
            input_result = self.test_jackpot_input(jackpot_data)
            self.results["jackpot_input"][jackpot_data['jackpot_id']] = input_result
            
            if not input_result.get("success"):
                print(f"  ⚠️  Skipping further tests for {jackpot_data['jackpot_id']} - input failed")
                continue
            
            time.sleep(1)  # Brief pause between API calls
            
            # 2. Test Probability Output
            prob_result = self.test_probability_output(jackpot_data['jackpot_id'])
            self.results["probability_output"][jackpot_data['jackpot_id']] = prob_result
            time.sleep(1)
            
            # 3. Test Sets Comparison
            sets_result = self.test_sets_comparison(jackpot_data['jackpot_id'])
            self.results["sets_comparison"][jackpot_data['jackpot_id']] = sets_result
            time.sleep(1)
            
            # 4. Test Ticket Construction
            ticket_result = self.test_ticket_construction(jackpot_data['jackpot_id'])
            self.results["ticket_construction"][jackpot_data['jackpot_id']] = ticket_result
            time.sleep(1)
            
            # 5. Prepare actual results for validation
            actual_results = {}
            for fix in jackpot_data['fixtures']:
                actual_results[str(fix['order'])] = fix['result']
            
            # 6. Test Jackpot Validation
            validation_result = self.test_jackpot_validation(jackpot_data['jackpot_id'], actual_results)
            self.results["jackpot_validation"][jackpot_data['jackpot_id']] = validation_result
            time.sleep(1)
            
            # 7. Test Backtesting
            backtest_result = self.test_backtesting(jackpot_data['jackpot_id'])
            self.results["backtesting"][jackpot_data['jackpot_id']] = backtest_result
            time.sleep(1)
            
            # 8. Test Explainability
            explain_result = self.test_explainability(jackpot_data['jackpot_id'])
            self.results["explainability"][jackpot_data['jackpot_id']] = explain_result
            time.sleep(1)
        
        # Test features that don't require jackpot_id
        # 9. Test Feature Store
        feature_result = self.test_feature_store()
        self.results["feature_store"] = feature_result
        time.sleep(1)
        
        # 10. Test Calibration
        calibration_result = self.test_calibration()
        self.results["calibration"] = calibration_result
        time.sleep(1)
        
        # 11. Test Model Health
        health_result = self.test_model_health()
        self.results["model_health"] = health_result
        
        # Save results
        self.save_results()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("JACKPOT TEST SUMMARY")
        print("="*80)
        
        # Count successes
        for feature, results in self.results.items():
            if isinstance(results, dict) and results:
                if feature in ["feature_store", "calibration", "model_health"]:
                    success = results.get("success", False)
                    print(f"{feature}: {'✅ PASS' if success else '❌ FAIL'}")
                else:
                    successful = sum(1 for r in results.values() if r.get("success", False))
                    total = len(results)
                    print(f"{feature}: {successful}/{total} successful")
        
        print(f"\nCreated {len(self.created_jackpot_ids)} jackpots")
        print("="*80)


if __name__ == "__main__":
    suite = JackpotComprehensiveTest()
    suite.run_all_tests()


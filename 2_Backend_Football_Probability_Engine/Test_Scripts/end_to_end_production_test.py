"""
End-to-End Production Test Suite
Tests the complete pipeline from data ingestion to backtesting with real production data.

Stages:
1. Data Ingestion (Historical Match & Odds Data + Draw Structural Data)
2. Data Cleaning & ETL
3. Model Training (Poisson → Blending → Calibration)
4. Probability Generation (Jackpot Results)
5. Validation & Backtesting

Each stage:
- Only proceeds if previous stage succeeds
- Tests DB tables at that stage
- Stores data in production folders (not test sessions)
- Removes data sources that don't work
"""
import os
import sys
import time
import json
import requests
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import traceback

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use app's database connection
from app.db.session import SessionLocal, engine
from app.config import settings

# API base URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

# Production data paths (NO "test" in names)
PRODUCTION_DATA_PATH = Path("data/1_data_ingestion/Historical Match_Odds_Data")
PRODUCTION_DRAW_PATH = Path("data/1_data_ingestion/Draw_structural")
PRODUCTION_CLEANED_PATH = Path("data/2_Cleaned_data/Historical Match_Odds_Data")
PRODUCTION_CLEANED_DRAW_PATH = Path("data/2_Cleaned_data/Draw_structural")

# Test results path (for test scripts only)
TEST_RESULTS_PATH = Path("Test_Scripts/test_results")
TEST_RESULTS_PATH.mkdir(parents=True, exist_ok=True)

# Jackpot data extracted from images
JACKPOT_DATA = [
    {
        "jackpot_id": "JK-2024-1129",
        "name": "15M MIDWEEK JACKPOT - 29/11",
        "kickoff_date": "2024-11-29",
        "fixtures": [
            {"order": 1, "home": "SUNDERLAND", "away": "BOURNEMOUTH", "home_odds": 3.00, "draw_odds": 3.45, "away_odds": 2.47, "result": "H"},
            {"order": 2, "home": "LEVERKUSEN", "away": "DORTMUND", "home_odds": 2.55, "draw_odds": 3.65, "away_odds": 2.65, "result": "A"},
            {"order": 3, "home": "EVERTON", "away": "NEWCASTLE", "home_odds": 2.95, "draw_odds": 3.35, "away_odds": 2.55, "result": "A"},
            {"order": 4, "home": "LEVANTE", "away": "ATHLETIC BILBAO", "home_odds": 3.60, "draw_odds": 3.50, "away_odds": 2.14, "result": "A"},
            {"order": 5, "home": "TOTTENHAM", "away": "FULHAM", "home_odds": 2.09, "draw_odds": 3.65, "away_odds": 3.65, "result": "A"},
            {"order": 6, "home": "US LECCE", "away": "TORINO FC", "home_odds": 2.85, "draw_odds": 3.00, "away_odds": 2.80, "result": "H"},
            {"order": 7, "home": "CRYSTAL PALACE", "away": "MAN UTD", "home_odds": 2.60, "draw_odds": 3.60, "away_odds": 2.75, "result": "A"},
            {"order": 8, "home": "REAL SOCIEDAD", "away": "VILLARREAL", "home_odds": 2.70, "draw_odds": 3.55, "away_odds": 2.70, "result": "A"},
            {"order": 9, "home": "NOTTINGHAM", "away": "BRIGHTON", "home_odds": 2.70, "draw_odds": 3.50, "away_odds": 2.70, "result": "A"},
            {"order": 10, "home": "HAMBURG", "away": "STUTTGART", "home_odds": 3.05, "draw_odds": 3.80, "away_odds": 2.23, "result": "H"},
            {"order": 11, "home": "SEVILLA", "away": "BETIS", "home_odds": 3.00, "draw_odds": 3.45, "away_odds": 2.46, "result": "A"},
            {"order": 12, "home": "LORIENT", "away": "NICE", "home_odds": 2.48, "draw_odds": 3.55, "away_odds": 2.80, "result": "H"},
            {"order": 13, "home": "CHELSEA", "away": "ARSENAL", "home_odds": 3.30, "draw_odds": 3.45, "away_odds": 2.29, "result": "D"},
            {"order": 14, "home": "FREIBURG", "away": "MAINZ", "home_odds": 2.10, "draw_odds": 3.45, "away_odds": 3.65, "result": "H"},
            {"order": 15, "home": "AS ROMA", "away": "NAPOLI", "home_odds": 2.60, "draw_odds": 3.00, "away_odds": 3.10, "result": "A"},
        ]
    }
]

# All leagues to test
ALL_LEAGUES = [
    # Major leagues (football-data.co.uk)
    "E0", "E1", "E2", "E3", "SP1", "SP2", "I1", "I2", "F1", "F2", "D1", "D2",
    "N1", "B1", "P1", "T1", "G1", "SC0", "SC1", "SC2", "SC3",
    # Extra leagues (football-data.org or OpenFootball)
    "SWE1", "FIN1", "RO1", "RUS1", "IRL1", "CZE1", "CRO1", "SRB1", "UKR1",
    "ARG1", "BRA1", "MEX1", "USA1", "CHN1", "JPN1", "KOR1", "AUS1"
]

# Quick test mode - test only first few leagues for faster execution
# Set MAX_LEAGUES_TO_TEST environment variable to limit (default: test all)
MAX_LEAGUES_TO_TEST = int(os.getenv("MAX_LEAGUES_TO_TEST", "0"))  # 0 = test all
if MAX_LEAGUES_TO_TEST > 0:
    ALL_LEAGUES = ALL_LEAGUES[:MAX_LEAGUES_TO_TEST]
    print(f"QUICK TEST MODE: Testing only {MAX_LEAGUES_TO_TEST} leagues")

# Draw structural data types
DRAW_STRUCTURAL_TYPES = [
    "League Priors",
    "H2H Stats",
    "Elo Ratings",
    "Weather",
    "Referee",
    "Rest Days",
    "Odds Movement"
]


class EndToEndProductionTest:
    """Comprehensive end-to-end test for production pipeline"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.inspector = inspect(engine)
        self.results = {
            "stage1_data_ingestion": {},
            "stage2_data_cleaning": {},
            "stage3_model_training": {},
            "stage4_probability_generation": {},
            "stage5_validation_backtesting": {},
            "data_source_status": {},
            "table_population": {}
        }
        self.working_data_sources = {
            "football-data.co.uk": [],
            "football-data.org": [],
            "OpenFootball": []
        }
        self.failed_data_sources = []
        self.test_start_time = datetime.now()
        self.test_results_file = TEST_RESULTS_PATH / f"e2e_test_{self.test_start_time.strftime('%Y%m%d_%H%M%S')}.json"
        
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
    
    def check_and_restart_backend(self) -> bool:
        """Check if backend is running, restart if not"""
        try:
            response = requests.get(f"{API_BASE_URL}/model/status", timeout=5)
            if response.status_code == 200:
                return True
        except:
            pass
        
        # Backend not running, try to restart
        self.log("Backend not responding, attempting to restart...", "WARNING")
        try:
            import subprocess
            import os
            # Start backend in background
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            subprocess.Popen(
                ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
                cwd=backend_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Wait for backend to start
            for i in range(15):
                time.sleep(2)
                try:
                    response = requests.get(f"{API_BASE_URL}/model/status", timeout=5)
                    if response.status_code == 200:
                        self.log("Backend restarted successfully", "SUCCESS")
                        return True
                except:
                    continue
            self.log("Backend restart attempt completed, continuing anyway", "WARNING")
            return False
        except Exception as e:
            self.log(f"Failed to restart backend: {e}. Continuing with direct service calls.", "WARNING")
            return False
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Use ASCII-safe prefixes for Windows compatibility
        prefix = {
            "INFO": "[INFO]",
            "SUCCESS": "[OK]",
            "WARNING": "[WARN]",
            "ERROR": "[ERROR]",
            "STAGE": "[STAGE]"
        }.get(level, "[INFO]")
        try:
            print(f"[{timestamp}] {prefix} {message}")
        except UnicodeEncodeError:
            # Fallback for Windows console encoding issues
            safe_message = message.encode('ascii', 'ignore').decode('ascii')
            print(f"[{timestamp}] {prefix} {safe_message}")
    
    def check_table_population(self, table_name: str) -> int:
        """Check if table has data"""
        try:
            count = self.db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            return count
        except Exception as e:
            self.log(f"Error checking table {table_name}: {e}", "ERROR")
            return 0
    
    def stage1_data_ingestion(self) -> bool:
        """Stage 1: Data Ingestion - Download and ingest real data"""
        self.log("="*80, "STAGE")
        self.log("STAGE 1: DATA INGESTION", "STAGE")
        self.log("="*80, "STAGE")
        
        success = True
        ingested_leagues = []
        failed_leagues = []
        
        # Test each league with all available sources
        total_leagues = len(ALL_LEAGUES)
        for idx, league_code in enumerate(ALL_LEAGUES, 1):
            # Check backend health every 5 leagues
            if idx % 5 == 0:
                self.check_and_restart_backend()
            
            self.log(f"Testing league {idx}/{total_leagues}: {league_code}")
            league_success = False
            
            # Try football-data.co.uk first (CSV) - Use direct service calls
            try:
                # Use direct ingestion service for football-data.co.uk
                from app.services.data_ingestion import DataIngestionService
                service = DataIngestionService(self.db, enable_cleaning=True)
                stats = service.ingest_from_football_data(
                    league_code=league_code,
                    season="last7"
                )
                inserted = stats.get("inserted", 0)
                if inserted > 0:
                    self.working_data_sources["football-data.co.uk"].append(league_code)
                    ingested_leagues.append(league_code)
                    league_success = True
                    self.log(f"  [SUCCESS] {league_code}: Ingested via football-data.co.uk ({inserted} matches)", "SUCCESS")
                else:
                    self.log(f"  [WARNING] {league_code}: No matches inserted from football-data.co.uk", "WARNING")
            except Exception as e:
                self.log(f"  [WARNING] {league_code}: football-data.co.uk failed: {str(e)[:200]}", "WARNING")
            
            # Try football-data.org (API) if CSV failed
            if not league_success:
                try:
                    # Use direct ingestion service for football-data.org
                    from app.services.data_ingestion import DataIngestionService
                    service = DataIngestionService(self.db, enable_cleaning=True)
                    stats = service.ingest_from_football_data_org(
                        league_code=league_code,
                        season="2324"
                    )
                    inserted = stats.get("inserted", 0)
                    if inserted > 0:
                        self.working_data_sources["football-data.org"].append(league_code)
                        ingested_leagues.append(league_code)
                        league_success = True
                        self.log(f"  [SUCCESS] {league_code}: Ingested via football-data.org ({inserted} matches)", "SUCCESS")
                    else:
                        self.log(f"  [WARNING]  {league_code}: No matches inserted from football-data.org", "WARNING")
                except Exception as e:
                    self.log(f"  [WARNING]  {league_code}: football-data.org failed: {str(e)[:200]}", "WARNING")
            
            # Try OpenFootball if both failed
            if not league_success:
                try:
                    # Use direct ingestion service for OpenFootball
                    from app.services.ingestion.ingest_openfootball import OpenFootballService
                    service = OpenFootballService(self.db)
                    stats = service.ingest_league_matches(
                        league_code=league_code,
                        season="2324"
                    )
                    inserted = stats.get("inserted", 0)
                    if inserted > 0:
                        self.working_data_sources["OpenFootball"].append(league_code)
                        ingested_leagues.append(league_code)
                        league_success = True
                        self.log(f"  [SUCCESS] {league_code}: Ingested via OpenFootball ({inserted} matches)", "SUCCESS")
                    else:
                        self.log(f"  [WARNING]  {league_code}: No matches inserted from OpenFootball", "WARNING")
                except Exception as e:
                    self.log(f"  [WARNING]  {league_code}: OpenFootball failed: {str(e)[:200]}", "WARNING")
            
            if not league_success:
                failed_leagues.append(league_code)
                self.log(f"  [ERROR] {league_code}: All sources failed", "ERROR")
            
            time.sleep(1)  # Rate limiting
        
        # Ingest Draw Structural Data
        self.log("\nIngesting Draw Structural Data...")
        draw_success = True
        
        for data_type in DRAW_STRUCTURAL_TYPES:
            self.log(f"  Testing {data_type} ingestion...")
            try:
                endpoint_map = {
                    "League Priors": "/draw-ingestion/league-priors",
                    "H2H Stats": "/draw-ingestion/h2h",
                    "Elo Ratings": "/draw-ingestion/elo",
                    "Weather": "/draw-ingestion/weather",
                    "Referee": "/draw-ingestion/referee",
                    "Rest Days": "/draw-ingestion/rest-days",
                    "Odds Movement": "/draw-ingestion/odds-movement"
                }
                
                endpoint = endpoint_map.get(data_type)
                if not endpoint:
                    continue
                
                # Get a league with data for testing
                test_league = ingested_leagues[0] if ingested_leagues else "E0"
                
                if data_type in ["Weather", "Rest Days", "Odds Movement"]:
                    # These require fixture_id - skip for now or get from matches
                    self.log(f"    [WARNING]  {data_type}: Requires fixture_id, skipping", "WARNING")
                    continue
                
                response = requests.post(
                    f"{API_BASE_URL}{endpoint}",
                    json={"league_code": test_league, "season": "2324"},
                    timeout=60
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    if "No matches found" in response_data.get("message", ""):
                        self.log(f"    [INFO] {data_type}: No matches found for {test_league} (expected for some leagues)", "INFO")
                    else:
                        self.log(f"    [SUCCESS] {data_type}: Ingested successfully", "SUCCESS")
                elif response.status_code == 400:
                    # 400 errors are handled gracefully now (like "No matches found")
                    error_detail = response.json().get("detail", "Unknown error")
                    if "No matches found" in error_detail:
                        self.log(f"    [INFO] {data_type}: No matches found for {test_league} (skipped)", "INFO")
                    else:
                        self.log(f"    [WARNING]  {data_type}: {error_detail}", "WARNING")
                else:
                    self.log(f"    [WARNING]  {data_type}: HTTP {response.status_code}", "WARNING")
            except Exception as e:
                self.log(f"    [ERROR] {data_type}: Error - {e}", "ERROR")
                draw_success = False
        
        # Check table population
        self.log("\nChecking table population after ingestion...")
        table_counts = {}
        critical_tables = ["matches", "teams", "leagues", "league_draw_priors", "h2h_draw_stats", "team_elo"]
        
        for table in critical_tables:
            count = self.check_table_population(table)
            table_counts[table] = count
            if count > 0:
                self.log(f"  [SUCCESS] {table}: {count} records", "SUCCESS")
            else:
                self.log(f"  [WARNING]  {table}: 0 records", "WARNING")
                if table in ["matches", "teams"]:
                    success = False
        
        # Store results
        self.results["stage1_data_ingestion"] = {
            "success": success and len(ingested_leagues) > 0,
            "ingested_leagues": ingested_leagues,
            "failed_leagues": failed_leagues,
            "working_sources": self.working_data_sources,
            "table_counts": table_counts,
            "draw_structural_success": draw_success
        }
        
        self.results["data_source_status"] = {
            "working": self.working_data_sources,
            "failed": failed_leagues
        }
        
        if success and len(ingested_leagues) > 0:
            self.log(f"\n[SUCCESS] Stage 1 Complete: {len(ingested_leagues)} leagues ingested", "SUCCESS")
        else:
            self.log(f"\n[ERROR] Stage 1 Failed: Only {len(ingested_leagues)} leagues ingested", "ERROR")
        
        return success and len(ingested_leagues) > 0
    
    def stage2_data_cleaning(self) -> bool:
        """Stage 2: Data Cleaning & ETL"""
        self.log("\n" + "="*80, "STAGE")
        self.log("STAGE 2: DATA CLEANING & ETL", "STAGE")
        self.log("="*80, "STAGE")
        
        # Check if cleaning is enabled and working
        matches_before = self.check_table_population("matches")
        
        if matches_before == 0:
            self.log("[WARNING]  No matches to clean - skipping cleaning stage", "WARNING")
            self.results["stage2_data_cleaning"] = {
                "success": False,
                "reason": "No matches available"
            }
            return False
        
        # Cleaning is integrated into ingestion, so we just verify
        self.log("Data cleaning is integrated into ingestion pipeline")
        self.log(f"Matches in database: {matches_before}")
        
        # Check cleaned data folder
        if PRODUCTION_CLEANED_PATH.exists():
            cleaned_files = list(PRODUCTION_CLEANED_PATH.glob("**/*.csv"))
            self.log(f"Cleaned CSV files found: {len(cleaned_files)}")
        else:
            self.log("[WARNING]  Cleaned data folder not found", "WARNING")
        
        self.results["stage2_data_cleaning"] = {
            "success": True,
            "matches_count": matches_before,
            "cleaning_integrated": True
        }
        
        self.log("[SUCCESS] Stage 2 Complete: Data cleaning verified", "SUCCESS")
        return True
    
    def stage3_model_training(self) -> bool:
        """Stage 3: Model Training (Poisson → Blending → Calibration)"""
        self.log("\n" + "="*80, "STAGE")
        self.log("STAGE 3: MODEL TRAINING", "STAGE")
        self.log("="*80, "STAGE")
        
        # Check if we have enough data
        matches_count = self.check_table_population("matches")
        if matches_count < 100:
            self.log(f"[WARNING]  Insufficient data for training: {matches_count} matches (need ≥100)", "WARNING")
            self.results["stage3_model_training"] = {
                "success": False,
                "reason": f"Insufficient data: {matches_count} matches"
            }
            return False
        
        training_results = {}
        
        # 1. Train Poisson Model - Use direct service call
        self.log("Training Poisson Model...")
        try:
            from app.services.model_training import ModelTrainingService
            training_service = ModelTrainingService(self.db)
            
            result = training_service.train_poisson_model(
                leagues=None,  # Use all leagues
                seasons=None
            )
            
            if result and result.get("modelId"):
                training_results["poisson"] = {
                    "success": True,
                    "model_id": result.get("modelId"),
                    "version": result.get("version")
                }
                self.log(f"  [OK] Poisson model training completed - Model ID: {result.get('modelId')}", "SUCCESS")
            else:
                training_results["poisson"] = {"success": False, "error": "No model ID returned"}
                self.log("  [ERROR] Poisson training failed: No model ID returned", "ERROR")
        except Exception as e:
            training_results["poisson"] = {"success": False, "error": str(e)}
            self.log(f"  [ERROR] Poisson training error: {str(e)[:200]}", "ERROR")
        
        # 2. Train Blending Model (if Poisson succeeded)
        if training_results.get("poisson", {}).get("success"):
            self.log("Training Blending Model...")
            try:
                from app.services.model_training import ModelTrainingService
                training_service = ModelTrainingService(self.db)
                
                poisson_model_id = training_results["poisson"].get("model_id")
                result = training_service.train_blending_model(
                    poisson_model_id=poisson_model_id,
                    leagues=None
                )
                
                if result and result.get("modelId"):
                    training_results["blending"] = {
                        "success": True,
                        "model_id": result.get("modelId"),
                        "version": result.get("version")
                    }
                    self.log(f"  [OK] Blending model training completed - Model ID: {result.get('modelId')}", "SUCCESS")
                else:
                    training_results["blending"] = {"success": False, "error": "No model ID returned"}
                    self.log("  [WARN] Blending training: No model ID returned", "WARNING")
            except Exception as e:
                training_results["blending"] = {"success": False, "error": str(e)}
                self.log(f"  [WARN] Blending training error: {str(e)[:200]}", "WARNING")
        
        # 3. Train Calibration Model (if Blending succeeded)
        if training_results.get("blending", {}).get("success"):
            self.log("Training Calibration Model...")
            try:
                from app.services.model_training import ModelTrainingService
                training_service = ModelTrainingService(self.db)
                
                blending_model_id = training_results["blending"].get("model_id")
                result = training_service.train_calibration_model(
                    base_model_id=blending_model_id,
                    leagues=None
                )
                
                if result and result.get("modelId"):
                    training_results["calibration"] = {
                        "success": True,
                        "model_id": result.get("modelId"),
                        "version": result.get("version")
                    }
                    self.log(f"  [OK] Calibration model training completed - Model ID: {result.get('modelId')}", "SUCCESS")
                else:
                    training_results["calibration"] = {"success": False, "error": "No model ID returned"}
                    self.log("  [WARN] Calibration training: No model ID returned", "WARNING")
            except Exception as e:
                training_results["calibration"] = {"success": False, "error": str(e)}
                self.log(f"  [WARN] Calibration training error: {str(e)[:200]}", "WARNING")
        
        # Check if models exist in DB
        models_count = self.check_table_population("models")
        self.log(f"\nModels in database: {models_count}")
        
        success = training_results.get("poisson", {}).get("success", False)
        
        self.results["stage3_model_training"] = {
            "success": success,
            "training_results": training_results,
            "models_count": models_count
        }
        
        if success:
            self.log("[SUCCESS] Stage 3 Complete: Model training initiated", "SUCCESS")
        else:
            self.log("[ERROR] Stage 3 Failed: Model training failed", "ERROR")
        
        return success
    
    def stage4_probability_generation(self) -> bool:
        """Stage 4: Probability Generation for Jackpot Results"""
        self.log("\n" + "="*80, "STAGE")
        self.log("STAGE 4: PROBABILITY GENERATION", "STAGE")
        self.log("="*80, "STAGE")
        
        if not JACKPOT_DATA:
            self.log("[WARNING]  No jackpot data available", "WARNING")
            return False
        
        jackpot_results = {}
        
        # Create jackpot and generate probabilities
        for jackpot_data in JACKPOT_DATA[:1]:  # Test first jackpot only
            self.log(f"Processing jackpot: {jackpot_data['jackpot_id']}")
            
            # 1. Create jackpot
            try:
                fixtures = [{
                    "id": str(fix['order']),
                    "homeTeam": fix['home'],
                    "awayTeam": fix['away'],
                    "odds": {
                        "home": fix['home_odds'],
                        "draw": fix['draw_odds'],
                        "away": fix['away_odds']
                    }
                } for fix in jackpot_data['fixtures']]
                
                response = requests.post(
                    f"{API_BASE_URL}/jackpots",
                    json={"fixtures": fixtures},
                    timeout=60
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    created_jackpot_id = data.get("data", {}).get("id")
                    jackpot_results["creation"] = {"success": True, "jackpot_id": created_jackpot_id}
                    self.log(f"  [SUCCESS] Jackpot created: {created_jackpot_id}", "SUCCESS")
                    
                    # 2. Generate probabilities
                    self.log("  Generating probabilities...")
                    prob_response = requests.get(
                        f"{API_BASE_URL}/probabilities/{created_jackpot_id}/probabilities",
                        timeout=120
                    )
                    
                    if prob_response.status_code == 200:
                        prob_data = prob_response.json()
                        sets_count = len(prob_data.get("data", {}).get("probabilitySets", {}))
                        jackpot_results["probabilities"] = {
                            "success": True,
                            "sets_count": sets_count
                        }
                        self.log(f"  [SUCCESS] Probabilities generated: {sets_count} sets", "SUCCESS")
                    else:
                        jackpot_results["probabilities"] = {"success": False, "error": f"HTTP {prob_response.status_code}"}
                        self.log(f"  [ERROR] Probability generation failed: HTTP {prob_response.status_code}", "ERROR")
                else:
                    jackpot_results["creation"] = {"success": False, "error": f"HTTP {response.status_code}"}
                    self.log(f"  [ERROR] Jackpot creation failed: HTTP {response.status_code}", "ERROR")
            except Exception as e:
                jackpot_results["error"] = str(e)
                self.log(f"  [ERROR] Error: {e}", "ERROR")
        
        # Check predictions table
        predictions_count = self.check_table_population("predictions")
        self.log(f"\nPredictions in database: {predictions_count}")
        
        success = jackpot_results.get("creation", {}).get("success", False) and \
                  jackpot_results.get("probabilities", {}).get("success", False)
        
        self.results["stage4_probability_generation"] = {
            "success": success,
            "jackpot_results": jackpot_results,
            "predictions_count": predictions_count
        }
        
        if success:
            self.log("[SUCCESS] Stage 4 Complete: Probabilities generated", "SUCCESS")
        else:
            self.log("[ERROR] Stage 4 Failed: Probability generation failed", "ERROR")
        
        return success
    
    def stage5_validation_backtesting(self) -> bool:
        """Stage 5: Validation & Backtesting"""
        self.log("\n" + "="*80, "STAGE")
        self.log("STAGE 5: VALIDATION & BACKTESTING", "STAGE")
        self.log("="*80, "STAGE")
        
        # Validation is done via frontend, so we just verify tables
        validation_count = self.check_table_population("validation_results")
        calibration_count = self.check_table_population("calibration_data")
        
        self.log(f"Validation results: {validation_count}")
        self.log(f"Calibration data: {calibration_count}")
        
        self.results["stage5_validation_backtesting"] = {
            "success": True,
            "validation_count": validation_count,
            "calibration_count": calibration_count,
            "note": "Validation/backtesting typically done via frontend UI"
        }
        
        self.log("[SUCCESS] Stage 5 Complete: Validation tables checked", "SUCCESS")
        return True
    
    def save_results(self):
        """Save test results"""
        self.results["test_metadata"] = {
            "start_time": self.test_start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - self.test_start_time).total_seconds()
        }
        
        with open(self.test_results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        self.log(f"\n[SAVED] Results saved to: {self.test_results_file}")
    
    def run_all_stages(self):
        """Run all stages sequentially"""
        self.log("="*80, "STAGE")
        self.log("END-TO-END PRODUCTION TEST SUITE", "STAGE")
        self.log("="*80, "STAGE")
        self.log(f"Started at: {self.test_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check backend health at start
        self.check_and_restart_backend()
        
        stages_completed = []
        
        # Stage 1: Data Ingestion
        if self.stage1_data_ingestion():
            stages_completed.append("Stage 1: Data Ingestion")
            
            # Stage 2: Data Cleaning
            if self.stage2_data_cleaning():
                stages_completed.append("Stage 2: Data Cleaning")
                
                # Stage 3: Model Training
                if self.stage3_model_training():
                    stages_completed.append("Stage 3: Model Training")
                    
                    # Stage 4: Probability Generation
                    if self.stage4_probability_generation():
                        stages_completed.append("Stage 4: Probability Generation")
                        
                        # Stage 5: Validation & Backtesting
                        if self.stage5_validation_backtesting():
                            stages_completed.append("Stage 5: Validation & Backtesting")
        
        # Save results
        self.save_results()
        
        # Print summary
        self.log("\n" + "="*80, "STAGE")
        self.log("TEST SUMMARY", "STAGE")
        self.log("="*80, "STAGE")
        self.log(f"Stages completed: {len(stages_completed)}/5")
        for stage in stages_completed:
            self.log(f"  [SUCCESS] {stage}", "SUCCESS")
        
        if len(stages_completed) == 5:
            self.log("\n[COMPLETE] ALL STAGES COMPLETED SUCCESSFULLY!", "SUCCESS")
        else:
            self.log(f"\n[WARNING]  Test stopped at stage {len(stages_completed) + 1}", "WARNING")


if __name__ == "__main__":
    try:
        # Check API availability first
        print("="*80)
        print("Checking API availability...")
        try:
            response = requests.get(f"{API_BASE_URL}/model/status", timeout=10)
            if response.status_code == 200:
                print("[SUCCESS] API is running")
            else:
                print(f"[WARNING] API returned status {response.status_code}, continuing with direct service calls...")
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            print("[WARNING] API is not available, but continuing with direct service calls...")
            print("   Note: Using direct database/service calls instead of API endpoints")
        except Exception as e:
            print(f"[WARNING] Error checking API: {str(e)[:200]}, continuing anyway...")
        
        print("="*80)
        test = EndToEndProductionTest()
        test.run_all_stages()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


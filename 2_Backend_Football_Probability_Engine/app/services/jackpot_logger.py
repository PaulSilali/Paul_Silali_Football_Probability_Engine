"""
Jackpot Logger Service
Tracks comprehensive information about each jackpot calculation:
- Data downloads (weather, rest days, form, injuries)
- Team training status
- Probability sources (default vs trained models)
- Data quality indicators
"""
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Create jackpot_logs directory if it doesn't exist
JACKPOT_LOGS_DIR = Path(__file__).parent.parent / "logs" / "jackpot_logs"
JACKPOT_LOGS_DIR.mkdir(parents=True, exist_ok=True)


class JackpotLogger:
    """Comprehensive logging for jackpot calculations"""
    
    def __init__(self, jackpot_id: str, db: Session):
        self.jackpot_id = jackpot_id
        self.db = db
        self.log_data = {
            "jackpot_id": jackpot_id,
            "timestamp": datetime.now().isoformat(),
            "fixtures": [],
            "teams": {},
            "data_ingestion": {
                "weather": {"downloaded": [], "failed": [], "skipped": []},
                "rest_days": {"calculated": [], "failed": [], "skipped": []},
                "team_form": {"calculated": [], "failed": [], "skipped": []},
                "injuries": {"downloaded": [], "failed": [], "skipped": []},
                "odds_movement": {"tracked": [], "failed": [], "skipped": []}
            },
            "training_status": {
                "teams_trained": [],
                "teams_using_defaults": [],
                "teams_using_db_ratings": [],
                "active_model": None,
                "model_version": None
            },
            "probability_sources": {
                "from_trained_model": 0,
                "from_db_ratings": 0,
                "from_defaults": 0,
                "total_fixtures": 0
            },
            "data_quality": {
                "high_quality": 0,  # All data available + trained
                "medium_quality": 0,  # Some data missing or using DB ratings
                "low_quality": 0  # Using defaults or missing critical data
            },
            "summary": {
                "total_fixtures": 0,
                "total_teams": 0,
                "teams_trained": 0,
                "teams_using_defaults": 0,
                "weather_downloaded": 0,
                "rest_days_calculated": 0,
                "team_form_calculated": 0,
                "injuries_downloaded": 0
            }
        }
    
    def log_fixture_data(
        self,
        fixture_id: int,
        home_team: str,
        away_team: str,
        home_team_id: Optional[int],
        away_team_id: Optional[int],
        weather_downloaded: bool = False,
        weather_error: Optional[str] = None,
        rest_days_calculated: bool = False,
        rest_days_error: Optional[str] = None,
        home_rest_days: Optional[int] = None,
        away_rest_days: Optional[int] = None,
        team_form_calculated: bool = False,
        form_error: Optional[str] = None,
        injuries_downloaded: bool = False,
        injuries_error: Optional[str] = None,
        odds_tracked: bool = False,
        odds_error: Optional[str] = None,
        home_trained: bool = False,
        away_trained: bool = False,
        home_strength_source: str = "default",  # "model", "database", "default"
        away_strength_source: str = "default",
        probability_quality: str = "low"  # "high", "medium", "low"
    ):
        """Log data for a single fixture"""
        fixture_log = {
            "fixture_id": fixture_id,
            "home_team": home_team,
            "away_team": away_team,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "data_ingestion": {
                "weather": {
                    "downloaded": weather_downloaded,
                    "error": weather_error
                },
                "rest_days": {
                    "calculated": rest_days_calculated,
                    "home_rest_days": home_rest_days,
                    "away_rest_days": away_rest_days,
                    "error": rest_days_error
                },
                "team_form": {
                    "calculated": team_form_calculated,
                    "error": form_error
                },
                "injuries": {
                    "downloaded": injuries_downloaded,
                    "error": injuries_error
                },
                "odds_movement": {
                    "tracked": odds_tracked,
                    "error": odds_error
                }
            },
            "training_status": {
                "home_team": {
                    "trained": home_trained,
                    "strength_source": home_strength_source
                },
                "away_team": {
                    "trained": away_trained,
                    "strength_source": away_strength_source
                }
            },
            "probability_quality": probability_quality
        }
        
        self.log_data["fixtures"].append(fixture_log)
        
        # Update data ingestion stats
        if weather_downloaded:
            self.log_data["data_ingestion"]["weather"]["downloaded"].append(fixture_id)
        elif weather_error:
            self.log_data["data_ingestion"]["weather"]["failed"].append({"fixture_id": fixture_id, "error": weather_error})
        else:
            self.log_data["data_ingestion"]["weather"]["skipped"].append(fixture_id)
        
        if rest_days_calculated:
            self.log_data["data_ingestion"]["rest_days"]["calculated"].append(fixture_id)
        elif rest_days_error:
            self.log_data["data_ingestion"]["rest_days"]["failed"].append({"fixture_id": fixture_id, "error": rest_days_error})
        else:
            self.log_data["data_ingestion"]["rest_days"]["skipped"].append(fixture_id)
        
        if team_form_calculated:
            self.log_data["data_ingestion"]["team_form"]["calculated"].append(fixture_id)
        elif form_error:
            self.log_data["data_ingestion"]["team_form"]["failed"].append({"fixture_id": fixture_id, "error": form_error})
        else:
            self.log_data["data_ingestion"]["team_form"]["skipped"].append(fixture_id)
        
        if injuries_downloaded:
            self.log_data["data_ingestion"]["injuries"]["downloaded"].append(fixture_id)
        elif injuries_error:
            self.log_data["data_ingestion"]["injuries"]["failed"].append({"fixture_id": fixture_id, "error": injuries_error})
        else:
            self.log_data["data_ingestion"]["injuries"]["skipped"].append(fixture_id)
        
        if odds_tracked:
            self.log_data["data_ingestion"]["odds_movement"]["tracked"].append(fixture_id)
        elif odds_error:
            self.log_data["data_ingestion"]["odds_movement"]["failed"].append({"fixture_id": fixture_id, "error": odds_error})
        else:
            self.log_data["data_ingestion"]["odds_movement"]["skipped"].append(fixture_id)
        
        # Update training status
        if home_trained:
            if home_team_id not in self.log_data["training_status"]["teams_trained"]:
                self.log_data["training_status"]["teams_trained"].append(home_team_id)
        elif home_strength_source == "database":
            if home_team_id not in self.log_data["training_status"]["teams_using_db_ratings"]:
                self.log_data["training_status"]["teams_using_db_ratings"].append(home_team_id)
        else:
            if home_team_id not in self.log_data["training_status"]["teams_using_defaults"]:
                self.log_data["training_status"]["teams_using_defaults"].append(home_team_id)
        
        if away_trained:
            if away_team_id not in self.log_data["training_status"]["teams_trained"]:
                self.log_data["training_status"]["teams_trained"].append(away_team_id)
        elif away_strength_source == "database":
            if away_team_id not in self.log_data["training_status"]["teams_using_db_ratings"]:
                self.log_data["training_status"]["teams_using_db_ratings"].append(away_team_id)
        else:
            if away_team_id not in self.log_data["training_status"]["teams_using_defaults"]:
                self.log_data["training_status"]["teams_using_defaults"].append(away_team_id)
        
        # Update probability sources
        # Count as "from_trained_model" if at least one team uses model strengths
        # This is more accurate than requiring both teams to use model strengths
        if home_strength_source == "model" or away_strength_source == "model":
            self.log_data["probability_sources"]["from_trained_model"] += 1
        elif home_strength_source == "database" or away_strength_source == "database":
            self.log_data["probability_sources"]["from_db_ratings"] += 1
        else:
            self.log_data["probability_sources"]["from_defaults"] += 1
        
        self.log_data["probability_sources"]["total_fixtures"] += 1
        
        # Update data quality
        if probability_quality == "high":
            self.log_data["data_quality"]["high_quality"] += 1
        elif probability_quality == "medium":
            self.log_data["data_quality"]["medium_quality"] += 1
        else:
            self.log_data["data_quality"]["low_quality"] += 1
    
    def set_active_model(self, model_id: Optional[int], model_version: Optional[str], model_type: Optional[str] = None):
        """Set the active model information"""
        self.log_data["training_status"]["active_model"] = model_id
        self.log_data["training_status"]["model_version"] = model_version
        self.log_data["training_status"]["model_type"] = model_type
    
    def finalize_summary(self):
        """Calculate final summary statistics"""
        self.log_data["summary"]["total_fixtures"] = len(self.log_data["fixtures"])
        self.log_data["summary"]["total_teams"] = len(set(
            [f["home_team_id"] for f in self.log_data["fixtures"] if f["home_team_id"]] +
            [f["away_team_id"] for f in self.log_data["fixtures"] if f["away_team_id"]]
        ))
        self.log_data["summary"]["teams_trained"] = len(self.log_data["training_status"]["teams_trained"])
        self.log_data["summary"]["teams_using_defaults"] = len(self.log_data["training_status"]["teams_using_defaults"])
        self.log_data["summary"]["weather_downloaded"] = len(self.log_data["data_ingestion"]["weather"]["downloaded"])
        self.log_data["summary"]["rest_days_calculated"] = len(self.log_data["data_ingestion"]["rest_days"]["calculated"])
        self.log_data["summary"]["team_form_calculated"] = len(self.log_data["data_ingestion"]["team_form"]["calculated"])
        self.log_data["summary"]["injuries_downloaded"] = len(self.log_data["data_ingestion"]["injuries"]["downloaded"])
    
    def save_log(self) -> str:
        """Save log to file and return file path"""
        self.finalize_summary()
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"jackpot_{self.jackpot_id}_{timestamp}.json"
        filepath = JACKPOT_LOGS_DIR / filename
        
        # Save as JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.log_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Saved jackpot log to: {filepath}")
        
        # Also save a human-readable summary
        summary_filepath = JACKPOT_LOGS_DIR / f"jackpot_{self.jackpot_id}_{timestamp}_SUMMARY.txt"
        self._save_summary(summary_filepath)
        
        return str(filepath)
    
    def _save_summary(self, filepath: Path):
        """Save human-readable summary"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"JACKPOT CALCULATION LOG: {self.jackpot_id}\n")
            f.write(f"Timestamp: {self.log_data['timestamp']}\n")
            f.write("=" * 80 + "\n\n")
            
            # Summary
            f.write("SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Fixtures: {self.log_data['summary']['total_fixtures']}\n")
            f.write(f"Total Teams: {self.log_data['summary']['total_teams']}\n")
            f.write(f"Teams Trained: {self.log_data['summary']['teams_trained']}\n")
            f.write(f"Teams Using Defaults: {self.log_data['summary']['teams_using_defaults']}\n")
            f.write(f"Weather Downloaded: {self.log_data['summary']['weather_downloaded']} fixtures\n")
            f.write(f"Rest Days Calculated: {self.log_data['summary']['rest_days_calculated']} fixtures\n")
            f.write(f"Team Form Calculated: {self.log_data['summary']['team_form_calculated']} fixtures\n")
            f.write(f"Injuries Downloaded: {self.log_data['summary']['injuries_downloaded']} fixtures\n")
            f.write("\n")
            
            # Active Model
            f.write("ACTIVE MODEL\n")
            f.write("-" * 80 + "\n")
            if self.log_data['training_status']['active_model']:
                f.write(f"Model ID: {self.log_data['training_status']['active_model']}\n")
                f.write(f"Model Version: {self.log_data['training_status']['model_version']}\n")
                f.write(f"Model Type: {self.log_data['training_status'].get('model_type', 'N/A')}\n")
            else:
                f.write("No active model found\n")
            f.write("\n")
            
            # Probability Sources
            f.write("PROBABILITY SOURCES\n")
            f.write("-" * 80 + "\n")
            total = self.log_data['probability_sources']['total_fixtures']
            if total > 0:
                f.write(f"From Trained Model: {self.log_data['probability_sources']['from_trained_model']} ({self.log_data['probability_sources']['from_trained_model']/total*100:.1f}%)\n")
                f.write(f"From DB Ratings: {self.log_data['probability_sources']['from_db_ratings']} ({self.log_data['probability_sources']['from_db_ratings']/total*100:.1f}%)\n")
                f.write(f"From Defaults: {self.log_data['probability_sources']['from_defaults']} ({self.log_data['probability_sources']['from_defaults']/total*100:.1f}%)\n")
            f.write("\n")
            
            # Data Quality
            f.write("DATA QUALITY\n")
            f.write("-" * 80 + "\n")
            total = self.log_data['data_quality']['high_quality'] + self.log_data['data_quality']['medium_quality'] + self.log_data['data_quality']['low_quality']
            if total > 0:
                f.write(f"High Quality: {self.log_data['data_quality']['high_quality']} ({self.log_data['data_quality']['high_quality']/total*100:.1f}%)\n")
                f.write(f"Medium Quality: {self.log_data['data_quality']['medium_quality']} ({self.log_data['data_quality']['medium_quality']/total*100:.1f}%)\n")
                f.write(f"Low Quality: {self.log_data['data_quality']['low_quality']} ({self.log_data['data_quality']['low_quality']/total*100:.1f}%)\n")
            f.write("\n")
            
            # Teams Status
            f.write("TEAMS STATUS\n")
            f.write("-" * 80 + "\n")
            f.write(f"Trained Teams ({len(self.log_data['training_status']['teams_trained'])}):\n")
            for team_id in self.log_data['training_status']['teams_trained']:
                f.write(f"  - Team ID: {team_id}\n")
            f.write(f"\nTeams Using DB Ratings ({len(self.log_data['training_status']['teams_using_db_ratings'])}):\n")
            for team_id in self.log_data['training_status']['teams_using_db_ratings']:
                f.write(f"  - Team ID: {team_id}\n")
            f.write(f"\nTeams Using Defaults ({len(self.log_data['training_status']['teams_using_defaults'])}):\n")
            for team_id in self.log_data['training_status']['teams_using_defaults']:
                f.write(f"  - Team ID: {team_id}\n")
            f.write("\n")
            
            # Fixture Details
            f.write("FIXTURE DETAILS\n")
            f.write("-" * 80 + "\n")
            for i, fixture in enumerate(self.log_data['fixtures'], 1):
                f.write(f"\nFixture {i}: {fixture['home_team']} vs {fixture['away_team']}\n")
                f.write(f"  Quality: {fixture['probability_quality'].upper()}\n")
                f.write(f"  Home Team: {'✓ Trained' if fixture['training_status']['home_team']['trained'] else '✗ ' + fixture['training_status']['home_team']['strength_source']}\n")
                f.write(f"  Away Team: {'✓ Trained' if fixture['training_status']['away_team']['trained'] else '✗ ' + fixture['training_status']['away_team']['strength_source']}\n")
                f.write(f"  Weather: {'✓ Downloaded' if fixture['data_ingestion']['weather']['downloaded'] else '✗ Missing'}\n")
                f.write(f"  Rest Days: {'✓ Calculated' if fixture['data_ingestion']['rest_days']['calculated'] else '✗ Missing'}\n")
                f.write(f"  Team Form: {'✓ Calculated' if fixture['data_ingestion']['team_form']['calculated'] else '✗ Missing'}\n")
                f.write(f"  Injuries: {'✓ Downloaded' if fixture['data_ingestion']['injuries']['downloaded'] else '✗ Missing'}\n")
        
        logger.info(f"✓ Saved jackpot summary to: {filepath}")


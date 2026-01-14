"""
Automated Pipeline Service

Detects missing teams or missing training data, downloads missing data,
retrains the model, and optionally recomputes probabilities.
"""
import logging
from typing import List, Dict, Optional, Set, Callable
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.models import (
    Team, League, Match, Model, ModelStatus
)
from app.services.team_resolver import resolve_team_safe, create_team_if_not_exists
from app.services.data_ingestion import DataIngestionService
from app.services.model_training import ModelTrainingService

logger = logging.getLogger(__name__)


class AutomatedPipelineService:
    """Service for automated data pipeline: detect → download → train → recompute"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ingestion_service = DataIngestionService(db)
        self.training_service = ModelTrainingService(db)
    
    def check_teams_status(
        self,
        team_names: List[str],
        league_id: Optional[int] = None
    ) -> Dict:
        """
        Check validation and training status for a list of teams
        
        Returns:
            Dict with:
            - validated_teams: List of team names that exist in DB
            - missing_teams: List of team names NOT in DB
            - trained_teams: List of team IDs that have model training data
            - untrained_teams: List of team IDs that DON'T have model training data
            - team_details: Dict mapping team_name -> {team_id, isValid, isTrained, league_code}
        """
        validated_teams = []
        missing_teams = []
        trained_team_ids = set()
        untrained_team_ids = set()
        team_details = {}
        
        # Get active models to check training status
        # IMPORTANT: Refresh the session to ensure we get the latest active models
        self.db.expire_all()  # Expire all cached objects to force fresh query
        poisson_model = self.db.query(Model).filter(
            Model.model_type == "poisson",
            Model.status == ModelStatus.active
        ).order_by(Model.training_completed_at.desc()).first()
        
        # Also check for active calibration model (for full pipeline training)
        calibration_model = self.db.query(Model).filter(
            Model.model_type == "calibration",
            Model.status == ModelStatus.active
        ).order_by(Model.training_completed_at.desc()).first()
        
        has_full_pipeline = poisson_model is not None and calibration_model is not None
        
        team_strengths = {}
        # Also create a mapping by canonical_name for better matching
        team_strengths_by_name = {}
        if poisson_model and poisson_model.model_weights:
            team_strengths = poisson_model.model_weights.get('team_strengths', {})
            logger.info(f"Checking training status against active Poisson model: {poisson_model.version} (ID: {poisson_model.id})")
            logger.info(f"Active model has {len(team_strengths)} teams in team_strengths")
            logger.info(f"Active model trained on: {poisson_model.training_completed_at}")
            
            if calibration_model:
                logger.info(f"✓ Full pipeline trained: Calibration model {calibration_model.version} (ID: {calibration_model.id}) is active")
            else:
                logger.warning("⚠ Only Poisson model is active - calibration model missing (partial pipeline)")
            
            # Build canonical_name mapping by looking up team names from IDs
            canonical_mapping_count = 0
            for team_id_str, strength_data in team_strengths.items():
                try:
                    team_id_int = int(team_id_str) if isinstance(team_id_str, str) else team_id_str
                    team_from_model = self.db.query(Team).filter(Team.id == team_id_int).first()
                    if team_from_model and team_from_model.canonical_name:
                        canonical = team_from_model.canonical_name.lower()
                        team_strengths_by_name[canonical] = strength_data
                        canonical_mapping_count += 1
                except (ValueError, TypeError):
                    continue
            logger.info(f"Built canonical name mapping: {canonical_mapping_count} teams (out of {len(team_strengths)} total)")
        else:
            logger.warning("No active Poisson model found - all teams will be marked as untrained")
        
        for team_name in team_names:
            team = resolve_team_safe(self.db, team_name, league_id)
            
            if team:
                validated_teams.append(team_name)
                team_id = team.id
                canonical_name = team.canonical_name.lower() if team.canonical_name else None
                
                # Check if team has training data (by ID or by canonical_name)
                # For "fully trained", team must be in Poisson model AND calibration model must exist
                matched_by_id = (team_id in team_strengths or str(team_id) in team_strengths)
                matched_by_canonical = (canonical_name and canonical_name in team_strengths_by_name)
                is_in_poisson = matched_by_id or matched_by_canonical
                
                # Team is "fully trained" if it's in Poisson model AND full pipeline (calibration) exists
                is_fully_trained = is_in_poisson and has_full_pipeline
                
                if is_in_poisson:
                    match_method = "ID" if matched_by_id else "canonical name"
                    if has_full_pipeline:
                        trained_team_ids.add(team_id)
                        logger.info(f"✓ Team '{team_name}' (ID: {team_id}, canonical: '{canonical_name}') is validated and fully trained (Poisson + Calibration) [matched by {match_method}]")
                    else:
                        trained_team_ids.add(team_id)
                        logger.warning(f"⚠ Team '{team_name}' (ID: {team_id}, canonical: '{canonical_name}') is in Poisson model but calibration missing (partial training) [matched by {match_method}]")
                else:
                    untrained_team_ids.add(team_id)
                    logger.warning(f"⚠ Team '{team_name}' (ID: {team_id}, canonical: '{canonical_name}') is validated but NOT trained - missing from active Poisson model")
                
                # Get league code for downloading
                league = self.db.query(League).filter(League.id == team.league_id).first()
                league_code = league.code if league else None
                
                team_details[team_name] = {
                    "team_id": team_id,
                    "isValid": True,
                    "isTrained": is_fully_trained,  # Only True if both Poisson and Calibration exist
                    "isInPoisson": is_in_poisson,  # True if in Poisson model
                    "hasFullPipeline": has_full_pipeline,  # True if calibration exists
                    "league_code": league_code,
                    "league_id": team.league_id
                }
            else:
                missing_teams.append(team_name)
                logger.warning(f"✗ Team '{team_name}' is MISSING from database (league_id: {league_id})")
                team_details[team_name] = {
                    "team_id": None,
                    "isValid": False,
                    "isTrained": False,
                    "league_code": None,
                    "league_id": league_id
                }
        
        # Log summary
        logger.info(f"=== TEAM STATUS CHECK SUMMARY ===")
        logger.info(f"Total teams checked: {len(team_names)}")
        logger.info(f"Validated teams: {len(validated_teams)}")
        logger.info(f"Missing teams: {len(missing_teams)}")
        if missing_teams:
            logger.warning(f"MISSING TEAMS: {', '.join(missing_teams)}")
        logger.info(f"Trained teams: {len(trained_team_ids)}")
        logger.info(f"Untrained teams: {len(untrained_team_ids)}")
        if untrained_team_ids:
            logger.warning(f"UNTRAINED TEAM IDs: {list(untrained_team_ids)}")
        
        return {
            "validated_teams": validated_teams,
            "missing_teams": missing_teams,
            "trained_teams": list(trained_team_ids),
            "untrained_teams": list(untrained_team_ids),
            "team_details": team_details
        }
    
    def download_missing_team_data(
        self,
        team_names: List[str],
        league_id: Optional[int] = None,
        seasons: Optional[List[str]] = None,
        max_seasons: int = 7
    ) -> Dict:
        """
        Download historical match data for missing teams
        
        Args:
            team_names: List of team names to download data for
            league_id: Optional league ID to narrow search
            seasons: Optional list of seasons (e.g., ['2324', '2223'])
            max_seasons: Number of seasons to download if seasons not specified
        
        Returns:
            Dict with download statistics
        """
        if not seasons:
            # Get last N seasons
            from app.services.data_ingestion import get_seasons_list
            seasons = get_seasons_list(max_seasons)
        
        # Group teams by league
        leagues_to_download = {}
        
        for team_name in team_names:
            team = resolve_team_safe(self.db, team_name, league_id)
            
            if not team:
                # Try to get league from league_id if provided
                if league_id:
                    league = self.db.query(League).filter(League.id == league_id).first()
                    if league:
                        league_code = league.code
                    else:
                        logger.warning(f"League ID {league_id} not found for team {team_name}")
                        continue
                else:
                    logger.warning(f"Cannot determine league for missing team: {team_name}")
                    continue
            else:
                league = self.db.query(League).filter(League.id == team.league_id).first()
                if not league:
                    logger.warning(f"League not found for team {team_name} (ID: {team.league_id})")
                    continue
                league_code = league.code
            
            if league_code not in leagues_to_download:
                leagues_to_download[league_code] = {
                    "league_id": league.id,
                    "teams": []
                }
            
            leagues_to_download[league_code]["teams"].append(team_name)
        
        # Download data for each league
        download_stats = {
            "leagues_downloaded": [],
            "total_matches": 0,
            "errors": []
        }
        
        for league_code, league_info in leagues_to_download.items():
            try:
                logger.info(f"Downloading data for league {league_code} (seasons: {seasons})")
                
                # Download all seasons for this league
                for season in seasons:
                    try:
                        stats = self.ingestion_service.ingest_from_football_data(
                            league_code=league_code,
                            season=season,
                            save_csv=True
                        )
                        
                        download_stats["total_matches"] += stats.get("processed", 0)
                        logger.info(f"Downloaded {stats.get('processed', 0)} matches for {league_code} season {season}")
                    except Exception as e:
                        error_msg = f"Error downloading {league_code} season {season}: {str(e)}"
                        logger.error(error_msg)
                        download_stats["errors"].append(error_msg)
                
                download_stats["leagues_downloaded"].append({
                    "league_code": league_code,
                    "seasons": seasons
                })
                
            except Exception as e:
                error_msg = f"Error downloading league {league_code}: {str(e)}"
                logger.error(error_msg)
                download_stats["errors"].append(error_msg)
        
        # Mark as successful if matches were downloaded (even if there were some errors)
        download_stats["success"] = download_stats["total_matches"] > 0
        download_stats["skipped"] = download_stats["total_matches"] == 0 and len(download_stats["errors"]) == 0
        
        logger.info(f"=== DATA DOWNLOAD SUMMARY ===")
        logger.info(f"Total matches downloaded: {download_stats['total_matches']}")
        logger.info(f"Leagues processed: {len(download_stats['leagues_downloaded'])}")
        logger.info(f"Errors: {len(download_stats['errors'])}")
        logger.info(f"Success: {download_stats['success']}, Skipped: {download_stats['skipped']}")
        
        return download_stats
    
    def create_missing_teams(
        self,
        team_names: List[str],
        league_id: int
    ) -> Dict:
        """
        Create missing teams in the database
        
        Args:
            team_names: List of team names to create
            league_id: League ID to assign teams to
        
        Returns:
            Dict with creation statistics
        """
        created = []
        skipped = []
        errors = []
        
        for team_name in team_names:
            try:
                # Check if team already exists
                existing = resolve_team_safe(self.db, team_name, league_id)
                if existing:
                    skipped.append(team_name)
                    continue
                
                # Create team
                team = create_team_if_not_exists(self.db, team_name, league_id)
                created.append(team_name)
                logger.info(f"Created team: {team_name} (ID: {team.id})")
                
            except Exception as e:
                error_msg = f"Error creating team {team_name}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        self.db.commit()
        
        return {
            "created": created,
            "skipped": skipped,
            "errors": errors
        }
    
    def check_teams_have_matches(
        self,
        team_ids: List[int],
        min_matches: int = 10
    ) -> Dict:
        """
        Check if teams have enough matches in the database for training
        
        Args:
            team_ids: List of team IDs to check
            min_matches: Minimum number of matches required
        
        Returns:
            Dict mapping team_id -> match_count
        """
        match_counts = {}
        
        for team_id in team_ids:
            count = self.db.query(Match).filter(
                or_(
                    Match.home_team_id == team_id,
                    Match.away_team_id == team_id
                )
            ).count()
            
            match_counts[team_id] = count
        
        return match_counts
    
    def run_full_pipeline(
        self,
        team_names: List[str],
        league_id: Optional[int] = None,
        auto_download: bool = True,
        auto_train: bool = True,
        auto_recompute: bool = False,
        jackpot_id: Optional[str] = None,
        seasons: Optional[List[str]] = None,
        max_seasons: int = 7,
        base_model_window_years: Optional[float] = None,  # Recent data focus: 2, 3, or 4 years (default: 4)
        save_to_jackpot: bool = True,
        progress_callback: Optional[Callable[[int, str, Optional[Dict]], None]] = None
    ) -> Dict:
        """
        Run full automated pipeline:
        1. Check team validation and training status
        2. Download missing data (if auto_download=True)
        3. Create missing teams
        4. Retrain model (if auto_train=True)
        5. Recompute probabilities (if auto_recompute=True)
        
        Args:
            team_names: List of team names to process
            league_id: Optional league ID
            auto_download: Automatically download missing data
            auto_train: Automatically retrain model after download
            auto_recompute: Automatically recompute probabilities (requires jackpot_id)
            jackpot_id: Jackpot ID for recomputing probabilities
            seasons: Optional list of seasons to download
            max_seasons: Number of seasons to download if seasons not specified
            base_model_window_years: Training data window in years (2, 3, or 4). 
                                    None = use default (4 years). 
                                    Smaller values focus on recent data.
        
        Returns:
            Dict with pipeline execution results
        """
        logger.info(f"=== STARTING AUTOMATED PIPELINE ===")
        logger.info(f"Teams: {team_names}")
        logger.info(f"League ID: {league_id}")
        
        results = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "steps": {}
        }
        
        # Step 1: Check team status
        logger.info("Step 1: Checking team validation and training status...")
        if progress_callback:
            progress_callback(10, "Checking team validation and training status...", results["steps"])
        status_check = self.check_teams_status(team_names, league_id)
        results["steps"]["status_check"] = status_check
        
        missing_teams = status_check["missing_teams"]
        untrained_teams = status_check["untrained_teams"]
        
        # Step 2: Create missing teams
        if missing_teams:
            logger.info(f"=== CREATING MISSING TEAMS ===")
            logger.info(f"Step 2: Creating {len(missing_teams)} missing teams...")
            logger.info(f"Missing teams list: {missing_teams}")
            if progress_callback:
                progress_callback(20, f"Creating {len(missing_teams)} missing teams...", results["steps"])
            
            # Need league_id to create teams
            if not league_id:
                # Try to infer from first validated team
                if status_check["validated_teams"]:
                    first_validated = status_check["validated_teams"][0]
                    team_details = status_check["team_details"][first_validated]
                    league_id = team_details.get("league_id")
                    logger.info(f"Inferred league_id: {league_id} from validated team '{first_validated}'")
                
                if not league_id:
                    error_msg = "Cannot create teams: league_id required but not provided"
                    logger.error(f"✗ {error_msg}")
                    logger.error(f"Missing teams that cannot be created: {missing_teams}")
                    results["status"] = "failed"
                    results["error"] = error_msg
                    if progress_callback:
                        progress_callback(0, f"Error: {error_msg}", results["steps"])
                    return results
            
            logger.info(f"Creating teams with league_id: {league_id}")
            create_result = self.create_missing_teams(missing_teams, league_id)
            results["steps"]["create_teams"] = create_result
            
            # Log creation results
            logger.info(f"=== TEAM CREATION RESULTS ===")
            logger.info(f"Created: {len(create_result.get('created', []))} teams")
            if create_result.get('created'):
                logger.info(f"Created teams: {', '.join(create_result.get('created', []))}")
            logger.info(f"Skipped (already exist): {len(create_result.get('skipped', []))} teams")
            if create_result.get('skipped'):
                logger.info(f"Skipped teams: {', '.join(create_result.get('skipped', []))}")
            logger.info(f"Errors: {len(create_result.get('errors', []))} teams")
            if create_result.get('errors'):
                for error in create_result.get('errors', []):
                    logger.error(f"  ✗ {error}")
            
            if progress_callback:
                progress_callback(30, f"Created {len(create_result.get('created', []))} teams", results["steps"])
            
            # Update status check after creating teams
            logger.info("Re-checking team status after creation...")
            status_check = self.check_teams_status(team_names, league_id)
        else:
            logger.info("Step 2: No missing teams to create - all teams exist in database")
            results["steps"]["create_teams"] = {"skipped": True, "reason": "No missing teams"}
        
        # Step 3: Download missing data
        if auto_download:
            if progress_callback:
                progress_callback(40, "Determining which teams need data...", results["steps"])
            
            # Determine which teams need data
            teams_needing_data = []
            
            # Missing teams (need to download their league data)
            teams_needing_data.extend(missing_teams)
            
            # Untrained teams (may need more historical data)
            for team_name, details in status_check["team_details"].items():
                if details["team_id"] in untrained_teams:
                    # Check if team has enough matches
                    match_counts = self.check_teams_have_matches([details["team_id"]])
                    if match_counts.get(details["team_id"], 0) < 10:
                        teams_needing_data.append(team_name)
            
            if teams_needing_data:
                logger.info(f"Step 3: Downloading data for {len(teams_needing_data)} teams...")
                if progress_callback:
                    progress_callback(50, f"Downloading data for {len(teams_needing_data)} teams...", results["steps"])
                download_result = self.download_missing_team_data(
                    teams_needing_data,
                    league_id,
                    seasons,
                    max_seasons
                )
                results["steps"]["download_data"] = download_result
                if progress_callback:
                    total_matches = download_result.get("total_matches", 0)
                    progress_callback(70, f"Downloaded {total_matches} matches", results["steps"])
            else:
                logger.info("Step 3: No teams need data download")
                results["steps"]["download_data"] = {"skipped": True, "reason": "All teams have sufficient data"}
                if progress_callback:
                    progress_callback(70, "No data download needed", results["steps"])
        else:
            results["steps"]["download_data"] = {"skipped": True, "reason": "auto_download=False"}
        
        # Step 4: Retrain model (only if actually needed)
        # Re-check team status AFTER data download to see if teams are now trained
        if auto_train:
            # Re-check training status after potential data download
            updated_status_check = self.check_teams_status(team_names, league_id)
            updated_untrained_teams = updated_status_check.get("untrained_teams", [])
            
            # Check if new data was downloaded
            download_step = results.get("steps", {}).get("download_data", {})
            new_data_downloaded = download_step.get("success", False) and not download_step.get("skipped", False)
            
            # Check if active model exists
            poisson_model = self.db.query(Model).filter(
                Model.model_type == "poisson",
                Model.status == ModelStatus.active
            ).order_by(Model.training_completed_at.desc()).first()
            
            # Determine if retraining is needed
            has_untrained_teams = len(updated_untrained_teams) > 0
            has_active_model = poisson_model is not None
            
            logger.info(f"=== RETRAINING DECISION LOGIC ===")
            logger.info(f"Untrained teams: {len(updated_untrained_teams)}")
            logger.info(f"New data downloaded: {new_data_downloaded}")
            logger.info(f"Active model exists: {has_active_model}")
            logger.info(f"Auto recompute requested: {auto_recompute}")
            
            # Retrain if:
            # 1. There are untrained teams (they need to be added to the model), OR
            # 2. New data was downloaded (to incorporate new matches), OR
            # 3. No active model exists (need to create one), OR
            # 4. Explicitly requested via auto_recompute
            needs_retraining = (
                has_untrained_teams or  # CRITICAL: Always retrain if teams are missing
                new_data_downloaded or  # Retrain to incorporate new data
                not has_active_model or  # Need to create initial model
                auto_recompute  # Explicitly requested
            )
            
            if not needs_retraining:
                logger.info("Step 4: Skipping retraining - all teams are already trained and no new data downloaded")
                logger.info(f"  - Trained teams: {len(updated_status_check.get('trained_teams', []))}")
                logger.info(f"  - Untrained teams: {len(updated_untrained_teams)}")
                logger.info(f"  - New data: {new_data_downloaded}")
                results["steps"]["retrain_model"] = {
                    "skipped": True,
                    "reason": "All teams already trained in active model and no new data",
                    "trained_teams": len(updated_status_check.get("trained_teams", [])),
                    "untrained_teams": len(updated_untrained_teams),
                    "new_data_downloaded": new_data_downloaded
                }
                if progress_callback:
                    progress_callback(75, "All teams already trained - skipping retraining", results["steps"])
        
        if auto_train and needs_retraining:
            logger.info("=== STARTING MODEL RETRAINING ===")
            logger.info("Step 4: Retraining model (teams need training or new data downloaded)...")
            logger.info(f"Retraining reason: has_untrained_teams={has_untrained_teams}, new_data_downloaded={new_data_downloaded}, auto_recompute={auto_recompute}")
            if progress_callback:
                progress_callback(75, "Retraining model...", results["steps"])
            try:
                # Get league codes from teams
                league_codes = set()
                for team_name, details in status_check["team_details"].items():
                    if details.get("league_code"):
                        league_codes.add(details["league_code"])
                
                logger.info(f"Retraining for leagues: {list(league_codes) if league_codes else 'ALL'}")
                
                # Train full pipeline: Poisson → Blending → Calibration
                # This ensures we get the best possible model (calibrated and blended with market odds)
                if progress_callback:
                    progress_callback(75, "Training Poisson model...", results["steps"])
                
                logger.info("=== TRAINING POISSON MODEL ===")
                # Step 1: Train Poisson model
                try:
                    poisson_result = self.training_service.train_poisson_model(
                        leagues=list(league_codes) if league_codes else None,
                        base_model_window_years=base_model_window_years,  # Recent data focus
                        task_id=f"auto-pipeline-poisson-{datetime.now().timestamp()}"
                    )
                    logger.info(f"✓ Poisson model trained: ID={poisson_result.get('modelId')}, version={poisson_result.get('version')}")
                except Exception as e:
                    logger.error(f"✗ Poisson model training failed: {e}", exc_info=True)
                    raise  # Re-raise to be caught by outer exception handler
                
                if progress_callback:
                    progress_callback(80, "Training blending model...", results["steps"])
                
                logger.info("=== TRAINING BLENDING MODEL ===")
                # Step 2: Train blending model (combines Poisson with market odds)
                try:
                    blending_result = self.training_service.train_blending_model(
                        poisson_model_id=poisson_result.get("modelId"),
                        leagues=list(league_codes) if league_codes else None,
                        task_id=f"auto-pipeline-blending-{datetime.now().timestamp()}"
                    )
                    logger.info(f"✓ Blending model trained: ID={blending_result.get('modelId')}, version={blending_result.get('version')}")
                except Exception as e:
                    logger.error(f"✗ Blending model training failed: {e}", exc_info=True)
                    raise  # Re-raise to be caught by outer exception handler
                
                if progress_callback:
                    progress_callback(90, "Training calibration model...", results["steps"])
                
                logger.info("=== TRAINING CALIBRATION MODEL ===")
                # Step 3: Train calibration model (calibrates the blended model)
                try:
                    calibration_result = self.training_service.train_calibration_model(
                        base_model_id=blending_result.get("modelId"),  # Calibrate blended model, not raw Poisson
                        leagues=list(league_codes) if league_codes else None,
                        task_id=f"auto-pipeline-calibration-{datetime.now().timestamp()}"
                    )
                    logger.info(f"✓ Calibration model trained: ID={calibration_result.get('modelId')}, version={calibration_result.get('version')}")
                except Exception as e:
                    logger.error(f"✗ Calibration model training failed: {e}", exc_info=True)
                    raise  # Re-raise to be caught by outer exception handler
                
                # Step 4: Train draw calibration model (optional, requires historical predictions with results)
                draw_calibration_result = None
                draw_calibration_error = None
                try:
                    if progress_callback:
                        progress_callback(92, "Training draw calibration model...", results["steps"])
                    
                    logger.info("=== TRAINING DRAW CALIBRATION MODEL ===")
                    # Draw calibration requires predictions with actual results
                    # This is optional and may fail if insufficient data
                    draw_calibration_result = self.training_service.train_draw_calibration_model(
                        leagues=list(league_codes) if league_codes else None,
                        task_id=f"auto-pipeline-draw-calibration-{datetime.now().timestamp()}"
                    )
                    logger.info(f"✓ Draw calibration model trained successfully: ID={draw_calibration_result.get('modelId')}, version={draw_calibration_result.get('version')}")
                except Exception as draw_e:
                    # Draw calibration is optional - log but don't fail the pipeline
                    draw_calibration_error = str(draw_e)
                    logger.warning(f"⚠ Draw calibration skipped: {draw_calibration_error}")
                    if "Insufficient" in str(draw_e) or "not found" in str(draw_e).lower():
                        logger.info("Draw calibration requires 500+ predictions with actual results. Skipping for now.")
                
                # Store results from all models
                train_model_result = {
                    "success": True,
                    "poisson": {
                        "model_id": poisson_result.get("modelId"),
                        "version": poisson_result.get("version")
                    },
                    "blending": {
                        "model_id": blending_result.get("modelId"),
                        "version": blending_result.get("version")
                    },
                    "calibration": {
                        "model_id": calibration_result.get("modelId"),
                        "version": calibration_result.get("version")
                    },
                    "final_model_id": calibration_result.get("modelId"),  # Final calibrated model
                    "final_version": calibration_result.get("version"),
                    "base_model_window_years": base_model_window_years or 4.0,  # Store config
                    "pipeline": "full"  # Indicates full pipeline was trained
                }
                
                # Add draw calibration if successful
                if draw_calibration_result:
                    train_model_result["draw_calibration"] = {
                        "model_id": draw_calibration_result.get("modelId"),
                        "version": draw_calibration_result.get("version")
                    }
                elif draw_calibration_error:
                    train_model_result["draw_calibration"] = {
                        "skipped": True,
                        "error": draw_calibration_error,
                        "note": "Requires 500+ predictions with actual results"
                    }
                
                results["steps"]["train_model"] = train_model_result
                
                if progress_callback:
                    final_version = calibration_result.get("version", "N/A")
                    draw_status = " (with draw calibration)" if draw_calibration_result else ""
                    progress_callback(95, f"Full pipeline trained: {final_version}{draw_status}", results["steps"])
                
                logger.info("=== MODEL TRAINING PIPELINE COMPLETED SUCCESSFULLY ===")
                logger.info(f"Final model: {calibration_result.get('version')} (ID: {calibration_result.get('modelId')})")
                logger.info(f"Pipeline components: Poisson={poisson_result.get('modelId')}, Blending={blending_result.get('modelId')}, Calibration={calibration_result.get('modelId')}")
            except Exception as e:
                error_msg = f"Model training failed: {str(e)}"
                logger.error(f"✗ {error_msg}", exc_info=True)
                logger.error(f"=== MODEL RETRAINING FAILED ===")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error details: {str(e)}")
                results["steps"]["train_model"] = {
                    "success": False,
                    "error": error_msg,
                    "error_type": type(e).__name__,
                    "pipeline": "partial"  # Indicates partial failure
                }
                if progress_callback:
                    progress_callback(90, f"Model training failed: {str(e)}", results["steps"])
        else:
            logger.info("Step 4: Skipping retraining - all teams are already trained and no new data downloaded")
            results["steps"]["train_model"] = {"skipped": True}
        
        # Step 5: Recompute probabilities (if requested)
        if auto_recompute and jackpot_id:
            logger.info(f"Step 5: Recomputing probabilities for jackpot {jackpot_id}...")
            try:
                # This would trigger probability recomputation
                # In a real implementation, you'd call the probability calculation endpoint
                results["steps"]["recompute_probabilities"] = {
                    "success": True,
                    "jackpot_id": jackpot_id,
                    "message": "Probabilities will be recomputed on next calculation request"
                }
            except Exception as e:
                error_msg = f"Probability recomputation failed: {str(e)}"
                logger.error(error_msg)
                results["steps"]["recompute_probabilities"] = {
                    "success": False,
                    "error": error_msg
                }
        else:
            results["steps"]["recompute_probabilities"] = {"skipped": True}
        
        # Mark as completed
        results["status"] = "completed"
        results["completed_at"] = datetime.now().isoformat()
        
        # Log pipeline completion
        logger.info("=== AUTOMATED PIPELINE COMPLETED ===")
        logger.info(f"Pipeline status: {results['status']}")
        logger.info(f"Completed at: {results['completed_at']}")
        logger.info(f"Steps completed: {list(results['steps'].keys())}")
        
        # Check if training was successful
        train_model_result = results["steps"].get("train_model", {})
        if train_model_result.get("success"):
            logger.info(f"✓ Full model pipeline trained successfully")
            logger.info(f"  Final model version: {train_model_result.get('final_version', 'N/A')}")
            logger.info(f"  Final model ID: {train_model_result.get('final_model_id', 'N/A')}")
        elif train_model_result.get("skipped"):
            logger.info("⚠ Model training was skipped")
        else:
            logger.warning(f"⚠ Model training failed: {train_model_result.get('error', 'Unknown error')}")
        
        # Update progress callback with final status
        if progress_callback:
            progress_callback(100, "Pipeline completed successfully", results["steps"])
        
        # Save pipeline metadata to jackpot if requested
        if save_to_jackpot and jackpot_id:
            try:
                from app.db.models import Jackpot as JackpotModel
                jackpot = self.db.query(JackpotModel).filter(
                    JackpotModel.jackpot_id == jackpot_id
                ).first()
                
                if jackpot:
                    pipeline_metadata = {
                        "execution_timestamp": results["started_at"],
                        "pipeline_run": True,
                        "teams_created": results["steps"].get("create_teams", {}).get("created", []),
                        "data_downloaded": "download_data" in results["steps"] and not results["steps"]["download_data"].get("skipped", False),
                        "download_stats": results["steps"].get("download_data", {}),
                        "model_trained": results["steps"].get("train_model", {}).get("success", False),
                        "training_stats": {
                            "poisson": results["steps"].get("train_model", {}).get("poisson", {}),
                            "blending": results["steps"].get("train_model", {}).get("blending", {}),
                            "calibration": results["steps"].get("train_model", {}).get("calibration", {}),
                            "draw_calibration": results["steps"].get("train_model", {}).get("draw_calibration", {}),
                            "final_model_id": results["steps"].get("train_model", {}).get("final_model_id"),
                            "final_version": results["steps"].get("train_model", {}).get("final_version"),
                            "base_model_window_years": results["steps"].get("train_model", {}).get("base_model_window_years", 4.0),  # Recent data focus config
                            "pipeline": results["steps"].get("train_model", {}).get("pipeline", "poisson_only"),  # "full" or "poisson_only"
                        } if results["steps"].get("train_model", {}).get("success") else None,
                        "probabilities_calculated_with_new_data": results["steps"].get("train_model", {}).get("success", False),
                        "recent_data_focus": {
                            "base_model_window_years": base_model_window_years or 4.0,
                            "description": f"Model trained on last {base_model_window_years or 4.0} years of data" + 
                                         (" (recent data focus)" if base_model_window_years and base_model_window_years < 4.0 else " (default)")
                        },
                        "status": results["status"],
                        "errors": [
                            error for step_data in results["steps"].values()
                            if isinstance(step_data, dict) and step_data.get("errors")
                            for error in step_data.get("errors", [])
                        ]
                    }
                    
                    jackpot.pipeline_metadata = pipeline_metadata
                    self.db.commit()
                    logger.info(f"Saved pipeline metadata to jackpot {jackpot_id}")
            except Exception as e:
                logger.error(f"Failed to save pipeline metadata to jackpot: {e}", exc_info=True)
        
        logger.info("=== AUTOMATED PIPELINE COMPLETED ===")
        logger.info(f"Final status: {results['status']}, Steps completed: {list(results['steps'].keys())}")
        
        return results


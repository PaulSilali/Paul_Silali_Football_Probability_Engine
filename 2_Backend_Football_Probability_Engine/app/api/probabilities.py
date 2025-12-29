"""
FastAPI Router for Probability Calculations
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.prediction import (
    JackpotInput, PredictionResponse, MatchProbabilitiesOutput, PredictionWarning
)
from app.models.dixon_coles import (
    TeamStrength, DixonColesParams, calculate_match_probabilities
)
from app.models.probability_sets import generate_all_probability_sets, PROBABILITY_SET_METADATA
from app.db.models import Model, Jackpot as JackpotModel, JackpotFixture, Prediction, Team
from datetime import datetime
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
router = APIRouter(tags=["probabilities"])


def resolve_team_name(db: Session, team_name: str, league_id: Optional[int] = None) -> Optional[Team]:
    """Resolve team name to Team model using fuzzy matching"""
    result = resolve_team(db, team_name, league_id)
    return result[0] if result else None


def get_team_strength(db: Session, team: Team) -> TeamStrength:
    """Get team strength parameters"""
    return TeamStrength(
        team_id=team.id,
        attack=team.attack_rating,
        defense=team.defense_rating,
        league_id=team.league_id
    )


@router.get("/{jackpot_id}/probabilities", response_model=PredictionResponse)
async def calculate_probabilities(
    jackpot_id: str,
    db: Session = Depends(get_db)
):
    """
    Calculate probabilities for a jackpot.
    
    This is the main prediction endpoint.
    """
    try:
        # Get jackpot
        jackpot = db.query(JackpotModel).filter(
            JackpotModel.jackpot_id == jackpot_id
        ).first()
        
        if not jackpot:
            raise HTTPException(status_code=404, detail="Jackpot not found")
        
        # Get active model
        model = db.query(Model).filter(Model.status == "active").first()
        if not model:
            raise HTTPException(status_code=500, detail="No active model found")
        
        # Get fixtures
        fixtures = db.query(JackpotFixture).filter(
            JackpotFixture.jackpot_id == jackpot.id
        ).order_by(JackpotFixture.match_order).all()
        
        if not fixtures:
            raise HTTPException(status_code=400, detail="No fixtures found for jackpot")
        
        # Process each fixture
        all_probability_sets: Dict[str, List[MatchProbabilitiesOutput]] = {}
        confidence_flags: Dict[int, str] = {}
        warnings: List[PredictionWarning] = []
        
        # Initialize probability sets dict
        for set_id in ["A", "B", "C", "D", "E", "F", "G"]:
            all_probability_sets[set_id] = []
        
        for idx, fixture in enumerate(fixtures):
            # Resolve team names
            home_team = resolve_team_name(db, fixture.home_team)
            away_team = resolve_team_name(db, fixture.away_team)
            
            if not home_team or not away_team:
                warnings.append(PredictionWarning(
                    fixtureId=fixture.id,
                    type="team_not_found",
                    message=f"Teams not found: {fixture.home_team} vs {fixture.away_team}",
                    severity="warning"
                ))
                # Use default probabilities
                default_probs = MatchProbabilitiesOutput(
                    homeWinProbability=0.33,
                    drawProbability=0.34,
                    awayWinProbability=0.33,
                    entropy=1.58
                )
                for set_id in all_probability_sets:
                    all_probability_sets[set_id].append(default_probs)
                confidence_flags[idx] = "low"
                continue
            
            # Get team strengths
            home_strength = get_team_strength(db, home_team)
            away_strength = get_team_strength(db, away_team)
            
            # Calculate model probabilities
            params = DixonColesParams(
                rho=-0.13,
                xi=0.0065,
                home_advantage=0.35
            )
            model_probs = calculate_match_probabilities(
                home_strength, away_strength, params
            )
            
            # Prepare market odds
            market_odds = None
            if fixture.odds_home and fixture.odds_draw and fixture.odds_away:
                market_odds = {
                    "home": fixture.odds_home,
                    "draw": fixture.odds_draw,
                    "away": fixture.odds_away
                }
            
            # Generate all probability sets
            probability_sets = generate_all_probability_sets(
                model_probs,
                market_odds
            )
            
            # Convert to output format
            for set_id, probs in probability_sets.items():
                output = MatchProbabilitiesOutput(
                    homeWinProbability=probs.home * 100,  # Convert to percentage
                    drawProbability=probs.draw * 100,
                    awayWinProbability=probs.away * 100,
                    entropy=probs.entropy
                )
                all_probability_sets[set_id].append(output)
            
            # Store predictions in database
            for set_id, probs in probability_sets.items():
                pred = Prediction(
                    fixture_id=fixture.id,
                    model_id=model.id,
                    set_type=set_id,
                    prob_home=probs.home,
                    prob_draw=probs.draw,
                    prob_away=probs.away,
                    predicted_outcome="H" if probs.home > max(probs.draw, probs.away) else "D" if probs.draw > probs.away else "A",
                    confidence=max(probs.home, probs.draw, probs.away),
                    entropy=probs.entropy,
                    expected_home_goals=probs.lambda_home,
                    expected_away_goals=probs.lambda_away
                )
                db.add(pred)
            
            # Confidence flag
            base_entropy = model_probs.entropy
            if base_entropy < 1.0:
                confidence_flags[idx] = "high"
            elif base_entropy > 1.2:
                confidence_flags[idx] = "low"
            else:
                confidence_flags[idx] = "medium"
        
        db.commit()
        
        # Build response
        return PredictionResponse(
            predictionId=jackpot.jackpot_id,
            modelVersion=model.version,
            createdAt=jackpot.created_at,
            fixtures=[
                {
                    "id": str(f.id),
                    "homeTeam": f.home_team,
                    "awayTeam": f.away_team,
                    "odds": {
                        "home": f.odds_home,
                        "draw": f.odds_draw,
                        "away": f.odds_away
                    } if f.odds_home else None
                }
                for f in fixtures
            ],
            probabilitySets=all_probability_sets,
            confidenceFlags={str(k): v for k, v in confidence_flags.items()},
            warnings=warnings if warnings else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{jackpot_id}/probabilities/{set_id}")
async def get_probability_set(
    jackpot_id: str,
    set_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific probability set for a jackpot"""
    if set_id not in ["A", "B", "C", "D", "E", "F", "G"]:
        raise HTTPException(status_code=400, detail="Invalid set ID")
    
    # Get predictions from database
    jackpot = db.query(JackpotModel).filter(
        JackpotModel.jackpot_id == jackpot_id
    ).first()
    
    if not jackpot:
        raise HTTPException(status_code=404, detail="Jackpot not found")
    
    fixtures = db.query(JackpotFixture).filter(
        JackpotFixture.jackpot_id == jackpot.id
    ).order_by(JackpotFixture.match_order).all()
    
    predictions = []
    for fixture in fixtures:
        pred = db.query(Prediction).filter(
            Prediction.fixture_id == fixture.id,
            Prediction.set_type == set_id
        ).first()
        
        if pred:
            predictions.append({
                "fixtureId": str(fixture.id),
                "homeTeam": fixture.home_team,
                "awayTeam": fixture.away_team,
                "homeWinProbability": pred.prob_home * 100,
                "drawProbability": pred.prob_draw * 100,
                "awayWinProbability": pred.prob_away * 100,
                "entropy": pred.entropy
            })
    
    metadata = PROBABILITY_SET_METADATA.get(set_id, {})
    
    return {
        "id": set_id,
        "name": metadata.get("name", f"Set {set_id}"),
        "description": metadata.get("description", ""),
        "probabilities": predictions
    }


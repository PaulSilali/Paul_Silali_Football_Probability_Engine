"""
Explainability API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Jackpot as JackpotModel, JackpotFixture, Prediction, Team
from app.models.dixon_coles import TeamStrength
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jackpots", tags=["explainability"])


def calculate_feature_contributions(
    home_team: Team,
    away_team: Team,
    prediction: Prediction
) -> List[Dict]:
    """
    Calculate feature contributions for a prediction
    
    Returns list of features with their contributions
    """
    contributions = []
    
    # Attack strength contribution
    home_attack_contribution = (home_team.attack_rating - 1.0) * 0.15
    away_attack_contribution = (away_team.attack_rating - 1.0) * 0.10
    
    # Defense strength contribution
    home_defense_contribution = (1.0 - away_team.defense_rating) * 0.12
    away_defense_contribution = (1.0 - home_team.defense_rating) * 0.10
    
    # Home advantage
    home_advantage_contribution = 0.07
    
    # Market signal (if available)
    if prediction.market_prob_home:
        market_signal = (prediction.prob_home - prediction.market_prob_home) * 0.06
        contributions.append({
            "feature": "Market Signal",
            "value": market_signal,
            "description": "Difference between model and market probabilities"
        })
    
    # Build contributions list
    contributions.extend([
        {
            "feature": f"{home_team.name} Attack Strength",
            "value": home_attack_contribution,
            "description": f"Attack rating: {home_team.attack_rating:.2f}"
        },
        {
            "feature": f"{away_team.name} Defense Weakness",
            "value": home_defense_contribution,
            "description": f"Defense rating: {away_team.defense_rating:.2f}"
        },
        {
            "feature": "Home Advantage",
            "value": home_advantage_contribution,
            "description": "Standard home advantage factor"
        },
        {
            "feature": f"{away_team.name} Attack Strength",
            "value": -away_attack_contribution,
            "description": f"Attack rating: {away_team.attack_rating:.2f}"
        },
        {
            "feature": f"{home_team.name} Defense Strength",
            "value": -away_defense_contribution,
            "description": f"Defense rating: {home_team.defense_rating:.2f}"
        }
    ])
    
    return contributions


@router.get("/{jackpot_id}/contributions")
async def get_feature_contributions(
    jackpot_id: str,
    set_id: str = "B",
    db: Session = Depends(get_db)
):
    """
    Get feature contributions for all fixtures in a jackpot
    
    Returns explainability data showing why predictions were made
    """
    jackpot = db.query(JackpotModel).filter(
        JackpotModel.jackpot_id == jackpot_id
    ).first()
    
    if not jackpot:
        raise HTTPException(status_code=404, detail="Jackpot not found")
    
    fixtures = db.query(JackpotFixture).filter(
        JackpotFixture.jackpot_id == jackpot.id
    ).order_by(JackpotFixture.match_order).all()
    
    if not fixtures:
        raise HTTPException(status_code=400, detail="No fixtures found")
    
    contributions_list = []
    
    for fixture in fixtures:
        # Get prediction
        prediction = db.query(Prediction).filter(
            Prediction.fixture_id == fixture.id,
            Prediction.set_type == set_id
        ).first()
        
        if not prediction:
            continue
        
        # Get teams
        home_team = db.query(Team).filter(Team.id == fixture.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == fixture.away_team_id).first()
        
        if not home_team or not away_team:
            continue
        
        # Calculate contributions
        contributions = calculate_feature_contributions(
            home_team, away_team, prediction
        )
        
        contributions_list.append({
            "fixtureId": str(fixture.id),
            "homeTeam": fixture.home_team,
            "awayTeam": fixture.away_team,
            "contributions": contributions
        })
    
    return {
        "data": contributions_list,
        "success": True
    }


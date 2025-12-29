"""
Export API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.db.models import Jackpot as JackpotModel, JackpotFixture, Prediction
from io import StringIO
import csv
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jackpots", tags=["export"])


@router.get("/{jackpot_id}/export")
async def export_predictions_csv(
    jackpot_id: str,
    set_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Export predictions as CSV
    
    Args:
        jackpot_id: Jackpot ID
        set_id: Optional probability set ID (A-G). If not provided, exports Set B
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
    
    # Use Set B by default
    set_id = set_id or "B"
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Match #",
        "Home Team",
        "Away Team",
        "Home Win %",
        "Draw %",
        "Away Win %",
        "Predicted Outcome",
        "Confidence",
        "Entropy"
    ])
    
    # Data rows
    for idx, fixture in enumerate(fixtures):
        prediction = db.query(Prediction).filter(
            Prediction.fixture_id == fixture.id,
            Prediction.set_type == set_id
        ).first()
        
        if prediction:
            writer.writerow([
                idx + 1,
                fixture.home_team,
                fixture.away_team,
                f"{prediction.prob_home * 100:.2f}",
                f"{prediction.prob_draw * 100:.2f}",
                f"{prediction.prob_away * 100:.2f}",
                prediction.predicted_outcome.value,
                f"{prediction.confidence * 100:.2f}",
                f"{prediction.entropy:.3f}" if prediction.entropy else ""
            ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=jackpot_{jackpot_id}_set_{set_id}.csv"
        }
    )


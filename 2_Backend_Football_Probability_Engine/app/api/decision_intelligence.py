"""
Decision Intelligence API Endpoints
===================================

Endpoints for ticket evaluation, threshold management, and decision intelligence metrics.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.db.session import get_db
from app.decision_intelligence.ticket_evaluator import evaluate_ticket
from app.decision_intelligence.thresholds import load_thresholds, learn_ev_threshold, update_thresholds, bootstrap_thresholds_from_backup
from app.db.models import Ticket, TicketPick, TicketOutcome, DecisionThreshold
from app.schemas.jackpot import ApiResponse
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/decision-intelligence", tags=["decision-intelligence"])


class EvaluateTicketRequest(BaseModel):
    """Request to evaluate a ticket using Unified Decision Score"""
    ticket_matches: List[Dict[str, Any]]
    ev_threshold: Optional[float] = None
    max_contradictions: Optional[int] = None


class SaveTicketRequest(BaseModel):
    """Request to save an evaluated ticket"""
    jackpot_id: Optional[int] = None
    ticket_type: str = "standard"
    ticket_matches: List[Dict[str, Any]]
    user_id: Optional[str] = None


@router.post("/evaluate", response_model=ApiResponse)
async def evaluate_ticket_endpoint(
    request: EvaluateTicketRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluate a ticket using Unified Decision Score (UDS).
    
    Returns:
        Evaluation result with accepted/rejected status, UDS score, contradictions, and enriched picks
    """
    try:
        evaluation = evaluate_ticket(
            ticket_matches=request.ticket_matches,
            db=db,
            ev_threshold=request.ev_threshold,
            max_contradictions=request.max_contradictions
        )
        
        return ApiResponse(
            success=True,
            message="Ticket evaluated successfully",
            data=evaluation
        )
    except Exception as e:
        logger.error(f"Error evaluating ticket: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to evaluate ticket: {str(e)}")


@router.post("/save-ticket", response_model=ApiResponse)
async def save_evaluated_ticket(
    request: SaveTicketRequest,
    db: Session = Depends(get_db)
):
    """
    Save an evaluated ticket to the database.
    
    This persists the ticket with its decision intelligence metadata for learning.
    """
    try:
        # Evaluate ticket first
        evaluation = evaluate_ticket(
            ticket_matches=request.ticket_matches,
            db=db
        )
        
        # Create ticket record
        ticket = Ticket(
            jackpot_id=request.jackpot_id,
            ticket_type=request.ticket_type,
            archetype=evaluation.get('archetype'),  # From ticket generation
            accepted=evaluation['accepted'],
            ev_score=evaluation['ev_score'],
            contradictions=evaluation['contradictions'],
            max_contradictions_allowed=evaluation['max_contradictions_allowed'],
            ev_threshold_used=evaluation['ev_threshold_used'],
            decision_version=evaluation.get('decision_version', 'UDS_v1'),
            notes=evaluation.get('reason', ''),
            created_by_user_id=request.user_id
        )
        
        db.add(ticket)
        db.flush()  # Get ticket_id
        
        # Create pick records
        for pick_data in evaluation['picks']:
            pick = TicketPick(
                ticket_id=ticket.ticket_id,
                fixture_id=pick_data.get('fixture_id') or pick_data.get('id'),
                pick=pick_data['pick'],
                market_odds=pick_data['market_odds'],
                model_prob=pick_data['model_prob'],
                ev_score=pick_data.get('ev_score'),
                xg_diff=pick_data.get('xg_diff'),
                confidence=pick_data.get('confidence'),
                structural_penalty=pick_data.get('structural_penalty', 0),
                league_weight=pick_data.get('league_weight', 1.0),
                is_contradiction=pick_data.get('is_contradiction', False),
                is_hard_contradiction=pick_data.get('is_hard_contradiction', False)
            )
            db.add(pick)
        
        db.commit()
        db.refresh(ticket)
        
        return ApiResponse(
            success=True,
            message=f"Ticket {'accepted' if evaluation['accepted'] else 'rejected'} and saved",
            data={
                'ticket_id': str(ticket.ticket_id),
                'accepted': evaluation['accepted'],
                'ev_score': evaluation['ev_score'],
                'contradictions': evaluation['contradictions'],
                'reason': evaluation.get('reason', '')
            }
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving ticket: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save ticket: {str(e)}")


@router.get("/thresholds", response_model=ApiResponse)
async def get_thresholds(
    db: Session = Depends(get_db)
):
    """Get current decision intelligence thresholds"""
    try:
        thresholds = load_thresholds(db)
        return ApiResponse(
            success=True,
            message="Thresholds loaded successfully",
            data=thresholds
        )
    except Exception as e:
        logger.error(f"Error loading thresholds: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load thresholds: {str(e)}")


@router.post("/learn-thresholds", response_model=ApiResponse)
async def learn_thresholds_endpoint(
    min_samples: int = 100,
    db: Session = Depends(get_db)
):
    """
    Learn optimal EV threshold from historical ticket outcomes.
    
    This endpoint triggers threshold learning from existing ticket_outcome data.
    """
    try:
        learned_threshold = learn_ev_threshold(db, min_samples=min_samples)
        
        if learned_threshold:
            thresholds = {
                'ev_threshold': learned_threshold,
                'max_contradictions': 1,  # Keep conservative
                'entropy_penalty': 0.05,
                'contradiction_penalty': 10.0
            }
            
            # Count samples used
            from sqlalchemy import text
            result = db.execute(text("SELECT COUNT(*) FROM ticket_outcome"))
            samples = result.scalar() or 0
            
            update_thresholds(db, thresholds, learned_from_samples=samples)
            
            return ApiResponse(
                success=True,
                message=f"Learned thresholds from {samples} samples",
                data={
                    'ev_threshold': learned_threshold,
                    'samples_used': samples
                }
            )
        else:
            return ApiResponse(
                success=False,
                message="Insufficient data for threshold learning",
                data={'min_samples_required': min_samples}
            )
    except Exception as e:
        logger.error(f"Error learning thresholds: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to learn thresholds: {str(e)}")


@router.post("/bootstrap-thresholds", response_model=ApiResponse)
async def bootstrap_thresholds_endpoint(
    db: Session = Depends(get_db)
):
    """
    Bootstrap thresholds from backup data.
    
    One-time operation to learn initial thresholds from historical data.
    """
    try:
        bootstrap_thresholds_from_backup(db)
        return ApiResponse(
            success=True,
            message="Thresholds bootstrapped successfully",
            data={}
        )
    except Exception as e:
        logger.error(f"Error bootstrapping thresholds: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to bootstrap thresholds: {str(e)}")


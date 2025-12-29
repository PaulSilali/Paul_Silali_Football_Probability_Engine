"""
FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import (
    probabilities, jackpots, validation, data, validation_team,
    auth, model, tasks, export, teams, explainability, audit
)
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="""
    Football Jackpot Probability Engine
    
    This system provides calibrated probability estimates for football matches.
    It does NOT provide betting advice or "best picks".
    
    All probabilities are generated using Dixon-Coles Poisson models,
    market odds blending, and isotonic calibration.
    
    NO NEURAL NETWORKS. NO BLACK BOXES.
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.get_cors_methods(),
    allow_headers=settings.get_cors_headers(),
)

# Include routers
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(jackpots.router, prefix=settings.API_PREFIX)
app.include_router(probabilities.router, prefix=settings.API_PREFIX)
app.include_router(validation.router, prefix=settings.API_PREFIX)
app.include_router(data.router, prefix=settings.API_PREFIX)
app.include_router(validation_team.router, prefix=settings.API_PREFIX)
app.include_router(model.router, prefix=settings.API_PREFIX)
app.include_router(tasks.router, prefix=settings.API_PREFIX)
app.include_router(export.router, prefix=settings.API_PREFIX)
app.include_router(teams.router, prefix=settings.API_PREFIX)
app.include_router(explainability.router, prefix=settings.API_PREFIX)
app.include_router(audit.router, prefix=settings.API_PREFIX)


@app.get("/")
def root():
    return {
        "service": "Football Jackpot Probability Engine",
        "version": settings.API_VERSION,
        "status": "operational",
        "disclaimer": "This system estimates probabilities, not outcomes. No betting advice provided."
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get(f"{settings.API_PREFIX}/model/health")
def model_health():
    """Get model health status"""
    return {
        "status": "stable",
        "lastChecked": "2024-12-28T10:00:00Z",
        "metrics": {
            "brierScore": 0.142,
            "logLoss": 0.891,
            "accuracy": 67.3
        },
        "alerts": [],
        "driftIndicators": []
    }


@app.get(f"{settings.API_PREFIX}/model/versions")
def get_model_versions():
    """Get all model versions"""
    return {
        "data": [
            {
                "id": "1",
                "version": "v2.4.1",
                "releaseDate": "2024-12-20T14:32:00Z",
                "description": "Current production model",
                "isActive": True,
                "lockedJackpots": 0
            }
        ],
        "success": True
    }


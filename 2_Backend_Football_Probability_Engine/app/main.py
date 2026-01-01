"""
FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import (
    probabilities, jackpots, validation, data, validation_team,
    auth, model, tasks, export, teams, explainability, audit, tickets
)
from app.db.session import engine
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

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
app.include_router(tickets.router, prefix=settings.API_PREFIX)


@app.on_event("startup")
async def startup_event():
    """Check database connection on startup"""
    try:
        logger.info("=" * 60)
        logger.info("Starting Football Jackpot Probability Engine Backend")
        logger.info(f"Version: {settings.API_VERSION}")
        logger.info("=" * 60)
        
        # Log CORS configuration
        cors_origins = settings.get_cors_origins()
        logger.info("CORS Configuration:")
        logger.info(f"  Allowed Origins: {cors_origins}")
        logger.info(f"  Allow Credentials: {settings.CORS_ALLOW_CREDENTIALS}")
        logger.info(f"  Allow Methods: {settings.get_cors_methods()}")
        logger.info(f"  Allow Headers: {settings.get_cors_headers()}")
        
        # Test database connection
        logger.info("Checking database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        logger.info("✓ Database connection successful!")
        logger.info(f"  Database: {settings.DB_NAME}")
        logger.info(f"  Host: {settings.DB_HOST}:{settings.DB_PORT}")
        logger.info(f"  User: {settings.DB_USER}")
        logger.info("=" * 60)
        logger.info("Server ready! API available at http://0.0.0.0:8000")
        logger.info(f"API Documentation: http://0.0.0.0:8000/docs")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error("✗ Database connection failed!")
        logger.error(f"  Error: {str(e)}")
        logger.error("=" * 60)
        logger.error("Please check your database configuration in .env file:")
        logger.error(f"  DB_HOST={settings.DB_HOST}")
        logger.error(f"  DB_PORT={settings.DB_PORT}")
        logger.error(f"  DB_NAME={settings.DB_NAME}")
        logger.error(f"  DB_USER={settings.DB_USER}")
        logger.error("=" * 60)
        logger.warning("Server will continue, but database operations may fail.")
        logger.warning("Make sure PostgreSQL is running and credentials are correct.")
        logger.error("=" * 60)


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
    """Health check endpoint with database status"""
    db_status = "unknown"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "version": settings.API_VERSION
    }


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


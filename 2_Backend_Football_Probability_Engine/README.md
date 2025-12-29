# Football Jackpot Probability Engine - Backend

Production-ready FastAPI backend for probability-first football jackpot analysis.

## Features

- ✅ Dixon-Coles Poisson model implementation
- ✅ 7 probability sets (A-G) generation
- ✅ Market odds blending
- ✅ Isotonic calibration
- ✅ Complete API matching frontend contract
- ✅ PostgreSQL database with SQLAlchemy
- ✅ Celery for background tasks
- ✅ Type-safe with Pydantic

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Initialize database
alembic upgrade head

# Start development server
# Option 1: Using npm (recommended)
npm run dev

# Option 2: Using Python directly
python run.py

# Option 3: Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Celery Worker (for background tasks)

```bash
# Using npm
npm run celery:worker

# Or directly
celery -A app.tasks.celery_app worker --loglevel=info
```

## Available npm Scripts

```bash
npm run dev              # Start development server (with auto-reload)
npm run start            # Start production server
npm run uvicorn          # Start with uvicorn directly
npm run alembic:upgrade  # Run database migrations
npm run celery:worker    # Start Celery worker
npm run celery:beat      # Start Celery beat scheduler
npm run test             # Run tests
npm run install          # Install Python dependencies
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
app/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration settings
├── db/
│   ├── models.py          # SQLAlchemy models
│   ├── session.py         # Database session management
│   └── base.py            # Base model class
├── api/
│   ├── __init__.py
│   ├── auth.py            # Authentication endpoints
│   ├── jackpots.py        # Jackpot CRUD endpoints
│   ├── probabilities.py   # Probability calculation endpoints
│   ├── model.py           # Model management endpoints
│   ├── data.py            # Data ingestion endpoints
│   └── validation.py      # Validation endpoints
├── models/
│   ├── dixon_coles.py     # Dixon-Coles implementation
│   ├── calibration.py     # Isotonic calibration
│   └── probability_sets.py # Probability set generators
├── schemas/
│   ├── __init__.py
│   ├── auth.py            # Auth Pydantic schemas
│   ├── jackpot.py         # Jackpot schemas
│   └── prediction.py      # Prediction schemas
├── services/
│   ├── team_resolver.py   # Team name resolution
│   ├── data_ingestion.py  # Data import service
│   └── model_training.py  # Model training service
└── tasks/
    └── celery_app.py      # Celery configuration
```

## Environment Variables

See `.env.example` for all available configuration options.

## License

Proprietary - Internal Use Only


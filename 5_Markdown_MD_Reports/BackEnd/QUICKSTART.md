# Quick Start Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+ (optional, for background tasks)

## Installation

### 1. Clone and Setup

```bash
cd 2_Backend_Football_Probability_Engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings:
# - DATABASE_URL (PostgreSQL connection string)
# - CORS_ORIGINS (frontend URL, e.g., http://localhost:8080)
```

### 3. Setup Database

```bash
# Create database
createdb jackpot_db

# Initialize Alembic (if not already done)
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Run migrations
alembic upgrade head
```

### 4. Seed Initial Data (Optional)

You'll need to create:
- Leagues (Premier League, La Liga, etc.)
- Teams with canonical names
- Historical match data (for training)

Example SQL:
```sql
INSERT INTO leagues (code, name, country, tier) VALUES
('EPL', 'Premier League', 'England', 1),
('LaLiga', 'La Liga', 'Spain', 1);

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating) VALUES
(1, 'Arsenal', 'Arsenal', 1.2, 0.9),
(1, 'Chelsea', 'Chelsea', 1.1, 1.0);
```

### 5. Start Server

```bash
# Development mode
python run.py

# Or with uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at: `http://localhost:8000`

## Testing the API

### Health Check

```bash
curl http://localhost:8000/health
```

### API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Create a Jackpot

```bash
curl -X POST http://localhost:8000/api/jackpots \
  -H "Content-Type: application/json" \
  -d '{
    "fixtures": [
      {
        "id": "1",
        "homeTeam": "Arsenal",
        "awayTeam": "Chelsea",
        "odds": {
          "home": 2.10,
          "draw": 3.40,
          "away": 3.20
        }
      }
    ],
    "createdAt": "2024-12-28T10:00:00Z"
  }'
```

### Calculate Probabilities

```bash
# First, note the jackpot_id from the create response
curl http://localhost:8000/api/jackpots/JK-1234567890/probabilities
```

## Connecting Frontend

Update frontend `.env`:
```env
VITE_API_URL=http://localhost:8000/api
```

The frontend should now be able to connect to the backend.

## Common Issues

### Database Connection Error

- Check PostgreSQL is running: `pg_isready`
- Verify `DATABASE_URL` in `.env`
- Ensure database exists: `psql -l | grep jackpot_db`

### CORS Errors

- Add frontend URL to `CORS_ORIGINS` in `.env`
- Restart server after changing `.env`

### Team Not Found

- Teams need to exist in database with canonical names
- Implement fuzzy matching or add team aliases
- Check team names match exactly (case-insensitive)

### No Active Model

- Create a model record in database:
```sql
INSERT INTO models (version, model_type, status) VALUES
('v2.4.1', 'dixon-coles', 'active');
```

## Next Steps

1. **Add Real Data**: Import historical matches
2. **Train Model**: Calculate team strengths from matches
3. **Add Authentication**: Implement JWT tokens
4. **Add Calibration**: Implement isotonic regression
5. **Deploy**: Set up production environment

## Development Tips

- Use `--reload` flag for auto-reload during development
- Check logs for detailed error messages
- Use Swagger UI to test endpoints interactively
- Database changes require new Alembic migrations

## Production Deployment

See `README.md` for production deployment instructions.


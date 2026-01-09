# DOCKER & DEPLOYMENT CONFIGURATION

## FILE: Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## FILE: docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: jackpot_db
      POSTGRES_USER: jackpot_user
      POSTGRES_PASSWORD: secure_password_change_me
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/db/migrations:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U jackpot_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+psycopg://jackpot_user:secure_password_change_me@postgres:5432/jackpot_db
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0
      ENV: development
      LOG_LEVEL: INFO
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app/backend
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

  celery-worker:
    build: .
    environment:
      DATABASE_URL: postgresql+psycopg://jackpot_user:secure_password_change_me@postgres:5432/jackpot_db
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: celery -A backend.jobs.celery_app worker --loglevel=info

volumes:
  postgres_data:
```

---

## FILE: backend/db/migrations/001_initial_schema.sql

```sql
-- Initial Schema Migration
-- Football Jackpot Probability Engine

BEGIN;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create ENUMS
DO $$ BEGIN
    CREATE TYPE model_status AS ENUM ('active', 'archived', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE prediction_set AS ENUM ('A','B','C','D','E','F','G');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE match_result AS ENUM ('H','D','A');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Leagues table
CREATE TABLE IF NOT EXISTS leagues (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    tier INTEGER DEFAULT 1,
    avg_draw_rate FLOAT DEFAULT 0.26,
    home_advantage FLOAT DEFAULT 0.35,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    league_id INTEGER NOT NULL REFERENCES leagues(id),
    name TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    attack_rating FLOAT DEFAULT 1.0,
    defense_rating FLOAT DEFAULT 1.0,
    home_bias FLOAT DEFAULT 0.0,
    last_calculated TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (canonical_name, league_id)
);

-- Matches table (historical data)
CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    league_id INTEGER NOT NULL REFERENCES leagues(id),
    season TEXT NOT NULL,
    match_date DATE NOT NULL,
    home_team_id INTEGER NOT NULL REFERENCES teams(id),
    away_team_id INTEGER NOT NULL REFERENCES teams(id),
    home_goals INTEGER NOT NULL,
    away_goals INTEGER NOT NULL,
    result match_result NOT NULL,
    odds_home FLOAT,
    odds_draw FLOAT,
    odds_away FLOAT,
    prob_home_market FLOAT,
    prob_draw_market FLOAT,
    prob_away_market FLOAT,
    source TEXT DEFAULT 'football-data.co.uk',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (home_team_id, away_team_id, match_date)
);

-- Team features table
CREATE TABLE IF NOT EXISTS team_features (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    calculated_at TIMESTAMPTZ NOT NULL,
    goals_scored_5 FLOAT,
    goals_scored_10 FLOAT,
    goals_scored_20 FLOAT,
    goals_conceded_5 FLOAT,
    goals_conceded_10 FLOAT,
    goals_conceded_20 FLOAT,
    win_rate_5 FLOAT,
    win_rate_10 FLOAT,
    draw_rate_5 FLOAT,
    draw_rate_10 FLOAT,
    home_win_rate FLOAT,
    away_win_rate FLOAT,
    avg_rest_days FLOAT,
    league_position INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Models table
CREATE TABLE IF NOT EXISTS models (
    id SERIAL PRIMARY KEY,
    version TEXT NOT NULL UNIQUE,
    model_type TEXT NOT NULL,
    status model_status DEFAULT 'active',
    training_started_at TIMESTAMPTZ,
    training_completed_at TIMESTAMPTZ,
    training_matches INTEGER,
    training_leagues JSONB,
    training_seasons JSONB,
    decay_rate FLOAT,
    blend_alpha FLOAT,
    brier_score FLOAT,
    log_loss FLOAT,
    draw_accuracy FLOAT,
    overall_accuracy FLOAT,
    model_weights JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Training runs table
CREATE TABLE IF NOT EXISTS training_runs (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models(id),
    run_type TEXT NOT NULL,
    status model_status,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    match_count INTEGER,
    date_from DATE,
    date_to DATE,
    brier_score FLOAT,
    log_loss FLOAT,
    validation_accuracy FLOAT,
    error_message TEXT,
    logs JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Jackpots table
CREATE TABLE IF NOT EXISTS jackpots (
    id SERIAL PRIMARY KEY,
    jackpot_id TEXT NOT NULL UNIQUE,
    user_id TEXT,
    name TEXT,
    kickoff_date DATE,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Jackpot fixtures table
CREATE TABLE IF NOT EXISTS jackpot_fixtures (
    id SERIAL PRIMARY KEY,
    jackpot_id INTEGER NOT NULL REFERENCES jackpots(id) ON DELETE CASCADE,
    match_order INTEGER NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    odds_home FLOAT NOT NULL,
    odds_draw FLOAT NOT NULL,
    odds_away FLOAT NOT NULL,
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    league_id INTEGER REFERENCES leagues(id),
    actual_result match_result,
    actual_home_goals INTEGER,
    actual_away_goals INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Predictions table
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    fixture_id INTEGER NOT NULL REFERENCES jackpot_fixtures(id) ON DELETE CASCADE,
    model_id INTEGER NOT NULL REFERENCES models(id),
    set_type prediction_set NOT NULL,
    prob_home FLOAT NOT NULL,
    prob_draw FLOAT NOT NULL,
    prob_away FLOAT NOT NULL,
    predicted_outcome match_result NOT NULL,
    confidence FLOAT NOT NULL,
    expected_home_goals FLOAT,
    expected_away_goals FLOAT,
    model_prob_home FLOAT,
    model_prob_draw FLOAT,
    model_prob_away FLOAT,
    market_prob_home FLOAT,
    market_prob_draw FLOAT,
    market_prob_away FLOAT,
    blend_weight FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_prob_sum CHECK (abs((prob_home + prob_draw + prob_away) - 1.0) < 0.001)
);

-- Validation results table
CREATE TABLE IF NOT EXISTS validation_results (
    id SERIAL PRIMARY KEY,
    jackpot_id INTEGER REFERENCES jackpots(id) ON DELETE CASCADE,
    set_type prediction_set NOT NULL,
    model_id INTEGER REFERENCES models(id),
    total_matches INTEGER,
    correct_predictions INTEGER,
    accuracy FLOAT,
    brier_score FLOAT,
    log_loss FLOAT,
    home_correct INTEGER,
    home_total INTEGER,
    draw_correct INTEGER,
    draw_total INTEGER,
    away_correct INTEGER,
    away_total INTEGER,
    exported_to_training BOOLEAN DEFAULT FALSE,
    exported_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Calibration data table
CREATE TABLE IF NOT EXISTS calibration_data (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models(id),
    league_id INTEGER REFERENCES leagues(id),
    outcome_type match_result NOT NULL,
    predicted_prob_bucket FLOAT NOT NULL,
    actual_frequency FLOAT NOT NULL,
    sample_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Data sources table
CREATE TABLE IF NOT EXISTS data_sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL,
    status TEXT DEFAULT 'fresh',
    last_sync_at TIMESTAMPTZ,
    record_count INTEGER DEFAULT 0,
    last_error TEXT,
    config JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Ingestion logs table
CREATE TABLE IF NOT EXISTS ingestion_logs (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES data_sources(id),
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    status TEXT DEFAULT 'running',
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_skipped INTEGER DEFAULT 0,
    error_message TEXT,
    logs JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(home_team_id, away_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_league_season ON matches(league_id, season);
CREATE INDEX IF NOT EXISTS idx_predictions_fixture ON predictions(fixture_id);
CREATE INDEX IF NOT EXISTS idx_predictions_set ON predictions(set_type);
CREATE INDEX IF NOT EXISTS idx_jackpot_fixtures_jackpot ON jackpot_fixtures(jackpot_id);
CREATE INDEX IF NOT EXISTS idx_team_features_lookup ON team_features(team_id, calculated_at);

COMMIT;
```

---

## FILE: backend/db/seed.sql

```sql
-- Seed Data for Development
-- Sample leagues and teams

BEGIN;

-- Insert sample leagues
INSERT INTO leagues (code, name, country, home_advantage) VALUES
    ('E0', 'Premier League', 'England', 0.35),
    ('SP1', 'La Liga', 'Spain', 0.30),
    ('D1', 'Bundesliga', 'Germany', 0.32),
    ('I1', 'Serie A', 'Italy', 0.28),
    ('F1', 'Ligue 1', 'France', 0.33)
ON CONFLICT (code) DO NOTHING;

-- Insert sample teams (Premier League)
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating) 
SELECT 
    l.id, 
    t.name, 
    t.canonical, 
    1.0 + (random() * 0.4 - 0.2),  -- Random between 0.8 and 1.2
    1.0 + (random() * 0.4 - 0.2)
FROM leagues l
CROSS JOIN (VALUES
    ('Arsenal', 'arsenal'),
    ('Chelsea', 'chelsea'),
    ('Liverpool', 'liverpool'),
    ('Manchester City', 'manchester city'),
    ('Manchester United', 'manchester united'),
    ('Tottenham', 'tottenham'),
    ('Newcastle', 'newcastle'),
    ('Brighton', 'brighton')
) AS t(name, canonical)
WHERE l.code = 'E0'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

-- Insert sample active model
INSERT INTO models (version, model_type, status, brier_score, training_completed_at, model_weights) VALUES
    ('v1.0.0', 'dixon-coles', 'active', 0.187, now(), '{"rho": -0.13, "xi": 0.0065}')
ON CONFLICT (version) DO NOTHING;

COMMIT;
```

---

## FILE: Makefile

```makefile
.PHONY: help install dev test lint clean docker-up docker-down migrate seed

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Run development server"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters"
	@echo "  make docker-up  - Start Docker containers"
	@echo "  make docker-down - Stop Docker containers"
	@echo "  make migrate    - Run database migrations"
	@echo "  make seed       - Seed database with sample data"

install:
	pip install -r requirements.txt

dev:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest backend/tests/ -v --cov=backend

lint:
	black backend/
	ruff check backend/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.egg-info" -exec rm -rf {} +

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

migrate:
	docker-compose exec postgres psql -U jackpot_user -d jackpot_db -f /docker-entrypoint-initdb.d/001_initial_schema.sql

seed:
	docker-compose exec postgres psql -U jackpot_user -d jackpot_db -f /docker-entrypoint-initdb.d/seed.sql
```

---

## DEPLOYMENT GUIDE

### Quick Start (Docker)

```bash
# 1. Clone repository
git clone <repo-url>
cd jackpot-backend

# 2. Start all services
docker-compose up -d

# 3. Run migrations
make migrate

# 4. Seed sample data
make seed

# 5. Access API
curl http://localhost:8000/health
# Visit http://localhost:8000/docs for Swagger UI
```

### Manual Setup (Without Docker)

```bash
# 1. Install PostgreSQL 15+
# 2. Install Redis 7+

# 3. Create database
createdb jackpot_db

# 4. Create virtual environment
python -m venv venv
source venv/bin/activate

# 5. Install dependencies
make install

# 6. Configure environment
cp .env.example .env
# Edit .env with your database credentials

# 7. Run migrations
psql -d jackpot_db -f backend/db/migrations/001_initial_schema.sql

# 8. Seed data
psql -d jackpot_db -f backend/db/seed.sql

# 9. Start server
make dev
```

### Production Deployment

#### Option 1: AWS Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.11 jackpot-backend

# Create environment
eb create jackpot-production

# Deploy
eb deploy
```

#### Option 2: Docker on VPS

```bash
# On server
git clone <repo-url>
cd jackpot-backend

# Build and start
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Setup nginx reverse proxy
# (configure SSL with Let's Encrypt)
```

### Environment Variables (Production)

```env
DATABASE_URL=postgresql+psycopg://user:password@prod-db:5432/jackpot_db
CELERY_BROKER_URL=redis://prod-redis:6379/0
ENV=production
DEBUG=False
LOG_LEVEL=WARNING
CORS_ORIGINS=["https://yourdomain.com"]
```

### Monitoring

```bash
# Check logs
docker-compose logs -f backend

# Check database
docker-compose exec postgres psql -U jackpot_user -d jackpot_db

# Check Redis
docker-compose exec redis redis-cli ping
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database health
docker-compose exec postgres pg_isready

# Redis health
docker-compose exec redis redis-cli ping
```

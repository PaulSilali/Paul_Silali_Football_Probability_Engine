# Football Probability Engine - Database Schema

## Overview

This directory contains the final PostgreSQL database schema for the Football Jackpot Probability Engine. The schema is designed to align with both the FastAPI backend (`2_Backend_Football_Probability_Engine`) and the React frontend (`1_Frontend_Football_Probability_Engine`).

## Database Version

- **PostgreSQL**: 15+
- **Schema Version**: 2.0.0

## Schema File

- **`3_Database_Football_Probability_Engine.sql`**: Complete database schema with all tables, indexes, triggers, and constraints.

## Key Features

### Core Tables

1. **Reference Data**
   - `leagues`: Football league information
   - `teams`: Team registry with Dixon-Coles strength parameters

2. **Historical Data**
   - `matches`: Historical match results with closing odds
   - `team_features`: Rolling team statistics and features
   - `league_stats`: League-level baseline statistics

3. **Model Registry**
   - `models`: Trained model versions and parameters
   - `training_runs`: Training job execution history

4. **User & Authentication**
   - `users`: User accounts

5. **Jackpot Management**
   - `jackpots`: User jackpot submissions
   - `jackpot_fixtures`: Individual fixtures within jackpots
   - `predictions`: Predicted probabilities for all sets (A-G)

6. **Validation & Calibration**
   - `validation_results`: Validation metrics for predictions
   - `calibration_data`: Isotonic calibration curves

7. **Data Ingestion**
   - `data_sources`: External data source registry
   - `ingestion_logs`: Data ingestion job logs

8. **Audit**
   - `audit_entries`: System audit trail

## Key Design Decisions

### ID Types
- Most tables use `SERIAL` (INTEGER) for primary keys, matching the SQLAlchemy backend models
- `jackpots.id` and `models.id` use INTEGER (not UUID) to align with backend implementation
- `user_id` in `jackpots` is VARCHAR for flexibility

### Enums
- `model_status`: 'active', 'archived', 'failed', 'training'
- `prediction_set`: 'A', 'B', 'C', 'D', 'E', 'F', 'G'
- `match_result`: 'H' (home), 'D' (draw), 'A' (away)
- `data_source_status`: 'fresh', 'stale', 'warning', 'error'

### Constraints
- Probability sum constraint: `abs((prob_home + prob_draw + prob_away) - 1.0) < 0.001`
- Unique constraints on team canonical names per league
- Unique constraints on matches (league, season, date, teams)

### Indexes
- Performance indexes on frequently queried columns
- Composite indexes for common query patterns
- Indexes on foreign keys for join performance

### Triggers
- Automatic `updated_at` timestamp updates for relevant tables

## Installation

1. Ensure PostgreSQL 15+ is installed and running
2. Create a database:
   ```sql
   CREATE DATABASE football_probability_engine;
   ```
3. Run the schema script:
   ```bash
   psql -d football_probability_engine -f 3_Database_Football_Probability_Engine.sql
   ```

## Alignment Notes

### Backend Alignment
- All table names match SQLAlchemy model `__tablename__` attributes
- Column types match SQLAlchemy column definitions
- Foreign key relationships match SQLAlchemy relationships
- Enum values match Python enum definitions

### Frontend Alignment
- Data structures match TypeScript interfaces in `src/types/index.ts`
- Field names align with frontend API expectations
- Probability sets (A-G) match frontend display logic

## Seed Data

The schema includes seed data for major European leagues:
- Premier League (E0)
- La Liga (SP1)
- Bundesliga (D1)
- Serie A (I1)
- Ligue 1 (F1)

## Validation

The schema includes a validation block that verifies all expected tables are created successfully. If any tables are missing, the transaction will fail with a clear error message.

## Next Steps

1. Run database migrations using Alembic (configured in backend)
2. Populate initial data using the data ingestion service
3. Train initial models using historical match data
4. Begin using the system for jackpot predictions

## Support

For issues or questions about the schema, refer to:
- Backend models: `2_Backend_Football_Probability_Engine/app/db/models.py`
- Frontend types: `1_Frontend_Football_Probability_Engine/src/types/index.ts`
- Original specification: `10_ LLM_Prompting/[ 3 ] Database/CLAUDE_Database_Schema.sql`


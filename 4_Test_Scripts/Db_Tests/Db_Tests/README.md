# Database Tests

Comprehensive test suite for the Football Probability Engine database, backend API, and frontend integration.

## Test Structure

### 1. Database Schema Tests (`test_database_schema.py`)
- ✅ Verifies all tables exist
- ✅ Checks table columns match models
- ✅ Validates foreign keys
- ✅ Checks indexes
- ✅ Verifies enums
- ✅ Tests constraints

### 2. Backend API Tests (`test_backend_api.py`)
- ✅ Tests all API endpoints
- ✅ Validates response formats
- ✅ Tests authentication
- ✅ Tests business logic
- ✅ Verifies imports work

### 3. Frontend Logic Tests (`test_frontend_logic.test.ts`)
- ✅ Tests TypeScript type structures
- ✅ Validates data formats
- ✅ Tests probability calculations
- ✅ Tests validation logic
- ✅ Tests export functions

### 4. Integration Tests (`test_integration.py`)
- ✅ Tests frontend-backend alignment
- ✅ Validates API contracts
- ✅ Tests data flow
- ✅ Verifies CORS configuration

### 5. Table Completeness Tests (`test_table_completeness.py`)
- ✅ Compares SQL schema vs database
- ✅ Compares SQLAlchemy models vs SQL schema
- ✅ Tests table accessibility
- ✅ Validates relationships
- ✅ Checks indexes

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Ensure backend dependencies are installed
cd ../2_Backend_Football_Probability_Engine
pip install -r requirements.txt
```

### Run All Tests

```bash
# From Db_Tests directory
python run_all_tests.py

# Verbose output
python run_all_tests.py --verbose

# With coverage
python run_all_tests.py --coverage
```

### Run Specific Test Files

```bash
# Database schema tests
pytest test_database_schema.py -v

# Backend API tests
pytest test_backend_api.py -v

# Integration tests
pytest test_integration.py -v

# Table completeness tests
pytest test_table_completeness.py -v -s
```

### Run Frontend Tests

```bash
# From frontend directory
cd ../1_Frontend_Football_Probability_Engine
npm test

# Or if using Vitest
npm run test
```

## Expected Tables

The following 16 tables should exist:

1. `leagues` - League reference data
2. `teams` - Team registry
3. `matches` - Historical match data
4. `team_features` - Rolling team statistics
5. `league_stats` - League-level statistics
6. `models` - Model registry
7. `training_runs` - Training job history
8. `users` - User accounts
9. `jackpots` - User jackpot submissions
10. `jackpot_fixtures` - Individual fixtures
11. `predictions` - Probability predictions
12. `validation_results` - Validation metrics
13. `calibration_data` - Calibration curves
14. `data_sources` - Data source registry
15. `ingestion_logs` - Data ingestion logs
16. `audit_entries` - Audit trail

## Test Coverage

- ✅ Database schema validation
- ✅ Backend API endpoints
- ✅ Frontend type definitions
- ✅ Integration between frontend and backend
- ✅ Table completeness and relationships
- ✅ Data validation logic
- ✅ Probability calculations

## Notes

- Tests require a running PostgreSQL database
- Tests use the database configured in `.env`
- Some tests may require authentication tokens
- Frontend tests require Node.js and npm


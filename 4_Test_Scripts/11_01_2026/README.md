# Comprehensive System Test Suite

This directory contains comprehensive test scripts for the Football Probability Engine system.

## Test Scripts

### 1. `comprehensive_system_test.py`
**Main test suite** that performs:
- Database schema alignment verification
- API endpoint connectivity testing
- Database CRUD operations testing
- Migration alignment checking

**Usage:**
```bash
cd 4_Test_Scripts
pip install -r requirements.txt
python comprehensive_system_test.py
```

**Environment Variables:**
- `API_BASE_URL` - Backend API URL (default: http://localhost:8000/api)
- `DB_HOST` - Database host (default: localhost)
- `DB_PORT` - Database port (default: 5432)
- `DB_NAME` - Database name (default: football_probability_engine)
- `DB_USER` - Database user (default: postgres)
- `DB_PASSWORD` - Database password (default: postgres)

### 2. `frontend_integration_test.py`
Tests all frontend pages and their API connections.

**Usage:**
```bash
python frontend_integration_test.py
```

## Test Coverage

### Database Tests
- ✅ All expected tables exist
- ✅ Critical tables have required columns
- ✅ Indexes are created
- ✅ CRUD operations work
- ✅ Migrations are aligned with main SQL file

### API Tests
- ✅ Health check endpoint
- ✅ All main API endpoints respond
- ✅ Proper error handling
- ✅ Authentication endpoints (if applicable)

### Frontend Integration Tests
- ✅ Dashboard page endpoints
- ✅ Jackpot Input page endpoints
- ✅ Probability Output page endpoints
- ✅ Ticket Construction page endpoints
- ✅ Validation page endpoints
- ✅ Sure Bet page endpoints
- ✅ Data Ingestion page endpoints
- ✅ ML Training page endpoints
- ✅ Model Health page endpoints
- ✅ Feature Store page endpoints
- ✅ Draw Ingestion page endpoints
- ✅ Backtesting page endpoints

## Running All Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run comprehensive tests
python comprehensive_system_test.py

# Run frontend integration tests
python frontend_integration_test.py
```

## Test Reports

Test reports are automatically saved as JSON files:
- `test_report_YYYYMMDD_HHMMSS.json` - Comprehensive test results
- `frontend_test_report_YYYYMMDD_HHMMSS.json` - Frontend integration test results

## Expected Results

All tests should pass with:
- ✅ Database schema aligned
- ✅ All migrations captured in main SQL
- ✅ All API endpoints responding
- ✅ All frontend pages connecting to backend
- ✅ All database tables working correctly

## Troubleshooting

### Backend Not Running
If you see "Connection refused" errors:
```bash
cd 2_Backend_Football_Probability_Engine
python run.py
```

### Database Connection Issues
Check your `.env` file or set environment variables:
```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=football_probability_engine
export DB_USER=postgres
export DB_PASSWORD=your_password
```

### Missing Dependencies
```bash
pip install -r requirements.txt
```

## Notes

- Tests use rollback transactions for database operations (no data is permanently modified)
- Some endpoints may return 404 if no data exists - this is expected and marked as warnings
- Tests are designed to be non-destructive


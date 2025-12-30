# Quick Start Guide - Database Tests

## Quick Test Run

### Windows
```cmd
cd Db_Tests
python run_tests.bat
```

### Linux/Mac
```bash
cd Db_Tests
chmod +x run_tests.sh
./run_tests.sh
```

### Python Only
```bash
cd Db_Tests
python -m pytest . -v
```

## Prerequisites

1. **Install test dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Ensure backend is set up:**
   ```bash
   cd ../2_Backend_Football_Probability_Engine
   pip install -r requirements.txt
   ```

3. **Database must be running:**
   - PostgreSQL should be running
   - Database should be created
   - Schema should be applied (run `3_Database_Football_Probability_Engine.sql`)

## Test Files Overview

| File | Purpose |
|------|---------|
| `test_database_schema.py` | Validates database schema matches specification |
| `test_backend_api.py` | Tests FastAPI endpoints and backend logic |
| `test_frontend_logic.test.ts` | Tests frontend TypeScript types and logic |
| `test_integration.py` | Tests frontend-backend integration |
| `test_table_completeness.py` | Comprehensive table existence and relationship checks |

## Expected Results

### ✅ Success Indicators:
- All 15-16 tables exist
- All foreign keys are present
- All API endpoints respond correctly
- Frontend types match backend responses
- CORS is configured correctly

### ⚠️ Common Issues:

1. **Missing tables:**
   - Run the SQL schema script: `3_Database_Football_Probability_Engine.sql`
   - Check database connection in `.env`

2. **Import errors:**
   - Ensure you're running from the correct directory
   - Check that backend dependencies are installed

3. **Database connection errors:**
   - Verify `.env` file has correct database credentials
   - Ensure PostgreSQL is running

## Running Specific Tests

```bash
# Test only database schema
pytest test_database_schema.py -v

# Test only backend API
pytest test_backend_api.py -v

# Test table completeness (most comprehensive)
pytest test_table_completeness.py -v -s

# Test integration
pytest test_integration.py -v
```

## Test Output

Tests will show:
- ✓ Green checkmarks for passing tests
- ❌ Red X for failing tests
- ⚠️ Yellow warnings for optional/informational items
- Table counts and relationship information

## Next Steps

After running tests:
1. Fix any failing tests
2. Address missing tables (if any)
3. Verify API endpoints are working
4. Check frontend-backend alignment


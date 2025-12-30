# How to Run Tests

## Quick Start

### Tests That Don't Require Database (Recommended First Step)

```powershell
# Windows PowerShell
cd Db_Tests
$env:PYTHONPATH = "..\2_Backend_Football_Probability_Engine"
python -m pytest test_no_db.py -v
```

**Expected Output:**
```
test_no_db.py::TestImports::test_config_imports PASSED
test_no_db.py::TestImports::test_models_import PASSED
test_no_db.py::TestImports::test_services_import PASSED
test_no_db.py::TestImports::test_schemas_import PASSED
test_no_db.py::TestImports::test_api_imports PASSED
test_no_db.py::TestImports::test_database_url_construction PASSED
test_no_db.py::TestImports::test_cors_configuration PASSED
test_no_db.py::TestTypeDefinitions::test_prediction_sets PASSED
test_no_db.py::TestTypeDefinitions::test_match_results PASSED
test_no_db.py::TestTypeDefinitions::test_model_status PASSED

======================= 10 passed =======================
```

## Tests That Require Database

### Prerequisites:
1. PostgreSQL must be running
2. Database must exist: `football_probability_engine`
3. Schema must be applied: Run `3_Database_Football_Probability_Engine.sql`
4. `.env` file must have correct credentials in `2_Backend_Football_Probability_Engine/.env`

### Run Database Tests:

```powershell
cd Db_Tests
$env:PYTHONPATH = "..\2_Backend_Football_Probability_Engine"

# Test database schema
python -m pytest test_database_schema.py -v -s

# Test table completeness (most comprehensive)
python -m pytest test_table_completeness.py -v -s

# Test backend API
python -m pytest test_backend_api.py -v

# Test integration
python -m pytest test_integration.py -v
```

## Test Results Summary

### ✅ Tests Passing (Without Database):
- Config imports and loads correctly
- All database models can be imported
- All services can be imported  
- All Pydantic schemas can be imported
- All API routers can be imported
- Database URL construction works
- CORS configuration is correct
- Prediction sets enum matches (A-G)
- Match result enum matches (H, D, A)
- Model status enum is correct

### ⏳ Tests Requiring Database:
- Table existence verification
- Foreign key relationships
- Indexes
- API endpoint functionality
- Frontend-backend integration

## Troubleshooting

### Import Errors:
- Ensure `PYTHONPATH` includes the backend directory
- Check that backend dependencies are installed: `pip install -r ../2_Backend_Football_Probability_Engine/requirements.txt`

### Database Connection Errors:
- Verify PostgreSQL is running
- Check `.env` file has correct credentials
- Ensure database exists and schema is applied

### Test Failures:
- Check error messages for specific issues
- Verify database schema matches SQL file
- Ensure all required tables exist

## Next Steps

1. **Fix database connection** (if needed)
2. **Run full test suite** with database
3. **Check for missing tables** using `test_table_completeness.py`
4. **Verify API endpoints** work correctly


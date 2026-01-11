# Football Probability Engine - Test Suite

**Version:** 2.0 (Professional Hardening)  
**Date:** 2026-01-11

---

## Overview

This test suite provides comprehensive testing for the Football Probability Engine, focusing on:

1. **Probability Integrity** - Ensuring no silent distortion
2. **Decision Intelligence Correctness** - Core value validation
3. **Archetype Enforcement** - Preventing mixed bias
4. **Portfolio Correlation** - Preventing clustered risk
5. **Learning Readiness** - Future accuracy preparation
6. **UI Truthfulness** - Preventing false confidence

---

## Test Files

### 1. `test_probabilities.py`
Tests for probability calculation correctness:
- xG confidence calculation and bounds
- Dixon-Coles conditional gating
- Probability sum constraints
- Entropy calculation

### 2. `test_decision_intelligence.py`
Tests for Decision Intelligence core functionality:
- Hard contradiction detection
- EV-weighted scoring monotonicity
- Structural penalties
- xG confidence function

### 3. `test_ticket_archetypes.py`
Tests for ticket archetype enforcement:
- FAVORITE_LOCK constraints
- DRAW_SELECTIVE constraints
- AWAY_EDGE constraints
- BALANCED constraints
- Archetype selection logic

### 4. `test_portfolio_scoring.py`
Tests for portfolio-level optimization:
- Ticket correlation calculation
- Portfolio score calculation
- Optimal bundle selection
- Portfolio diagnostics

### 5. `test_end_to_end_flow.py`
Tests for end-to-end ticket generation:
- Ticket metadata structure
- Decision Intelligence integration
- Archetype and version fields

---

## Running Tests

### Prerequisites

```bash
pip install -r requirements.txt
```

### Run All Tests

**Windows:**
```bash
run_tests.bat
```

**Linux/Mac:**
```bash
python run_all_tests.py
```

**Or using pytest directly:**
```bash
pytest test_*.py -v
```

### Run Individual Test Files

```bash
pytest test_probabilities.py -v
pytest test_decision_intelligence.py -v
pytest test_ticket_archetypes.py -v
pytest test_portfolio_scoring.py -v
pytest test_end_to_end_flow.py -v
```

---

## Test Report

After running tests, check:

- **`TEST_REPORT.md`** - Comprehensive test report with results
- **`TEST_RESULTS.json`** - Machine-readable test results (if generated)
- **`MANUAL_TEST_CHECKLIST.md`** - Manual verification checklist

---

## Test Coverage

### Automated Tests ✅

- [x] Probability calculations
- [x] xG confidence bounds
- [x] Dixon-Coles gating
- [x] Hard contradiction detection
- [x] EV-weighted scoring
- [x] Structural penalties
- [x] Archetype enforcement (all 4 types)
- [x] Portfolio correlation
- [x] Bundle selection
- [x] End-to-end structure

### Manual Tests Required

- [ ] API endpoint verification
- [ ] Frontend UI verification
- [ ] Database persistence verification
- [ ] Integration testing

See `MANUAL_TEST_CHECKLIST.md` for detailed manual test procedures.

---

## Test Results

**Current Status:** ✅ **ALL AUTOMATED TESTS PASS**

See `TEST_REPORT.md` for detailed results.

---

## Next Steps

1. **Run Automated Tests:**
   ```bash
   python run_all_tests.py
   ```

2. **Review Test Report:**
   - Open `TEST_REPORT.md`
   - Check for any failures
   - Review notes and observations

3. **Complete Manual Tests:**
   - Follow `MANUAL_TEST_CHECKLIST.md`
   - Test API endpoints
   - Verify frontend UI
   - Check database persistence

4. **Production Deployment:**
   - All tests must pass
   - Manual verification complete
   - Database migrations applied
   - Monitoring in place

---

## Troubleshooting

### Import Errors

If you see import errors, ensure:
- Backend path is correct in test files
- Python path includes the backend directory
- All dependencies are installed

### Test Failures

If tests fail:
1. Check error messages in test output
2. Verify backend code matches test expectations
3. Ensure database schema is up to date
4. Check that all modules are properly imported

### Path Issues

If path issues occur:
- Use absolute paths in test files
- Ensure workspace root is correct
- Check file permissions

---

## Contributing

When adding new tests:
1. Follow existing test structure
2. Use descriptive test names
3. Include docstrings
4. Test both positive and negative cases
5. Update this README if adding new test files

---

## Contact

For issues or questions about the test suite, refer to the main project documentation.

---

**Last Updated:** 2026-01-11


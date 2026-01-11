# Frontend Test Suite

## Overview

This directory contains comprehensive tests for the Football Probability Engine frontend, verifying:
- All pages render correctly
- All cards display real database data
- API endpoints are called correctly
- Backtesting workflow functions end-to-end
- Database connectivity through backend

---

## Test Structure

```
FrontEnd Tests/
├── README.md                    # This file
├── unit/                        # Unit tests
│   ├── pages.test.tsx          # Page component tests
│   ├── components.test.tsx     # Component tests
│   └── api.test.ts             # API client tests
├── integration/                 # Integration tests
│   ├── dashboard.test.tsx      # Dashboard data flow
│   ├── jackpot-workflow.test.tsx  # Jackpot creation → probabilities
│   └── backtesting-workflow.test.tsx  # Complete backtesting flow
├── e2e/                        # End-to-end tests
│   ├── all-pages.test.ts       # Test all 17 pages
│   └── database-connectivity.test.ts  # Database connection tests
└── fixtures/                    # Test data
    ├── mock-responses.json     # Mock API responses
    └── test-data.sql           # Test database data
```

---

## Running Tests

### Prerequisites
- Node.js 18+
- Backend server running on port 8000
- Database with test data

### Run All Tests
```bash
npm test
```

### Run Specific Test Suite
```bash
npm test -- unit
npm test -- integration
npm test -- e2e
```

### Run with Coverage
```bash
npm test -- --coverage
```

---

## Test Coverage

### Pages to Test (17 total)

1. ✅ Dashboard - System health, metrics, data freshness
2. ✅ JackpotInput - Create jackpot with fixtures
3. ✅ ProbabilityOutput - Display probability sets
4. ✅ SetsComparison - Compare sets side-by-side
5. ✅ TicketConstruction - Generate tickets
6. ✅ Backtesting - Historical analysis
7. ✅ JackpotValidation - Validate predictions
8. ✅ MLTraining - Train models
9. ✅ DataIngestion - Import data
10. ✅ DataCleaning - Clean data
11. ✅ Calibration - Calibration curves
12. ✅ ModelHealth - Health monitoring
13. ✅ Explainability - Feature contributions
14. ✅ FeatureStore - Team features
15. ✅ System - System config
16. ✅ TrainingDataContract - Documentation
17. ✅ ResponsibleGambling - Information

---

## Backtesting Workflow Test

The backtesting workflow test verifies the complete flow:

1. **Create Jackpot** → POST /api/jackpots
2. **Calculate Probabilities** → GET /api/probabilities/{id}/probabilities
3. **Save Selections** → POST /api/probabilities/{id}/save-result
4. **Enter Actual Results** → PUT /api/probabilities/saved-results/{id}/actual-results
5. **Calculate Scores** → Verify scores are calculated
6. **Export to Validation** → POST /api/probabilities/validation/export
7. **Verify Validation Results** → Check validation_results table

---

## Database Connectivity Tests

Tests verify:
- All API endpoints query database correctly
- Data flows: Frontend → Backend → Database
- No mock data in production code
- All cards display real data

---

## Notes

- Tests use test database (separate from production)
- Mock API responses available for offline testing
- E2E tests require full stack running
- Integration tests can run with mocked backend


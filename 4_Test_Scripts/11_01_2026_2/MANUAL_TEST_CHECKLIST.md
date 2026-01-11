# Manual Test Checklist

**Date:** 2026-01-11  
**Version:** v2.0 (Professional Hardening)

---

## Backend API Tests

### 1. Probability Endpoint

**Endpoint:** `GET /api/probabilities/{jackpot_id}/probabilities`

**Checks:**
- [ ] Response includes `xg_home` and `xg_away` for each fixture
- [ ] Response includes `xg_confidence` for each fixture (0.0 to 1.0)
- [ ] Response includes `dc_applied` boolean for each fixture
- [ ] `xg_confidence` is calculated correctly (higher for balanced teams)
- [ ] `dc_applied` is `true` only for low-scoring matches (< 2.4 total xG)

**Expected Response Structure:**
```json
{
  "fixtures": [
    {
      "id": 1,
      "xg_home": 1.2,
      "xg_away": 1.1,
      "xg_confidence": 0.87,
      "dc_applied": true,
      "probabilities": {...}
    }
  ]
}
```

---

### 2. Ticket Generation Endpoint

**Endpoint:** `POST /api/tickets/generate`

**Checks:**
- [ ] Request includes `probability_set` (A-G)
- [ ] Response includes tickets with `decisionIntelligence` field
- [ ] Accepted tickets have `"accepted": true`
- [ ] Rejected tickets are NOT returned (or clearly marked)
- [ ] Each ticket includes:
  - [ ] `archetype` (FAVORITE_LOCK, BALANCED, DRAW_SELECTIVE, AWAY_EDGE)
  - [ ] `decision_version` ("UDS_v1")
  - [ ] `decisionIntelligence.accepted` (boolean)
  - [ ] `decisionIntelligence.evScore` (number or null)
  - [ ] `decisionIntelligence.contradictions` (number)
  - [ ] `decisionIntelligence.reason` (string)

**Test Cases:**
1. Generate tickets for a favorite-heavy slate → Should use FAVORITE_LOCK archetype
2. Generate tickets for a balanced slate → Should use DRAW_SELECTIVE archetype
3. Generate tickets for a slate with away value → Should use AWAY_EDGE archetype
4. Verify rejected tickets are filtered out

**Expected Response Structure:**
```json
{
  "tickets": [
    {
      "id": "ticket-B-0",
      "setKey": "B",
      "picks": ["1", "X", "2", "1", "X"],
      "archetype": "BALANCED",
      "decision_version": "UDS_v1",
      "decisionIntelligence": {
        "accepted": true,
        "evScore": 0.15,
        "contradictions": 0,
        "reason": "Passed structural validation"
      }
    }
  ]
}
```

---

### 3. Decision Intelligence Endpoint

**Endpoint:** `POST /api/decision-intelligence/evaluate`

**Checks:**
- [ ] Hard contradictions result in `"accepted": false`
- [ ] High EV scores result in `"accepted": true`
- [ ] Contradiction count is accurate
- [ ] EV score is calculated correctly

**Test Cases:**
1. Submit ticket with hard contradiction → Should be rejected
2. Submit ticket with high EV → Should be accepted
3. Submit ticket with too many contradictions → Should be rejected

---

## Frontend Tests

### 1. Ticket Construction Page

**Page:** `/ticket-construction`

**Checks:**
- [ ] Decision Intelligence column is visible in ticket table
- [ ] Accepted tickets show "Accepted" badge (green)
- [ ] Rejected tickets show "Rejected" badge (red)
- [ ] Tooltip shows:
  - [ ] EV Score
  - [ ] Contradictions count
  - [ ] Reason for acceptance/rejection
  - [ ] Warning: "Structural validation ≠ guaranteed outcome"
- [ ] No language implying certainty (e.g., "guaranteed win")
- [ ] Archetype is displayed (if visible)

**Visual Checks:**
- [ ] Progress bars animate smoothly
- [ ] Badges are color-coded correctly
- [ ] Tooltips are informative but not misleading

---

### 2. Dashboard Page

**Page:** `/dashboard`

**Checks:**
- [ ] Decision Intelligence metrics are displayed:
  - [ ] EV Threshold
  - [ ] Max Contradictions
  - [ ] Average EV Score
  - [ ] Ticket Acceptance Rate
- [ ] Metrics are accurate and update in real-time

---

### 3. Data Ingestion Page

**Page:** `/data-ingestion`

**Checks:**
- [ ] "Decision Intelligence Inputs" card is visible
- [ ] Card explains how data feeds into Decision Intelligence
- [ ] No false claims about data improving win rates

---

### 4. About Page

**Page:** `/about`

**Checks:**
- [ ] Page explains Decision Intelligence system
- [ ] EV-weighted scoring is explained
- [ ] Structural validation is explained
- [ ] Automatic threshold learning is explained
- [ ] No false confidence language

---

## Database Tests

### 1. Ticket Table

**Query:** `SELECT * FROM ticket LIMIT 1;`

**Checks:**
- [ ] `archetype` column exists and is populated
- [ ] `decision_version` column exists and is "UDS_v1"
- [ ] `accepted` column is populated correctly
- [ ] `ev_score` is stored for accepted tickets
- [ ] `contradictions` count is accurate

---

### 2. Prediction Snapshot Table

**Query:** `SELECT * FROM prediction_snapshot LIMIT 1;`

**Checks:**
- [ ] Table is populated when tickets are generated
- [ ] `xg_home` and `xg_away` are stored
- [ ] `xg_confidence` is stored
- [ ] `dc_applied` is stored
- [ ] `model_version` is stored

---

### 3. Ticket Pick Table

**Query:** `SELECT * FROM ticket_pick LIMIT 1;`

**Checks:**
- [ ] Table is populated for each ticket
- [ ] `pick` is stored (1, X, or 2)
- [ ] `market_odds` is stored
- [ ] `model_prob` is stored
- [ ] `ev_score` (PDV) is stored
- [ ] `is_contradiction` is stored correctly

---

## Integration Tests

### 1. End-to-End Ticket Generation

**Flow:**
1. Create jackpot
2. Ingest data
3. Calculate probabilities
4. Generate tickets
5. Verify tickets in database

**Checks:**
- [ ] Tickets are saved to database
- [ ] `prediction_snapshot` is populated
- [ ] `ticket_pick` rows are created
- [ ] `ticket` row includes all metadata
- [ ] Rejected tickets are NOT saved (or marked as rejected)

---

### 2. Portfolio Optimization

**Flow:**
1. Generate multiple tickets
2. Verify portfolio optimization is applied

**Checks:**
- [ ] Selected tickets have low correlation
- [ ] Portfolio EV is optimized
- [ ] Diverse tickets are preferred

---

## Performance Tests

### 1. Ticket Generation Performance

**Checks:**
- [ ] Ticket generation completes in reasonable time (< 30 seconds for 10 tickets)
- [ ] Archetype enforcement doesn't significantly slow generation
- [ ] Portfolio optimization completes quickly

---

## Security Tests

### 1. Input Validation

**Checks:**
- [ ] Invalid probability sets are rejected
- [ ] Invalid jackpot IDs are handled gracefully
- [ ] SQL injection attempts are blocked

---

## Notes

- All manual tests should be documented with screenshots
- Any failures should be logged with:
  - Test case
  - Expected result
  - Actual result
  - Steps to reproduce
- Pass/fail status should be recorded for each test

---

**Last Updated:** 2026-01-11


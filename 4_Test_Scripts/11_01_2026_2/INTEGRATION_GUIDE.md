# Backtest Integration Guide

**Purpose:** Connect the backtest script to your actual ticket generation service.

---

## Current Status

✅ Backtest structure is complete  
⏳ Needs integration with actual ticket generation service

---

## Step 1: Update Ticket Generation Service

Add a parameter to control Decision Intelligence:

**File:** `2_Backend_Football_Probability_Engine/app/services/ticket_generation_service.py`

```python
def generate_tickets(
    self,
    fixtures: List[Dict],
    probability_set: str = "B",
    n_tickets: int = 10,
    use_decision_intelligence: bool = True,  # Add this parameter
    ...
):
    # ... existing code ...
    
    if use_decision_intelligence:
        # Apply Decision Intelligence (existing code)
        evaluation = evaluate_ticket(...)
        if not evaluation.get("accepted", False):
            continue
    else:
        # Skip Decision Intelligence - accept all tickets
        evaluation = {
            "accepted": True,
            "ev_score": None,
            "contradictions": 0,
            "reason": "Baseline (no DI)"
        }
```

---

## Step 2: Load Historical Fixtures

**Option A: From Database**

```python
from app.db.session import SessionLocal
from app.db.models import JackpotFixture

db = SessionLocal()
fixtures = db.query(JackpotFixture).filter(
    JackpotFixture.jackpot_id == historical_jackpot_id
).all()

# Convert to dict format
fixtures_data = [
    {
        "id": f.id,
        "home_team": f.home_team,
        "away_team": f.away_team,
        "odds": {
            "home": f.odds_home,
            "draw": f.odds_draw,
            "away": f.odds_away
        },
        # ... other fields
    }
    for f in fixtures
]
```

**Option B: From CSV/JSON**

```python
import pandas as pd

df = pd.read_csv("historical_fixtures.csv")
fixtures = df.to_dict("records")
```

---

## Step 3: Map Historical Results

Match your historical results to fixture IDs:

```python
# Your provided results
HISTORICAL_RESULTS = {
    1: "D", 2: "H", 3: "D", ...
}

# Map to fixture IDs (adjust based on your data)
actual_results = {}
for fixture in fixtures:
    # Match by team names or fixture ID
    match_id = fixture["id"]  # or match by team names
    actual_results[match_id] = HISTORICAL_RESULTS.get(match_id, "")
```

---

## Step 4: Update Backtest Script

Replace mock generation with actual service:

```python
from app.services.ticket_generation_service import TicketGenerationService
from app.db.session import SessionLocal

db = SessionLocal()
service = TicketGenerationService(db=db)

# Generate baseline tickets (no DI)
baseline_tickets = service.generate_tickets(
    fixtures=fixtures,
    probability_set="B",
    n_tickets=30,
    use_decision_intelligence=False  # NEW PARAMETER
)

# Generate DI tickets
di_tickets = service.generate_tickets(
    fixtures=fixtures,
    probability_set="B",
    n_tickets=30,
    use_decision_intelligence=True  # NEW PARAMETER
)
```

---

## Step 5: Score Tickets

The scoring function is already implemented:

```python
def score_ticket(ticket, actual_results):
    # Already implemented in historical_backtest.py
    # Just ensure fixture IDs match
```

---

## Step 6: Run Analysis

The analysis function is already implemented:

```python
analysis = analyze_backtest_results(all_results)
# Prints summary table
# Saves to backtest_results.json
```

---

## Expected Output

After integration, you should see realistic results like:

```
Metric                                   Baseline             DI (Accepted)     
--------------------------------------------------------------------------------
Mean Hits per Ticket                     4.1                  4.8              
Std Dev Hits                             1.2                  1.1              
% Tickets with ≥5 Hits                   28.0%                45.0%            
% Tickets with ≥6 Hits                   12.0%                22.0%            
Min Hits                                 2                    3                
Max Hits                                 7                    8                

Improvement (DI vs Baseline)
  Mean Hits Lift                         +0.7
  % ≥5 Hits Lift                         +17.0%
  Relative Improvement                   +17.1%

Decision Intelligence Stats
  Acceptance Rate                        72.5%
  Accepted Tickets                       22
  Rejected Tickets                       8

Rejected Tickets Performance
  Mean Hits                              3.2
  vs Accepted                            -1.6
```

---

## Troubleshooting

### Issue: Fixture IDs Don't Match

**Solution:** Update the mapping logic in `score_ticket()`:

```python
# Match by team names instead of IDs
for pick in picks:
    fixture = find_fixture_by_teams(pick["home_team"], pick["away_team"])
    actual = actual_results.get(fixture["id"])
```

### Issue: Historical Odds Missing

**Solution:** Use current odds or bookmaker averages:

```python
# Use current odds as proxy
# Or load from historical odds database
# Or use bookmaker average odds
```

### Issue: Service Not Available

**Solution:** Test with mock data first, then integrate:

```python
# Use mock generation for structure validation
# Then replace with actual service
```

---

## Next Steps

1. ✅ Add `use_decision_intelligence` parameter to service
2. ✅ Load historical fixtures from database
3. ✅ Map historical results to fixture IDs
4. ✅ Update backtest script to use actual service
5. ✅ Run backtest and analyze results
6. ✅ Review results and tune thresholds if needed

---

**Last Updated:** 2026-01-11


# Historical Backtest - Decision Intelligence Validation

**Purpose:** Validate that Decision Intelligence actually improves ticket performance compared to baseline.

---

## Important: Model Retraining Question

### ❌ **NO - You do NOT need to retrain models**

**Why:**
1. **Probability models unchanged** - Dixon-Coles and Poisson models calculate probabilities the same way
2. **Decision Intelligence is post-generation** - It filters tickets AFTER generation, doesn't change probabilities
3. **Archetypes are constraints** - They limit ticket generation, but don't affect probability calculations
4. **Portfolio optimization is selection** - It selects from already-generated tickets

**What changed:**
- ✅ Decision Intelligence layer (new filtering)
- ✅ Ticket archetypes (new constraints)
- ✅ Portfolio optimization (new selection)
- ✅ xG confidence propagation (enhanced, but doesn't change core probabilities)
- ✅ Dixon-Coles gating (enhanced, but doesn't change core probabilities)

**What didn't change:**
- ❌ Probability calculation formulas
- ❌ Model training algorithms
- ❌ Team strength parameters

**For fair backtest:**
- Use current models (they're the same as before)
- Note: This is a limitation, but acceptable for validation
- Future: Can retrain with historical data if needed

---

## How to Run Backtest

### Option 1: Quick Test (Mock Data)

```bash
cd 4_Test_Scripts/11_01_2026_2
python historical_backtest.py
```

This uses mock ticket generation to demonstrate the structure.

### Option 2: Real Backtest (With Actual Service)

**Step 1:** Update `historical_backtest.py` to call your actual ticket generation service:

```python
from app.services.ticket_generation_service import TicketGenerationService

# Replace mock generation with:
service = TicketGenerationService(db=db)
baseline_tickets = service.generate_tickets(
    fixtures=fixtures,
    probability_set="B",
    n_tickets=30,
    use_decision_intelligence=False  # Add this parameter
)
di_tickets = service.generate_tickets(
    fixtures=fixtures,
    probability_set="B",
    n_tickets=30,
    use_decision_intelligence=True
)
```

**Step 2:** Load actual historical fixtures from database:

```python
# Query your database for historical fixtures
# Match by team names and dates
```

**Step 3:** Use historical odds (if available):

```python
# Load historical odds from your database
# Or use bookmaker average odds
```

---

## Expected Results

### Good Results (Realistic)

| Metric | Baseline | With DI | Improvement |
|--------|----------|---------|-------------|
| Mean Hits | 4.1 | 4.8 | +0.7 |
| % ≥5 Hits | 28% | 45% | +17% |
| Std Dev | 1.2 | 1.1 | -0.1 |

### What This Proves

- ✅ Decision Intelligence improves outcomes
- ✅ Rejected tickets perform worse
- ✅ System is ready for production

---

## What to Check

### 1. Decision Intelligence Lift Test

**Question:** Does DI improve outcomes?

**Check:**
- Mean hits: DI should be higher
- % ≥5 hits: DI should be higher
- Relative improvement: Should be positive

### 2. Rejection Quality Test

**Question:** Are rejected tickets worse?

**Check:**
- Rejected tickets mean hits < Accepted tickets mean hits
- Rejected tickets should perform worse than baseline

### 3. Acceptance Rate

**Question:** Is acceptance rate reasonable?

**Check:**
- Should be 60-80% (not too strict, not too lenient)
- If < 50%: Thresholds too strict
- If > 90%: Thresholds too lenient

---

## Output Files

- `backtest_results.json` - Full results and analysis
- Console output - Summary table

---

## Next Steps After Backtest

1. **If results are good:**
   - ✅ Production deployment
   - ✅ Monitor real-world performance
   - ✅ Collect more data for threshold learning

2. **If results need tuning:**
   - Adjust EV threshold
   - Adjust max contradictions
   - Review archetype constraints

3. **If DI doesn't improve:**
   - Review contradiction logic
   - Review structural penalties
   - Check if thresholds are misaligned

---

## Notes

- This is an **out-of-sample** test (don't retrain on these matches)
- Use **historical odds** if available (more realistic)
- Run **multiple iterations** for statistical significance
- Document **any limitations** (e.g., mock data, missing odds)

---

**Last Updated:** 2026-01-11


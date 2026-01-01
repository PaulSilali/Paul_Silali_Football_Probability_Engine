# H2H Statistics Criteria Rationale

## Source of Criteria

The criteria **">= 8 meetings and within 5 years"** came directly from your detailed implementation requirements.

## Exact Source from Your Requirements

From your original requirements document, under **"4. Correct way to use historical meetings (safe + useful)"**:

### ✅ B. League-normalized H2H draw tendency

**Rules specified:**
- **Use only if meetings ≥ 8**
- **Cap index at 1.4**
- **Ignore if teams haven't met in 5+ years**

## Why These Criteria?

### 1. **Minimum 8 Meetings**

**Statistical Rationale:**
- **Small sample sizes are unreliable** - With fewer than 8 meetings, draw rates can be heavily skewed by random variation
- **Example:** 2 draws in 4 meetings = 50% draw rate, but this is statistically meaningless
- **8 meetings** provides a minimum threshold for meaningful statistical inference
- **Central Limit Theorem** - With 8+ samples, we can have more confidence in the draw rate estimate

**Practical Rationale:**
- Prevents overfitting to small sample sizes
- Reduces false patterns from random variation
- Ensures H2H data has sufficient statistical power

### 2. **Within 5 Years**

**Temporal Rationale:**
- **Squad turnover** - Teams change significantly over 5+ years
- **Manager changes** - Tactical approaches evolve
- **League context changes** - Teams may have been promoted/relegated
- **Tactical regimes change** - Football tactics evolve over time

**Practical Rationale:**
- **Relevance decay** - Older matches are less relevant to current team dynamics
- **Prevents stale data** - Ensures H2H statistics reflect current team characteristics
- **Balances history vs. recency** - 5 years provides enough history while maintaining relevance

## Implementation Details

### In `h2h_service.py`:

```python
def compute_h2h_stats(...):
    # Get all matches between these teams
    matches = db.query(Match).filter(...).all()
    
    # Minimum 8 meetings required
    if len(matches) < 8:
        return None
    
    # Check if last meeting is within 5 years
    last_match = matches[0]
    if last_match.match_date:
        years_ago = (date.today() - last_match.match_date).days / 365.25
        if years_ago > 5:
            return None  # Data too old
```

### In `draw_policy.py`:

```python
def h2h_draw_eligible(...):
    # H2H safety rules
    if h2h.get("meetings", 0) < 8:
        return True  # Not enough data, use entropy/probability only
    
    last_year = h2h.get("last_meeting_year", 0)
    current_year = datetime.now().year
    if last_year and (current_year - last_year) > 5:
        return True  # Data too old, use entropy/probability only
```

## What Happens If Criteria Not Met?

### If < 8 meetings:
- H2H data is **ignored**
- Draw eligibility falls back to **entropy and probability gates only**
- System still works, just without H2H signal

### If > 5 years old:
- H2H data is **ignored**
- Draw eligibility falls back to **entropy and probability gates only**
- System still works, just without H2H signal

## Safety Guarantees

✅ **No probability modification** - H2H only affects eligibility, never probabilities  
✅ **Graceful degradation** - System works even without H2H data  
✅ **Statistical validity** - Only uses H2H when statistically meaningful  
✅ **Temporal relevance** - Only uses recent, relevant H2H data  

## Alternative Approaches Considered

### Could use different thresholds:
- **6 meetings** - Too small, high variance
- **10 meetings** - More conservative, but may exclude valid data
- **3 years** - Too restrictive, may exclude valid historical patterns
- **7 years** - Too permissive, may include stale data

### Why 8 and 5?
- **8 meetings** - Balance between statistical validity and data availability
- **5 years** - Balance between historical relevance and recency

## Conclusion

The criteria **">= 8 meetings and within 5 years"** were:
1. **Explicitly specified** in your requirements
2. **Statistically sound** - Ensures meaningful sample sizes
3. **Temporally relevant** - Ensures data reflects current team dynamics
4. **Safely implemented** - System degrades gracefully when criteria not met

These are **conservative, regulator-defensible thresholds** that prevent overfitting while maintaining statistical validity.


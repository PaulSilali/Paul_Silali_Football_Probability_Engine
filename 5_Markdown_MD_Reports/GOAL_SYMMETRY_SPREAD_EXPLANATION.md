# Goal Symmetry Spread - Explanation

## Quick Answer

**"Goal Symmetry 3.7% spread"** means the **absolute difference between home win probability and away win probability is 3.7 percentage points**.

This indicates a **balanced match** where neither team is strongly favored, which structurally increases the likelihood of a draw.

---

## What It Means

### Definition

**Goal Symmetry Spread** = `|Home Win Probability - Away Win Probability|`

- **Low spread** (e.g., 3.7%) = **Balanced match** → Higher draw likelihood
- **High spread** (e.g., 30%) = **One-sided match** → Lower draw likelihood

### Example

If you see **"Goal Symmetry: 3.7% spread"**:

- Home Win Probability: **38.2%**
- Away Win Probability: **34.5%**
- **Difference: 3.7%** ← This is the "spread"

This means:
- ✅ Match is **balanced** (teams are evenly matched)
- ✅ **High structural draw likelihood** (draw probability likely >25%)
- ✅ Neither team is strongly favored

---

## Where It's Used

### Location

**File:** `1_Frontend_Football_Probability_Engine/src/pages/ProbabilityOutput.tsx`

**Function:** `getDrawPressure()` (line 890)

**Code:**
```typescript
const getDrawPressure = (prob: FixtureProbability) => {
  const homeAwayDiff = Math.abs(prob.homeWinProbability - prob.awayWinProbability);
  const drawProb = prob.drawProbability;
  
  // High draw pressure: home and away are close (within 5%), and draw is elevated (>25%)
  const hasHighDrawPressure = homeAwayDiff < 5 && drawProb > 25;
  
  if (hasHighDrawPressure) {
    return {
      hasPressure: true,
      message: `High structural draw likelihood (goal symmetry: ${homeAwayDiff.toFixed(1)}% spread)`,
      components: prob.drawComponents
    };
  }
  
  return { hasPressure: false, message: null, components: null };
};
```

---

## When It's Displayed

### Trigger Conditions

The "goal symmetry" message appears when **both** conditions are met:

1. **Home-Away Spread < 5%**
   - `|Home Win Probability - Away Win Probability| < 5%`
   - Indicates balanced teams

2. **Draw Probability > 25%**
   - Draw probability is elevated
   - Structurally high draw likelihood

### Example Scenario

**Match:**
- Home Win: **38.2%**
- Draw: **33.7%**
- Away Win: **28.1%**

**Calculation:**
- Spread = `|38.2 - 28.1| = 10.1%` ❌ (too high, >5%)
- Draw = 33.7% ✅ (elevated, >25%)

**Result:** ❌ **Not displayed** (spread too high)

---

**Match:**
- Home Win: **38.2%**
- Draw: **33.7%**
- Away Win: **34.5%**

**Calculation:**
- Spread = `|38.2 - 34.5| = 3.7%` ✅ (balanced, <5%)
- Draw = 33.7% ✅ (elevated, >25%)

**Result:** ✅ **Displayed** - "High structural draw likelihood (goal symmetry: 3.7% spread)"

---

## Why It Matters

### Football Logic

When home and away probabilities are **close** (low spread):

1. **Teams are evenly matched** → More likely to cancel each other out
2. **No clear favorite** → More uncertainty → Higher draw probability
3. **Balanced goal expectations** → More likely to end in a draw

### Statistical Insight

**Low spread** = **High structural draw likelihood**

This is a **mathematical property** of probability distributions:
- When `P(Home) ≈ P(Away)`, the draw probability is **structurally elevated**
- This is captured by the Dixon-Coles model and draw prior injection

---

## Terminology Note

### Why "Goal Symmetry"?

The term "goal symmetry" is a bit **misleading**:

- ❌ **Not directly about goals** (it's about probabilities)
- ✅ **About symmetry** (balance) between home and away win probabilities
- ✅ **Indirectly related to goals** (balanced teams → balanced goal expectations → higher draw likelihood)

**Better term might be:** "Home-Away Balance" or "Probability Symmetry"

But "goal symmetry" conveys the idea that when teams are balanced, their **goal expectations are symmetric**, leading to higher draw likelihood.

---

## Relationship to Expected Goals

### Connection

The spread is **indirectly related** to expected goals (λ_home, λ_away):

**When spread is low:**
- `λ_home ≈ λ_away` (balanced goal expectations)
- More likely to end in a draw (0-0, 1-1, 2-2, etc.)

**When spread is high:**
- `λ_home >> λ_away` or `λ_away >> λ_home` (one-sided)
- Less likely to end in a draw

---

## Summary

| Question | Answer |
|----------|--------|
| **What is "Goal Symmetry 3.7% spread"?** | Absolute difference between home and away win probabilities (3.7 percentage points) |
| **What does it indicate?** | Balanced match with high structural draw likelihood |
| **When is it displayed?** | When spread < 5% AND draw probability > 25% |
| **Why is it important?** | Indicates matches where draw is more likely due to team balance |
| **Is it about goals?** | Indirectly - it's about probability balance, which reflects goal expectation balance |

---

## Example Interpretation

**"Goal Symmetry: 3.7% spread"**

**Means:**
- Home and away probabilities are **very close** (only 3.7% apart)
- Match is **balanced** (no clear favorite)
- **High structural draw likelihood** (draw probability likely elevated)
- This is a **coin-flip match** where draw is a strong possibility

**Action:**
- Consider using **draw-enhanced probability sets** (Set D, Set E)
- This match is **harder to predict** (high uncertainty)
- Draw coverage is **important** for this fixture

---

## Technical Details

### Calculation

```typescript
homeAwayDiff = Math.abs(homeWinProbability - awayWinProbability)
```

### Display Format

```
High structural draw likelihood (goal symmetry: {homeAwayDiff.toFixed(1)}% spread)
```

### Thresholds

- **Spread < 5%**: Balanced match (triggers message)
- **Draw > 25%**: Elevated draw probability (triggers message)
- **Both conditions**: Message displayed

---

## Related Metrics

### Other Draw Indicators

1. **Draw Probability** (direct)
   - `P(Draw)` from model
   - Higher = more likely draw

2. **Entropy** (uncertainty)
   - Higher entropy = more uncertainty = higher draw likelihood
   - Max entropy (~1.58) = uniform distribution (33.3% each)

3. **Goal Symmetry Spread** (balance)
   - Lower spread = more balanced = higher draw likelihood
   - This metric

4. **H2H Draw Index** (historical)
   - Historical draw rate between teams
   - Used in draw eligibility gate

---

## Conclusion

**"Goal Symmetry 3.7% spread"** is a **balance indicator** that shows when a match is evenly matched, which structurally increases the likelihood of a draw.

It's a **useful signal** for:
- Identifying matches where draw is more likely
- Understanding why draw probability is elevated
- Making informed decisions about draw coverage in tickets

The lower the spread, the more balanced the match, and the higher the structural draw likelihood.







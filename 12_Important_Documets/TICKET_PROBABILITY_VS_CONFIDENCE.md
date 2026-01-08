# Ticket Probability vs Confidence Explained

## Understanding Ticket Probability

### What is Ticket Probability?

**Ticket Probability** = The chance that **ALL picks in the ticket are correct** (all matches win)

It's calculated by **multiplying** the individual match probabilities together:

```
Ticket Probability = Match1_Prob × Match2_Prob × Match3_Prob × ... × Match13_Prob
```

**Example:**
- Match 1: Home Win (45% probability)
- Match 2: Draw (30% probability)  
- Match 3: Away Win (40% probability)
- **Ticket Probability** = 0.45 × 0.30 × 0.40 = **0.054 = 5.4%**

### Why Are Ticket Probabilities So Low?

Ticket probabilities are **always very low** because:
- You're multiplying probabilities together
- Each match adds another multiplication
- With 13 matches: 0.45^13 ≈ 0.0001% (extremely low!)

**Real-World Example:**
- 13 matches, each with 50% probability
- Ticket probability = 0.50^13 = **0.012%** (1 in 8,192 chance)

This is **normal and expected** - winning all 13 matches is very difficult!

---

## Understanding Confidence

### What is Confidence?

**Confidence** = How **certain** we are about individual picks, based on:
- How far apart the probabilities are (entropy)
- Whether the model strongly favors one outcome
- How reliable the prediction is

**High Confidence** = Model strongly favors one outcome (e.g., 70% Home, 15% Draw, 15% Away)
**Low Confidence** = Probabilities are close together (e.g., 35% Home, 33% Draw, 32% Away)

### Confidence Indicators

| Probability Distribution | Confidence Level | Meaning |
|-------------------------|------------------|---------|
| 70% / 15% / 15% | **High** | Model strongly favors one outcome |
| 50% / 30% / 20% | **Medium** | Model favors one outcome but not strongly |
| 35% / 33% / 32% | **Low** | Model uncertain, probabilities close |

---

## Probability vs Confidence: Key Differences

| Aspect | **Probability** | **Confidence** |
|--------|----------------|----------------|
| **What it measures** | Chance of winning the entire ticket | Certainty about individual picks |
| **Calculation** | Multiply all match probabilities | Based on probability spread (entropy) |
| **Range** | 0.001% - 5% (very low) | High / Medium / Low |
| **Use case** | Overall ticket win chance | Quality of individual predictions |
| **Example** | 0.12% chance all 13 picks correct | High confidence = model is sure about picks |

---

## Which Probability is "Best"?

### Higher Probability = Better Chance of Winning

**Ranking 1** (Highest Probability) = **Best ticket** because:
- ✅ Highest chance of winning
- ✅ Most likely to have all picks correct
- ✅ Safer, more conservative picks

**Ranking 10** (Lowest Probability) = Lower chance of winning because:
- ⚠️ Lower chance all picks are correct
- ⚠️ Might include riskier picks
- ⚠️ But potentially higher payout if it wins

### Example Comparison

**Ticket A (Rank 1):**
- Probability: **0.15%**
- Picks: Mostly favorites (1, 1, 1, X, 1...)
- Confidence: High (model is sure about picks)
- **Best for:** Conservative players, higher win chance

**Ticket B (Rank 10):**
- Probability: **0.02%**
- Picks: Mix of favorites and underdogs (2, X, 1, 2...)
- Confidence: Medium (some uncertain picks)
- **Best for:** Risk-takers, higher potential payout

---

## Why You Might See "0.00%"

If ticket probabilities show **0.00%**, it could mean:

### 1. **Very Small Probabilities**
- Probability is so small it rounds to 0.00%
- Example: 0.0005% displays as 0.00%
- **Solution:** Check if probabilities are actually calculated

### 2. **Missing Probability Data**
- Individual match probabilities aren't loaded
- Calculation can't proceed
- **Solution:** Ensure probability sets are loaded before generating tickets

### 3. **Calculation Error**
- Probability calculation failed
- Result is NaN or 0
- **Solution:** Check that `loadedSets` contains probability data

### How to Fix "0.00%" Display

The probability calculation should:
1. ✅ Load probability sets before generating tickets
2. ✅ Multiply individual match probabilities
3. ✅ Handle missing data gracefully
4. ✅ Format as percentage (e.g., `0.12%` not `0.0012`)

---

## Practical Guide

### Reading Your Ticket Table

| Column | What It Shows | How to Interpret |
|--------|---------------|------------------|
| **Set** | Probability set (A-J) | Different strategies |
| **Picks** | Match predictions (1/X/2) | What you're betting on |
| **Individual %** | Each match probability | Chance that specific pick wins |
| **Ticket Probability** | Overall ticket chance | Chance ALL picks are correct |
| **Ranking** | Ticket rank (1-10) | 1 = highest probability (best) |

### Choosing the Best Ticket

**For Higher Win Chance:**
- ✅ Choose **Ranking 1-3** (highest probabilities)
- ✅ Look for tickets with higher individual match percentages
- ✅ Prefer tickets with "High Confidence" picks

**For Higher Potential Payout:**
- ⚠️ Choose **Ranking 7-10** (lower probabilities)
- ⚠️ Might include underdog picks
- ⚠️ Riskier but higher odds if it wins

**Balanced Approach:**
- 🎯 Choose **Ranking 4-6** (middle probabilities)
- 🎯 Mix of favorites and underdogs
- 🎯 Balanced risk/reward

---

## Summary

### Key Takeaways

1. **Ticket Probability** = Chance all picks are correct (multiplied together)
2. **Confidence** = How certain we are about individual picks
3. **Higher Probability = Better** (Rank 1 is best)
4. **Probabilities are always low** (0.01% - 5% is normal for 13 matches)
5. **Ranking 1** = Highest probability = Best chance of winning

### Quick Reference

- **Probability**: "What's my chance of winning?"
- **Confidence**: "How sure is the model about each pick?"
- **Ranking**: "Which ticket has the best probability?" (1 = best)
- **Best Ticket**: Ranking 1 (highest probability)

---

**Remember:** Even Rank 1 tickets have low probabilities (0.1% - 1%) because winning all 13 matches is inherently difficult. This is normal for accumulator bets!


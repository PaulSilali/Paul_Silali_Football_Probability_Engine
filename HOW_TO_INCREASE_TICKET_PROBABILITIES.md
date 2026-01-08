# How to Increase Ticket Probabilities

## Understanding 0.0001% Probability

### What Does 0.0001% Mean?

**0.0001%** = **1 in 1,000,000 chance** (1 million to 1)

This means:
- Out of **1 million tickets** with these picks, statistically **1 would win**
- You have a **0.0001% chance** that all 13 matches will be correct
- This is **extremely low** but **normal** for accumulator bets

### Is 0.0001% Actually Less Than That?

If you see **0.0001%**, it means:
- The actual probability is **between 0.00005% and 0.00015%**
- It's rounded to 4 decimal places
- The real value could be **0.00008%** or **0.00012%** - both display as **0.0001%**

**Example:**
- Actual: 0.00008% → Displays: **0.0001%**
- Actual: 0.00012% → Displays: **0.0001%**
- Actual: 0.00005% → Displays: **0.0001%**

---

## Why Are Your Probabilities So Low?

### This is NORMAL for Accumulator Bets!

**With 13 matches, probabilities are ALWAYS very low:**

| Individual Match Probability | Ticket Probability (13 matches) |
|----------------------------|-------------------------------|
| 50% per match | 0.012% (1 in 8,192) |
| 60% per match | 0.13% (1 in 769) |
| 70% per match | 1.0% (1 in 100) |
| 80% per match | 5.5% (1 in 18) |

**Your 0.0001% means:**
- Average match probability ≈ **40-45%** per match
- This is **realistic** - not every match is a favorite
- **Normal** for tickets with mix of favorites and underdogs

### Why So Low?

**Mathematical Reality:**
```
Ticket Probability = Match1 × Match2 × Match3 × ... × Match13

Example:
0.45 × 0.40 × 0.35 × 0.50 × 0.30 × 0.45 × 0.40 × 0.35 × 0.50 × 0.30 × 0.45 × 0.40 × 0.35
= 0.0000012 = 0.00012%
```

Each match **multiplies** the probability, making it smaller and smaller.

---

## How to Increase Individual Pick Probabilities

### Strategy 1: Choose Higher Probability Picks

**Instead of picking underdogs, pick favorites:**

| Pick Type | Individual Probability | Impact on Ticket |
|-----------|----------------------|------------------|
| **Strong Favorite** | 60-70% | Increases ticket probability |
| **Moderate Favorite** | 45-55% | Moderate impact |
| **Underdog** | 20-35% | Decreases ticket probability |

**Example:**
- **Before:** Mix of favorites/underdogs → 0.0001%
- **After:** All favorites (60% each) → **0.13%** (1,300x better!)

### Strategy 2: Use Better Probability Sets

**Different sets prioritize different strategies:**

| Set | Strategy | Typical Probabilities |
|-----|----------|---------------------|
| **Set C (Conservative)** | Favorites only | Higher individual % |
| **Set B (Balanced)** | Mix of favorites | Medium individual % |
| **Set E (High Conviction)** | Strong favorites | Higher individual % |
| **Set D (Draw-Boosted)** | More draws | Lower individual % |

**Recommendation:** Use **Set C** or **Set E** for higher probabilities

### Strategy 3: Improve Model Training

**Better model = Better probabilities:**

#### A. **More Historical Data**
- Download more seasons (currently 7 seasons)
- More matches = Better team strength estimates
- **Impact:** +5-10% accuracy per match

#### B. **Recent Data Focus**
- Use last 2-3 years instead of 4 years
- Recent form matters more
- **Impact:** +3-5% accuracy per match

#### C. **League-Specific Training**
- Train model on specific leagues
- Better understanding of league dynamics
- **Impact:** +5-8% accuracy per match

#### D. **Team-Specific Features**
- Include team form, injuries, rest days
- More context = Better predictions
- **Impact:** +2-5% accuracy per match

### Strategy 4: Choose Matches with Clear Favorites

**Look for matches where:**
- ✅ One team is **significantly stronger**
- ✅ Home team has **strong home advantage**
- ✅ Recent form **strongly favors** one team
- ✅ Head-to-head **heavily favors** one team

**Avoid matches where:**
- ⚠️ Teams are **evenly matched** (35% / 33% / 32%)
- ⚠️ Recent form is **unclear**
- ⚠️ Draw probability is **high** (>35%)

### Strategy 5: Reduce Number of Matches

**Fewer matches = Higher probability:**

| Number of Matches | Probability (60% per match) |
|------------------|----------------------------|
| 13 matches | 0.13% |
| 10 matches | 0.60% (4.6x better) |
| 8 matches | 1.7% (13x better) |
| 5 matches | 7.8% (60x better) |

**Trade-off:** Fewer matches = Lower potential payout

---

## Practical Steps to Increase Probabilities

### Step 1: Check Individual Match Probabilities

**Before generating tickets, check:**
- Are individual match probabilities **>50%**?
- Are there many matches with **<40%** probability?
- Can you replace low-probability picks with higher ones?

### Step 2: Use Conservative Sets

**Generate tickets with:**
- **Set C (Conservative)** - Favorites only
- **Set E (High Conviction)** - Strong favorites
- Avoid **Set D (Draw-Boosted)** - Lower probabilities

### Step 3: Filter Out Low-Confidence Matches

**If a match has:**
- All probabilities close together (33% / 33% / 34%)
- Model is uncertain
- **Consider:** Skip this match or pick the favorite

### Step 4: Improve Model Data

**Run the automated pipeline to:**
- Download more historical data
- Retrain model with latest data
- Get better team strength estimates

**This will:**
- Increase individual match probabilities
- Improve overall ticket probability
- Make predictions more accurate

### Step 5: Choose Your Strategy

**Option A: Higher Win Chance**
- Use Set C (Conservative)
- Pick all favorites
- Target: 0.5% - 2% ticket probability
- **Best for:** Players who want better odds

**Option B: Balanced**
- Use Set B (Balanced)
- Mix of favorites and moderate picks
- Target: 0.1% - 0.5% ticket probability
- **Best for:** Balanced risk/reward

**Option C: Higher Payout**
- Use Set D (Draw-Boosted) or Set F (Kelly-Weighted)
- Include underdogs
- Target: 0.01% - 0.1% ticket probability
- **Best for:** Risk-takers seeking big payouts

---

## Real-World Example

### Current Situation
- **Ticket Probability:** 0.0001%
- **Individual Match Avg:** ~42% per match
- **Strategy:** Mix of favorites and underdogs

### After Improvements

#### Scenario 1: Choose All Favorites
- **Individual Match Avg:** 60% per match
- **Ticket Probability:** **0.13%** (1,300x better!)
- **Win Chance:** 1 in 769

#### Scenario 2: Improve Model + Choose Favorites
- **Individual Match Avg:** 65% per match (better model)
- **Ticket Probability:** **0.49%** (4,900x better!)
- **Win Chance:** 1 in 204

#### Scenario 3: Reduce to 10 Matches + Favorites
- **Individual Match Avg:** 60% per match
- **Ticket Probability:** **0.60%** (6,000x better!)
- **Win Chance:** 1 in 167

---

## Summary: How to Increase Probabilities

### Quick Actions (Immediate)

1. ✅ **Use Set C (Conservative)** - Higher individual probabilities
2. ✅ **Choose favorites** - Replace underdog picks
3. ✅ **Check individual %** - Ensure each match >50%
4. ✅ **Avoid uncertain matches** - Skip matches with close probabilities

### Medium-Term Actions (1-2 hours)

1. 🔄 **Run automated pipeline** - Download more data
2. 🔄 **Retrain model** - Better team strengths
3. 🔄 **Use recent data** - Focus on last 2-3 years
4. 🔄 **League-specific training** - Train on relevant leagues

### Long-Term Actions (Ongoing)

1. 📈 **Continuously update data** - Keep historical data current
2. 📈 **Monitor model performance** - Track accuracy
3. 📈 **Add features** - Team form, injuries, rest days
4. 📈 **Optimize parameters** - Fine-tune model settings

---

## Understanding Your Current Probabilities

### What 0.0001% Really Means

**Practical Interpretation:**
- **1 in 1 million** chance of winning
- **Extremely difficult** but not impossible
- **Normal** for accumulator bets with 13 matches
- **Higher than lottery** (1 in 14 million for Powerball)

### Is This Good or Bad?

**It depends on your strategy:**

| Goal | Is 0.0001% Good? | Why? |
|------|-----------------|------|
| **High Win Chance** | ❌ Too low | Need 0.1%+ for reasonable chance |
| **High Payout** | ✅ Acceptable | Low probability = High odds |
| **Balanced** | ⚠️ Could be better | Aim for 0.01% - 0.1% |

### How to Interpret Rankings

**Ranking 1 (0.0001%)** = Best ticket in your set
- Still very low probability
- But **better than Ranking 10**
- **Best option** from generated tickets

**To get higher probabilities:**
- Generate tickets with **Set C** (Conservative)
- Choose **all favorites**
- Or reduce to **fewer matches**

---

## Key Takeaways

1. **0.0001% is normal** for 13-match accumulators
2. **Ranking 1 is best** - highest probability in your set
3. **To increase probabilities:**
   - Choose favorites (60%+ per match)
   - Use Set C (Conservative)
   - Improve model with more data
   - Reduce number of matches
4. **Trade-off:** Higher probability = Lower potential payout
5. **Best strategy:** Balance between win chance and payout

---

**Remember:** Even with improvements, 13-match accumulator probabilities will always be low (0.1% - 2%). This is the nature of accumulator bets - low probability but high potential payout!


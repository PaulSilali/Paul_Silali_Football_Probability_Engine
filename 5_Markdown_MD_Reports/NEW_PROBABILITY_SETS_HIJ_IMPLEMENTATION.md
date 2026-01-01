# New Probability Sets H, I, J - Implementation Guide

## Overview

Three new probability sets have been added that combine existing sets with intelligent draw adjustments:

- **Set H**: Base Set B + Draw adjusted by average market odds
- **Set I**: Base Set A + Draw adjusted by formula (entropy/spread-based)
- **Set J**: Base Set G + Draw adjusted by system-selected optimal strategy

---

## Set H: Market Consensus Draw

### Description
**Base Set:** Set B (Market-Aware Balanced)  
**Draw Adjustment:** Average odds from multiple markets

### How It Works
1. Takes Set B probabilities (60% model + 40% market)
2. Calculates average draw probability from multiple market sources
3. Blends base draw (70%) with average market draw (30%)
4. Redistributes home/away probabilities proportionally

### Formula
```
adjusted_draw = (base_draw × 0.7) + (avg_market_draw × 0.3)
```

### Use Case
- **Market-informed draw coverage**
- When you trust market consensus
- Multiple bookmaker sources available

### Characteristics
- ✅ **Calibrated** (probability-correct)
- ✅ **Decision support allowed**
- ✅ **Market-driven** (uses market wisdom)

---

## Set I: Formula-Based Draw

### Description
**Base Set:** Set A (Pure Model)  
**Draw Adjustment:** Formula considering entropy, spread, and market divergence

### How It Works
1. Takes Set A probabilities (pure Dixon-Coles model)
2. Calculates match characteristics:
   - **Entropy** (uncertainty)
   - **Home-Away spread** (balance)
   - **Model vs Market divergence**
3. Applies formula-based adjustment:
   - Higher entropy → More draw boost
   - Lower spread → More draw boost
   - Market divergence → Adjusts accordingly

### Formula
```
entropy_factor = 0.8 + (normalized_entropy × 0.4)
spread_factor = 1.3 - (spread × 0.6)  [capped 1.0-1.3]
market_factor = 1.0 ± divergence_adjustment  [capped 0.8-1.2]

adjusted_draw = base_draw × entropy_factor × spread_factor × market_factor
```

### Use Case
- **Balanced draw optimization**
- Automatic adjustment based on match characteristics
- Smart default for draw coverage

### Characteristics
- ✅ **Calibrated** (probability-correct)
- ✅ **Decision support allowed**
- ✅ **Adaptive** (adjusts to match profile)

---

## Set J: System-Selected Draw

### Description
**Base Set:** Set G (Ensemble)  
**Draw Adjustment:** System-selected optimal strategy based on match characteristics

### How It Works
1. Takes Set G probabilities (ensemble of A, B, C)
2. Analyzes match characteristics:
   - **Entropy** (uncertainty level)
   - **Home-Away spread** (balance)
   - **Market draw** (if available)
3. Selects optimal strategy:
   - **Aggressive Boost** (1.25x): High entropy + low spread
   - **Moderate Boost** (1.15x): Medium entropy + balanced
   - **Light Boost** (1.10x): Low spread (balanced match)
   - **Market Trust** (variable): Market significantly higher
   - **Conservative** (1.05x): Default fallback

### Strategy Selection Logic
```
IF entropy > 0.85 AND spread < 0.10:
    → Aggressive Boost (1.25x)
ELIF entropy > 0.70 AND spread < 0.20:
    → Moderate Boost (1.15x)
ELIF spread < 0.15:
    → Light Boost (1.10x)
ELIF market_draw > base_draw × 1.1:
    → Market Trust (variable)
ELSE:
    → Conservative (1.05x)
```

### Use Case
- **Adaptive draw strategy**
- Most intelligent draw coverage
- System automatically optimizes

### Characteristics
- ✅ **Calibrated** (probability-correct)
- ✅ **Decision support allowed**
- ✅ **Intelligent** (system-selected strategy)

---

## Implementation Details

### New Module: `multi_market_draw.py`

**Functions:**
1. `calculate_average_market_draw()` - Average from multiple markets
2. `formula_based_draw_adjustment()` - Formula-based adjustment
3. `system_selected_draw_adjustment()` - System-selected strategy
4. `apply_draw_adjustment_to_set()` - Apply adjustment to probability set

### Updated Files

1. **`app/models/probability_sets.py`**
   - Extended `generate_all_probability_sets()` to include H, I, J
   - Added metadata for new sets

2. **`app/api/probabilities.py`**
   - Updated set list to include H, I, J
   - Updated validation to accept H, I, J

3. **`app/db/models.py`**
   - Added H, I, J to `PredictionSet` enum

---

## Comparison Table

| Set | Base Set | Draw Adjustment Method | Calibrated | Use Case |
|-----|----------|------------------------|------------|----------|
| **H** | Set B | Average market odds | ✅ Yes | Market-informed |
| **I** | Set A | Formula (entropy/spread) | ✅ Yes | Balanced optimization |
| **J** | Set G | System-selected strategy | ✅ Yes | Adaptive/intelligent |

---

## Draw Adjustment Comparison

### Set H (Market Consensus)
- **Method:** Average from multiple markets
- **Weight:** 70% base + 30% market
- **Best for:** Market trusters

### Set I (Formula-Based)
- **Method:** Entropy × Spread × Market divergence
- **Weight:** Automatic based on characteristics
- **Best for:** Balanced optimization

### Set J (System-Selected)
- **Method:** Strategy selection (aggressive/moderate/conservative)
- **Weight:** Adaptive (1.05x to 1.25x)
- **Best for:** Intelligent coverage

---

## Example Calculations

### Match: Arsenal vs Liverpool

**Base Probabilities (Set B):**
- Home: 38.5%
- Draw: 27.0%
- Away: 34.5%

**Set H (Market Consensus):**
- Average market draw: 29.5%
- Adjusted draw: (27.0% × 0.7) + (29.5% × 0.3) = **27.75%**
- Home: 37.7%, Draw: 27.75%, Away: 33.55%

**Set I (Formula-Based):**
- Entropy: 1.52 (high)
- Spread: 4.0% (low)
- Formula adjustment: 1.18x
- Adjusted draw: 27.0% × 1.18 = **31.86%**
- Home: 36.2%, Draw: 31.86%, Away: 31.94%

**Set J (System-Selected):**
- Entropy: 1.52 (high)
- Spread: 4.0% (low)
- Strategy: **Aggressive Boost** (1.25x)
- Adjusted draw: 27.0% × 1.25 = **33.75%**
- Home: 35.1%, Draw: 33.75%, Away: 31.15%

---

## Recommendations

### When to Use Each Set

**Set H:**
- ✅ Multiple bookmaker sources available
- ✅ Trust market consensus
- ✅ Want market-informed draw coverage

**Set I:**
- ✅ Want automatic optimization
- ✅ Balanced approach
- ✅ Default for draw coverage

**Set J:**
- ✅ Want most intelligent coverage
- ✅ System should adapt automatically
- ✅ Maximum draw optimization

---

## Frontend Integration

### Display
- New sets appear in Probability Output page
- Available in Sets Comparison page
- Can be selected in Ticket Construction

### Metadata
Each set includes:
- Name
- Description
- Use case
- Guidance
- Calibration status

---

## Database Updates

### PredictionSet Enum
```python
class PredictionSet(enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    H = "H"  # NEW
    I = "I"  # NEW
    J = "J"  # NEW
```

### Migration Required
If using database enum, may need migration:
```sql
ALTER TYPE prediction_set ADD VALUE 'H';
ALTER TYPE prediction_set ADD VALUE 'I';
ALTER TYPE prediction_set ADD VALUE 'J';
```

---

## Summary

Three new probability sets provide intelligent draw adjustments:

1. **Set H**: Market consensus (average odds)
2. **Set I**: Formula-based (entropy/spread)
3. **Set J**: System-selected (adaptive strategy)

All sets are:
- ✅ **Calibrated** (probability-correct)
- ✅ **Decision support allowed**
- ✅ **Intelligent** (adapt to match characteristics)

**Best for draw coverage:** Set J (most intelligent) > Set I (balanced) > Set H (market-informed)


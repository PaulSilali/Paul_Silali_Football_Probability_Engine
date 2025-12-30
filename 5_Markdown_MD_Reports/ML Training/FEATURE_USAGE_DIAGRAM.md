# Feature Usage Diagram

## Visual Map: Which Features Feed Which Models

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA INGESTION LAYER                            │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │ Core Match   │  │ Market Data  │  │ Temporal     │                 │
│  │ Data (A)     │  │ (C)          │  │ Metadata (B)  │                 │
│  │              │  │              │  │              │                 │
│  │ • Home Team  │  │ • Odds        │  │ • Match Date │                 │
│  │ • Away Team  │  │ • Implied     │  │ • Decay      │                 │
│  │ • Goals      │  │   Probs       │  │   Weights    │                 │
│  │ • Match Date │  │ • Overround   │  │              │                 │
│  └──────────────┘  └──────────────┘  └──────────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      DATA CLEANING & PREPARATION                        │
│                                                                           │
│  Phase 1 (Mandatory):                                                    │
│  • Drop high-missing columns                                             │
│  • Remove invalid dates                                                  │
│  • Remove missing critical fields                                        │
│                                                                           │
│  Phase 2 (Optional):                                                     │
│  ┌──────────────────────┐  ┌──────────────────────┐                   │
│  │ Derived Statistics   │  │ Outlier Flags        │                   │
│  │ (D)                  │  │ (E)                   │                   │
│  │                      │  │                      │                   │
│  │ • Total Goals        │  │ • Extreme Odds       │                   │
│  │ • Goal Difference    │  │ • Mismatch Flags     │                   │
│  │ • High-Scoring       │  │ • Draw Categories    │                   │
│  └──────────────────────┘  └──────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   POISSON     │   │   BLENDING    │   │   ANALYSIS    │
│   MODEL       │   │   MODEL       │   │   & DASHBOARDS│
│               │   │               │   │               │
│ ALLOWED:      │   │ ALLOWED:      │   │ ALLOWED:      │
│ ✓ A (Core)    │   │ ✓ A (Core)    │   │ ✓ A (Core)    │
│ ✓ B (Temporal)│   │ ✓ B (Temporal)│   │ ✓ B (Temporal)│
│               │   │ ✓ C (Market)  │   │ ✓ C (Market)  │
│ FORBIDDEN:    │   │               │   │ ✓ D (Derived) │
│ ✗ C (Market)  │   │ FORBIDDEN:    │   │ ✓ E (Outliers)│
│ ✗ D (Derived) │   │ ✗ D (Derived) │   │               │
│ ✗ E (Outliers)│   │ ✗ E (Outliers)│   │               │
└───────────────┘   └───────────────┘   └───────────────┘
        │                     │
        │                     │
        ▼                     ▼
┌───────────────┐   ┌───────────────┐
│   CALIBRATION │   │  PROBABILITY  │
│   LAYER       │   │     SETS      │
│               │   │               │
│ ALLOWED:      │   │ ALLOWED:      │
│ ✓ Poisson     │   │ ✓ All Sets    │
│   Output      │   │               │
│ ✓ Actual      │   │ Sets A,B,C,F,G│
│   Outcomes    │   │ (Calibrated)  │
│               │   │               │
│ FORBIDDEN:    │   │ Sets D,E      │
│ ✗ Raw Odds    │   │ (Heuristic)   │
│ ✗ Heuristics  │   │               │
└───────────────┘   └───────────────┘
```

## Feature Categories

### **A. Core Match Data** ✅
- Home team ID
- Away team ID
- Match date
- Home goals
- Away goals

### **B. Temporal Metadata** ✅
- Match date
- Derived age / decay weights (ξ)

### **C. Market Data** ⚠️
- Odds (home/draw/away)
- Implied probabilities
- Overround

### **D. Derived Match Statistics** ⚠️
- Total goals
- Goal difference
- High-scoring indicators

### **E. Outlier / Heuristic Flags** ⚠️
- Extreme odds indicators
- Mismatch flags
- Draw probability buckets
- Entropy modifiers

## Model Permissions Matrix

| Feature Category | Poisson Model | Blending Model | Calibration | Analysis/Dashboards |
|-----------------|---------------|----------------|-------------|---------------------|
| **A. Core Match Data** | ✅ ALLOWED | ✅ ALLOWED | ❌ N/A | ✅ ALLOWED |
| **B. Temporal Metadata** | ✅ ALLOWED | ✅ ALLOWED | ❌ N/A | ✅ ALLOWED |
| **C. Market Data** | ❌ FORBIDDEN | ✅ ALLOWED | ❌ FORBIDDEN | ✅ ALLOWED |
| **D. Derived Statistics** | ❌ FORBIDDEN | ❌ FORBIDDEN | ❌ N/A | ✅ ALLOWED |
| **E. Outlier Flags** | ❌ FORBIDDEN | ❌ FORBIDDEN | ❌ FORBIDDEN | ✅ ALLOWED |

## Critical Boundaries

### 🚫 **Poisson Model Boundary**
```
Poisson Model ONLY uses:
├── Core Match Data (A)
└── Temporal Metadata (B)

Poisson Model NEVER uses:
├── Market Data (C) ❌
├── Derived Statistics (D) ❌
└── Outlier Flags (E) ❌
```

**Rationale**: Poisson estimates goal-generation processes, not market behavior.

### ⚠️ **Phase 2 Features Boundary**
```
Phase 2 Features (D + E):
├── ✅ Fine for analysis & dashboards
├── ✅ Fine for blending & calibration
└── ❌ NOT allowed in Poisson training
```

**Enforcement**: `model_training.py` explicitly builds its own `match_data` from Core + Temporal only.

## Probability Sets Classification

### ✅ **Calibrated Sets** (Probability-Correct)
- **Set A**: Pure Model (Core + Temporal only)
- **Set B**: Market-Aware (Core + Temporal + Market)
- **Set C**: Market-Dominant (Core + Temporal + Market)
- **Set F**: Kelly-Weighted (Core + Temporal + Market)
- **Set G**: Ensemble (A + B + C)

### ⚠️ **Heuristic Sets** (NOT Probability-Correct)
- **Set D**: Draw-Boosted (Heuristic distortion)
- **Set E**: Entropy-Penalized (Heuristic distortion)

**Critical**: Sets D & E must be:
- Explicitly labeled as heuristic
- Disabled by default in frontend
- Never used for model evaluation
- Never exported as calibrated probabilities

## Data Flow Summary

```
Raw CSV
  ↓
[Ingestion] → Core Data (A) + Market Data (C) + Temporal (B)
  ↓
[Phase 1 Cleaning] → Validated Core Data
  ↓
[Phase 2 Cleaning] → + Derived Stats (D) + Outlier Flags (E)
  ↓
                    ┌─────────────────┐
                    │                 │
         ┌──────────▼──────────┐      │
         │  Poisson Training   │      │
         │  (A + B only)       │      │
         └──────────┬──────────┘      │
                    │                 │
         ┌──────────▼──────────┐      │
         │  Poisson Output     │      │
         └──────────┬──────────┘      │
                    │                 │
         ┌──────────▼──────────┐      │
         │  Blending          │      │
         │  (Poisson + Market)│      │
         └──────────┬──────────┘      │
                    │                 │
         ┌──────────▼──────────┐      │
         │  Calibration       │      │
         │  (Poisson Output)  │      │
         └──────────┬──────────┘      │
                    │                 │
         ┌──────────▼──────────┐      │
         │  Probability Sets  │      │
         │  A-G               │      │
         └────────────────────┘      │
                    │                 │
         ┌──────────▼──────────┐      │
         │  Analysis          │      │
         │  (All Features)    │      │
         └────────────────────┘      │
```

## Compliance Checklist

- ✅ Poisson model uses only Core + Temporal
- ✅ Market data never affects Poisson training
- ✅ Phase 2 features excluded from Poisson
- ✅ Blending uses Poisson + Market (not outcomes)
- ✅ Calibration uses Poisson output (not raw odds)
- ✅ Heuristic sets explicitly labeled
- ✅ Feature boundaries documented and enforced


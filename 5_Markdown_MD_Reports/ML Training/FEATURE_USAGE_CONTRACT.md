# FEATURE USAGE CONTRACT

Football Probability Engine

## 1. Purpose

This contract defines **which features are allowed to feed which models**.

Its purpose is to:

- prevent feature leakage
- preserve probabilistic correctness
- enforce methodological honesty
- guarantee auditability

This contract is **non-negotiable**.

---

## 2. Feature Categories

All features fall into exactly one of the following categories.

### A. Core Match Data

- Home team ID
- Away team ID
- Match date
- Home goals
- Away goals

### B. Temporal Metadata

- Match date
- Derived age / decay weights (ξ)

### C. Market Data

- Odds (home/draw/away)
- Implied probabilities
- Overround

### D. Derived Match Statistics

- Total goals
- Goal difference
- High-scoring indicators

### E. Outlier / Heuristic Flags

- Extreme odds indicators
- Mismatch flags
- Draw probability buckets
- Entropy modifiers

---

## 3. Model-Level Feature Permissions

### 3.1 Poisson / Dixon–Coles Model

**ALLOWED**

- Core Match Data (A)
- Temporal Metadata (B)

**EXPLICITLY FORBIDDEN**

- Market Data (C)
- Derived Match Statistics (D)
- Outlier / Heuristic Flags (E)

> Rationale:  
> The Poisson model estimates *goal-generation processes*, not market behavior.

---

### 3.2 Calibration Layer

**ALLOWED**

- Poisson output probabilities
- Actual match outcomes
- Temporal ordering

**FORBIDDEN**

- Raw odds
- Heuristic probability distortions

> Calibration corrects probability mapping, not signal generation.

---

### 3.3 Blending / Market Combination

**ALLOWED**

- Poisson probabilities
- Market implied probabilities
- Overround-adjusted odds

**FORBIDDEN**

- Match outcomes (post-hoc)
- Goal counts

> Blending treats the market as a **signal**, not an oracle.

---

### 3.4 Heuristic Probability Sets

**ALLOWED**

- Any probabilistic output
- Entropy manipulation
- Draw boosts
- Temperature scaling

**RESTRICTIONS**

- Must be explicitly labeled as *heuristic*
- Must never be treated as calibrated probabilities
- Must never be used for model evaluation

---

## 4. Evaluation & Metrics Rules

### Probability-correct evaluation (ONLY)

- Brier Score
- Log Loss
- Reliability curves

### Diagnostic metrics (SECONDARY)

- Accuracy
- Hit rate
- Confusion matrices

Diagnostic metrics must never drive:

- training decisions
- calibration decisions
- model promotion

---

## 5. Frontend Enforcement Rules

The frontend must:

- Clearly label which features feed which outputs
- Prevent heuristic sets from being selected by default
- Prevent heuristic sets from being exported as probabilities
- Display warnings when heuristic outputs are viewed

---

## 6. Feature Leakage Prevention

The system must never allow:

- Market odds to influence Poisson parameters
- Outcome-derived features to leak into training
- Heuristic flags to affect calibration
- Post-event information to affect prior probabilities

Violations invalidate all downstream results.

---

## 7. Determinism Guarantee

Given:

- identical feature inputs
- identical model versions
- identical configuration

The system must produce identical probabilities.

---

## 8. Compliance Statement

This feature usage contract ensures:

- methodological integrity
- statistical correctness
- audit defensibility
- long-horizon stability

Any deviation must be explicitly documented and approved.


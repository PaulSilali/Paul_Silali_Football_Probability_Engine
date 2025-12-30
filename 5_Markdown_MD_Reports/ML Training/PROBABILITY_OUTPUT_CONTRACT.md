# PROBABILITY OUTPUT CONTRACT

Football Jackpot Probability Engine

## 1. Purpose

This contract defines which outputs of the system are
**probability-correct**, which are **heuristic**, and how they
MUST be interpreted.

Misuse of outputs is explicitly prevented by design.

---

## 2. Probability Sets Classification

| Set | Calibrated | Heuristic | Allowed for Decision Support |
|-----|------------|-----------|------------------------------|
| A   | ✅         | ❌        | ✅                            |
| B   | ✅         | ❌        | ✅                            |
| C   | ✅         | ❌        | ✅                            |
| D   | ❌         | ✅        | ❌                            |
| E   | ❌         | ✅        | ❌                            |
| F   | ✅         | ❌        | ✅                            |
| G   | ✅         | ❌        | ✅                            |

---

## 3. Calibration Scope

- Calibration is **marginal only**
- Outcomes (H/D/A) are calibrated independently
- Renormalization preserves simplex but does NOT guarantee joint calibration

This limitation is explicit and intentional.

---

## 4. Heuristic Outputs

Sets D and E:

- Are intentional distortions
- Exist for exploratory or jackpot-survival strategies
- MUST NOT be presented as calibrated probabilities
- MUST be visually and programmatically labeled as heuristic

---

## 5. Frontend Enforcement Rules

The frontend MUST:

- Visually distinguish calibrated vs heuristic sets
- Disable export / default selection for heuristic sets
- Display warnings when heuristic sets are selected

---

## 6. Audit Guarantees

For every probability shown, the system can identify:

- model version
- probability set
- calibration status
- heuristic flag

This ensures full traceability.

---

## 7. Compliance Statement

The system prioritizes:

probability correctness > hit rate > narrative appeal

Heuristic outputs are provided transparently and never misrepresented.


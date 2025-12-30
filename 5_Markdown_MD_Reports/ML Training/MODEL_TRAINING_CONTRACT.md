# MODEL TRAINING CONTRACT

Football Probability Engine

## 1. Purpose

This document defines the **non-negotiable guarantees** provided by the
model training subsystem.

The system is designed for:

- probability correctness
- auditability
- deterministic reproducibility
- long-horizon stability

It is **not** a prediction tipster.

---

## 2. Model Class

### Primary Model

- Poisson goal model with Dixon–Coles correction

### Explicit Exclusions

- No neural networks
- No stochastic optimizers
- No opaque binaries

---

## 3. Training Methodology

### Estimation

- Team attack/defense: iterative proportional fitting
- Home advantage: weighted residual estimation
- Dixon–Coles rho: maximum likelihood optimization

> This is a **likelihood-consistent hybrid estimator**, not joint MLE.

---

## 4. Determinism Guarantees

Training is deterministic given:

- identical match dataset
- identical decay rate
- identical initial parameters
- identical code version

No randomness is permitted.

---

## 5. Data Integrity

Each training run records:

- SHA-256 hash of training data
- leagues and seasons used
- date bounds
- match count

Any change in data produces a different hash.

---

## 6. Validation Rules

- All validation splits are **time-ordered**
- No future data is allowed in training
- Metrics reported:
  - Brier Score (primary)
  - Log Loss (primary)
  - Accuracy (diagnostic only)

---

## 7. Normalization Invariants

The following constraints are enforced:

- mean attack = 1.0
- mean defense = 1.0

Normalization method:

- post-iteration scaling

---

## 8. Model Lifecycle

### States

- training
- active
- archived
- failed

### Rules

- Only **one active model per model_type**
- New activation archives the previous model
- All transitions are transactional

---

## 9. Audit Requirements

For every prediction, the system can identify:

- exact model version
- training run ID
- data hash
- parameters used

Reproduction is guaranteed.

---

## 10. Compliance Statement

This system is designed to be:

- regulator-defensible
- explainable end-to-end
- resistant to narrative bias

Probability correctness is prioritized over hit rate.


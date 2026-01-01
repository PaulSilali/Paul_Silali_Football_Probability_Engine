# PROBABILITY_OUTPUT_CONTRACT_V2

## Purpose

Define probability outputs that are calibrated, uncertainty-aware,
and regulator-defensible.

This contract extends the original probability output contract with
uncertainty control mechanisms (temperature scaling and entropy-weighted blending)
to prevent overconfidence and improve Log Loss.

---

## Output Structure (per fixture)

### Core Probabilities

- `homeWinProbability` ∈ [0, 1]
- `drawProbability` ∈ [0, 1]
- `awayWinProbability` ∈ [0, 1]

**Constraints:**
- Sum = 1.000 (±0.001 tolerance)
- No value < 1e-6
- No value > 0.99 (extreme predictions are capped)

### Uncertainty Metadata (MANDATORY for Set B)

For Set B (Market-Aware), the following metadata is included:

- `entropy`: Shannon entropy of the probability distribution (bits)
- `alphaEffective`: Adaptive blend weight actually used (0.15-0.75)
- `temperature`: Softening parameter applied (typically 1.0-1.5)
- `modelEntropy`: Normalized entropy of model predictions before blending (0-1)

**Example:**
```json
{
  "homeWinProbability": 45.2,
  "drawProbability": 28.5,
  "awayWinProbability": 26.3,
  "entropy": 1.523,
  "alphaEffective": 0.42,
  "temperature": 1.25,
  "modelEntropy": 0.71
}
```

---

## Interpretation Rules

### Entropy

- **High entropy** (≈1.0 normalized) → High uncertainty, model is uncertain
- **Low entropy** (<0.5 normalized) → Low uncertainty, model is overconfident

### Alpha Effective

- **Low alpha** (<0.3) → Market dominates (model was overconfident)
- **High alpha** (>0.6) → Model dominates (model was appropriately uncertain)

### Temperature

- **T = 1.0** → No softening (original probabilities)
- **T > 1.0** → Conservative softening (reduces overconfidence)
- **T ≈ 1.2-1.3** → Typical learned value

---

## Design Guarantees

### Deterministic

- Same inputs → same outputs
- No randomness
- Fully reproducible

### Probability-Correct

- Probabilities sum to 1.0
- No probability mass leakage
- Proper normalization

### Uncertainty-Aware

- Overconfident predictions are softened
- Low-entropy models defer to market
- High-entropy models retain signal

### Auditable

- All transformations are explicit
- Temperature and alpha are stored
- Entropy is tracked per prediction

---

## Explicitly Forbidden

- Outcome-based probability tuning
- ML-derived blending (beyond learned temperature)
- Hidden confidence inflation
- Non-auditable heuristics
- Temperature < 1.0 (never sharpen probabilities)
- Alpha outside [0.15, 0.75] bounds

---

## Compliance Notes

### Regulator-Defensible

- All parameters are learned on validation data only
- No outcome-based optimization
- Transparent uncertainty control

### Production-Ready

- Temperature is learned during training
- Entropy is monitored for drift
- Alerts trigger on entropy collapse

### Backward Compatible

- Set A (Pure Model) unchanged
- Sets C-G unchanged
- Only Set B enhanced with uncertainty metadata

---

## Expected Improvements

After implementing this contract:

| Metric | Before | After |
|--------|--------|-------|
| Poisson Log Loss | ~1.43 | ~1.20 |
| Blending Log Loss | ~1.75 | ~1.10-1.15 |
| Calibrated Log Loss | ~1.00 | ~0.95-0.98 |
| Entropy Collapse | Frequent | Rare |

---

## Version History

- **V1**: Original probability output contract
- **V2**: Added uncertainty control (temperature scaling, entropy-weighted blending)

---

## Related Documents

- `BLENDING_V2_CONTRACT.md`: Detailed blending algorithm specification
- `MODEL_TRAINING_CONTRACT.md`: Training methodology and guarantees
- `CALIBRATION_WORKFLOW.md`: Calibration model training workflow


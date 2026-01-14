# Draw Probability Model Contract

## Purpose

Adjust draw probability using structural, long-horizon signals without modifying team strength estimates.

This model treats draw as a first-class structural outcome, distinct from home/away win probabilities which are derived from goal-expectancy models.

## Design Principles

1. **Draw-Only Adjustment**: Only draw probability is directly modified
2. **Home/Away Preservation**: Home and away probabilities are never independently boosted or penalized
3. **Probability Conservation**: Total probability always sums to 1.0 (enforced via renormalization)
4. **Deterministic**: All adjustments are deterministic and auditable
5. **Bounded**: Draw adjustments are bounded to prevent extreme values

## Inputs

### Base Probabilities (from Poisson/Dixon-Coles)
- `p_home_base`: Base home win probability
- `p_draw_base`: Base draw probability  
- `p_away_base`: Base away win probability

### Structural Signals
1. **League Draw Prior**: Historical draw rate per league/season
2. **Elo Symmetry**: Closeness of team Elo ratings (closer = higher draw probability)
3. **Head-to-Head**: Historical draw rate between specific teams (minimum 4 matches)
4. **Weather**: Weather conditions at match time (rain, wind, temperature)
5. **Fatigue**: Team rest days and congestion (less rest = higher draw probability)
6. **Referee**: Referee behavioral profile (control level affects draw rate)
7. **Odds Movement**: Market draw odds drift (positive drift = higher draw probability)

## Rules

### Adjustment Process

1. **Compute Draw Multiplier**: Multiply all structural signals
   ```
   multiplier = league_prior × elo_symmetry × h2h_factor × 
                weather_factor × fatigue_factor × referee_factor × 
                odds_drift_factor
   ```
   Bounded: [0.75, 1.35]

2. **Adjust Draw Probability**:
   ```
   p_draw_adj = clip(p_draw_base × multiplier, 0.12, 0.38)
   ```

3. **Renormalize Home/Away**:
   ```
   remaining_prob = 1.0 - p_draw_adj
   scale = remaining_prob / (p_home_base + p_away_base)
   p_home_final = p_home_base × scale
   p_away_final = p_away_base × scale
   ```

### Bounds

- **Draw Probability**: [0.12, 0.38]
- **Draw Multiplier**: [0.75, 1.35]
- **Individual Component Factors**: Varies by component (see code)

### Missing Data Handling

- Missing data → component factor = 1.0 (neutral)
- Low sample H2H (< 4 matches) → ignored (factor = 1.0)
- Extreme values → clipped to bounds

## Calibration

### Draw-Only Isotonic Calibration

After structural adjustment, draw probabilities are calibrated using isotonic regression:

- Trains on: `(p_draw_predicted, is_draw_actual)`
- Outputs: Calibrated draw probability
- Evaluated using: Brier score (draw-only), reliability curve

### Validation Metrics

- **Draw Brier Score**: Lower is better (0 = perfect, 1 = worst)
- **Draw Reliability**: Calibration curve for draw probabilities
- **Coverage Diagnostics**: Expected vs observed draw frequency

## Failure Modes

### Missing Data
- **Behavior**: Component factor defaults to 1.0 (neutral)
- **Impact**: Minimal - other components still apply
- **Audit**: Logged in `draw_components` metadata

### Low Sample H2H
- **Behavior**: H2H factor = 1.0 (ignored)
- **Threshold**: Minimum 4 matches required
- **Rationale**: Prevents noise from small samples

### Extreme Values
- **Behavior**: Clipped to bounds
- **Bounds**: See "Bounds" section above
- **Rationale**: Prevents unrealistic probabilities

### Database Errors
- **Behavior**: Fallback to base probabilities
- **Impact**: System continues with unadjusted probabilities
- **Logging**: Warning logged, no exception raised

## Auditability

### Prediction Metadata

Each prediction logs:

```json
{
  "probabilities": {
    "home": 0.36,
    "draw": 0.29,
    "away": 0.35
  },
  "drawStructuralComponents": {
    "league_prior": 1.12,
    "elo_symmetry": 1.08,
    "h2h": 1.04,
    "weather": 1.02,
    "fatigue": 1.05,
    "referee": 0.98,
    "odds_drift": 1.06,
    "total_multiplier": 1.35
  }
}
```

### Audit Trail

- All adjustments are logged
- Component values are stored in prediction metadata
- Base probabilities are preserved (not overwritten)
- Renormalization is deterministic and verifiable

## Regulatory Compliance

### Explainability

- **No Black Box**: All adjustments are explicit and logged
- **Component Transparency**: Each factor is visible in metadata
- **Deterministic**: Same inputs → same outputs (no randomness)

### Probability Correctness

- **Sum to 1.0**: Enforced at every step
- **Bounded**: All probabilities within valid ranges
- **Calibrated**: Validated against historical outcomes

### Team Strength Preservation

- **Home/Away Ordering**: Relative team strength ordering is preserved
- **No Direct Modification**: Home/away never receive external signals
- **Proportional Scaling**: Home/away change only through renormalization

## Integration Points

### Upstream
- Poisson/Dixon-Coles base model
- Market odds blending (if applicable)

### Downstream
- Probability set generation (Sets A-J)
- Isotonic calibration
- Prediction persistence

### Parallel Systems
- Draw model (Poisson-based draw calculation)
- Draw prior injection (league-level adjustment)

## Testing Requirements

### Unit Tests (Mandatory)

1. **Probability Sum**: `assert abs(sum(probs) - 1.0) < 1e-6`
2. **Home/Away Ordering**: Relative ordering preserved
3. **Draw Bounds**: `assert 0.12 <= p_draw <= 0.38`
4. **Missing Data**: Neutral behavior (multiplier = 1.0)
5. **H2H Threshold**: Low sample ignored

### Integration Tests

1. **End-to-End**: Full prediction pipeline with draw adjustment
2. **Calibration**: Draw-only isotonic calibration
3. **Persistence**: Metadata stored correctly

### Validation Tests

1. **Brier Score**: Draw-only Brier score improvement
2. **Reliability**: Calibration curve validation
3. **Coverage**: Expected vs observed draw frequency

## Version History

- **v1.0** (2025-01-27): Initial implementation
  - League priors
  - Elo symmetry
  - H2H factors
  - Weather, fatigue, referee, odds movement

## References

- Dixon-Coles model: Base probability calculation
- Isotonic regression: Calibration method
- Brier score: Validation metric
- Probability theory: Renormalization principles


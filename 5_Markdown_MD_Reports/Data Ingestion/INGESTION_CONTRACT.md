# INGESTION CONTRACT

Football Probability Engine

## 1. Purpose

This contract defines the **rules, guarantees, and constraints** of the data ingestion layer.

The ingestion layer is responsible for:

- safely importing raw football match data
- enforcing minimum structural validity
- preserving raw informational content
- recording a complete audit trail

The ingestion layer is **not** responsible for:

- model feature engineering
- probability estimation
- calibration
- heuristic manipulation

---

## 2. Accepted Input Formats

### Supported formats

- CSV (UTF-8 encoded)
- Optional Parquet (internal use only)

### Required semantic fields (case-insensitive)

At least the following must be present **per row**:

| Concept | Accepted Column Names |
|---------|----------------------|
| Match date | `Date`, `match_date` |
| Home team | `HomeTeam`, `home_team` |
| Away team | `AwayTeam`, `away_team` |
| Home goals | `FTHG`, `home_goals` |
| Away goals | `FTAG`, `away_goals` |

Rows missing any of these are **discarded**.

---

## 3. Optional Market Data

If present, the following columns are accepted:

| Concept | Examples |
|---------|----------|
| Home odds | `AvgH`, `odds_home` |
| Draw odds | `AvgD`, `odds_draw` |
| Away odds | `AvgA`, `odds_away` |

### Ingestion behavior

- Odds are converted to **implied probabilities**
- Overround is **removed via normalization**
- Market data is treated as **informational only**

Market data **never directly affects model training**.

---

## 4. Cleaning Integration

### Phase 1 Cleaning (MANDATORY)

Applied during ingestion:

- Drop columns with excessive missingness
- Remove rows with invalid or missing dates
- Remove rows with missing critical fields
- Preserve all remaining raw information

### Phase 2 Cleaning (OPTIONAL)

May be applied if explicitly enabled:

- Feature creation
- Odds-derived features
- Outlier indicators

Phase 2 outputs **do not affect Poisson model training**.

---

## 5. Deduplication Rules

A match is considered duplicate if all are equal:

- match date
- home team (resolved ID)
- away team (resolved ID)

Duplicates are ignored, not overwritten.

---

## 6. Team Resolution Rules

- Team names are resolved deterministically
- Alias mapping and fuzzy matching are conservative
- If a team cannot be resolved, the match is skipped
- Skipped matches are logged

No team identifiers are invented.

---

## 7. Audit Logging

Each ingestion batch records:

- ingestion timestamp
- source file name
- number of rows processed
- number of rows skipped
- number of rows inserted
- cleaning statistics
- error summaries (truncated)

Failures do **not** corrupt existing data.

---

## 8. Determinism Guarantee

Given identical input files and configuration:

- the same matches will be ingested
- the same records will be skipped
- the same implied probabilities will be computed

No randomness is permitted.

---

## 9. Non-Goals (Explicit Exclusions)

The ingestion layer must never:

- infer outcomes
- modify goal counts
- apply model priors
- apply calibration
- apply heuristics

All such logic belongs to downstream layers.

---

## 10. Compliance Statement

This ingestion pipeline is designed to be:

- deterministic
- auditable
- reproducible
- regulator-defensible

Raw data integrity is preserved at all times.


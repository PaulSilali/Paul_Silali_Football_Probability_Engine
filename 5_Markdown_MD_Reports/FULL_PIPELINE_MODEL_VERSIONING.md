# Full Pipeline Training - Model Versioning Explained

## Overview

When you click **"Train Full Pipeline"**, the system trains models in a sequential chain, where each step uses the **newly created model** from the previous step. This ensures all models in the pipeline are aligned and use the latest versions.

## Training Sequence

```
Step 1: Train Poisson Model
   ↓ (creates new Poisson model, archives old one)
Step 2: Train Blending Model
   ↓ (uses NEW Poisson model from Step 1)
   ↓ (creates new Blending model, archives old one)
Step 3: Train Calibration Model
   ↓ (uses NEW Blending model from Step 2)
   ↓ (creates new Calibration model, archives old one)
```

**Note:** Draw Model is **NOT** part of the full pipeline because:
- Draw model is a **deterministic computation** (not a trained model)
- It uses outputs from Poisson/Dixon-Coles models at inference time
- Draw **calibration** can be trained separately if needed

## How Model Versioning Works

### 1. **Poisson Model Training**

**What happens:**
- Archives all previously active Poisson models (`status = 'archived'`)
- Creates a new Poisson model with version: `poisson-YYYYMMDD-HHMMSS`
- Sets the new model as `status = 'active'`
- Returns `modelId` and `version` to the next step

**Code:**
```python
# Archive old models
self.db.query(Model).filter(
    Model.model_type == 'poisson',
    Model.status == ModelStatus.active
).update({"status": ModelStatus.archived})

# Create new model
version = f"poisson-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
model = Model(
    version=version,
    model_type='poisson',
    status=ModelStatus.active,
    ...
)
```

### 2. **Blending Model Training**

**What happens:**
- **Uses the NEW Poisson model** from Step 1 (via `poisson_model_id`)
- Archives all previously active Blending models
- Creates a new Blending model with version: `blending-YYYYMMDD-HHMMSS`
- Stores reference to the Poisson model in `model_weights['poisson_model_id']`
- Sets the new model as `status = 'active'`
- Returns `modelId` and `version` to the next step

**Code:**
```python
# Uses the newly trained Poisson model
poisson_result = self.train_poisson_model(...)  # Step 1

# Step 2: Train blending with NEW Poisson model
blending_result = self.train_blending_model(
    poisson_model_id=poisson_result['modelId'],  # ← Uses NEW model
    ...
)
```

### 3. **Calibration Model Training**

**What happens:**
- **Uses the NEW Blending model** from Step 2 (via `base_model_id`)
- Archives all previously active Calibration models
- Creates a new Calibration model with version: `calibration-YYYYMMDD-HHMMSS`
- Stores reference to the Blending model in `model_weights['base_model_id']`
- Sets the new model as `status = 'active'`

**Code:**
```python
# Step 3: Train calibration with NEW Blending model
calibration_result = self.train_calibration_model(
    base_model_id=blending_result['modelId'],  # ← Uses NEW model
    ...
)
```

## Key Points

### ✅ **Always Uses Latest Models**

The pipeline **always uses the newly created models**, not old ones:

1. **Poisson → Blending**: Blending uses the Poisson model just created
2. **Blending → Calibration**: Calibration uses the Blending model just created

### ✅ **Automatic Archiving**

Each training step automatically archives the previous active model:

- Old models are **not deleted** (preserved for history)
- Only **one active model** per type exists at any time
- You can query archived models for comparison/rollback

### ✅ **Model Chain Integrity**

The model chain is always consistent:

```
Active Calibration Model
  └─> References: Active Blending Model (ID: X)
        └─> References: Active Poisson Model (ID: Y)
```

### ✅ **Version Tracking**

Each model gets a unique version string:
- `poisson-20250115-143022`
- `blending-20250115-143045`
- `calibration-20250115-143108`

## What Happens on Multiple Runs?

### Scenario: Train Full Pipeline Twice

**First Run:**
```
Poisson v1 (active) → Blending v1 (active) → Calibration v1 (active)
```

**Second Run:**
```
Poisson v1 (archived)
Poisson v2 (active) → Blending v1 (archived)
                    → Blending v2 (active) → Calibration v1 (archived)
                                          → Calibration v2 (active)
```

**Result:**
- All v1 models are archived
- All v2 models are active
- v2 models reference each other in the chain

## Database State After Full Pipeline

```sql
-- Active models (one of each type)
SELECT * FROM models WHERE status = 'active';
-- Returns: 1 Poisson, 1 Blending, 1 Calibration

-- Model chain
SELECT 
    c.id AS calibration_id,
    c.version AS calibration_version,
    c.model_weights->>'base_model_id' AS blending_id,
    b.model_weights->>'poisson_model_id' AS poisson_id
FROM models c
LEFT JOIN models b ON (c.model_weights->>'base_model_id')::int = b.id
WHERE c.model_type = 'calibration' AND c.status = 'active';
```

## Benefits of This Approach

1. **Consistency**: All models in the chain are trained on the same data
2. **Version Control**: Each run creates a new versioned chain
3. **Rollback Capability**: Archived models can be reactivated if needed
4. **No Stale References**: Models always reference the correct upstream version
5. **Reproducibility**: Each version is timestamped and traceable

## Important Notes

### ⚠️ **Individual Model Training**

If you train models individually (not full pipeline):
- **Poisson**: Creates new version, archives old
- **Blending**: Uses **current active** Poisson (may be old if you didn't retrain)
- **Calibration**: Uses **current active** Blending (may be old if you didn't retrain)

**Recommendation**: Use "Train Full Pipeline" to ensure all models are aligned.

### ⚠️ **Draw Model**

The Draw Model is **not part of the full pipeline**:
- It's a deterministic computation (no training needed)
- Uses outputs from Poisson/Dixon-Coles models
- Can be trained separately for draw-only calibration

## Summary

**When you click "Train Full Pipeline":**

1. ✅ Creates **new versions** of all models
2. ✅ Uses **latest models** in the chain (not old ones)
3. ✅ Archives **old models** (preserves history)
4. ✅ Maintains **model chain integrity**
5. ✅ Each model references the **correct upstream version**

The system ensures you always have a **coherent, versioned model chain** where each component uses the latest upstream model.


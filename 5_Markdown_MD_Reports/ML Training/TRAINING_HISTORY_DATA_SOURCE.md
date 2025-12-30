# Training History Data Source

## Database Table

**Table Name:** `training_runs`

**Schema:** `3_Database_Football_Probability_Engine/3_Database_Football_Probability_Engine.sql`

---

## Data Flow

```
Frontend (MLTraining.tsx)
    ↓
loadTrainingHistory() → apiClient.getTrainingHistory(50)
    ↓
GET /api/model/training-history?limit=50
    ↓
Backend (app/api/model.py)
    ↓
db.query(TrainingRun).order_by(TrainingRun.started_at.desc()).limit(limit)
    ↓
PostgreSQL Database
    ↓
SELECT * FROM training_runs ORDER BY started_at DESC LIMIT 50
```

---

## Table Structure

### **`training_runs` Table**

| Column | Type | Description | Frontend Display |
|--------|------|-------------|------------------|
| `id` | Integer (PK) | Unique training run ID | Not displayed |
| `model_id` | Integer (FK) | Reference to `models.id` | Not displayed |
| `run_type` | String | Type of training run (`poisson`, `blending`, `calibration`) | **Run Type** column |
| `status` | Enum(ModelStatus) | Status (`active`, `archived`, `failed`, `training`) | **Status** column |
| `started_at` | DateTime | When training started | **Date** column |
| `completed_at` | DateTime | When training completed | Used for **Duration** calculation |
| `match_count` | Integer | Number of matches used for training | **Matches** column |
| `date_from` | Date | Start date filter | Not displayed |
| `date_to` | Date | End date filter | Not displayed |
| `brier_score` | Float | Brier score metric | **Brier Score** column |
| `log_loss` | Float | Log loss metric | **Log Loss** column |
| `validation_accuracy` | Float | Validation accuracy | Not displayed |
| `error_message` | Text | Error message if failed | Not displayed |
| `logs` | JSON | Training logs/metadata | Not displayed |
| `created_at` | DateTime | Record creation timestamp | Not displayed |

---

## Backend Endpoint

### **`GET /api/model/training-history`**

**File:** `2_Backend_Football_Probability_Engine/app/api/model.py` (lines 211-247)

**Query:**
```python
runs = db.query(TrainingRun).order_by(TrainingRun.started_at.desc()).limit(limit).all()
```

**Response Format:**
```json
{
  "success": true,
  "data": [
    {
      "id": "123",
      "modelId": "456",
      "runType": "poisson",
      "status": "active",
      "startedAt": "2025-12-29T10:00:00",
      "completedAt": "2025-12-29T10:05:00",
      "matchCount": 51836,
      "dateFrom": "2020-01-01",
      "dateTo": "2024-12-31",
      "brierScore": 0.182,
      "logLoss": 0.954,
      "validationAccuracy": 65.0,
      "errorMessage": null,
      "duration": 5.0
    }
  ],
  "count": 1
}
```

---

## Frontend Mapping

**File:** `1_Frontend_Football_Probability_Engine/src/pages/MLTraining.tsx` (lines 858-910)

| Backend Field | Frontend Display | Column |
|---------------|------------------|--------|
| `startedAt` | `formatDate(run.startedAt)` | **Date** |
| `runType` | `run.runType` (capitalized) | **Run Type** |
| `matchCount` | `run.matchCount.toLocaleString()` | **Matches** |
| `duration` | `Math.round(run.duration) + 'm'` | **Duration** |
| `status` | Badge with icon | **Status** |
| `brierScore` | `run.brierScore.toFixed(3)` | **Brier Score** |
| `logLoss` | `run.logLoss.toFixed(3)` | **Log Loss** |

---

## When Data is Inserted

Training runs are created in `model_training.py`:

**File:** `2_Backend_Football_Probability_Engine/app/services/model_training.py`

**Line 103-112:**
```python
# CREATE TRAINING RUN FIRST (for audit trail)
training_run = TrainingRun(
    run_type='poisson',
    status=ModelStatus.training,
    started_at=datetime.utcnow(),
    date_from=date_from,
    date_to=date_to,
)
self.db.add(training_run)
self.db.flush()
```

**After Training Completes (lines 146-153):**
```python
# Update training run with model ID and results
training_run.model_id = model.id
training_run.status = ModelStatus.completed
training_run.completed_at = datetime.utcnow()
training_run.match_count = len(match_data)
training_run.brier_score = metrics['brierScore']
training_run.log_loss = metrics['logLoss']
training_run.validation_accuracy = metrics.get('overallAccuracy', 65.0)
self.db.commit()
```

---

## SQL Query Equivalent

```sql
SELECT 
    id,
    model_id,
    run_type,
    status,
    started_at,
    completed_at,
    match_count,
    date_from,
    date_to,
    brier_score,
    log_loss,
    validation_accuracy,
    error_message,
    (completed_at - started_at) / 60.0 AS duration_minutes
FROM training_runs
ORDER BY started_at DESC
LIMIT 50;
```

---

## Summary

**Training History Data Source:**
- **Table:** `training_runs`
- **Backend Endpoint:** `GET /api/model/training-history`
- **Backend Model:** `TrainingRun` (SQLAlchemy)
- **Created By:** `ModelTrainingService.train_poisson_model()` (and other training methods)
- **Frontend:** `MLTraining.tsx` → `loadTrainingHistory()`

All data shown in the Training History table comes directly from the `training_runs` database table, with no mock data or hardcoded values.


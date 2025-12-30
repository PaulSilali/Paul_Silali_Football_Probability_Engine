# Model Storage and Output Structure

## 📊 **Model Storage Overview**

Trained models are stored in **two locations**:
1. **Database** (`models` table) - Metadata, metrics, and weights
2. **File System** (`Model/` folder) - Optional model artifacts (currently empty)

---

## 🗄️ **Database Storage**

### **Table: `models`**

All model information is stored in the PostgreSQL `models` table:

#### **Columns:**

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `version` | String | Unique version identifier (e.g., `poisson-20251229-100805`) |
| `model_type` | String | Type: `'poisson'`, `'blending'`, `'calibration'` |
| `status` | Enum | `active`, `archived`, `failed`, `training` |
| `training_started_at` | DateTime | When training started |
| `training_completed_at` | DateTime | When training completed |
| `training_matches` | Integer | Number of matches used for training |
| `training_leagues` | JSON | List of league codes used |
| `training_seasons` | JSON | List of seasons used |
| `decay_rate` | Float | Time decay parameter (ξ) |
| `blend_alpha` | Float | Blending weight (for blending models) |
| `brier_score` | Float | Brier Score metric |
| `log_loss` | Float | Log Loss metric |
| `draw_accuracy` | Float | Draw prediction accuracy (%) |
| `overall_accuracy` | Float | Overall prediction accuracy (%) |
| `model_weights` | JSON | **Team strengths and parameters** |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

#### **`model_weights` JSON Structure:**

```json
{
  "team_strengths": {
    "580": {
      "attack": 1.234,
      "defense": 0.876
    },
    "581": {
      "attack": 0.987,
      "defense": 1.123
    }
    // ... all teams
  },
  "home_advantage": 0.345,
  "rho": -0.128,
  "decay_rate": 0.0065,
  "training_date": "2025-12-29T10:08:05"
}
```

---

### **Table: `training_runs`**

Training history and execution logs:

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `model_id` | Integer | Foreign key to `models.id` |
| `run_type` | String | `'poisson'`, `'blending'`, `'calibration'`, `'full'` |
| `status` | Enum | `active`, `archived`, `failed`, `training` |
| `started_at` | DateTime | Start time |
| `completed_at` | DateTime | Completion time |
| `match_count` | Integer | Matches processed |
| `date_from` | Date | Training data start date |
| `date_to` | Date | Training data end date |
| `brier_score` | Float | Validation Brier Score |
| `log_loss` | Float | Validation Log Loss |
| `validation_accuracy` | Float | Validation accuracy (%) |
| `error_message` | Text | Error message if failed |
| `logs` | JSON | Additional training logs |

---

## 📁 **File System Structure**

### **Current Structure:**

```
2_Backend_Football_Probability_Engine/
├── Model/                          # Model artifacts folder (currently empty)
│   └── (future: saved model files)
├── data/
│   ├── 1_data_ingestion/          # Raw ingested data
│   │   └── batch_*/               # Batch folders
│   └── 2_Cleaned_data/            # Cleaned training data
│       ├── E0_Premier_League_all_seasons.csv
│       ├── E0_Premier_League_all_seasons.parquet
│       └── ...
└── app/
    ├── models/                     # Model implementations
    │   ├── dixon_coles.py         # Dixon-Coles prediction logic
    │   ├── calibration.py         # Calibration model
    │   └── probability_sets.py    # Probability set calculations
    └── services/
        ├── model_training.py       # Training orchestration
        └── poisson_trainer.py      # Actual training algorithm
```

### **Future Model Artifacts (Optional):**

If you want to save model files to disk, they would go in:

```
2_Backend_Football_Probability_Engine/Model/
├── poisson-20251229-100805/
│   ├── team_strengths.json        # Team attack/defense ratings
│   ├── parameters.json            # Model parameters (rho, home_advantage, etc.)
│   └── metadata.json              # Training metadata
├── blending-20251229-100810/
│   └── ...
└── calibration-20251229-100815/
    └── ...
```

**Note:** Currently, models are **only stored in the database**. The `Model/` folder exists but is empty. This is intentional - database storage is faster and more reliable for production use.

---

## 🔍 **How to Access Model Data**

### **1. Via API Endpoints:**

#### **Get Model Versions:**
```bash
GET /api/model/versions
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "version": "poisson-20251229-100805",
      "modelType": "poisson",
      "status": "active",
      "brierScore": 0.134,
      "logLoss": 0.867,
      "drawAccuracy": 58.2,
      "overallAccuracy": 67.3,
      "trainingMatches": 51836,
      "createdAt": "2025-12-29T10:08:05"
    }
  ]
}
```

#### **Get Training History:**
```bash
GET /api/model/training-history?limit=50
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "1",
      "modelId": "1",
      "runType": "poisson",
      "status": "active",
      "startedAt": "2025-12-29T10:08:04",
      "completedAt": "2025-12-29T10:08:05",
      "matchCount": 51836,
      "brierScore": 0.134,
      "logLoss": 0.867,
      "validationAccuracy": 67.3,
      "duration": 0.02  // minutes
    }
  ]
}
```

#### **Get Model Status:**
```bash
GET /api/model/status
```

---

### **2. Via Database Query:**

```sql
-- Get latest active model
SELECT * FROM models 
WHERE status = 'active' 
ORDER BY training_completed_at DESC 
LIMIT 1;

-- Get model weights (team strengths)
SELECT model_weights FROM models 
WHERE version = 'poisson-20251229-100805';

-- Get training history
SELECT * FROM training_runs 
ORDER BY started_at DESC 
LIMIT 10;
```

---

### **3. Via Python Code:**

```python
from app.db.session import SessionLocal
from app.db.models import Model, TrainingRun

db = SessionLocal()

# Get latest model
model = db.query(Model).filter(
    Model.status == ModelStatus.active
).order_by(Model.training_completed_at.desc()).first()

# Access team strengths
team_strengths = model.model_weights['team_strengths']
home_advantage = model.model_weights['home_advantage']
rho = model.model_weights['rho']

# Get training run
training_run = db.query(TrainingRun).filter(
    TrainingRun.model_id == model.id
).first()
```

---

## 📊 **What Gets Stored**

### **After Training, You Get:**

1. **Model Record** (`models` table):
   - Version identifier
   - Training metadata (matches, leagues, seasons)
   - Validation metrics (Brier Score, Log Loss, Accuracy)
   - Model parameters (decay_rate, home_advantage, rho)

2. **Team Strengths** (`model_weights` JSON):
   - Attack rating for each team
   - Defense rating for each team
   - Used for predictions

3. **Training Run Record** (`training_runs` table):
   - Execution log
   - Validation metrics
   - Duration and timestamps

---

## 🎯 **Summary**

| Storage Location | What's Stored | Access Method |
|-----------------|---------------|---------------|
| **Database (`models`)** | Model metadata, metrics, team strengths | API, SQL, Python |
| **Database (`training_runs`)** | Training history, logs | API, SQL, Python |
| **File System (`Model/`)** | Currently empty (optional) | N/A |

**Primary Storage:** Database (PostgreSQL)
**Model Weights:** Stored as JSON in `models.model_weights`
**Team Strengths:** Included in `model_weights` JSON

---

**Status:** ✅ **Models stored in database, accessible via API**


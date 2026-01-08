# Automated Pipeline Guide

## 🎯 Overview

The automated pipeline system checks for missing teams or missing training data, automatically downloads missing data, retrains the model, and optionally recomputes probabilities.

---

## ✅ Enhanced Validation

### **What Changed?**

The validation endpoint now checks **both**:
1. **Team Validation** - Does team exist in `teams` table?
2. **Model Training** - Does team have training data in model's `team_strengths`?

### **API Endpoint**

**Endpoint:** `POST /api/validation/team`

**Request:**
```json
{
  "teamName": "Arsenal",
  "leagueId": 1,
  "checkTraining": true  // NEW: Check model training status
}
```

**Response (Valid + Trained):**
```json
{
  "success": true,
  "data": {
    "isValid": true,
    "normalizedName": "arsenal",
    "confidence": 0.95,
    "teamId": 580,
    "isTrained": true,        // NEW
    "strengthSource": "model"  // NEW: "model", "database", or "default"
  }
}
```

**Response (Valid but NOT Trained):**
```json
{
  "success": true,
  "data": {
    "isValid": true,
    "normalizedName": "arsenal",
    "teamId": 580,
    "isTrained": false,           // Team exists but no training data
    "strengthSource": "database"  // Falls back to DB ratings
  }
}
```

**Response (Invalid):**
```json
{
  "success": true,
  "data": {
    "isValid": false,
    "suggestions": ["Arsenal FC", "Arsenal", "Arsenal London"]
  }
}
```

### **Batch Validation**

**Endpoint:** `POST /api/validation/team/batch`

**Request:**
```json
[
  {
    "teamName": "Arsenal",
    "leagueId": 1,
    "checkTraining": true
  },
  {
    "teamName": "Chelsea",
    "leagueId": 1,
    "checkTraining": true
  }
]
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "teamName": "Arsenal",
      "isValid": true,
      "isTrained": true,
      "strengthSource": "model"
    },
    {
      "teamName": "Chelsea",
      "isValid": true,
      "isTrained": false,
      "strengthSource": "database"
    }
  ]
}
```

---

## 🔄 Automated Pipeline

### **What It Does**

The automated pipeline performs these steps:

1. **Check Status** - Validates teams and checks training status
2. **Create Missing Teams** - Creates teams that don't exist in DB
3. **Download Missing Data** - Downloads historical match data for untrained teams
4. **Retrain Model** - Retrains the Poisson model with new data
5. **Recompute Probabilities** (optional) - Recomputes probabilities for a jackpot

### **API Endpoint**

**Endpoint:** `POST /api/pipeline/run`

**Request:**
```json
{
  "team_names": ["Arsenal", "Chelsea", "New Team"],
  "league_id": 1,
  "auto_download": true,      // Automatically download missing data
  "auto_train": true,         // Automatically retrain model
  "auto_recompute": false,    // Recompute probabilities (requires jackpot_id)
  "jackpot_id": null,         // Required if auto_recompute=true
  "seasons": ["2324", "2223"], // Optional: specific seasons to download
  "max_seasons": 7            // Number of seasons if seasons not specified
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "taskId": "pipeline-1704067200-abc12345",
    "status": "queued",
    "message": "Pipeline started. Use /api/pipeline/status/{taskId} to check status."
  }
}
```

### **Check Pipeline Status**

**Endpoint:** `GET /api/pipeline/status/{task_id}`

**Response:**
```json
{
  "success": true,
  "data": {
    "taskId": "pipeline-1704067200-abc12345",
    "status": "completed",
    "progress": 100,
    "phase": "Complete",
    "startedAt": "2024-01-01T10:00:00",
    "completedAt": "2024-01-01T10:15:00",
    "steps": {
      "status_check": {
        "validated_teams": ["Arsenal", "Chelsea"],
        "missing_teams": ["New Team"],
        "trained_teams": [580],
        "untrained_teams": [581]
      },
      "create_teams": {
        "created": ["New Team"],
        "skipped": [],
        "errors": []
      },
      "download_data": {
        "leagues_downloaded": [
          {
            "league_code": "E0",
            "seasons": ["2324", "2223"]
          }
        ],
        "total_matches": 1520,
        "errors": []
      },
      "train_model": {
        "success": true,
        "model_id": 42,
        "version": "poisson-20240101-100500"
      },
      "recompute_probabilities": {
        "skipped": true
      }
    }
  }
}
```

---

## 📊 Check Team Status (Without Running Pipeline)

**Endpoint:** `POST /api/pipeline/check-status`

**Request:**
```json
{
  "team_names": ["Arsenal", "Chelsea", "New Team"],
  "league_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "validated_teams": ["Arsenal", "Chelsea"],
    "missing_teams": ["New Team"],
    "trained_teams": [580],
    "untrained_teams": [581],
    "team_details": {
      "Arsenal": {
        "team_id": 580,
        "isValid": true,
        "isTrained": true,
        "league_code": "E0",
        "league_id": 1
      },
      "Chelsea": {
        "team_id": 581,
        "isValid": true,
        "isTrained": false,
        "league_code": "E0",
        "league_id": 1
      },
      "New Team": {
        "team_id": null,
        "isValid": false,
        "isTrained": false,
        "league_code": null,
        "league_id": 1
      }
    }
  }
}
```

---

## 🔽 Download Missing Data Only

**Endpoint:** `POST /api/pipeline/download-missing`

**Request:**
```json
{
  "team_names": ["Arsenal", "Chelsea"],
  "league_id": 1
}
```

**Query Parameters:**
- `seasons` (optional): List of seasons to download (e.g., `["2324", "2223"]`)
- `max_seasons` (optional): Number of seasons if not specified (default: 7)

**Response:**
```json
{
  "success": true,
  "data": {
    "leagues_downloaded": [
      {
        "league_code": "E0",
        "seasons": ["2324", "2223", "2122"]
      }
    ],
    "total_matches": 1520,
    "errors": []
  }
}
```

---

## 🎯 Use Cases

### **Use Case 1: Check Teams Before Creating Jackpot**

```python
# 1. Check status of all teams
response = requests.post("/api/pipeline/check-status", json={
    "team_names": ["Arsenal", "Chelsea", "Liverpool"],
    "league_id": 1
})

status = response.json()["data"]

# 2. If teams missing or untrained, run pipeline
if status["missing_teams"] or status["untrained_teams"]:
    pipeline_response = requests.post("/api/pipeline/run", json={
        "team_names": ["Arsenal", "Chelsea", "Liverpool"],
        "league_id": 1,
        "auto_download": True,
        "auto_train": True,
        "auto_recompute": False
    })
    
    task_id = pipeline_response.json()["data"]["taskId"]
    
    # 3. Wait for completion
    import time
    while True:
        status_response = requests.get(f"/api/pipeline/status/{task_id}")
        task_status = status_response.json()["data"]["status"]
        
        if task_status == "completed":
            break
        elif task_status == "failed":
            raise Exception("Pipeline failed")
        
        time.sleep(5)
```

### **Use Case 2: Validate Single Team with Training Check**

```python
response = requests.post("/api/validation/team", json={
    "teamName": "Arsenal",
    "leagueId": 1,
    "checkTraining": True
})

data = response.json()["data"]

if not data["isValid"]:
    print(f"Team not found. Suggestions: {data['suggestions']}")
elif not data["isTrained"]:
    print(f"Team exists but not trained. Strength source: {data['strengthSource']}")
    # Optionally trigger pipeline
else:
    print(f"Team validated and trained! ✅")
```

### **Use Case 3: Automatic Fix Before Probability Calculation**

```python
# In your jackpot creation flow:

# 1. Get all teams from fixtures
team_names = [fixture.home_team for fixture in fixtures] + \
             [fixture.away_team for fixture in fixtures]

# 2. Check status
status = check_teams_status(team_names, league_id)

# 3. If issues found, run pipeline automatically
if status["missing_teams"] or status["untrained_teams"]:
    run_pipeline(
        team_names=team_names,
        league_id=league_id,
        auto_download=True,
        auto_train=True,
        auto_recompute=False  # Will recompute when calculating probabilities
    )

# 4. Proceed with jackpot creation
# Probabilities will use trained strengths automatically
```

---

## 🔍 How It Works

### **Step-by-Step Process**

1. **Status Check**
   - Resolves each team name to database team
   - Checks if team exists in `teams` table
   - Checks if team_id exists in active model's `team_strengths`
   - Returns detailed status for each team

2. **Create Missing Teams**
   - Creates teams that don't exist in database
   - Uses `create_team_if_not_exists()` function
   - Assigns teams to specified league

3. **Download Missing Data**
   - Groups teams by league
   - Downloads historical match data for each league
   - Uses `DataIngestionService.ingest_from_football_data()`
   - Downloads last N seasons (default: 7)

4. **Retrain Model**
   - Trains Poisson model with new data
   - Includes all teams that now have matches
   - Stores team strengths in `model_weights['team_strengths']`

5. **Recompute Probabilities** (optional)
   - Triggers probability recalculation for a jackpot
   - Uses newly trained model strengths

---

## ⚙️ Configuration

### **Pipeline Options**

| Option | Default | Description |
|-------|---------|-------------|
| `auto_download` | `true` | Automatically download missing data |
| `auto_train` | `true` | Automatically retrain model after download |
| `auto_recompute` | `false` | Automatically recompute probabilities |
| `max_seasons` | `7` | Number of seasons to download |

### **Strength Source Priority**

The system uses strengths in this order:

1. **Model Strengths** (`strengthSource: "model"`)
   - From active Poisson model's `team_strengths`
   - **Best accuracy** ✅

2. **Database Ratings** (`strengthSource: "database"`)
   - From `teams.attack_rating` / `teams.defense_rating`
   - **Good accuracy** ⚠️

3. **Default Strengths** (`strengthSource: "default"`)
   - `attack = 1.0`, `defense = 1.0`
   - **Uniform probabilities** ❌

---

## 🚨 Error Handling

### **Common Errors**

1. **League ID Missing**
   - Error: "Cannot create teams: league_id required but not provided"
   - Solution: Provide `league_id` in request

2. **Download Failed**
   - Error: "Error downloading {league_code} season {season}"
   - Solution: Check data source availability, network connection

3. **Model Training Failed**
   - Error: "Model training failed: {error}"
   - Solution: Check database, ensure sufficient match data

### **Error Response Format**

```json
{
  "success": false,
  "error": "Error message",
  "data": {
    "steps": {
      "download_data": {
        "errors": [
          "Error downloading E0 season 2324: Connection timeout"
        ]
      }
    }
  }
}
```

---

## 📝 Best Practices

1. **Check Status First**
   - Use `/api/pipeline/check-status` before running full pipeline
   - Only run pipeline if teams are missing or untrained

2. **Batch Operations**
   - Use batch validation for multiple teams
   - More efficient than individual requests

3. **Monitor Progress**
   - Check pipeline status regularly
   - Handle errors appropriately

4. **League ID Required**
   - Always provide `league_id` when creating teams
   - Helps ensure teams are assigned correctly

5. **Seasons Configuration**
   - Specify `seasons` if you need specific data
   - Use `max_seasons` for automatic selection

---

## 🎯 Summary

✅ **Enhanced Validation** - Checks both team existence AND training status

✅ **Automated Pipeline** - Detects → Downloads → Trains → Recomputes

✅ **Flexible Options** - Control each step independently

✅ **Error Handling** - Comprehensive error reporting

✅ **Status Tracking** - Monitor pipeline progress

---

## 📚 Related Documentation

- [Validation vs Model Training](./VALIDATION_VS_MODEL_TRAINING.md)
- [Model Training Impact on Probabilities](./MODEL_TRAINING_IMPACT_ON_PROBABILITIES.md)
- [What Happens If Team Not Validated](./WHAT_HAPPENS_IF_TEAM_NOT_VALIDATED.md)


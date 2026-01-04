# Jackpot Results Input Format Guide

## Overview

There are **two main ways** to input jackpot results into the system:

1. **API Endpoint** - Using JSON format via REST API
2. **CSV File** - Upload CSV file with results

---

## Format 1: API Endpoint (JSON)

### Endpoint
```
POST /api/probabilities/{jackpot_id}/save-result
```

### Request Body Format

```json
{
  "name": "15M MIDWEEK JACKPOT - 22/11 Results",
  "description": "Optional description",
  "selections": {
    "A": {
      "1": "1",
      "2": "X",
      "3": "2",
      ...
    },
    "B": {
      "1": "X",
      "2": "1",
      ...
    }
  },
  "actual_results": {
    "1": "X",
    "2": "1",
    "3": "2",
    "4": "1",
    "5": "X",
    ...
  },
  "scores": {
    "A": {
      "correct": 10,
      "total": 15
    },
    "B": {
      "correct": 8,
      "total": 15
    }
  }
}
```

### Field Descriptions

#### `name` (Required)
- String: Name/identifier for this result set
- Example: `"15M MIDWEEK JACKPOT - 22/11 Results"`

#### `description` (Optional)
- String: Additional description or notes
- Example: `"Results from 22/11 midweek jackpot"`

#### `selections` (Required)
- Object: User's selections per probability set
- Format: `{"SET_ID": {"fixture_id": "result", ...}}`
- Set IDs: `"A"`, `"B"`, `"C"`, `"D"`, `"E"`, `"F"`, `"G"`, `"H"`, `"I"`, `"J"`
- Fixture IDs: String numbers (`"1"`, `"2"`, `"3"`, etc.) corresponding to `match_order` in `jackpot_fixtures`
- Results: `"1"` (Home Win), `"X"` (Draw), `"2"` (Away Win)

#### `actual_results` (Optional)
- Object: Actual match results
- Format: `{"fixture_id": "result", ...}`
- Fixture IDs: String numbers (`"1"`, `"2"`, `"3"`, etc.)
- Results: 
  - `"1"` or `"H"` = Home Win
  - `"X"` or `"D"` = Draw
  - `"2"` or `"A"` = Away Win

#### `scores` (Optional)
- Object: Calculated scores per set
- Format: `{"SET_ID": {"correct": number, "total": number}}`
- Automatically calculated if not provided

---

## Format 2: CSV File Upload

### CSV Format

```csv
Match,HomeTeam,AwayTeam,Result
1,Tottenham,Man Utd,X
2,Girona,Alaves,1
3,US Lecce,Hellas Verona,X
4,Hoffenheim,Leipzig,1
5,Espanyol,Villarreal,2
...
```

### CSV Column Descriptions

#### `Match` (Required)
- Integer: Match order number (1-15, corresponds to `match_order` in `jackpot_fixtures`)
- Example: `1`, `2`, `3`, etc.

#### `HomeTeam` (Required)
- String: Home team name
- Example: `"Tottenham"`, `"Girona"`, `"US Lecce"`

#### `AwayTeam` (Required)
- String: Away team name
- Example: `"Man Utd"`, `"Alaves"`, `"Hellas Verona"`

#### `Result` (Required)
- String: Match result
- Values: 
  - `"1"` or `"H"` = Home Win
  - `"X"` or `"D"` = Draw
  - `"2"` or `"A"` = Away Win
- Example: `"X"`, `"1"`, `"2"`

---

## Example: Complete JSON Request

Based on the "15M MIDWEEK JACKPOT RESULTS" from 22/11:

```json
{
  "name": "15M MIDWEEK JACKPOT - 22/11 Results",
  "description": "Results ended on 22/11 17:30",
  "selections": {
    "A": {
      "1": "1",
      "2": "2",
      "3": "2",
      "4": "1",
      "5": "X",
      "6": "2",
      "7": "1",
      "8": "2",
      "9": "1",
      "10": "1",
      "11": "2",
      "12": "X",
      "13": "2",
      "14": "X",
      "15": "2"
    }
  },
  "actual_results": {
    "1": "1",
    "2": "2",
    "3": "2",
    "4": "1",
    "5": "X",
    "6": "2",
    "7": "1",
    "8": "2",
    "9": "1",
    "10": "1",
    "11": "2",
    "12": "X",
    "13": "2",
    "14": "X",
    "15": "2"
  }
}
```

---

## Example: Complete CSV File

```csv
Match,HomeTeam,AwayTeam,Result
1,AUGSBURG,HAMBURG,1
2,WOLFSBURG,LEVERKUSEN,2
3,HEIDENHEIM,BORUSSIA (MG),2
4,FULHAM,SUNDERLAND,1
5,ACF FIORENTINA,JUVENTUS,X
6,1. FC COLOGNE,EINTRACHT FR,2
7,NEWCASTLE,MAN CITY,1
8,OSASUNA,REAL SOCIEDAD,2
9,RENNES,MONACO,1
10,NAPOLI,ATALANTA BC,1
11,HELLAS VERONA,PARMA,2
12,OVIEDO,RAYO VALLECANO,X
13,LEEDS,ASTON VILLA,2
14,NANTES,LORIENT,X
15,ST. PAULI,UNION BERLIN,2
```

---

## Result Value Mapping

| Input Value | Database Value | Meaning |
|------------|----------------|---------|
| `"1"` | `'H'` | Home Team Wins |
| `"X"` | `'D'` | Draw |
| `"2"` | `'A'` | Away Team Wins |
| `"H"` | `'H'` | Home Team Wins (alternative) |
| `"D"` | `'D'` | Draw (alternative) |
| `"A"` | `'A'` | Away Team Wins (alternative) |

**Note:** The system accepts both formats (`"1"/"X"/"2"` and `"H"/"D"/"A"`) and converts them internally.

---

## Database Storage

### Table: `saved_probability_results`

```sql
CREATE TABLE saved_probability_results (
    id SERIAL PRIMARY KEY,
    jackpot_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    description TEXT,
    selections JSONB NOT NULL,        -- {"A": {"1": "1", "2": "X"}, ...}
    actual_results JSONB,            -- {"1": "X", "2": "1", ...}
    scores JSONB,                    -- {"A": {"correct": 10, "total": 15}}
    model_version VARCHAR,
    total_fixtures INTEGER,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

### Table: `jackpot_fixtures` (Alternative)

You can also update fixtures directly:

```sql
UPDATE jackpot_fixtures 
SET actual_result = 'D',
    actual_home_goals = 1,
    actual_away_goals = 1
WHERE jackpot_id = (SELECT id FROM jackpots WHERE jackpot_id = 'JK-2024-1122')
  AND match_order = 1;
```

**Values for `actual_result`:**
- `'H'` = Home Win
- `'D'` = Draw
- `'A'` = Away Win

---

## Usage Examples

### Example 1: Using cURL (API)

```bash
curl -X POST "http://localhost:8000/api/probabilities/JK-2024-1122/save-result" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "15M MIDWEEK JACKPOT - 22/11 Results",
    "actual_results": {
      "1": "1",
      "2": "2",
      "3": "2",
      "4": "1",
      "5": "X",
      "6": "2",
      "7": "1",
      "8": "2",
      "9": "1",
      "10": "1",
      "11": "2",
      "12": "X",
      "13": "2",
      "14": "X",
      "15": "2"
    },
    "selections": {
      "A": {
        "1": "1",
        "2": "2",
        "3": "2",
        "4": "1",
        "5": "X",
        "6": "2",
        "7": "1",
        "8": "2",
        "9": "1",
        "10": "1",
        "11": "2",
        "12": "X",
        "13": "2",
        "14": "X",
        "15": "2"
      }
    }
  }'
```

### Example 2: Python Script

```python
import requests

jackpot_id = "JK-2024-1122"
url = f"http://localhost:8000/api/probabilities/{jackpot_id}/save-result"

data = {
    "name": "15M MIDWEEK JACKPOT - 22/11 Results",
    "actual_results": {
        "1": "1",  # AUGSBURG vs HAMBURG - Home Win
        "2": "2",  # WOLFSBURG vs LEVERKUSEN - Away Win
        "3": "2",  # HEIDENHEIM vs BORUSSIA (MG) - Away Win
        "4": "1",  # FULHAM vs SUNDERLAND - Home Win
        "5": "X",  # ACF FIORENTINA vs JUVENTUS - Draw
        # ... continue for all 15 matches
    },
    "selections": {
        "A": {
            "1": "1",
            "2": "2",
            # ... your selections
        }
    }
}

response = requests.post(url, json=data)
print(response.json())
```

### Example 3: CSV Upload (Frontend)

1. Navigate to **Data Ingestion Page → "Jackpot Results" Tab**
2. Click **"Upload CSV"**
3. Select your CSV file with format:
   ```csv
   Match,HomeTeam,AwayTeam,Result
   1,AUGSBURG,HAMBURG,1
   2,WOLFSBURG,LEVERKUSEN,2
   ...
   ```
4. Click **"Import Results"**

---

## Important Notes

1. **Fixture IDs**: Use string numbers (`"1"`, `"2"`, etc.) that correspond to `match_order` in `jackpot_fixtures` table
2. **Result Format**: Accepts both `"1"/"X"/"2"` and `"H"/"D"/"A"` formats
3. **Jackpot ID**: Must match an existing jackpot in the `jackpots` table
4. **Selections**: Required for saving results, but `actual_results` can be added later
5. **Scores**: Can be calculated automatically if not provided

---

## Related Endpoints

- `POST /api/probabilities/{jackpot_id}/save-result` - Save results
- `GET /api/probabilities/{jackpot_id}/saved-results` - Get saved results
- `PUT /api/probabilities/saved-results/{id}/actual-results` - Update actual results
- `POST /api/probabilities/saved-results/{id}/calculate-scores` - Calculate scores

---

## Data Flow

```
Input Jackpot Results
    ↓
saved_probability_results table
    ↓
┌─────────────────────────────────────┐
│  Backtesting                       │
│  Calibration                       │
│  Model Health                      │
│  Jackpot Validation                │
└─────────────────────────────────────┘
```


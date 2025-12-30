# Batch Per League Implementation - With League Name

## ✅ **Implementation Complete**

**One batch per league** with league name in folder name.

---

## 📁 **New Folder Structure**

### Format
```
data/1_data_ingestion/batch_{N}_{League_Name}/
```

### Examples
```
data/1_data_ingestion/
  batch_176_Premier_League/
    E0_2425.csv
    E0_2324.csv
    E0_2223.csv
    E0_2122.csv
    E0_2021.csv
    E0_1920.csv
    E0_1819.csv
  
  batch_177_La_Liga/
    SP1_2425.csv
    SP1_2324.csv
    SP1_2223.csv
    ...
  
  batch_178_Bundesliga/
    D1_2425.csv
    D1_2324.csv
    ...
```

---

## 🎯 **How It Works**

### Scenario 1: Download One League, All Seasons
**Action:** Download Premier League (E0) with "All Seasons"

**Result:**
- Creates: `batch_176_Premier_League/`
- Contains: All 7 seasons for Premier League
- Files: `E0_2425.csv`, `E0_2324.csv`, ..., `E0_1819.csv`

### Scenario 2: Download Multiple Leagues
**Action:** Download 10 leagues × 1 season each

**Result:**
- Creates: 10 batch folders (one per league)
- `batch_177_Premier_League/E0_2324.csv`
- `batch_178_La_Liga/SP1_2324.csv`
- `batch_179_Bundesliga/D1_2324.csv`
- ... (one folder per league)

### Scenario 3: Download Multiple Leagues × All Seasons
**Action:** Download 10 leagues × "All Seasons"

**Result:**
- Creates: 10 batch folders (one per league)
- Each folder contains all 7 seasons for that league
- `batch_180_Premier_League/` → 7 CSV files
- `batch_181_La_Liga/` → 7 CSV files
- `batch_182_Bundesliga/` → 7 CSV files
- ... (10 folders total, not 70!)

---

## 🔧 **Code Changes**

### 1. `_save_csv_file()` - Include League Name
**File:** `app/services/data_ingestion.py`

```python
def _save_csv_file(self, csv_content, league_code, season, batch_number):
    # Get league name from database
    league = self.db.query(League).filter(League.code == league_code).first()
    
    # Create safe folder name: batch_{N}_{League_Name}
    if league:
        league_name_safe = league.name.replace(' ', '_')
        batch_folder_name = f"batch_{batch_number}_{league_name_safe}"
    else:
        batch_folder_name = f"batch_{batch_number}_{league_code}"
    
    # Save to: data/1_data_ingestion/batch_{N}_{League_Name}/{code}_{season}.csv
```

### 2. `batch_download()` - One Batch Per League
**File:** `app/api/data.py`

- Creates **one batch per league** (not one for all)
- Each league gets its own `IngestionLog` record
- All seasons for that league go into the same batch folder

### 3. `ingest_all_seasons()` - One Batch Per League
**File:** `app/services/data_ingestion.py`

- Creates **one batch** for all seasons of a league
- All seasons reuse the same batch number
- All CSV files go into the same folder: `batch_{N}_{League_Name}/`

---

## 📊 **Comparison**

### Before (Old Behavior)
```
Download: 10 leagues × "All Seasons"
Result: 70 batch folders (one per CSV file)
  batch_100/E0_2425.csv
  batch_101/E0_2324.csv
  ...
  batch_169/SP1_1819.csv
```

### After (New Behavior - One Batch Per League)
```
Download: 10 leagues × "All Seasons"
Result: 10 batch folders (one per league)
  batch_176_Premier_League/
    E0_2425.csv
    E0_2324.csv
    ... (7 files)
  batch_177_La_Liga/
    SP1_2425.csv
    SP1_2324.csv
    ... (7 files)
  ...
```

---

## ✅ **Benefits**

1. **Better Organization:** Each league has its own folder
2. **Easy Identification:** League name in folder name
3. **Logical Grouping:** All seasons for a league together
4. **Less Clutter:** 10 folders instead of 70
5. **Easy Management:** Can delete entire league batch if needed

---

## 📝 **Folder Name Format**

### Safe Character Handling
- Spaces → Underscores: `Premier League` → `Premier_League`
- Special chars removed: Only alphanumeric, `_`, and `-` allowed
- Fallback: If league not found, uses league code: `batch_100_E0/`

### Examples
| League Name | Folder Name |
|-------------|-------------|
| Premier League | `batch_176_Premier_League` |
| La Liga | `batch_177_La_Liga` |
| 2. Bundesliga | `batch_178_2_Bundesliga` |
| League One | `batch_179_League_One` |

---

## 🔍 **Database Tracking**

Each league batch creates one `IngestionLog` record:
- `id`: Batch number
- `league_code`: Stored in `logs` JSONB field
- `records_inserted`: Total for all seasons in that league
- `records_updated`: Total for all seasons in that league

---

## 📋 **Summary**

✅ **One batch per league**  
✅ **League name in folder name**  
✅ **All seasons grouped together**  
✅ **Clean, organized structure**  

**Example Structure:**
```
data/1_data_ingestion/
  batch_176_Premier_League/     # All Premier League seasons
  batch_177_La_Liga/            # All La Liga seasons
  batch_178_Bundesliga/         # All Bundesliga seasons
  ...
```


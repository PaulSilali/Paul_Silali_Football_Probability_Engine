# Batch Folder Explanation - Why So Many Batches?

## 🔍 **Current Behavior: One Batch Per CSV File**

### The Problem

**Each CSV file gets its own batch folder**, not each download operation.

### How It Works Currently

1. **Every time `ingest_csv()` is called**, it creates a **NEW** `IngestionLog` record
2. **Each `IngestionLog.id` becomes a batch number**
3. **Each CSV file is saved to its own batch folder**

### Example Scenarios

#### Scenario 1: Download "All Seasons" for One League
- **Action:** Download Premier League (E0) with "All Seasons" (7 seasons)
- **Result:** **7 batch folders** created
  - `batch_100/E0_2425.csv`
  - `batch_101/E0_2324.csv`
  - `batch_102/E0_2223.csv`
  - `batch_103/E0_2122.csv`
  - `batch_104/E0_2021.csv`
  - `batch_105/E0_1920.csv`
  - `batch_106/E0_1819.csv`

**Why?** Each season calls `ingest_csv()` separately, creating a new `IngestionLog` each time.

#### Scenario 2: Download Multiple Leagues
- **Action:** Download 10 leagues × 1 season each
- **Result:** **10 batch folders** created (one per league)

#### Scenario 3: Download Multiple Leagues × All Seasons
- **Action:** Download 10 leagues × "All Seasons" (7 seasons each)
- **Result:** **70 batch folders** created!

---

## 📊 **Your Current Situation**

You have **batch_76 through batch_175** = **~100 batch folders**

This suggests you've downloaded approximately:
- **100 individual league+season combinations**, OR
- **~14 leagues with "All Seasons"** (14 × 7 = 98 batches), OR
- **Multiple smaller downloads** that accumulated

---

## 🔧 **The Root Cause**

### Code Location: `app/services/data_ingestion.py`

```python
def ingest_csv(self, csv_content, league_code, season, batch_number=None, ...):
    # Creates NEW IngestionLog EVERY TIME
    ingestion_log = IngestionLog(
        source_id=data_source.id,
        status="running"
    )
    self.db.add(ingestion_log)
    self.db.flush()
    
    # Uses ingestion_log.id as batch number if not provided
    if batch_number is None:
        batch_number = ingestion_log.id  # ❌ NEW batch every time!
```

**Problem:** Even when `batch_number` is passed (like in `ingest_all_seasons()`), a new `IngestionLog` is still created. The `batch_number` parameter is only used for the folder name, but a new database record is created anyway.

---

## ✅ **What SHOULD Happen**

### Option 1: One Batch Per Download Operation (Recommended)

**When you click "Download Selected":**
- Create **ONE** batch for the entire operation
- All CSV files from that download go into the **SAME** batch folder
- All seasons/leagues share the same batch number

**Example:**
```
batch_100/
  E0_2425.csv    # Premier League 2024-25
  E0_2324.csv    # Premier League 2023-24
  E0_2223.csv    # Premier League 2022-23
  SP1_2425.csv   # La Liga 2024-25
  SP1_2324.csv   # La Liga 2023-24
  ...
```

### Option 2: One Batch Per League (Alternative)

**Group by league:**
- Each league gets its own batch
- All seasons for that league go into the same batch folder

**Example:**
```
batch_100/  # Premier League batch
  E0_2425.csv
  E0_2324.csv
  E0_2223.csv
  ...

batch_101/  # La Liga batch
  SP1_2425.csv
  SP1_2324.csv
  ...
```

---

## 📁 **Current File Structure**

### What You're Seeing

```
data/1_data_ingestion/
  batch_76/
    SC0_2425.csv          # 1 file
  batch_77/
    E0_2324.csv           # 1 file
  batch_78/
    SP1_2425.csv          # 1 file
  ...
  batch_175/
    NO1_1920.csv          # 1 file
```

**Pattern:** Each batch folder contains **1 CSV file** (one league+season combination)

---

## 🎯 **Recommended Fix**

### Change: One Batch Per Download Operation

**Modify the code to:**
1. Create **ONE** `IngestionLog` at the start of a download operation
2. Reuse that batch number for all CSV files in that operation
3. All CSV files go into the same batch folder

**Benefits:**
- ✅ Logical grouping: All files from one download together
- ✅ Easier to track: One batch = one download operation
- ✅ Less clutter: Fewer batch folders
- ✅ Better organization: Related files grouped together

---

## 📝 **Current vs. Recommended**

### Current Behavior
```
Download: 10 leagues × "All Seasons"
Result: 70 batch folders (one per CSV file)
```

### Recommended Behavior
```
Download: 10 leagues × "All Seasons"
Result: 1 batch folder containing 70 CSV files
```

---

## 🔍 **How to Check Your Batches**

### Query Database
```sql
-- See all ingestion logs (batches)
SELECT 
    id as batch_number,
    started_at,
    records_inserted,
    records_updated,
    status,
    logs->>'league_code' as league_code,
    logs->>'season' as season
FROM ingestion_logs
ORDER BY id DESC
LIMIT 20;
```

### Check Batch Folders
```bash
# Count batch folders
ls -d data/1_data_ingestion/batch_* | wc -l

# See files in a batch
ls data/1_data_ingestion/batch_100/
```

---

## 💡 **Summary**

**Why so many batches?**
- ❌ **Current:** Each CSV file = 1 batch folder
- ✅ **Should be:** Each download operation = 1 batch folder

**Your 100 batches mean:**
- You've downloaded ~100 individual league+season combinations
- Each one created its own batch folder
- This is working as designed, but not ideal for organization

**Recommendation:**
- Fix the code to create one batch per download operation
- This will group related files together
- Much cleaner file structure


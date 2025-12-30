# Batch Folder Fix - Explanation

## ✅ **FIXED: One Batch Per Download Operation**

### What Was Wrong

**Before:** Each CSV file created its own batch folder
- Download 10 leagues × 7 seasons = **70 batch folders** ❌
- Each CSV file in its own folder
- Hard to track which files belong together

**After:** One batch folder per download operation
- Download 10 leagues × 7 seasons = **1 batch folder** ✅
- All CSV files from one download grouped together
- Easy to track and manage

---

## How It Works Now

### Single Download (One League, One Season)
```
POST /api/data/refresh
→ Creates batch_176
→ Saves: batch_176/E0_2324.csv
```

### Single Download (One League, All Seasons)
```
POST /api/data/refresh with season="all"
→ Creates batch_177
→ Saves: 
   batch_177/E0_2425.csv
   batch_177/E0_2324.csv
   batch_177/E0_2223.csv
   batch_177/E0_2122.csv
   batch_177/E0_2021.csv
   batch_177/E0_1920.csv
   batch_177/E0_1819.csv
```

### Batch Download (Multiple Leagues)
```
POST /api/data/batch-download
→ Creates batch_178
→ Saves:
   batch_178/E0_2324.csv
   batch_178/SP1_2324.csv
   batch_178/D1_2324.csv
   ... (all leagues in same batch)
```

### Batch Download (Multiple Leagues × All Seasons)
```
POST /api/data/batch-download with season="all"
→ Creates batch_179
→ Saves:
   batch_179/E0_2425.csv
   batch_179/E0_2324.csv
   ...
   batch_179/SP1_2425.csv
   batch_179/SP1_2324.csv
   ...
   (all leagues × all seasons in ONE batch folder)
```

---

## Code Changes

### 1. `ingest_csv()` - Reuse Batch Number
- **Before:** Always created new `IngestionLog` → new batch
- **After:** Only creates new log if `batch_number` is None
- **Result:** Can reuse same batch for multiple CSV files

### 2. `batch_download()` - Create One Batch
- **Before:** Each league+season created its own batch
- **After:** Creates ONE batch at start, reuses for all files
- **Result:** All files from one download in same folder

### 3. `ingest_all_seasons()` - Create One Batch
- **Before:** Each season created its own batch
- **After:** Creates ONE batch at start, reuses for all seasons
- **Result:** All seasons for one league in same folder

---

## Your Existing Batches

**Current:** batch_76 through batch_175 (100 batches)

**What happened:**
- Each CSV file created its own batch (old behavior)
- You downloaded ~100 individual league+season combinations
- Each got its own folder

**Going forward:**
- New downloads will use the fixed behavior
- One batch per download operation
- Much cleaner organization

**Old batches:** Can be left as-is or manually consolidated if desired

---

## Example: Before vs After

### Before (Old Behavior)
```
Download: 10 leagues × "All Seasons"
Result:
  batch_100/E0_2425.csv
  batch_101/E0_2324.csv
  batch_102/E0_2223.csv
  ...
  batch_109/E0_1819.csv
  batch_110/SP1_2425.csv
  batch_111/SP1_2324.csv
  ...
  (70 separate batch folders)
```

### After (Fixed Behavior)
```
Download: 10 leagues × "All Seasons"
Result:
  batch_176/
    E0_2425.csv
    E0_2324.csv
    E0_2223.csv
    E0_2122.csv
    E0_2021.csv
    E0_1920.csv
    E0_1819.csv
    SP1_2425.csv
    SP1_2324.csv
    ...
    (all 70 files in ONE batch folder)
```

---

## Benefits

✅ **Better Organization:** Related files grouped together  
✅ **Easier Tracking:** One batch = one download operation  
✅ **Less Clutter:** Fewer batch folders  
✅ **Logical Grouping:** All files from same download together  
✅ **Easier Cleanup:** Can delete entire batch if needed  

---

## Summary

**Question:** Why so many batch folders?  
**Answer:** Each CSV file was creating its own batch (old behavior)

**Fix:** One batch per download operation  
**Result:** Much cleaner file structure going forward


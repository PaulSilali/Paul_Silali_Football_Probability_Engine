# Draw Structural vs Historical Data: Cleaning Differences

## Important Distinction

There are **TWO different types of data** with different cleaning behaviors:

### 1. Historical Match Odds Data (NEEDS CLEANING)

**Location:**
- Raw: `1_data_ingestion/Historical Match_Odds_Data/`
- Cleaned: `2_Cleaned_data/Historical Match_Odds_Data/`

**Process:**
1. **Raw data downloaded** → Saved to `1_data_ingestion` (before cleaning)
2. **ETL Cleaning applied** → Removes bad rows, fixes formats, validates data
3. **Cleaned data saved** → Saved to `2_Cleaned_data` (after cleaning)
4. **Database ingestion** → Uses cleaned data

**Cleaning Applied:**
- Removes rows with missing critical data
- Fixes date formats
- Validates odds values
- Removes duplicate rows
- Standardizes team names

### 2. Draw Structural Data (NO CLEANING NEEDED)

**Location:**
- Processed: `1_data_ingestion/Draw_structural/{type}/`
- Copy: `2_Cleaned_data/Draw_structural/{type}/`

**Process:**
1. **Data calculated/processed** → From matches table or external APIs
2. **Same DataFrame saved** → To BOTH folders (identical data)
3. **No cleaning applied** → Data is already processed/calculated

**Why No Cleaning?**
- Draw Structural data is **calculated/processed** data, not raw downloads
- Examples:
  - **Team Form**: Calculated from recent match results
  - **Referee Stats**: Calculated from match statistics
  - **H2H Stats**: Calculated from historical matches
  - **Elo Ratings**: Calculated using Elo algorithm
  - **Rest Days**: Calculated from match dates
- The data is already "clean" when calculated - no ETL cleaning needed

## Referee Folder - What Happened

### The Copy Operation

When we copied Referee files:
- **Method:** Direct file copy (`shutil.copy2`)
- **Cleaning Applied:** None
- **Is This OK?** ✅ **YES**

### Why It's OK

1. **Draw Structural data doesn't need cleaning**
   - The data is already processed/calculated
   - Both folders should contain identical data
   - The `save_draw_structural_csv()` function saves the SAME DataFrame to both locations

2. **The "cleaned_data" folder for Draw Structural is:**
   - A "ready-to-use" copy
   - Not an ETL-cleaned version
   - Identical to ingestion folder

3. **Code Evidence:**
   ```python
   # From draw_structural_utils.py
   def save_draw_structural_csv(df, folder_name, filename, save_to_cleaned=True):
       # Save to ingestion folder
       df.to_csv(ingestion_path, index=False)
       
       # Save to cleaned folder (SAME DataFrame, no transformation)
       if save_to_cleaned:
           df.to_csv(cleaned_path, index=False)  # Same data!
   ```

## Comparison Table

| Data Type | Raw Location | Cleaned Location | Cleaning Applied? |
|-----------|-------------|------------------|-------------------|
| **Historical Match Odds** | `1_data_ingestion/Historical Match_Odds_Data/` | `2_Cleaned_data/Historical Match_Odds_Data/` | ✅ YES - ETL cleaning |
| **Draw Structural** | `1_data_ingestion/Draw_structural/` | `2_Cleaned_data/Draw_structural/` | ❌ NO - Already processed |

## Answer to Your Question

**Q: Were the Referee files cleaned when copied?**

**A: No, they were not cleaned - and that's correct!**

- Draw Structural data (including Referee) doesn't need ETL cleaning
- The files are already processed/calculated data
- Copying them directly is the correct approach
- Both folders contain identical, ready-to-use data

## Future Behavior

Going forward:
- **New Referee ingestions** will automatically save to both folders (code fixed)
- **Historical Match Odds** will continue to have raw → cleaned flow
- **Draw Structural** will continue to save identical data to both folders

## Summary

✅ **Referee files are correct** - they don't need cleaning because:
1. They're calculated/processed data, not raw downloads
2. Draw Structural data is already "clean" when created
3. Both folders should contain identical data
4. The copy operation was appropriate


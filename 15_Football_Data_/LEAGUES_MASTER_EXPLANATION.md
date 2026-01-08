# Why "UNKNOWN" Leagues Despite leagues-master Folder

## The Problem

The `leagues-master` folder contains **metadata/reference files**, NOT match data files. This is why it doesn't help with league code detection during extraction.

## What's in leagues-master?

### ✅ Metadata Files (Reference Only)
- `leagues.txt` - League definitions and codes
- `seasons.txt` - Season information
- `europe/england/eng.leagues.txt` - England league definitions
- `europe/germany/de.leagues.txt` - Germany league definitions
- etc.

### ❌ NOT Match Data Files
- No files like `1-premierleague.txt` (match data)
- No files like `2023-24_fr1.txt` (match data)
- Only reference/metadata files

## Why This Causes "UNKNOWN" Leagues

### Current Extraction Process

1. **Script scans all `*-master` folders**:
   ```python
   for master_dir in self.data_dir.glob('*-master'):
       for txt_file in master_dir.rglob('*.txt'):
   ```

2. **Finds files in leagues-master**:
   - `leagues.txt` (metadata)
   - `eng.leagues.txt` (metadata)
   - `de.leagues.txt` (metadata)
   - etc.

3. **Tries to parse as match data**:
   - These files don't contain match results
   - They contain league definitions like:
     ```
     = England =
     1   1992/93-    Premier League
     2   2004/05-    Championship
     ```

4. **League code detection fails**:
   - File name is `eng.leagues.txt` (not a match data pattern)
   - No recognizable pattern like `1-premierleague.txt` or `2023-24_fr1.txt`
   - Returns `None` → marked as "UNKNOWN"

## The Real Issue

The extraction script's `extract_league_code_from_path()` function looks for:
- File naming patterns: `1-premierleague.txt`, `2023-24_fr1.txt`, `be1.txt`
- Directory patterns: `england-master`, `france/`, etc.

But many files from `europe-master`, `south-america-master`, and `world-master` have different naming patterns that aren't recognized.

## Solution

### Option 1: Skip leagues-master (Recommended)
The `leagues-master` folder is metadata only - skip it during extraction:

```python
def find_txt_files(self) -> List[Path]:
    """Find all Football.TXT files"""
    txt_files = []
    for master_dir in self.data_dir.glob('*-master'):
        # Skip leagues-master (metadata only, no match data)
        if master_dir.name == 'leagues-master':
            continue
        for txt_file in master_dir.rglob('*.txt'):
            # Skip README, LICENSE, NOTES files
            if txt_file.name.lower() in ['readme.md', 'license.md', 'notes.md']:
                continue
            txt_files.append(txt_file)
    return sorted(txt_files)
```

### Option 2: Use leagues-master for Better Mapping
Parse `leagues-master` files to build a comprehensive league code mapping, then use it during extraction.

### Option 3: Fix During Database Population (Current Approach)
- Extract all matches (even with "UNKNOWN" codes)
- Use `league_mapping.json` during database population to map correctly
- More flexible and doesn't require re-extraction

## Current Status

✅ **Extraction is working correctly**
- All match data folders scanned
- 103,921 matches extracted
- League codes can be fixed during database population

⚠️ **"UNKNOWN" leagues are expected**
- Many file naming patterns not yet recognized
- Will be mapped correctly during database population
- Using `league_mapping.json` for accurate mapping

## Recommendation

**Keep current approach** - extract first, map later:
1. ✅ More flexible
2. ✅ Can handle new leagues without code changes
3. ✅ Database population uses `league_mapping.json` for accurate mapping
4. ✅ No need to re-extract

The `leagues-master` folder is useful for:
- Understanding league structures
- Building comprehensive league mappings
- Reference documentation

But it doesn't contain match data, so it won't help with league code detection during extraction.


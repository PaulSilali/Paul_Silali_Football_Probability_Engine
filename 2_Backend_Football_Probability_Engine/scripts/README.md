# Scripts Directory

Utility scripts for database management and data processing.

## create_teams_from_csv.py

Extracts unique team names from CSV files and creates them in the database.

### Purpose

This script solves the issue where matches aren't inserted into the database because teams don't exist. It:
1. Scans all CSV files in `data/1_data_ingestion/batch_*/`
2. Extracts unique team names per league
3. Creates teams in the database if they don't exist
4. Uses normalized team names for `canonical_name`

### Usage

**From the backend directory:**

```bash
# Preview what will be created (dry run)
python scripts/create_teams_from_csv.py --dry-run

# Create teams for all leagues
python scripts/create_teams_from_csv.py

# Create teams for specific league only
python scripts/create_teams_from_csv.py --league E0

# Custom data directory
python scripts/create_teams_from_csv.py --data-dir ../data/1_data_ingestion
```

### Options

- `--dry-run`: Preview changes without creating teams
- `--league CODE`: Filter by league code (e.g., E0, SP1, D1)
- `--data-dir PATH`: Path to data ingestion directory (default: `data/1_data_ingestion`)

### Example Output

```
============================================================
Team Extraction and Creation Script
============================================================
📂 Extracting teams from CSV files...
Found 203 CSV files
Extracted 20 unique teams from E0_1920.csv
...

📊 Summary:
  E0: 20 teams
  SP1: 20 teams
  D1: 18 teams
  Total: 58 unique teams across 3 leagues

💾 Creating teams in database...
============================================================
Processing league: Premier League (E0)
Found 20 unique team names
============================================================
  ✓ Created: Arsenal -> arsenal
  ✓ Created: Chelsea -> chelsea
  ✓ Created: Liverpool -> liverpool
  ...

📈 Final Statistics:
============================================================
  Leagues processed: 3
  Teams created: 58
  Teams already existing: 0
  Teams skipped: 0
  Errors: 0
============================================================

✅ Teams created successfully!
```

### Requirements

- Python 3.8+
- pandas
- Database connection configured in `.env`
- CSV files in `data/1_data_ingestion/batch_*/`

### Notes

- Teams are created with normalized `canonical_name` using `normalize_team_name()`
- Existing teams are skipped (no duplicates created)
- Commits are made periodically (every 50 teams) and per league
- Script handles errors gracefully and continues processing


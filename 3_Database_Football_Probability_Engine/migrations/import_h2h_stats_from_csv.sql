-- ============================================================================
-- IMPORT H2H STATS FROM CSV FILES
-- ============================================================================
-- 
-- This SQL script provides an alternative method to import H2H stats using
-- PostgreSQL's COPY command. However, the recommended method is to use the
-- Python script: scripts/import_h2h_stats_from_csv.py
-- 
-- The Python script provides better validation, error handling, and logging.
-- 
-- ============================================================================

-- Note: This is a template. You'll need to:
-- 1. Adjust the CSV file paths
-- 2. Ensure CSV files match the expected format
-- 3. Handle team ID mapping if needed

-- Example COPY command (adjust path and format as needed):
/*
COPY h2h_draw_stats (team_home_id, team_away_id, matches_played, draw_count, avg_goals)
FROM '/path/to/h2h_stats/PL1_1617_h2h_stats.csv'
WITH (FORMAT csv, HEADER true, DELIMITER ',');
*/

-- However, the CSV files have additional columns (home_team_name, away_team_name, season, draw_rate)
-- So we need to use a temporary table or process via Python

-- ============================================================================
-- RECOMMENDED APPROACH: Use Python Script
-- ============================================================================
-- 
-- Run: python scripts/import_h2h_stats_from_csv.py
-- 
-- This script will:
-- 1. Find all CSV files in data/2_Cleaned_data/Draw_structural/h2h_stats/
-- 2. Validate each record
-- 3. Check team IDs exist in database
-- 4. Insert or update records in h2h_draw_stats table
-- 5. Provide detailed logging and summary
-- 
-- ============================================================================

-- Verify current H2H stats count
SELECT COUNT(*) as total_h2h_records FROM h2h_draw_stats;

-- View sample records
SELECT 
    h.team_home_id,
    ht.name as home_team_name,
    h.team_away_id,
    at.name as away_team_name,
    h.matches_played,
    h.draw_count,
    h.avg_goals
FROM h2h_draw_stats h
JOIN teams ht ON ht.id = h.team_home_id
JOIN teams at ON at.id = h.team_away_id
LIMIT 10;


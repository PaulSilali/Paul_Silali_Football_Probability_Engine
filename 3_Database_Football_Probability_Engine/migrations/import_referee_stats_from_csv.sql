-- ============================================================================
-- IMPORT REFEREE STATS FROM CSV FILES
-- ============================================================================
-- 
-- This SQL script provides an alternative method to import referee stats using
-- PostgreSQL's COPY command. However, the recommended method is to use the
-- Python script: scripts/import_referee_stats_from_csv.py
-- 
-- The Python script provides better validation, error handling, and logging.
-- 
-- ============================================================================

-- Note: This is a template. You'll need to:
-- 1. Adjust the CSV file paths
-- 2. Ensure CSV files match the expected format
-- 3. Handle referee_id mapping if needed

-- Example COPY command (adjust path and format as needed):
/*
COPY referee_stats (referee_id, referee_name, matches, avg_cards, avg_penalties, draw_rate)
FROM '/path/to/referee_stats/AUS1_2122_referee_stats.csv'
WITH (FORMAT csv, HEADER true, DELIMITER ',');
*/

-- However, the CSV files have additional columns (league_code, season)
-- So we need to use a temporary table or process via Python

-- ============================================================================
-- RECOMMENDED APPROACH: Use Python Script
-- ============================================================================
-- 
-- Run: python scripts/import_referee_stats_from_csv.py
-- 
-- This script will:
-- 1. Find all CSV files in data/1_data_ingestion/Draw_structural/Referee/
-- 2. Validate each record
-- 3. Insert or update records in referee_stats table
-- 4. Provide detailed logging and summary
-- 
-- ============================================================================

-- Verify current referee stats count
SELECT COUNT(*) as total_referee_records FROM referee_stats;

-- View sample records
SELECT 
    referee_id,
    referee_name,
    matches,
    avg_cards,
    avg_penalties,
    draw_rate,
    updated_at
FROM referee_stats
ORDER BY referee_id
LIMIT 10;

-- View referees by draw rate (for analysis)
SELECT 
    referee_id,
    referee_name,
    matches,
    draw_rate,
    avg_cards,
    avg_penalties
FROM referee_stats
WHERE matches >= 10  -- Only referees with sufficient sample size
ORDER BY draw_rate DESC
LIMIT 20;

-- View referees with highest draw rates
SELECT 
    referee_id,
    referee_name,
    matches,
    draw_rate,
    CASE 
        WHEN draw_rate > 0.30 THEN 'High Draw Rate'
        WHEN draw_rate > 0.25 THEN 'Medium Draw Rate'
        ELSE 'Low Draw Rate'
    END as draw_category
FROM referee_stats
WHERE matches >= 10
ORDER BY draw_rate DESC;

-- View referees with lowest draw rates
SELECT 
    referee_id,
    referee_name,
    matches,
    draw_rate,
    CASE 
        WHEN draw_rate > 0.30 THEN 'High Draw Rate'
        WHEN draw_rate > 0.25 THEN 'Medium Draw Rate'
        ELSE 'Low Draw Rate'
    END as draw_category
FROM referee_stats
WHERE matches >= 10
ORDER BY draw_rate ASC;


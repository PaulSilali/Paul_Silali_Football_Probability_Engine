-- ============================================================================
-- DATABASE REBUILD SCRIPT - STANDALONE SQL
-- ============================================================================
-- 
-- Run this script in your PostgreSQL client (pgAdmin, DBeaver, etc.)
-- 
-- Instructions:
--   1. Connect to PostgreSQL as superuser (postgres)
--   2. Run this entire script
--   3. The script will drop and recreate the database
-- 
-- WARNING: This will DROP all existing data!
-- 
-- ============================================================================

-- ============================================================================
-- STEP 1: DISCONNECT ALL USERS AND DROP DATABASE
-- ============================================================================

-- Disconnect all users from the database
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'football_probability_engine'
  AND pid <> pg_backend_pid();

-- Drop database (run this from 'postgres' database)
DROP DATABASE IF EXISTS football_probability_engine;

-- ============================================================================
-- STEP 2: CREATE NEW DATABASE
-- ============================================================================

CREATE DATABASE football_probability_engine
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- ============================================================================
-- STEP 3: CONNECT TO NEW DATABASE
-- ============================================================================
-- Note: In some clients, you may need to manually switch to the new database
-- before running the rest of the script

\c football_probability_engine

-- ============================================================================
-- STEP 4: RUN MAIN SCHEMA
-- ============================================================================
-- Copy and paste the contents of 3_Database_Football_Probability_Engine.sql here
-- OR run it separately after connecting to the new database

-- ============================================================================
-- ALTERNATIVE: Run migrations manually
-- ============================================================================
-- If you can't run the main schema file, you can run the migrations individually
-- after creating the database structure

-- After running the main schema, verify tables were created:
SELECT COUNT(*) as total_tables
FROM pg_tables
WHERE schemaname = 'public';


# 📊 DATABASE SCHEMA - DEPLOYMENT GUIDE

## Football Jackpot Probability Engine - PostgreSQL Database

---

## 📦 Files Provided

1. **`database_schema.sql`** (Primary Schema)
   - Complete database structure
   - All 14 tables with constraints
   - Enums, indexes, and triggers
   - Row Level Security policies
   - ~700 lines of production-ready SQL

2. **`seed_data.sql`** (Initial Data)
   - Sample leagues (12 major leagues)
   - Premier League teams (20 teams)
   - La Liga teams (10 teams)
   - Data source registry
   - Development model placeholder
   - ~200 lines

---

## 🚀 QUICK START

### Option 1: Local PostgreSQL

```bash
# 1. Create database
createdb jackpot_db

# 2. Run schema
psql -d jackpot_db -f database_schema.sql

# 3. Run seed data
psql -d jackpot_db -f seed_data.sql

# 4. Verify
psql -d jackpot_db -c "SELECT COUNT(*) FROM leagues;"
# Expected: 12 leagues
```

### Option 2: Docker PostgreSQL

```bash
# 1. Start PostgreSQL container
docker run -d \
  --name jackpot-db \
  -e POSTGRES_DB=jackpot_db \
  -e POSTGRES_USER=jackpot_user \
  -e POSTGRES_PASSWORD=secure_password \
  -p 5432:5432 \
  postgres:15

# 2. Wait for PostgreSQL to start (5 seconds)
sleep 5

# 3. Run schema
docker exec -i jackpot-db psql -U jackpot_user -d jackpot_db < database_schema.sql

# 4. Run seed data
docker exec -i jackpot-db psql -U jackpot_user -d jackpot_db < seed_data.sql

# 5. Verify
docker exec -it jackpot-db psql -U jackpot_user -d jackpot_db \
  -c "SELECT code, name, COUNT(t.id) as teams FROM leagues l LEFT JOIN teams t ON t.league_id = l.id GROUP BY l.id ORDER BY teams DESC;"
```

### Option 3: Supabase

```bash
# Using Supabase CLI
supabase db push --db-url "postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres" \
  < database_schema.sql

# Or use Supabase Dashboard:
# 1. Go to Database > SQL Editor
# 2. Paste contents of database_schema.sql
# 3. Click "Run"
# 4. Repeat for seed_data.sql
```

---

## 📋 DATABASE SCHEMA OVERVIEW

### Core Tables

| Table | Purpose | Records (Typical) |
|-------|---------|-------------------|
| `leagues` | Football league reference | 10-50 |
| `teams` | Team registry with strengths | 200-500 |
| `matches` | Historical match results | 10,000-100,000+ |
| `team_features` | Rolling team statistics | 5,000-50,000 |
| `models` | Trained model registry | 5-20 |
| `jackpots` | User jackpot submissions | 100-10,000+ |
| `jackpot_fixtures` | Individual fixtures | 1,300-130,000+ |
| `predictions` | Calculated probabilities | 9,100-910,000+ |

### Key Constraints

✅ **Probability Conservation**: Probabilities must sum to 1.0 (enforced at DB level)
✅ **Unique Matches**: No duplicate historical matches
✅ **Immutable Jackpots**: Status check prevents invalid states
✅ **Referential Integrity**: All foreign keys with cascading deletes
✅ **Row Level Security**: User isolation for jackpots

---

## 🔑 KEY FEATURES

### 1. Enums (Type Safety)

```sql
-- Model status
CREATE TYPE model_status AS ENUM ('active', 'archived', 'failed');

-- Prediction sets (A-G)
CREATE TYPE prediction_set AS ENUM ('A', 'B', 'C', 'D', 'E', 'F', 'G');

-- Match results
CREATE TYPE match_result AS ENUM ('H', 'D', 'A');
```

### 2. Probability Validation

```sql
-- Enforced at database level
CHECK (abs((prob_home + prob_draw + prob_away) - 1.0) < 1e-6)
```

### 3. Time Decay Support

```sql
-- Team features table includes decay parameters
decay_lambda DOUBLE PRECISION NOT NULL  -- For reproducibility
```

### 4. Versioned Features

```sql
-- Feature store with versioning
UNIQUE (team_id, snapshot_date, feature_version)
```

### 5. Row Level Security (Supabase)

```sql
-- Users can only see their own jackpots
CREATE POLICY "Users can view own jackpots" ON jackpots
    FOR SELECT USING (auth.uid() = user_id);
```

---

## 📊 SAMPLE QUERIES

### Check System Health

```sql
-- Count records per table
SELECT 
    'leagues' as table_name, COUNT(*) as count FROM leagues
UNION ALL
SELECT 'teams', COUNT(*) FROM teams
UNION ALL
SELECT 'matches', COUNT(*) FROM matches
UNION ALL
SELECT 'models', COUNT(*) FROM models
UNION ALL
SELECT 'jackpots', COUNT(*) FROM jackpots;
```

### View Active Model

```sql
SELECT 
    version,
    model_type,
    training_completed_at,
    brier_score,
    training_matches
FROM models
WHERE status = 'active'
ORDER BY training_completed_at DESC
LIMIT 1;
```

### Team Strengths (Premier League)

```sql
SELECT 
    t.name,
    t.attack_rating,
    t.defense_rating,
    (t.attack_rating - t.defense_rating) as net_strength
FROM teams t
JOIN leagues l ON l.id = t.league_id
WHERE l.code = 'E0'
ORDER BY net_strength DESC;
```

### Recent Jackpots

```sql
SELECT 
    j.jackpot_id,
    j.status,
    COUNT(jf.id) as fixture_count,
    j.created_at
FROM jackpots j
LEFT JOIN jackpot_fixtures jf ON jf.jackpot_id = j.id
GROUP BY j.id
ORDER BY j.created_at DESC
LIMIT 10;
```

---

## 🧪 TESTING

### Verify Schema

```bash
# Count tables
psql -d jackpot_db -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
# Expected: 14 tables

# Verify enums
psql -d jackpot_db -c "SELECT typname FROM pg_type WHERE typtype = 'e';"
# Expected: model_status, prediction_set, match_result, data_source_status

# Check indexes
psql -d jackpot_db -c "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public';"
# Expected: 15+ indexes
```

### Test Constraints

```sql
-- This should FAIL (probability sum != 1.0)
INSERT INTO predictions (
    fixture_id, model_id, set_type,
    prob_home, prob_draw, prob_away,
    predicted_outcome, confidence,
    expected_home_goals, expected_away_goals
) VALUES (
    1, 'some-uuid', 'A',
    0.4, 0.3, 0.2,  -- WRONG: sums to 0.9, not 1.0
    'H', 0.4,
    1.5, 1.2
);
-- Expected: ERROR: check constraint "predictions_prob_home_prob_draw_prob_away_check" violated
```

---

## 🔄 MIGRATION STRATEGY

### For Production

**Option A: All-in-One (Recommended for Initial Setup)**

```bash
# Single transaction, all tables at once
psql -d jackpot_db -f database_schema.sql
```

**Option B: Incremental (For Existing Databases)**

Create separate migration files:
```
migrations/
├── 001_enable_extensions.sql
├── 002_create_enums.sql
├── 003_create_leagues.sql
├── 004_create_teams.sql
├── 005_create_matches.sql
...
├── 015_create_indexes.sql
└── 016_enable_rls.sql
```

Run sequentially:
```bash
for file in migrations/*.sql; do
    echo "Running $file..."
    psql -d jackpot_db -f "$file"
done
```

---

## 📈 PERFORMANCE OPTIMIZATION

### Recommended Settings

```sql
-- For PostgreSQL config (postgresql.conf)
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1  -- For SSD
effective_io_concurrency = 200
```

### Additional Indexes (Heavy Load)

```sql
-- If queries are slow, add these
CREATE INDEX idx_matches_result ON matches(result);
CREATE INDEX idx_predictions_created_at ON predictions(created_at DESC);
CREATE INDEX idx_jackpots_status ON jackpots(status);
CREATE INDEX idx_teams_ratings ON teams(attack_rating DESC, defense_rating);
```

---

## 🔒 SECURITY CHECKLIST

- [ ] Change default passwords
- [ ] Enable SSL connections
- [ ] Configure firewall rules
- [ ] Enable Row Level Security
- [ ] Restrict database user privileges
- [ ] Set up automated backups
- [ ] Enable audit logging
- [ ] Use connection pooling (PgBouncer)

---

## 🛠️ MAINTENANCE

### Backup

```bash
# Full backup
pg_dump -U jackpot_user -d jackpot_db -F c -f jackpot_backup_$(date +%Y%m%d).dump

# Schema only
pg_dump -U jackpot_user -d jackpot_db --schema-only > schema_backup.sql

# Data only
pg_dump -U jackpot_user -d jackpot_db --data-only > data_backup.sql
```

### Restore

```bash
# From custom format
pg_restore -U jackpot_user -d jackpot_db jackpot_backup_20250101.dump

# From SQL file
psql -U jackpot_user -d jackpot_db < schema_backup.sql
```

### Vacuum & Analyze

```sql
-- Regular maintenance
VACUUM ANALYZE;

-- Aggressive cleanup (run weekly)
VACUUM FULL ANALYZE;

-- Per table
VACUUM ANALYZE matches;
VACUUM ANALYZE predictions;
```

---

## 📞 TROUBLESHOOTING

### Issue: "relation already exists"

```bash
# Drop and recreate (CAUTION: DATA LOSS)
psql -d jackpot_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
psql -d jackpot_db -f database_schema.sql
```

### Issue: Slow queries

```sql
-- Find slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Analyze query plan
EXPLAIN ANALYZE SELECT * FROM matches WHERE match_date > '2024-01-01';
```

### Issue: Connection limit reached

```sql
-- Check current connections
SELECT COUNT(*) FROM pg_stat_activity;

-- Kill idle connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
AND state_change < now() - interval '1 hour';
```

---

## ✅ POST-DEPLOYMENT CHECKLIST

- [ ] Schema created successfully
- [ ] Seed data loaded
- [ ] All 14 tables present
- [ ] Indexes created (15+)
- [ ] RLS policies enabled
- [ ] Triggers working (updated_at)
- [ ] Sample queries return data
- [ ] Constraints enforced (probability sum)
- [ ] Backups configured
- [ ] Connection pooling set up

---

## 📚 ADDITIONAL RESOURCES

- PostgreSQL Documentation: https://www.postgresql.org/docs/
- Supabase SQL Editor: https://supabase.com/docs/guides/database
- Dixon-Coles Paper: See architecture documentation

---

**Schema Version**: 1.0.0  
**Last Updated**: December 28, 2025  
**Status**: Production Ready ✅

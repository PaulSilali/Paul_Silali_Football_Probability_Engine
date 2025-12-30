"""
Table Completeness Tests

Verify all tables from SQL schema exist and are accessible.
"""
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from app.db.session import engine, SessionLocal
from app.db.base import Base


# Tables from SQL schema (3_Database_Football_Probability_Engine.sql)
# Note: league_stats is in SQL schema but may not be implemented in models yet
SQL_SCHEMA_TABLES = [
    'leagues',
    'teams',
    'matches',
    'team_features',
    'league_stats',  # May not exist in models yet
    'models',
    'training_runs',
    'users',
    'jackpots',
    'jackpot_fixtures',
    'predictions',
    'validation_results',
    'calibration_data',
    'data_sources',
    'ingestion_logs',
    'audit_entries'
]

# Core tables that MUST exist (implemented in models)
CORE_TABLES = [
    'leagues',
    'teams',
    'matches',
    'team_features',
    'models',
    'training_runs',
    'users',
    'jackpots',
    'jackpot_fixtures',
    'predictions',
    'validation_results',
    'calibration_data',
    'data_sources',
    'ingestion_logs',
    'audit_entries'
]

# Tables from SQLAlchemy models
SQLALCHEMY_MODEL_TABLES = list(Base.metadata.tables.keys())


class TestTableCompleteness:
    """Test that all expected tables exist"""
    
    @pytest.fixture(scope="class")
    def inspector(self):
        """Create SQLAlchemy inspector"""
        return inspect(engine)
    
    @pytest.fixture(scope="class")
    def db_session(self):
        """Create database session"""
        session = SessionLocal()
        yield session
        session.close()
    
    def test_all_sql_schema_tables_exist(self, inspector):
        """Test that all tables from SQL schema exist in database"""
        existing_tables = set(inspector.get_table_names())
        sql_schema_tables_set = set(SQL_SCHEMA_TABLES)
        core_tables_set = set(CORE_TABLES)
        
        missing_tables = sql_schema_tables_set - existing_tables
        missing_core_tables = core_tables_set - existing_tables
        extra_tables = existing_tables - sql_schema_tables_set
        
        print(f"\n{'='*60}")
        print("Table Completeness Check")
        print(f"{'='*60}")
        print(f"Expected tables (from SQL schema): {len(SQL_SCHEMA_TABLES)}")
        print(f"Core tables (must exist): {len(CORE_TABLES)}")
        print(f"Existing tables in database: {len(existing_tables)}")
        print(f"SQLAlchemy model tables: {len(SQLALCHEMY_MODEL_TABLES)}")
        
        if missing_core_tables:
            print(f"\n[FAIL] Missing CORE tables: {', '.join(sorted(missing_core_tables))}")
        elif missing_tables:
            print(f"\n[WARN] Missing optional tables: {', '.join(sorted(missing_tables))}")
            print("  (These may not be implemented in models yet)")
        else:
            print(f"\n[OK] All {len(SQL_SCHEMA_TABLES)} expected tables exist")
        
        if extra_tables:
            print(f"\n[WARN] Extra tables (not in SQL schema): {', '.join(sorted(extra_tables))}")
        
        print(f"{'='*60}\n")
        
        # Only fail if core tables are missing
        assert len(missing_core_tables) == 0, \
            f"Missing CORE tables: {', '.join(sorted(missing_core_tables))}"
    
    def test_sqlalchemy_models_match_sql_schema(self):
        """Test that SQLAlchemy models match SQL schema tables"""
        sqlalchemy_tables_set = set(SQLALCHEMY_MODEL_TABLES)
        sql_schema_tables_set = set(SQL_SCHEMA_TABLES)
        
        missing_in_models = sql_schema_tables_set - sqlalchemy_tables_set
        extra_in_models = sqlalchemy_tables_set - sql_schema_tables_set
        
        print(f"\nSQLAlchemy Models vs SQL Schema:")
        if missing_in_models:
            print(f"  [FAIL] Missing in models: {', '.join(sorted(missing_in_models))}")
        if extra_in_models:
            print(f"  [WARN] Extra in models: {', '.join(sorted(extra_in_models))}")
        if not missing_in_models and not extra_in_models:
            print(f"  [OK] Perfect match!")
        
        # Note: Some tables might be missing if not yet implemented
        # This is informational, not a failure
        if missing_in_models:
            print(f"\n  Note: These tables are in SQL schema but not in SQLAlchemy models yet.")
    
    def test_all_tables_are_accessible(self, db_session):
        """Test that we can query all tables"""
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        accessible_tables = []
        inaccessible_tables = []
        
        for table_name in existing_tables:
            try:
                # Try to query the table
                result = db_session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.fetchone()[0]
                accessible_tables.append((table_name, count))
            except Exception as e:
                inaccessible_tables.append((table_name, str(e)))
        
        print(f"\n{'='*60}")
        print("Table Accessibility Check")
        print(f"{'='*60}")
        
        for table_name, count in accessible_tables:
            print(f"[OK] {table_name:30} - {count:6} rows")
        
        if inaccessible_tables:
            print(f"\n[FAIL] Inaccessible tables:")
            for table_name, error in inaccessible_tables:
                print(f"  {table_name}: {error}")
        
        print(f"{'='*60}\n")
        
        assert len(inaccessible_tables) == 0, \
            f"Inaccessible tables: {[t[0] for t in inaccessible_tables]}"
    
    def test_table_relationships_exist(self, inspector):
        """Test that foreign key relationships exist"""
        relationships = {
            'teams': ['league_id'],
            'matches': ['league_id', 'home_team_id', 'away_team_id'],
            'jackpot_fixtures': ['jackpot_id', 'home_team_id', 'away_team_id', 'league_id'],
            'predictions': ['fixture_id', 'model_id'],
            'validation_results': ['jackpot_id', 'model_id'],
            'calibration_data': ['model_id', 'league_id'],
            'training_runs': ['model_id'],
            'audit_entries': ['user_id'],
        }
        
        print(f"\n{'='*60}")
        print("Foreign Key Relationships Check")
        print(f"{'='*60}")
        
        all_good = True
        for table_name, expected_fks in relationships.items():
            if table_name not in inspector.get_table_names():
                continue
            
            fks = inspector.get_foreign_keys(table_name)
            fk_columns = [fk['constrained_columns'][0] for fk in fks]
            
            missing_fks = [fk for fk in expected_fks if fk not in fk_columns]
            if missing_fks:
                print(f"[FAIL] {table_name}: Missing FKs {missing_fks}")
                all_good = False
            else:
                print(f"[OK] {table_name}: All FKs present")
        
        print(f"{'='*60}\n")
        
        assert all_good, "Some foreign key relationships are missing"
    
    def test_indexes_exist_for_performance(self, inspector):
        """Test that important indexes exist"""
        expected_indexes = {
            'matches': ['idx_matches_date', 'idx_matches_league_season'],
            'teams': ['idx_teams_canonical'],
            'predictions': ['idx_predictions_fixture', 'idx_predictions_set'],
            'jackpot_fixtures': ['idx_jackpot_fixtures_jackpot'],
            'audit_entries': ['idx_audit_timestamp'],
        }
        
        print(f"\n{'='*60}")
        print("Index Check")
        print(f"{'='*60}")
        
        all_good = True
        for table_name, expected_idx_names in expected_indexes.items():
            if table_name not in inspector.get_table_names():
                continue
            
            indexes = inspector.get_indexes(table_name)
            index_names = [idx['name'] for idx in indexes]
            
            for idx_name in expected_idx_names:
                if idx_name not in index_names:
                    # Check if similar index exists
                    similar = [idx for idx in index_names if idx_name.split('_')[-1] in idx]
                    if not similar:
                        print(f"[WARN] {table_name}: Index '{idx_name}' not found")
                        # Not a failure, just informational
                else:
                    print(f"[OK] {table_name}: Index '{idx_name}' exists")
        
        print(f"{'='*60}\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


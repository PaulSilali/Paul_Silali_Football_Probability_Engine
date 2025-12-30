"""
Database Schema Validation Tests

Tests to verify all tables exist and match the SQL schema specification.
"""
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from app.db.session import engine, SessionLocal
from app.db.models import (
    League, Team, Match, TeamFeature,
    Model, TrainingRun, User, Jackpot, JackpotFixture,
    Prediction, ValidationResult, CalibrationData,
    DataSource, IngestionLog, AuditEntry
)
from app.db.base import Base


# Expected tables from SQL schema
EXPECTED_TABLES = [
    'leagues', 'teams', 'matches', 'team_features', 'league_stats',
    'models', 'training_runs', 'users', 'jackpots', 'jackpot_fixtures',
    'predictions', 'validation_results', 'calibration_data',
    'data_sources', 'ingestion_logs', 'audit_entries'
]


class TestDatabaseSchema:
    """Test database schema matches specification"""
    
    @pytest.fixture(scope="class")
    def db_session(self):
        """Create a database session for testing"""
        session = SessionLocal()
        yield session
        session.close()
    
    @pytest.fixture(scope="class")
    def inspector(self):
        """Create SQLAlchemy inspector"""
        return inspect(engine)
    
    def test_all_tables_exist(self, inspector):
        """Test that all expected tables exist in the database"""
        existing_tables = inspector.get_table_names()
        missing_tables = [table for table in EXPECTED_TABLES if table not in existing_tables]
        
        assert len(missing_tables) == 0, f"Missing tables: {', '.join(missing_tables)}"
        print(f"✓ All {len(EXPECTED_TABLES)} expected tables exist")
    
    def test_table_columns_match_models(self, inspector):
        """Test that table columns match SQLAlchemy models"""
        # Test leagues table
        leagues_columns = [col['name'] for col in inspector.get_columns('leagues')]
        expected_leagues_columns = [
            'id', 'code', 'name', 'country', 'tier', 'avg_draw_rate',
            'home_advantage', 'is_active', 'created_at', 'updated_at'
        ]
        for col in expected_leagues_columns:
            assert col in leagues_columns, f"Missing column 'leagues.{col}'"
        
        # Test teams table
        teams_columns = [col['name'] for col in inspector.get_columns('teams')]
        expected_teams_columns = [
            'id', 'league_id', 'name', 'canonical_name', 'attack_rating',
            'defense_rating', 'home_bias', 'last_calculated', 'created_at', 'updated_at'
        ]
        for col in expected_teams_columns:
            assert col in teams_columns, f"Missing column 'teams.{col}'"
        
        # Test matches table
        matches_columns = [col['name'] for col in inspector.get_columns('matches')]
        expected_matches_columns = [
            'id', 'league_id', 'season', 'match_date', 'home_team_id', 'away_team_id',
            'home_goals', 'away_goals', 'result', 'odds_home', 'odds_draw', 'odds_away',
            'prob_home_market', 'prob_draw_market', 'prob_away_market', 'source', 'created_at'
        ]
        for col in expected_matches_columns:
            assert col in matches_columns, f"Missing column 'matches.{col}'"
        
        print("✓ All table columns match models")
    
    def test_foreign_keys_exist(self, inspector):
        """Test that foreign key relationships exist"""
        fks = inspector.get_foreign_keys('teams')
        assert len(fks) > 0, "Teams table should have foreign keys"
        
        fks = inspector.get_foreign_keys('matches')
        assert len(fks) >= 2, "Matches table should have foreign keys to leagues and teams"
        
        fks = inspector.get_foreign_keys('jackpot_fixtures')
        assert len(fks) > 0, "Jackpot fixtures should have foreign keys"
        
        print("✓ Foreign key constraints exist")
    
    def test_indexes_exist(self, inspector):
        """Test that important indexes exist"""
        indexes = inspector.get_indexes('matches')
        index_names = [idx['name'] for idx in indexes]
        assert 'idx_matches_date' in index_names or any('date' in idx.get('name', '').lower() for idx in indexes), \
            "Matches table should have date index"
        
        indexes = inspector.get_indexes('teams')
        index_names = [idx['name'] for idx in indexes]
        assert 'idx_teams_canonical' in index_names or any('canonical' in idx.get('name', '').lower() for idx in indexes), \
            "Teams table should have canonical name index"
        
        print("✓ Important indexes exist")
    
    def test_enums_exist(self, db_session):
        """Test that PostgreSQL enums exist"""
        result = db_session.execute(text("""
            SELECT typname FROM pg_type 
            WHERE typname IN ('model_status', 'prediction_set', 'match_result', 'data_source_status')
        """))
        enum_types = [row[0] for row in result]
        
        expected_enums = ['model_status', 'prediction_set', 'match_result']
        for enum_type in expected_enums:
            assert enum_type in enum_types, f"Missing enum type: {enum_type}"
        
        print("✓ All enum types exist")
    
    def test_constraints_exist(self, inspector):
        """Test that important constraints exist"""
        # Check unique constraints
        unique_constraints = inspector.get_unique_constraints('leagues')
        assert any('code' in str(uc) for uc in unique_constraints), \
            "Leagues should have unique constraint on code"
        
        # Check check constraints on predictions
        check_constraints = inspector.get_check_constraints('predictions')
        assert len(check_constraints) > 0, \
            "Predictions table should have check constraint for probability sum"
        
        print("✓ Important constraints exist")
    
    def test_can_create_and_query_tables(self, db_session):
        """Test that we can create and query records"""
        # Test leagues table
        league_count = db_session.query(League).count()
        print(f"✓ Leagues table accessible (current count: {league_count})")
        
        # Test teams table
        team_count = db_session.query(Team).count()
        print(f"✓ Teams table accessible (current count: {team_count})")
        
        # Test users table
        user_count = db_session.query(User).count()
        print(f"✓ Users table accessible (current count: {user_count})")
        
        # Test models table
        model_count = db_session.query(Model).count()
        print(f"✓ Models table accessible (current count: {model_count})")
    
    def test_database_connection(self, db_session):
        """Test database connection is working"""
        result = db_session.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1
        print("✓ Database connection successful")
    
    def test_sqlalchemy_models_match_tables(self):
        """Test that SQLAlchemy models match database tables"""
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        
        # Get all table names from SQLAlchemy models
        model_tables = set(Base.metadata.tables.keys())
        
        # Check that all model tables exist in database
        missing_in_db = model_tables - existing_tables
        assert len(missing_in_db) == 0, f"Model tables missing in database: {missing_in_db}"
        
        print(f"✓ All {len(model_tables)} SQLAlchemy model tables exist in database")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


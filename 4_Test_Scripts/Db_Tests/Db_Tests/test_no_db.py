"""
Tests that don't require database connection
"""
import pytest
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent / "2_Backend_Football_Probability_Engine"
if backend_dir.exists():
    sys.path.insert(0, str(backend_dir))

# Load environment variables
env_file = backend_dir / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

# Don't use conftest fixtures
pytest_plugins = []


class TestImports:
    """Test that all modules can be imported"""
    
    def test_config_imports(self):
        """Test config module imports"""
        from app.config import settings
        assert settings.API_VERSION is not None
        assert settings.DB_HOST is not None
        print(f"✓ Config loaded: API v{settings.API_VERSION}")
    
    def test_models_import(self):
        """Test that models can be imported"""
        from app.db.models import (
            League, Team, Match, TeamFeature,
            Model, TrainingRun, User, Jackpot, JackpotFixture,
            Prediction, ValidationResult, CalibrationData,
            DataSource, IngestionLog, AuditEntry
        )
        print("✓ All database models importable")
    
    def test_services_import(self):
        """Test that services can be imported"""
        # Check what's actually available in the services
        import app.services.team_resolver as team_resolver
        import app.services.data_ingestion as data_ingestion
        # Just verify modules can be imported
        assert team_resolver is not None
        assert data_ingestion is not None
        print("✓ All services importable")
    
    def test_schemas_import(self):
        """Test that Pydantic schemas can be imported"""
        from app.schemas.prediction import PredictionResponse, JackpotInput
        from app.schemas.auth import LoginCredentials, AuthResponse
        from app.schemas.jackpot import Jackpot as JackpotSchema
        print("✓ All Pydantic schemas importable")
    
    def test_api_imports(self):
        """Test that API routers can be imported"""
        from app.api import (
            probabilities, jackpots, validation, data, validation_team,
            auth, model, tasks, export, teams, explainability, audit
        )
        print("✓ All API routers importable")
    
    def test_database_url_construction(self):
        """Test database URL construction"""
        from app.config import settings
        db_url = settings.get_database_url()
        assert db_url.startswith("postgresql+psycopg://")
        assert settings.DB_NAME in db_url
        print(f"✓ Database URL: {db_url.split('@')[1] if '@' in db_url else 'constructed'}")
    
    def test_cors_configuration(self):
        """Test CORS configuration"""
        from app.config import settings
        origins = settings.get_cors_origins()
        assert isinstance(origins, list)
        assert len(origins) > 0
        print(f"✓ CORS configured for {len(origins)} origins: {origins}")


class TestTypeDefinitions:
    """Test type definitions match expectations"""
    
    def test_prediction_sets(self):
        """Test prediction set enum"""
        from app.db.models import PredictionSet
        valid_sets = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        model_sets = [set.value for set in PredictionSet]
        assert set(model_sets) == set(valid_sets)
        print(f"✓ Prediction sets: {model_sets}")
    
    def test_match_results(self):
        """Test match result enum"""
        from app.db.models import MatchResult
        expected_results = ['H', 'D', 'A']
        model_results = [result.value for result in MatchResult]
        assert set(model_results) == set(expected_results)
        print(f"✓ Match results: {model_results}")
    
    def test_model_status(self):
        """Test model status enum"""
        from app.db.models import ModelStatus
        statuses = [status.value for status in ModelStatus]
        assert 'active' in statuses
        assert 'archived' in statuses
        print(f"✓ Model statuses: {statuses}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


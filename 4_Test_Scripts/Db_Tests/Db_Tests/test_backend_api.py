"""
Backend API Tests

Tests for FastAPI endpoints and backend logic.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import SessionLocal, engine
from app.db.models import Base, League, Team, User, Jackpot, Model
import json


@pytest.fixture(scope="module")
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    """Create a database session for testing"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Setup test database (create tables if needed)"""
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup if needed


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert data["service"] == "Football Jackpot Probability Engine"
        print("✓ Root endpoint works")
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "version" in data
        print(f"✓ Health check: {data['status']}, Database: {data['database']}")
    
    def test_api_docs_available(self, client):
        """Test that API documentation is available"""
        response = client.get("/docs")
        assert response.status_code == 200
        print("✓ API documentation available at /docs")


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_login_endpoint_exists(self, client):
        """Test login endpoint exists"""
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword"
        })
        # Should return 401 or 404, not 405 (method not allowed)
        assert response.status_code != 405
        print("✓ Login endpoint exists")
    
    def test_auth_me_endpoint_exists(self, client):
        """Test /auth/me endpoint exists"""
        response = client.get("/api/auth/me")
        # Should return 401 (unauthorized) or 200, not 404
        assert response.status_code != 404
        print("✓ Auth me endpoint exists")


class TestJackpotEndpoints:
    """Test jackpot endpoints"""
    
    def test_get_jackpots_endpoint(self, client):
        """Test GET /jackpots endpoint"""
        response = client.get("/api/jackpots")
        # Should return 200 or 401, not 404
        assert response.status_code != 404
        print("✓ Get jackpots endpoint exists")
    
    def test_create_jackpot_endpoint(self, client):
        """Test POST /jackpots endpoint"""
        response = client.post("/api/jackpots", json={
            "fixtures": []
        })
        # Should return 200, 201, 400, or 401, not 404
        assert response.status_code != 404
        print("✓ Create jackpot endpoint exists")


class TestProbabilityEndpoints:
    """Test probability calculation endpoints"""
    
    def test_get_probabilities_endpoint(self, client):
        """Test GET /jackpots/{id}/probabilities endpoint"""
        response = client.get("/api/jackpots/test-id/probabilities")
        # Should return 404 (not found) or 401, not 405
        assert response.status_code != 405
        print("✓ Get probabilities endpoint exists")
    
    def test_get_probability_set_endpoint(self, client):
        """Test GET /jackpots/{id}/probabilities/{set_id} endpoint"""
        response = client.get("/api/jackpots/test-id/probabilities/A")
        # Should return 404 (not found) or 401, not 405
        assert response.status_code != 405
        print("✓ Get probability set endpoint exists")


class TestModelEndpoints:
    """Test model management endpoints"""
    
    def test_get_model_health(self, client):
        """Test GET /model/health endpoint"""
        response = client.get("/api/model/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        print("✓ Model health endpoint works")
    
    def test_get_model_versions(self, client):
        """Test GET /model/versions endpoint"""
        response = client.get("/api/model/versions")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data or "success" in data
        print("✓ Model versions endpoint works")


class TestDataEndpoints:
    """Test data management endpoints"""
    
    def test_get_data_freshness(self, client):
        """Test GET /data/freshness endpoint"""
        response = client.get("/api/data/freshness")
        # Should return 200 or 401, not 404
        assert response.status_code != 404
        print("✓ Data freshness endpoint exists")
    
    def test_get_data_updates(self, client):
        """Test GET /data/updates endpoint"""
        response = client.get("/api/data/updates")
        # Should return 200 or 401, not 404
        assert response.status_code != 404
        print("✓ Data updates endpoint exists")


class TestValidationEndpoints:
    """Test validation endpoints"""
    
    def test_get_calibration_data(self, client):
        """Test GET /calibration endpoint"""
        response = client.get("/api/calibration")
        # Should return 200 or 401, not 404
        assert response.status_code != 404
        print("✓ Calibration endpoint exists")
    
    def test_validate_team_endpoint(self, client):
        """Test POST /validation/team endpoint"""
        response = client.post("/api/validation/team", json={
            "teamName": "Arsenal"
        })
        # Should return 200, 400, or 401, not 404
        assert response.status_code != 404
        print("✓ Validate team endpoint exists")


class TestBackendLogic:
    """Test backend business logic"""
    
    def test_config_loaded(self):
        """Test that configuration loads correctly"""
        from app.config import settings
        assert settings.API_VERSION is not None
        assert settings.DB_HOST is not None
        assert settings.DB_NAME is not None
        print(f"✓ Configuration loaded: API v{settings.API_VERSION}")
    
    def test_database_url_construction(self):
        """Test database URL construction"""
        from app.config import settings
        db_url = settings.get_database_url()
        assert db_url.startswith("postgresql+psycopg://")
        assert settings.DB_NAME in db_url
        print("✓ Database URL constructed correctly")
    
    def test_cors_configuration(self):
        """Test CORS configuration"""
        from app.config import settings
        origins = settings.get_cors_origins()
        assert isinstance(origins, list)
        assert len(origins) > 0
        print(f"✓ CORS configured for {len(origins)} origins")
    
    def test_models_importable(self):
        """Test that all models can be imported"""
        from app.db.models import (
            League, Team, Match, TeamFeature, Model, TrainingRun,
            User, Jackpot, JackpotFixture, Prediction,
            ValidationResult, CalibrationData, DataSource,
            IngestionLog, AuditEntry
        )
        print("✓ All database models importable")
    
    def test_services_importable(self):
        """Test that services can be imported"""
        from app.services.team_resolver import TeamResolverService
        from app.services.data_ingestion import DataIngestionService
        print("✓ All services importable")
    
    def test_schemas_importable(self):
        """Test that Pydantic schemas can be imported"""
        from app.schemas.prediction import PredictionResponse, JackpotInput
        from app.schemas.auth import LoginCredentials, AuthResponse
        from app.schemas.jackpot import Jackpot as JackpotSchema
        print("✓ All Pydantic schemas importable")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


"""
Integration Tests

Tests that verify frontend and backend work together correctly.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import SessionLocal
from app.db.models import Base, League, Team, User, Jackpot
from app.config import settings


@pytest.fixture(scope="module")
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    """Create a database session"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestFrontendBackendIntegration:
    """Test frontend-backend integration"""
    
    def test_api_base_url_matches_backend(self):
        """Test that frontend API URL matches backend"""
        # Frontend expects: VITE_API_URL or http://localhost:8000/api
        # Backend runs on: http://0.0.0.0:8000 with prefix /api
        expected_prefix = "/api"
        assert settings.API_PREFIX == expected_prefix
        print(f"✓ API prefix matches: {settings.API_PREFIX}")
    
    def test_cors_allows_frontend_origins(self):
        """Test that CORS allows frontend origins"""
        from app.config import settings
        origins = settings.get_cors_origins()
        
        # Check for common frontend dev ports
        frontend_ports = ['5173', '3000', '8080']
        has_frontend_origin = any(
            any(port in origin for port in frontend_ports) 
            for origin in origins
        )
        assert has_frontend_origin, "CORS should allow frontend development origins"
        print(f"✓ CORS configured for frontend: {origins}")
    
    def test_api_response_format_matches_frontend_types(self, client):
        """Test that API responses match frontend TypeScript types"""
        # Test health endpoint format
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        # Should match frontend expectations
        assert "status" in data
        assert "database" in data
        assert isinstance(data["status"], str)
        print("✓ Health endpoint response format matches frontend types")
    
    def test_jackpot_api_matches_frontend_contract(self, client):
        """Test that jackpot API matches frontend contract"""
        # Test GET /jackpots format
        response = client.get("/api/jackpots")
        
        if response.status_code == 200:
            data = response.json()
            # Should have pagination structure or array structure
            assert "data" in data or isinstance(data, list)
            print("✓ Jackpot API format matches frontend contract")
        else:
            # 401 is acceptable (needs auth)
            assert response.status_code in [200, 401]
            print("✓ Jackpot API endpoint exists (requires auth)")


class TestDataFlow:
    """Test data flow between frontend and backend"""
    
    def test_probability_set_structure(self):
        """Test that probability sets match frontend expectations"""
        # Frontend expects sets A-G
        valid_sets = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        
        from app.db.models import PredictionSet
        model_sets = [set.value for set in PredictionSet]
        
        assert set(model_sets) == set(valid_sets), \
            f"Prediction sets mismatch: {model_sets} vs {valid_sets}"
        print("✓ Probability sets match frontend expectations")
    
    def test_match_result_enum_matches_frontend(self):
        """Test that match result enum matches frontend"""
        from app.db.models import MatchResult
        
        # Frontend expects: 'H', 'D', 'A'
        expected_results = ['H', 'D', 'A']
        model_results = [result.value for result in MatchResult]
        
        assert set(model_results) == set(expected_results)
        print("✓ Match result enum matches frontend")
    
    def test_fixture_structure_matches_frontend(self):
        """Test that fixture structure matches frontend Fixture type"""
        # Frontend Fixture type expects:
        # - homeTeam, awayTeam (strings)
        # - homeOdds, drawOdds, awayOdds (numbers)
        # - matchDate (optional string)
        # - league (optional string)
        
        from app.db.models import JackpotFixture
        
        # Check that model has required fields
        assert hasattr(JackpotFixture, 'home_team')
        assert hasattr(JackpotFixture, 'away_team')
        assert hasattr(JackpotFixture, 'odds_home')
        assert hasattr(JackpotFixture, 'odds_draw')
        assert hasattr(JackpotFixture, 'odds_away')
        
        print("✓ Fixture structure matches frontend type")


class TestDatabaseFrontendAlignment:
    """Test database schema alignment with frontend"""
    
    def test_user_structure_matches_frontend(self):
        """Test that User model matches frontend User type"""
        from app.db.models import User
        
        # Frontend expects: id, email, name
        assert hasattr(User, 'id')
        assert hasattr(User, 'email')
        assert hasattr(User, 'name')
        
        print("✓ User structure matches frontend")
    
    def test_jackpot_structure_matches_frontend(self):
        """Test that Jackpot model matches frontend Jackpot type"""
        from app.db.models import Jackpot
        
        # Frontend expects: id, name, fixtures, createdAt, modelVersion, status
        assert hasattr(Jackpot, 'id')
        assert hasattr(Jackpot, 'jackpot_id')  # Maps to frontend 'id'
        assert hasattr(Jackpot, 'name')
        assert hasattr(Jackpot, 'status')
        assert hasattr(Jackpot, 'model_version')
        assert hasattr(Jackpot, 'created_at')
        
        print("✓ Jackpot structure matches frontend")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


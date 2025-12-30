"""
Pytest configuration and shared fixtures
"""
import pytest
import os
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent / "2_Backend_Football_Probability_Engine"
if backend_dir.exists():
    sys.path.insert(0, str(backend_dir))

# Load environment variables from .env file if it exists
env_file = backend_dir / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from app.db.base import Base
from app.config import settings


# Global flag to track if database is available
DATABASE_AVAILABLE = None


def check_database_available():
    """Check if database is available"""
    global DATABASE_AVAILABLE
    if DATABASE_AVAILABLE is None:
        try:
            test_db_url = os.getenv("TEST_DATABASE_URL", settings.get_database_url())
            engine = create_engine(test_db_url, connect_args={"connect_timeout": 2})
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            DATABASE_AVAILABLE = True
        except Exception:
            DATABASE_AVAILABLE = False
    return DATABASE_AVAILABLE


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine"""
    if not check_database_available():
        pytest.skip("Database not available - skipping database tests")
    
    test_db_url = os.getenv("TEST_DATABASE_URL", settings.get_database_url())
    engine = create_engine(test_db_url)
    return engine


@pytest.fixture(scope="session", autouse=False)
def setup_test_database(test_engine):
    """Setup test database schema (not auto-used)"""
    if not check_database_available():
        return
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=test_engine)
        yield
        # Optionally drop tables after tests
        # Base.metadata.drop_all(bind=test_engine)
    except OperationalError as e:
        pytest.skip(f"Database connection failed: {e}")


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a database session for each test"""
    if not check_database_available():
        pytest.skip("Database not available")
    
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


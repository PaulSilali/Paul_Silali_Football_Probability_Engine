"""
Application configuration using Pydantic settings
"""
from pydantic_settings import BaseSettings
from typing import List, Optional, Union
from urllib.parse import quote_plus
import os
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database - Individual connection parameters (preferred)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "football_probability_engine"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    
    # Database - Full URL (optional, will be constructed from individual params if not provided)
    DATABASE_URL: Optional[str] = None
    
    # Database connection pool settings
    # Increased for concurrent data ingestion operations
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    DATABASE_ECHO: bool = False
    
    def get_database_url(self) -> str:
        """Get database URL, constructing it from individual components if not provided"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        # Construct from individual components
        password_encoded = quote_plus(self.DB_PASSWORD) if self.DB_PASSWORD else ""
        return (
            f"postgresql+psycopg://{self.DB_USER}:{password_encoded}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    
    @property
    def database_url(self) -> str:
        """Property accessor for DATABASE_URL"""
        return self.get_database_url()
    
    # API Configuration
    API_PREFIX: str = "/api"
    API_TITLE: str = "Football Jackpot Probability Engine API"
    API_VERSION: str = "v2.4.1"
    
    # CORS - Accept comma-separated string or JSON array
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:8080,http://localhost:3000,http://localhost:8081"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: Union[str, List[str]] = "*"
    CORS_ALLOW_HEADERS: Union[str, List[str]] = "*"
    
    def get_cors_origins(self) -> List[str]:
        """Parse CORS_ORIGINS from string or list"""
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        if isinstance(self.CORS_ORIGINS, str):
            # Try JSON first
            try:
                parsed = json.loads(self.CORS_ORIGINS)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            # Fall back to comma-separated
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return []
    
    def get_cors_methods(self) -> List[str]:
        """Parse CORS_ALLOW_METHODS from string or list"""
        if isinstance(self.CORS_ALLOW_METHODS, list):
            return self.CORS_ALLOW_METHODS
        if isinstance(self.CORS_ALLOW_METHODS, str):
            if self.CORS_ALLOW_METHODS == "*":
                # Return explicit methods for better compatibility
                return ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
            return [method.strip() for method in self.CORS_ALLOW_METHODS.split(",") if method.strip()]
        return ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
    
    def get_cors_headers(self) -> List[str]:
        """Parse CORS_ALLOW_HEADERS from string or list"""
        if isinstance(self.CORS_ALLOW_HEADERS, list):
            return self.CORS_ALLOW_HEADERS
        if isinstance(self.CORS_ALLOW_HEADERS, str):
            if self.CORS_ALLOW_HEADERS == "*":
                return ["*"]
            return [header.strip() for header in self.CORS_ALLOW_HEADERS.split(",") if header.strip()]
        return ["*"]
    
    # Security
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # External APIs
    API_FOOTBALL_KEY: str = ""
    FOOTBALL_DATA_BASE_URL: str = "https://www.football-data.co.uk"
    FOOTBALL_DATA_ORG_KEY: str = ""  # Football-Data.org API key (free tier available)
    FOOTBALL_DATA_ORG_BASE_URL: str = "https://api.football-data.org/v4"
    
    # OpenFootball Local Data Path (optional)
    # If set, will use local files instead of downloading from GitHub
    # Should point to the repository root folder (e.g., "12_Important_Documets/world-master" for world repo)
    # For europe and south-america repos, set separate paths or use full path
    OPENFOOTBALL_LOCAL_PATH: Optional[str] = None  # e.g., "12_Important_Documets/world-master"
    
    # Environment
    ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Model Configuration
    MODEL_VERSION: str = "v2.4.1"
    DEFAULT_DECAY_RATE: float = 0.0065
    DEFAULT_HOME_ADVANTAGE: float = 0.35
    DEFAULT_RHO: float = -0.13
    
    # Constants
    MIN_VALID_ODDS: float = 1.01
    MAX_VALID_ODDS: float = 100.0
    PROBABILITY_SUM_TOLERANCE: float = 0.001
    MAX_GOALS_IN_CALCULATION: int = 8
    
    # Data Cleaning Configuration
    ENABLE_DATA_CLEANING: bool = True  # Enable data cleaning
    DATA_CLEANING_MISSING_THRESHOLD: float = 0.5  # Drop columns with >50% missing
    DATA_CLEANING_PHASE: str = "phase2"  # "phase1", "phase2", or "both" - Phase 2 includes Phase 1 + outlier-based features
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        env_file_encoding = 'utf-8'
        # Ignore parsing errors for comment lines and empty lines
        env_ignore_empty = True


settings = Settings()


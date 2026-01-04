"""
SQLAlchemy 2.0 Database Models

All tables follow the architecture specification exactly.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, 
    ForeignKey, Enum, JSON, Boolean, Text,
    UniqueConstraint, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.db.base import Base


# ============================================================================
# ENUMS
# ============================================================================

class ModelStatus(enum.Enum):
    active = "active"
    archived = "archived"
    failed = "failed"
    training = "training"


class PredictionSet(enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    H = "H"
    I = "I"
    J = "J"


class MatchResult(enum.Enum):
    H = "H"  # Home win
    D = "D"  # Draw
    A = "A"  # Away win


# ============================================================================
# REFERENCE TABLES
# ============================================================================

class League(Base):
    __tablename__ = "leagues"
    
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    tier = Column(Integer, default=1)
    avg_draw_rate = Column(Float, default=0.26)
    home_advantage = Column(Float, default=0.35)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    teams = relationship("Team", back_populates="league")
    matches = relationship("Match", back_populates="league")
    league_stats = relationship("LeagueStats", back_populates="league")


class Team(Base):
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    name = Column(String, nullable=False)
    canonical_name = Column(String, nullable=False)
    attack_rating = Column(Float, default=1.0)
    defense_rating = Column(Float, default=1.0)
    home_bias = Column(Float, default=0.0)
    last_calculated = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    league = relationship("League", back_populates="teams")
    home_matches = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")
    
    __table_args__ = (
        UniqueConstraint('canonical_name', 'league_id', name='uix_team_league'),
        Index('idx_teams_canonical', 'canonical_name'),
    )


# ============================================================================
# HISTORICAL DATA
# ============================================================================

class Match(Base):
    __tablename__ = "matches"
    
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    season = Column(String, nullable=False)
    match_date = Column(Date, nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    home_goals = Column(Integer, nullable=False)
    away_goals = Column(Integer, nullable=False)
    result = Column(Enum(MatchResult, name='match_result', create_type=False), nullable=False)
    
    # Closing odds
    odds_home = Column(Float)
    odds_draw = Column(Float)
    odds_away = Column(Float)
    
    # Market-implied probabilities
    prob_home_market = Column(Float)
    prob_draw_market = Column(Float)
    prob_away_market = Column(Float)
    
    source = Column(String, default='football-data.co.uk')
    created_at = Column(DateTime, server_default=func.now())
    
    league = relationship("League", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    
    __table_args__ = (
        UniqueConstraint('home_team_id', 'away_team_id', 'match_date', name='uix_match'),
        Index('idx_matches_date', 'match_date'),
        Index('idx_matches_teams', 'home_team_id', 'away_team_id'),
        Index('idx_matches_league_season', 'league_id', 'season'),
    )


class TeamFeature(Base):
    __tablename__ = "team_features"
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    calculated_at = Column(DateTime, nullable=False)
    
    # Rolling metrics
    goals_scored_5 = Column(Float)
    goals_scored_10 = Column(Float)
    goals_scored_20 = Column(Float)
    goals_conceded_5 = Column(Float)
    goals_conceded_10 = Column(Float)
    goals_conceded_20 = Column(Float)
    
    # Win rates
    win_rate_5 = Column(Float)
    win_rate_10 = Column(Float)
    draw_rate_5 = Column(Float)
    draw_rate_10 = Column(Float)
    
    # Splits
    home_win_rate = Column(Float)
    away_win_rate = Column(Float)
    
    avg_rest_days = Column(Float)
    league_position = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_team_features_lookup', 'team_id', 'calculated_at'),
    )


class LeagueStats(Base):
    """League-level baseline statistics per season"""
    __tablename__ = "league_stats"
    
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False)
    season = Column(String, nullable=False)
    calculated_at = Column(DateTime, nullable=False)
    
    total_matches = Column(Integer, nullable=False)
    home_win_rate = Column(Float, nullable=False)
    draw_rate = Column(Float, nullable=False)
    away_win_rate = Column(Float, nullable=False)
    avg_goals_per_match = Column(Float, nullable=False)
    home_advantage_factor = Column(Float, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    
    league = relationship("League", back_populates="league_stats")
    
    __table_args__ = (
        UniqueConstraint('league_id', 'season', name='uix_league_stats'),
    )


# ============================================================================
# MODEL TABLES
# ============================================================================

class Model(Base):
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True)
    version = Column(String, unique=True, nullable=False)
    model_type = Column(String, nullable=False)
    status = Column(Enum(ModelStatus), default=ModelStatus.active)
    
    # Training metadata
    training_started_at = Column(DateTime)
    training_completed_at = Column(DateTime)
    training_matches = Column(Integer)
    training_leagues = Column(JSON)
    training_seasons = Column(JSON)
    
    # Parameters
    decay_rate = Column(Float)
    blend_alpha = Column(Float)
    
    # Metrics
    brier_score = Column(Float)
    log_loss = Column(Float)
    draw_accuracy = Column(Float)
    overall_accuracy = Column(Float)
    
    # Stored weights (JSON)
    model_weights = Column(JSON)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    predictions = relationship("Prediction", back_populates="model")


class TrainingRun(Base):
    __tablename__ = "training_runs"
    
    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey("models.id"))
    run_type = Column(String, nullable=False)
    status = Column(Enum(ModelStatus))
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    
    match_count = Column(Integer)
    date_from = Column(Date)
    date_to = Column(Date)
    
    brier_score = Column(Float)
    log_loss = Column(Float)
    validation_accuracy = Column(Float)
    error_message = Column(Text)
    logs = Column(JSON)
    
    # Entropy and temperature metrics (for uncertainty monitoring)
    avg_entropy = Column(Float)
    p10_entropy = Column(Float)
    p90_entropy = Column(Float)
    temperature = Column(Float)
    alpha_mean = Column(Float)
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_training_runs_entropy', 'avg_entropy'),
        Index('idx_training_runs_temperature', 'temperature'),
    )


# ============================================================================
# JACKPOT TABLES
# ============================================================================

class Jackpot(Base):
    __tablename__ = "jackpots"
    
    id = Column(Integer, primary_key=True)
    jackpot_id = Column(String, unique=True, nullable=False)
    user_id = Column(String)  # From auth
    name = Column(String)
    kickoff_date = Column(Date)
    status = Column(String, default='pending')
    model_version = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    fixtures = relationship("JackpotFixture", back_populates="jackpot", cascade="all, delete-orphan")


class JackpotFixture(Base):
    __tablename__ = "jackpot_fixtures"
    
    id = Column(Integer, primary_key=True)
    jackpot_id = Column(Integer, ForeignKey("jackpots.id", ondelete="CASCADE"), nullable=False)
    match_order = Column(Integer, nullable=False)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    
    # Input odds
    odds_home = Column(Float, nullable=False)
    odds_draw = Column(Float, nullable=False)
    odds_away = Column(Float, nullable=False)
    
    # Resolved team IDs
    home_team_id = Column(Integer, ForeignKey("teams.id"))
    away_team_id = Column(Integer, ForeignKey("teams.id"))
    league_id = Column(Integer, ForeignKey("leagues.id"))
    referee_id = Column(Integer, ForeignKey("referee_stats.referee_id"))
    
    # Actual result (for validation)
    actual_result = Column(Enum(MatchResult, name='match_result', create_type=False))
    actual_home_goals = Column(Integer)
    actual_away_goals = Column(Integer)
    
    created_at = Column(DateTime, server_default=func.now())
    
    jackpot = relationship("Jackpot", back_populates="fixtures")
    predictions = relationship("Prediction", back_populates="fixture", cascade="all, delete-orphan")


class TeamH2HStats(Base):
    """Head-to-head statistics for team pairs"""
    __tablename__ = "team_h2h_stats"
    
    id = Column(Integer, primary_key=True)
    team_home_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    team_away_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    meetings = Column(Integer, nullable=False, default=0)
    draws = Column(Integer, nullable=False, default=0)
    home_draws = Column(Integer, nullable=False, default=0)
    away_draws = Column(Integer, nullable=False, default=0)
    draw_rate = Column(Float, nullable=False, default=0.0)
    home_draw_rate = Column(Float, nullable=False, default=0.0)
    away_draw_rate = Column(Float, nullable=False, default=0.0)
    league_draw_rate = Column(Float, nullable=False, default=0.0)
    h2h_draw_index = Column(Float, nullable=False, default=1.0)
    last_meeting_date = Column(Date)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('team_home_id', 'team_away_id', name='uix_h2h_pair'),
        Index('idx_h2h_pair', 'team_home_id', 'team_away_id'),
        Index('idx_h2h_draw_index', 'h2h_draw_index'),
    )


class SavedJackpotTemplate(Base):
    """Saved fixture list templates for reuse"""
    __tablename__ = "saved_jackpot_templates"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String)  # From auth
    name = Column(String, nullable=False)
    description = Column(Text)
    fixtures = Column(JSON, nullable=False)  # Array of fixtures
    fixture_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint('fixture_count >= 1 AND fixture_count <= 20', name='chk_fixture_count'),
        Index('idx_saved_templates_user', 'user_id'),
        Index('idx_saved_templates_created', 'created_at'),
    )


class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True)
    fixture_id = Column(Integer, ForeignKey("jackpot_fixtures.id", ondelete="CASCADE"), nullable=False)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    set_type = Column(Enum(PredictionSet, name='prediction_set', create_type=False), nullable=False)
    
    # Probabilities
    prob_home = Column(Float, nullable=False)
    prob_draw = Column(Float, nullable=False)
    prob_away = Column(Float, nullable=False)
    
    predicted_outcome = Column(Enum(MatchResult, name='match_result', create_type=False), nullable=False)
    confidence = Column(Float, nullable=False)
    entropy = Column(Float)
    
    # Draw model components (for explainability and auditing)
    # Stores JSON: {"poisson": 0.25, "dixon_coles": 0.27, "market": 0.26}
    draw_components = Column(JSON)
    
    # Model components
    expected_home_goals = Column(Float)
    expected_away_goals = Column(Float)
    model_prob_home = Column(Float)
    model_prob_draw = Column(Float)
    model_prob_away = Column(Float)
    market_prob_home = Column(Float)
    market_prob_draw = Column(Float)
    market_prob_away = Column(Float)
    blend_weight = Column(Float)
    
    created_at = Column(DateTime, server_default=func.now())
    
    fixture = relationship("JackpotFixture", back_populates="predictions")
    model = relationship("Model", back_populates="predictions")
    
    __table_args__ = (
        Index('idx_predictions_fixture', 'fixture_id'),
        Index('idx_predictions_set', 'set_type'),
        Index('idx_predictions_model', 'model_id'),
        CheckConstraint(
            'abs((prob_home + prob_draw + prob_away) - 1.0) < 0.001',
            name='check_prob_sum'
        ),
    )


# ============================================================================
# VALIDATION TABLES
# ============================================================================

class ValidationResult(Base):
    __tablename__ = "validation_results"
    
    id = Column(Integer, primary_key=True)
    jackpot_id = Column(Integer, ForeignKey("jackpots.id", ondelete="CASCADE"))
    set_type = Column(Enum(PredictionSet, name='prediction_set', create_type=False), nullable=False)
    model_id = Column(Integer, ForeignKey("models.id"))
    
    total_matches = Column(Integer)
    correct_predictions = Column(Integer)
    accuracy = Column(Float)
    brier_score = Column(Float)
    log_loss = Column(Float)
    
    # Breakdown by outcome
    home_correct = Column(Integer)
    home_total = Column(Integer)
    draw_correct = Column(Integer)
    draw_total = Column(Integer)
    away_correct = Column(Integer)
    away_total = Column(Integer)
    
    exported_to_training = Column(Boolean, default=False)
    exported_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_validation_results_jackpot', 'jackpot_id'),
        Index('idx_validation_results_model', 'model_id'),
    )
    
    __table_args__ = (
        Index('idx_validation_results_jackpot', 'jackpot_id'),
        Index('idx_validation_results_model', 'model_id'),
    )


class CalibrationData(Base):
    __tablename__ = "calibration_data"
    
    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey("models.id"))
    league_id = Column(Integer, ForeignKey("leagues.id"))
    outcome_type = Column(Enum(MatchResult, name='match_result', create_type=False), nullable=False)
    
    predicted_prob_bucket = Column(Float, nullable=False)
    actual_frequency = Column(Float, nullable=False)
    sample_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
# DATA INGESTION TABLES
# ============================================================================

class DataSource(Base):
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    source_type = Column(String, nullable=False)
    status = Column(String, default='fresh')
    last_sync_at = Column(DateTime)
    record_count = Column(Integer, default=0)
    last_error = Column(Text)
    config = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class IngestionLog(Base):
    __tablename__ = "ingestion_logs"
    
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"))
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    status = Column(String, default='running')
    records_processed = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    error_message = Column(Text)
    logs = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
# USER & AUTH TABLES
# ============================================================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SavedProbabilityResult(Base):
    """Saved probability output selections and actual results for backtesting"""
    __tablename__ = "saved_probability_results"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String)  # From auth
    jackpot_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # User selections per probability set
    selections = Column(JSON, nullable=False)  # {"A": {"fixture_1": "1", "fixture_2": "X"}, "B": {...}}
    
    # Actual results (entered after matches complete)
    actual_results = Column(JSON)  # {"fixture_1": "X", "fixture_2": "1"}
    
    # Score tracking per set
    scores = Column(JSON)  # {"A": {"correct": 10, "total": 15}, "B": {...}}
    
    # Metadata
    model_version = Column(String)
    total_fixtures = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint('total_fixtures >= 1 AND total_fixtures <= 20', name='chk_total_fixtures'),
        Index('idx_saved_results_user', 'user_id'),
        Index('idx_saved_results_jackpot', 'jackpot_id'),
        Index('idx_saved_results_created', 'created_at'),
    )


class AuditEntry(Base):
    __tablename__ = "audit_entries"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    action = Column(String, nullable=False)
    model_version = Column(String)
    probability_set = Column(String)
    jackpot_id = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    details = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_jackpot', 'jackpot_id'),
        Index('idx_audit_user', 'user_id'),
    )


# ============================================================================
# DRAW STRUCTURAL MODELING TABLES
# ============================================================================

class LeagueDrawPrior(Base):
    """League-level draw priors for structural draw modeling"""
    __tablename__ = "league_draw_priors"
    
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False)
    season = Column(String(20), nullable=False)
    draw_rate = Column(Float, nullable=False)
    sample_size = Column(Integer, nullable=False)
    updated_at = Column(DateTime, server_default=func.now())
    
    league = relationship("League")
    
    __table_args__ = (
        UniqueConstraint('league_id', 'season', name='uix_league_draw_prior'),
        Index('idx_league_draw_priors_league', 'league_id'),
        Index('idx_league_draw_priors_season', 'season'),
    )


class H2HDrawStats(Base):
    """Head-to-head statistics specifically for draw probability modeling"""
    __tablename__ = "h2h_draw_stats"
    
    id = Column(Integer, primary_key=True)
    team_home_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    team_away_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    matches_played = Column(Integer, nullable=False, default=0)
    draw_count = Column(Integer, nullable=False, default=0)
    avg_goals = Column(Float)
    last_updated = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('team_home_id', 'team_away_id', name='uix_h2h_draw_pair'),
        Index('idx_h2h_draw_pair', 'team_home_id', 'team_away_id'),
    )


class TeamElo(Base):
    """Team Elo ratings over time for draw symmetry modeling"""
    __tablename__ = "team_elo"
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    elo_rating = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    team = relationship("Team")
    
    __table_args__ = (
        UniqueConstraint('team_id', 'date', name='uix_team_elo_date'),
        Index('idx_team_elo_team_date', 'team_id', 'date'),
        Index('idx_team_elo_date', 'date'),
    )


class MatchWeather(Base):
    """Weather conditions at match time for draw probability adjustment"""
    __tablename__ = "match_weather"
    
    id = Column(Integer, primary_key=True)
    fixture_id = Column(Integer, ForeignKey("jackpot_fixtures.id", ondelete="CASCADE"), nullable=False)
    temperature = Column(Float)
    rainfall = Column(Float)
    wind_speed = Column(Float)
    weather_draw_index = Column(Float)
    recorded_at = Column(DateTime, server_default=func.now())
    
    fixture = relationship("JackpotFixture")
    
    __table_args__ = (
        UniqueConstraint('fixture_id', name='uix_match_weather_fixture'),
        Index('idx_match_weather_fixture', 'fixture_id'),
        Index('idx_match_weather_index', 'weather_draw_index'),
    )


class RefereeStats(Base):
    """Referee behavioral statistics for draw probability adjustment"""
    __tablename__ = "referee_stats"
    
    id = Column(Integer, primary_key=True)
    referee_id = Column(Integer, unique=True, nullable=False)
    referee_name = Column(String(200))
    matches = Column(Integer, nullable=False, default=0)
    avg_cards = Column(Float)
    avg_penalties = Column(Float)
    draw_rate = Column(Float)
    updated_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_referee_stats_id', 'referee_id'),
        Index('idx_referee_stats_draw_rate', 'draw_rate'),
    )


class TeamRestDays(Base):
    """Team rest days and congestion data for fatigue-based draw adjustment"""
    __tablename__ = "team_rest_days"
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    fixture_id = Column(Integer, ForeignKey("jackpot_fixtures.id", ondelete="CASCADE"), nullable=False)
    rest_days = Column(Integer, nullable=False)
    is_midweek = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    team = relationship("Team")
    fixture = relationship("JackpotFixture")
    
    __table_args__ = (
        UniqueConstraint('team_id', 'fixture_id', name='uix_team_rest_fixture'),
        Index('idx_team_rest_team', 'team_id'),
        Index('idx_team_rest_fixture', 'fixture_id'),
        Index('idx_team_rest_days', 'rest_days'),
    )


class OddsMovement(Base):
    """Odds movement data for draw probability adjustment"""
    __tablename__ = "odds_movement"
    
    id = Column(Integer, primary_key=True)
    fixture_id = Column(Integer, ForeignKey("jackpot_fixtures.id", ondelete="CASCADE"), nullable=False)
    draw_open = Column(Float)
    draw_close = Column(Float)
    draw_delta = Column(Float)
    recorded_at = Column(DateTime, server_default=func.now())
    
    fixture = relationship("JackpotFixture")
    
    __table_args__ = (
        UniqueConstraint('fixture_id', name='uix_odds_movement_fixture'),
        Index('idx_odds_movement_fixture', 'fixture_id'),
        Index('idx_odds_movement_delta', 'draw_delta'),
    )


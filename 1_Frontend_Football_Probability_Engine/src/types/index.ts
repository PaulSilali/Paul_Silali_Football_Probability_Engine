// Core application types for Football Jackpot Probability Engine

// Authentication
export interface User {
  id: string;
  email: string;
  name: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthResponse {
  user: User;
  token: string;
  refreshToken?: string;
}

// Fixture & Jackpot
export interface Fixture {
  id: string;
  homeTeam: string;
  awayTeam: string;
  homeOdds: number;
  drawOdds: number;
  awayOdds: number;
  matchDate?: string;
  league?: string;
  validationWarnings?: string[];
}

export interface Jackpot {
  id: string;
  name: string;
  fixtures: Fixture[];
  createdAt: string;
  modelVersion: string;
  status: 'draft' | 'submitted' | 'calculated';
}

// Probability Output
export interface FixtureProbability {
  fixtureId: string;
  homeTeam: string;
  awayTeam: string;
  homeWinProbability: number;
  drawProbability: number;
  awayWinProbability: number;
  confidenceLow?: number;
  confidenceHigh?: number;
}

export interface ProbabilitySet {
  id: string;
  name: string;
  description: string;
  probabilities: FixtureProbability[];
}

// Calibration & Validation
export interface CalibrationPoint {
  predictedProbability: number;
  observedFrequency: number;
  sampleSize: number;
}

export interface BrierScorePoint {
  date: string;
  score: number;
  league?: string;
}

export interface CalibrationData {
  reliabilityCurve: CalibrationPoint[];
  brierScoreTrend: BrierScorePoint[];
  expectedVsActual: {
    outcome: string;
    expected: number;
    actual: number;
  }[];
}

// Model Explainability
export interface FeatureContribution {
  fixtureId: string;
  contributions: {
    feature: string;
    value: number;
    description: string;
  }[];
}

// Model Health
export type ModelStatus = 'stable' | 'watch' | 'degraded';

export interface ModelHealth {
  status: ModelStatus;
  lastValidationDate: string;
  oddsDistribution: {
    divergence: number;
    bucket: string;
  }[];
  leagueDrift: {
    league: string;
    driftScore: number;
    signal: 'normal' | 'elevated' | 'high';
  }[];
}

// System Management
export interface ModelVersion {
  id: string;
  version: string;
  releaseDate: string;
  description: string;
  isActive: boolean;
  lockedJackpots: number;
}

export interface DataUpdate {
  id: string;
  source: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress: number;
  startedAt: string;
  completedAt?: string;
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  action: string;
  modelVersion: string;
  probabilitySet: string;
  jackpotId?: string;
  details: string;
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
}

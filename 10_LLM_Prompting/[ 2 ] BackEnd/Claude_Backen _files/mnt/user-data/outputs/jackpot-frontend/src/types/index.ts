/**
 * Core Type Definitions for Jackpot Probability Engine
 * 
 * These types define the contract between frontend and backend,
 * ensuring type safety across the application.
 */

// ============================================================================
// FIXTURE & INPUT TYPES
// ============================================================================

export interface Fixture {
  id: string;
  homeTeam: string;
  awayTeam: string;
  odds: MarketOdds | null;
}

export interface MarketOdds {
  home: number;  // 1X2 format: home win odds
  draw: number;  // X
  away: number;  // 2
  bookmaker?: string;
  timestamp?: string;
}

export interface JackpotInput {
  fixtures: Fixture[];
  createdAt: string;
}

// ============================================================================
// PROBABILITY TYPES
// ============================================================================

export interface MatchProbabilities {
  home: number;    // 0.0 to 1.0
  draw: number;    // 0.0 to 1.0
  away: number;    // 0.0 to 1.0
  entropy: number; // Shannon entropy
}

export interface ProbabilitySet {
  id: ProbabilitySetId;
  name: string;
  description: string;
  methodology: string;
  useCase: string;
  riskProfile: 'conservative' | 'balanced' | 'aggressive';
  probabilities: MatchProbabilities[];
}

export type ProbabilitySetId = 
  | 'A_pure_model'
  | 'B_balanced'
  | 'C_market_dominant'
  | 'D_draw_boosted'
  | 'E_entropy_penalized'
  | 'F_kelly_weighted'
  | 'G_ensemble';

// ============================================================================
// PREDICTION RESPONSE
// ============================================================================

export interface PredictionResponse {
  predictionId: string;
  modelVersion: string;
  createdAt: string;
  fixtures: Fixture[];
  probabilitySets: Record<ProbabilitySetId, MatchProbabilities[]>;
  confidenceFlags: Record<number, ConfidenceLevel>;
  explainability?: Record<number, FeatureContribution[]>;
  warnings?: PredictionWarning[];
}

export type ConfidenceLevel = 'low' | 'medium' | 'high';

export interface PredictionWarning {
  fixtureId: string;
  type: 'missing_odds' | 'new_team' | 'high_uncertainty' | 'stale_data';
  message: string;
  severity: 'info' | 'warning' | 'error';
}

// ============================================================================
// EXPLAINABILITY
// ============================================================================

export interface FeatureContribution {
  name: string;
  contribution: number;  // Signed contribution to log-odds
  description: string;
}

export interface MatchExplainability {
  fixtureId: string;
  baseRate: MatchProbabilities;
  features: FeatureContribution[];
  modelVsMarket: {
    modelProbabilities: MatchProbabilities;
    marketImplied: MatchProbabilities;
    divergence: number;
  };
}

// ============================================================================
// CALIBRATION & VALIDATION
// ============================================================================

export interface CalibrationMetrics {
  brierScore: number;
  logLoss: number;
  calibrationError: number;
  sampleSize: number;
  timeWindow: {
    start: string;
    end: string;
  };
}

export interface ReliabilityPoint {
  predictedProbability: number;
  observedFrequency: number;
  count: number;
}

export interface ReliabilityCurve {
  outcome: 'home' | 'draw' | 'away';
  points: ReliabilityPoint[];
}

export interface ValidationMetrics {
  overallBrier: number;
  brierTrend: BrierScorePoint[];
  reliabilityCurves: ReliabilityCurve[];
  expectedVsObserved: ExpectedVsObserved[];
}

export interface BrierScorePoint {
  date: string;
  score: number;
  league?: string;
}

export interface ExpectedVsObserved {
  outcome: 'home' | 'draw' | 'away';
  expected: number;
  observed: number;
  sampleSize: number;
}

// ============================================================================
// MODEL HEALTH & MONITORING
// ============================================================================

export interface ModelHealth {
  status: 'healthy' | 'watch' | 'degraded';
  lastChecked: string;
  metrics: {
    modelMarketDivergence: number;
    oddsVolatilityIndex: number;
    averageEntropy: number;
  };
  alerts: ModelAlert[];
  driftIndicators: DriftIndicator[];
}

export interface ModelAlert {
  id: string;
  timestamp: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  resolved: boolean;
}

export interface DriftIndicator {
  metric: string;
  currentValue: number;
  threshold: number;
  status: 'normal' | 'warning' | 'critical';
  league?: string;
}

// ============================================================================
// MODEL & DATA MANAGEMENT
// ============================================================================

export interface ModelVersion {
  version: string;
  trainedAt: string;
  dataVersion: string;
  validationMetrics: CalibrationMetrics;
  status: 'active' | 'archived';
  hyperparameters?: Record<string, unknown>;
}

export interface DataSource {
  name: string;
  type: 'api' | 'csv';
  lastUpdate: string;
  coverage: LeagueCoverage[];
}

export interface LeagueCoverage {
  leagueId: string;
  leagueName: string;
  seasons: string[];
  matchCount: number;
  status: 'complete' | 'partial' | 'outdated';
}

export interface DataRefreshTask {
  taskId: string;
  status: 'queued' | 'running' | 'complete' | 'failed';
  progress: number;
  startedAt?: string;
  completedAt?: string;
  error?: string;
  details?: {
    league: string;
    season: string;
    matchesAdded: number;
  };
}

// ============================================================================
// API RESPONSE TYPES
// ============================================================================

export interface ApiResponse<T> {
  data?: T;
  error?: ApiError;
  meta?: {
    requestId: string;
    timestamp: string;
  };
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// ============================================================================
// UI STATE TYPES
// ============================================================================

export interface AppState {
  // Current jackpot being edited
  currentJackpot: JackpotInput | null;
  
  // Active prediction
  activePrediction: PredictionResponse | null;
  
  // Selected probability sets for comparison
  selectedSets: ProbabilitySetId[];
  
  // UI state
  activeSection: NavigationSection;
  isLoading: boolean;
  error: string | null;
  
  // Model state
  currentModelVersion: ModelVersion | null;
  modelHealth: ModelHealth | null;
  
  // Validation data
  validationMetrics: ValidationMetrics | null;
}

export type NavigationSection = 
  | 'input'
  | 'output'
  | 'comparison'
  | 'calibration'
  | 'explainability'
  | 'health'
  | 'management';

// ============================================================================
// EXPORT TYPES
// ============================================================================

export interface ExportOptions {
  format: 'csv' | 'pdf' | 'json';
  includeSets: ProbabilitySetId[];
  includeExplainability: boolean;
}

export interface CSVExportRow {
  fixture: string;
  homeTeam: string;
  awayTeam: string;
  marketOdds: string;
  [key: string]: string | number; // Dynamic columns for each probability set
}

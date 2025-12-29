/**
 * Utility Functions
 * 
 * Helper functions for probability calculations, formatting,
 * and common operations.
 */

import type { MatchProbabilities, ProbabilitySetId } from '../types';

// ============================================================================
// PROBABILITY CALCULATIONS
// ============================================================================

/**
 * Calculate Shannon entropy of probability distribution
 */
export function calculateEntropy(probs: MatchProbabilities): number {
  const values = [probs.home, probs.draw, probs.away];
  return -values.reduce((sum, p) => {
    if (p === 0) return sum;
    return sum + p * Math.log2(p);
  }, 0);
}

/**
 * Verify probabilities sum to 1.0 (within tolerance)
 */
export function validateProbabilities(
  probs: MatchProbabilities,
  tolerance: number = 0.001
): boolean {
  const sum = probs.home + probs.draw + probs.away;
  return Math.abs(sum - 1.0) < tolerance;
}

/**
 * Convert odds to implied probability
 */
export function oddsToImpliedProbability(odds: number): number {
  return 1 / odds;
}

/**
 * Remove bookmaker margin from odds
 */
export function removeBk(odds: { home: number; draw: number; away: number }): {
  home: number;
  draw: number;
  away: number;
} {
  const impliedProbs = {
    home: oddsToImpliedProbability(odds.home),
    draw: oddsToImpliedProbability(odds.draw),
    away: oddsToImpliedProbability(odds.away),
  };
  
  const total = impliedProbs.home + impliedProbs.draw + impliedProbs.away;
  
  return {
    home: impliedProbs.home / total,
    draw: impliedProbs.draw / total,
    away: impliedProbs.away / total,
  };
}

/**
 * Calculate divergence between two probability distributions
 * (using Jensen-Shannon divergence)
 */
export function calculateDivergence(
  p1: MatchProbabilities,
  p2: MatchProbabilities
): number {
  const m = {
    home: (p1.home + p2.home) / 2,
    draw: (p1.draw + p2.draw) / 2,
    away: (p1.away + p2.away) / 2,
  };
  
  const kl1 = kldivergence(p1, m);
  const kl2 = kldivergence(p2, m);
  
  return (kl1 + kl2) / 2;
}

function kldivergence(p: MatchProbabilities, q: MatchProbabilities): number {
  let sum = 0;
  const pairs = [
    [p.home, q.home],
    [p.draw, q.draw],
    [p.away, q.away],
  ];
  
  for (const [pi, qi] of pairs) {
    if (pi > 0 && qi > 0) {
      sum += pi * Math.log2(pi / qi);
    }
  }
  
  return sum;
}

// ============================================================================
// FORMATTING UTILITIES
// ============================================================================

/**
 * Format probability as percentage with specified decimal places
 */
export function formatProbability(
  probability: number,
  decimals: number = 2
): string {
  return `${(probability * 100).toFixed(decimals)}%`;
}

/**
 * Format entropy with appropriate precision
 */
export function formatEntropy(entropy: number): string {
  return entropy.toFixed(2);
}

/**
 * Format Brier score
 */
export function formatBrierScore(score: number): string {
  return score.toFixed(3);
}

/**
 * Format date for display
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  if (diffMins < 60) return `${diffMins} ${diffMins === 1 ? 'minute' : 'minutes'} ago`;
  if (diffHours < 24) return `${diffHours} ${diffHours === 1 ? 'hour' : 'hours'} ago`;
  if (diffDays < 7) return `${diffDays} ${diffDays === 1 ? 'day' : 'days'} ago`;
  
  return formatDate(dateString);
}

// ============================================================================
// PROBABILITY SET METADATA
// ============================================================================

export const PROBABILITY_SET_METADATA: Record<ProbabilitySetId, {
  name: string;
  shortName: string;
  description: string;
  methodology: string;
  useCase: string;
  riskProfile: 'conservative' | 'balanced' | 'aggressive';
  color: string;
}> = {
  A_pure_model: {
    name: 'Pure Model (Statistical)',
    shortName: 'Pure Model',
    description: 'Statistical model probabilities with no market influence',
    methodology: 'Dixon-Coles goal model with isotonic calibration',
    useCase: 'For users who believe the model captures value the market misses',
    riskProfile: 'aggressive',
    color: '#64748b', // slate
  },
  B_balanced: {
    name: 'Market-Aware (Balanced)',
    shortName: 'Balanced',
    description: 'Weighted blend of model predictions and market odds',
    methodology: 'GLM-weighted combination (60% model, 40% market)',
    useCase: 'Default recommendation: trust model but respect market wisdom',
    riskProfile: 'balanced',
    color: '#3b82f6', // blue
  },
  C_market_dominant: {
    name: 'Market-Dominant (Conservative)',
    shortName: 'Conservative',
    description: 'Heavy reliance on market odds with minor model adjustment',
    methodology: 'Conservative blend (80% market, 20% model)',
    useCase: 'For users who believe markets are usually efficient',
    riskProfile: 'conservative',
    color: '#6b7280', // gray
  },
  D_draw_boosted: {
    name: 'Draw-Boosted (Risk-Adjusted)',
    shortName: 'Draw-Boosted',
    description: 'Draw probabilities increased to counter jackpot bias',
    methodology: 'Draw probability multiplied by 1.15, then renormalized',
    useCase: 'For jackpot-specific strategies recognizing draw undervaluation',
    riskProfile: 'balanced',
    color: '#8b5cf6', // violet
  },
  E_entropy_penalized: {
    name: 'Entropy-Penalized (High Conviction)',
    shortName: 'Sharp',
    description: 'Probabilities pushed toward extremes for clearer picks',
    methodology: 'Softmax with temperature adjustment (T=1.5)',
    useCase: 'For accumulator builders seeking decisive probabilities',
    riskProfile: 'aggressive',
    color: '#ef4444', // red
  },
  F_kelly_weighted: {
    name: 'Kelly-Weighted (Bankroll Optimized)',
    shortName: 'Kelly',
    description: 'Probabilities adjusted for optimal bankroll growth',
    methodology: 'Kelly criterion weighting based on model-odds divergence',
    useCase: 'For professional bettors optimizing long-term returns',
    riskProfile: 'balanced',
    color: '#10b981', // emerald
  },
  G_ensemble: {
    name: 'Ensemble (Meta-Model)',
    shortName: 'Ensemble',
    description: 'Weighted average of Sets A, B, C by historical performance',
    methodology: 'Performance-weighted ensemble (weights ∝ 1/Brier score)',
    useCase: 'For risk-averse users seeking consensus across perspectives',
    riskProfile: 'conservative',
    color: '#f59e0b', // amber
  },
};

// ============================================================================
// VALIDATION HELPERS
// ============================================================================

/**
 * Validate team name (basic sanitization)
 */
export function validateTeamName(name: string): boolean {
  return name.trim().length >= 2 && name.trim().length <= 50;
}

/**
 * Validate odds value
 */
export function validateOdds(odds: number): boolean {
  return odds >= 1.01 && odds <= 100;
}

/**
 * Check if fixture is complete (has all required fields)
 */
export function isFixtureComplete(fixture: {
  homeTeam: string;
  awayTeam: string;
  odds: { home: number; draw: number; away: number } | null;
}): boolean {
  return (
    validateTeamName(fixture.homeTeam) &&
    validateTeamName(fixture.awayTeam) &&
    fixture.odds !== null &&
    validateOdds(fixture.odds.home) &&
    validateOdds(fixture.odds.draw) &&
    validateOdds(fixture.odds.away)
  );
}

// ============================================================================
// COMBINATORIAL CALCULATIONS
// ============================================================================

/**
 * Calculate overall jackpot win probability
 * (product of highest probabilities per fixture)
 */
export function calculateJackpotWinProbability(
  probabilities: MatchProbabilities[]
): number {
  return probabilities.reduce((product, probs) => {
    const maxProb = Math.max(probs.home, probs.draw, probs.away);
    return product * maxProb;
  }, 1.0);
}

/**
 * Calculate expected value of a jackpot bet
 */
export function calculateExpectedValue(
  winProbability: number,
  stake: number,
  potentialWin: number
): number {
  return winProbability * potentialWin - (1 - winProbability) * stake;
}

// ============================================================================
// CSV EXPORT UTILITIES
// ============================================================================

/**
 * Convert data to CSV format
 */
export function convertToCSV(rows: Record<string, string | number>[]): string {
  if (rows.length === 0) return '';
  
  const headers = Object.keys(rows[0]);
  const csvRows = [
    headers.join(','),
    ...rows.map(row =>
      headers.map(header => {
        const value = row[header];
        const stringValue = String(value);
        // Escape values containing commas or quotes
        return stringValue.includes(',') || stringValue.includes('"')
          ? `"${stringValue.replace(/"/g, '""')}"`
          : stringValue;
      }).join(',')
    ),
  ];
  
  return csvRows.join('\n');
}

/**
 * Download data as file
 */
export function downloadFile(content: string | Blob, filename: string): void {
  const blob = content instanceof Blob
    ? content
    : new Blob([content], { type: 'text/plain' });
  
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// ============================================================================
// COLOR UTILITIES
// ============================================================================

/**
 * Get color based on confidence level
 */
export function getConfidenceColor(level: 'low' | 'medium' | 'high'): string {
  const colors = {
    low: '#ef4444',    // red
    medium: '#f59e0b', // amber
    high: '#10b981',   // emerald
  };
  return colors[level];
}

/**
 * Get color for probability value (muted scale)
 */
export function getProbabilityColor(probability: number): string {
  // Muted, professional color scale
  if (probability < 0.2) return '#cbd5e1'; // slate-300
  if (probability < 0.4) return '#94a3b8'; // slate-400
  if (probability < 0.6) return '#64748b'; // slate-500
  if (probability < 0.8) return '#475569'; // slate-600
  return '#334155'; // slate-700
}

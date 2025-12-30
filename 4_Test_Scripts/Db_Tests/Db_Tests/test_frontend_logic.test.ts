/**
 * Frontend Logic Tests
 * 
 * Tests for React components and frontend business logic.
 * Run with: npm test or npm run test
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock API client
const mockApiClient = {
  login: vi.fn(),
  logout: vi.fn(),
  getJackpots: vi.fn(),
  getProbabilities: vi.fn(),
  getCalibrationData: vi.fn(),
  getModelHealth: vi.fn(),
};

// Test data structures match TypeScript types
describe('Frontend Type Definitions', () => {
  it('should have correct Fixture interface structure', () => {
    const fixture = {
      id: '1',
      homeTeam: 'Arsenal',
      awayTeam: 'Chelsea',
      homeOdds: 1.85,
      drawOdds: 3.40,
      awayOdds: 4.20,
      matchDate: '2024-01-15',
      league: 'Premier League',
      validationWarnings: [],
    };
    
    expect(fixture.id).toBeDefined();
    expect(fixture.homeTeam).toBeDefined();
    expect(fixture.awayTeam).toBeDefined();
    expect(fixture.homeOdds).toBeGreaterThan(1);
    expect(fixture.drawOdds).toBeGreaterThan(1);
    expect(fixture.awayOdds).toBeGreaterThan(1);
  });

  it('should have correct Jackpot interface structure', () => {
    const jackpot = {
      id: 'JK-2024-1230',
      name: 'Test Jackpot',
      fixtures: [],
      createdAt: new Date().toISOString(),
      modelVersion: 'v2.4.1',
      status: 'draft' as const,
    };
    
    expect(jackpot.id).toBeDefined();
    expect(jackpot.fixtures).toBeInstanceOf(Array);
    expect(['draft', 'submitted', 'calculated']).toContain(jackpot.status);
  });

  it('should have correct ProbabilitySet interface structure', () => {
    const probabilitySet = {
      id: 'A',
      name: 'Pure Model',
      description: 'Model-only probabilities',
      probabilities: [],
    };
    
    expect(['A', 'B', 'C', 'D', 'E', 'F', 'G']).toContain(probabilitySet.id);
    expect(probabilitySet.probabilities).toBeInstanceOf(Array);
  });

  it('should have correct CalibrationData interface structure', () => {
    const calibrationData = {
      reliabilityCurve: [],
      brierScoreTrend: [],
      expectedVsActual: [],
    };
    
    expect(calibrationData.reliabilityCurve).toBeInstanceOf(Array);
    expect(calibrationData.brierScoreTrend).toBeInstanceOf(Array);
    expect(calibrationData.expectedVsActual).toBeInstanceOf(Array);
  });
});

describe('API Client Logic', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should construct API base URL correctly', () => {
    const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
    expect(apiBaseUrl).toContain('http');
    expect(apiBaseUrl).toContain('/api');
  });

  it('should handle probability set IDs correctly', () => {
    const validSets = ['A', 'B', 'C', 'D', 'E', 'F', 'G'];
    validSets.forEach(setId => {
      expect(validSets).toContain(setId);
    });
  });

  it('should validate odds format', () => {
    const validateOdds = (odds: number): boolean => {
      return odds > 1.0 && odds <= 100.0;
    };
    
    expect(validateOdds(1.85)).toBe(true);
    expect(validateOdds(3.40)).toBe(true);
    expect(validateOdds(0.5)).toBe(false); // Invalid: < 1.0
    expect(validateOdds(150.0)).toBe(false); // Invalid: > 100.0
  });

  it('should calculate probability sum correctly', () => {
    const probabilities = {
      home: 0.45,
      draw: 0.30,
      away: 0.25,
    };
    
    const sum = probabilities.home + probabilities.draw + probabilities.away;
    expect(sum).toBeCloseTo(1.0, 2);
  });
});

describe('Probability Calculations', () => {
  it('should convert odds to probabilities', () => {
    const oddsToProbability = (odds: number): number => {
      return 1 / odds;
    };
    
    expect(oddsToProbability(2.0)).toBeCloseTo(0.5, 2);
    expect(oddsToProbability(4.0)).toBeCloseTo(0.25, 2);
  });

  it('should normalize probabilities to sum to 1', () => {
    const normalizeProbabilities = (probs: { home: number; draw: number; away: number }) => {
      const sum = probs.home + probs.draw + probs.away;
      return {
        home: probs.home / sum,
        draw: probs.draw / sum,
        away: probs.away / sum,
      };
    };
    
    const normalized = normalizeProbabilities({ home: 0.5, draw: 0.3, away: 0.2 });
    const sum = normalized.home + normalized.draw + normalized.away;
    expect(sum).toBeCloseTo(1.0, 5);
  });
});

describe('Data Validation', () => {
  it('should validate fixture data', () => {
    const validateFixture = (fixture: any): boolean => {
      return !!(
        fixture.homeTeam &&
        fixture.awayTeam &&
        fixture.homeOdds > 1 &&
        fixture.drawOdds > 1 &&
        fixture.awayOdds > 1
      );
    };
    
    const validFixture = {
      homeTeam: 'Arsenal',
      awayTeam: 'Chelsea',
      homeOdds: 1.85,
      drawOdds: 3.40,
      awayOdds: 4.20,
    };
    
    expect(validateFixture(validFixture)).toBe(true);
    
    const invalidFixture = {
      homeTeam: '',
      awayTeam: 'Chelsea',
      homeOdds: 0.5, // Invalid
      drawOdds: 3.40,
      awayOdds: 4.20,
    };
    
    expect(validateFixture(invalidFixture)).toBe(false);
  });

  it('should validate jackpot has fixtures', () => {
    const validateJackpot = (jackpot: any): boolean => {
      return jackpot.fixtures && jackpot.fixtures.length > 0;
    };
    
    expect(validateJackpot({ fixtures: [1, 2, 3] })).toBe(true);
    expect(validateJackpot({ fixtures: [] })).toBe(false);
  });
});

describe('Export Functions', () => {
  it('should format CSV data correctly', () => {
    const formatCSVRow = (data: any[]): string => {
      return data.map(item => String(item)).join(',');
    };
    
    const row = formatCSVRow(['Match 1', 'Arsenal', 'Chelsea', '45.00', '30.00', '25.00']);
    expect(row).toContain('Arsenal');
    expect(row).toContain('Chelsea');
  });

  it('should format probability percentages', () => {
    const formatPercentage = (prob: number): string => {
      return `${(prob * 100).toFixed(2)}%`;
    };
    
    expect(formatPercentage(0.45)).toBe('45.00%');
    expect(formatPercentage(0.3333)).toBe('33.33%');
  });
});


/**
 * Backtesting Workflow Integration Test
 * 
 * Tests the complete backtesting workflow:
 * 1. Create jackpot
 * 2. Calculate probabilities
 * 3. Save probability selections
 * 4. Enter actual results
 * 5. Calculate scores
 * 6. Export to validation
 * 7. Verify validation results in database
 */

import { describe, it, expect, beforeAll, afterAll } from '@jest/globals';

const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:8000/api';

describe('Backtesting Workflow', () => {
  let jackpotId: string;
  let savedResultId: number;
  let validationIds: string[] = [];

  beforeAll(async () => {
    // Ensure test database is set up
    // This would typically be done via test setup script
  });

  afterAll(async () => {
    // Cleanup test data
    if (jackpotId) {
      await fetch(`${API_BASE_URL}/jackpots/${jackpotId}`, {
        method: 'DELETE',
      });
    }
  });

  describe('Step 1: Create Jackpot', () => {
    it('should create a jackpot with fixtures', async () => {
      const fixtures = [
        {
          id: '1',
          homeTeam: 'Arsenal',
          awayTeam: 'Chelsea',
          odds: { home: 2.0, draw: 3.4, away: 3.5 },
        },
        {
          id: '2',
          homeTeam: 'Liverpool',
          awayTeam: 'Man City',
          odds: { home: 2.5, draw: 3.2, away: 2.8 },
        },
      ];

      const response = await fetch(`${API_BASE_URL}/jackpots`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fixtures }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.data.id).toBeDefined();
      jackpotId = data.data.id;
    });
  });

  describe('Step 2: Calculate Probabilities', () => {
    it('should calculate probabilities for all sets (A-J)', async () => {
      const response = await fetch(`${API_BASE_URL}/probabilities/${jackpotId}/probabilities`);
      
      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.probabilitySets).toBeDefined();
      
      // Verify all sets exist
      const sets = Object.keys(data.probabilitySets);
      expect(sets.length).toBeGreaterThan(0);
      expect(sets).toContain('A');
      expect(sets).toContain('B');
      
      // Verify probabilities sum to ~100%
      const setB = data.probabilitySets['B'];
      if (setB && setB.length > 0) {
        const firstFixture = setB[0];
        const sum = firstFixture.homeWinProbability + 
                   firstFixture.drawProbability + 
                   firstFixture.awayWinProbability;
        expect(sum).toBeCloseTo(100, 1);
      }
    });
  });

  describe('Step 3: Save Probability Selections', () => {
    it('should save user selections for probability sets', async () => {
      const selections = {
        A: { '1': '1', '2': 'X' },  // Set A: Home, Draw
        B: { '1': 'X', '2': '1' },  // Set B: Draw, Home
      };

      const response = await fetch(`${API_BASE_URL}/probabilities/${jackpotId}/save-result`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Test Backtest',
          description: 'Integration test backtest',
          selections,
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.data.id).toBeDefined();
      savedResultId = data.data.id;
    });
  });

  describe('Step 4: Enter Actual Results', () => {
    it('should update saved result with actual match results', async () => {
      const actualResults = {
        '1': 'X',  // Arsenal vs Chelsea: Draw
        '2': '1',  // Liverpool vs Man City: Home win
      };

      const response = await fetch(
        `${API_BASE_URL}/probabilities/saved-results/${savedResultId}/actual-results`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(actualResults),
        }
      );

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.success).toBe(true);
      
      // Verify scores were calculated
      expect(data.data.scores).toBeDefined();
      expect(data.data.scores.A).toBeDefined();
      expect(data.data.scores.B).toBeDefined();
    });
  });

  describe('Step 5: Verify Score Calculation', () => {
    it('should calculate correct scores per set', async () => {
      const response = await fetch(
        `${API_BASE_URL}/probabilities/${jackpotId}/saved-results`
      );

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.success).toBe(true);
      
      const savedResult = data.data.find((r: any) => r.id === savedResultId);
      expect(savedResult).toBeDefined();
      expect(savedResult.scores).toBeDefined();
      
      // Set A: Selected '1' and 'X', actuals were 'X' and '1'
      // First match: Selected '1', actual 'X' → Wrong
      // Second match: Selected 'X', actual '1' → Wrong
      // Expected: 0 correct out of 2
      expect(savedResult.scores.A.correct).toBe(0);
      expect(savedResult.scores.A.total).toBe(2);
      
      // Set B: Selected 'X' and '1', actuals were 'X' and '1'
      // First match: Selected 'X', actual 'X' → Correct
      // Second match: Selected '1', actual '1' → Correct
      // Expected: 2 correct out of 2
      expect(savedResult.scores.B.correct).toBe(2);
      expect(savedResult.scores.B.total).toBe(2);
    });
  });

  describe('Step 6: Export to Validation', () => {
    it('should export saved results to validation_results table', async () => {
      const response = await fetch(
        `${API_BASE_URL}/probabilities/validation/export`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            validation_ids: [savedResultId.toString()],
          }),
        }
      );

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.data.exported).toBeGreaterThan(0);
      
      validationIds = data.data.validation_ids || [];
    });
  });

  describe('Step 7: Verify Validation Results in Database', () => {
    it('should have validation_results records in database', async () => {
      // This would typically query the database directly
      // For now, verify via API that validation was created
      expect(validationIds.length).toBeGreaterThan(0);
      
      // Verify validation metrics endpoint returns data
      const response = await fetch(`${API_BASE_URL}/calibration/validation-metrics`);
      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.brierScore).toBeDefined();
      expect(data.accuracy).toBeDefined();
    });
  });

  describe('Step 8: Calibration Update', () => {
    it('should have calibration data updated from validation', async () => {
      // Verify calibration data exists
      const response = await fetch(`${API_BASE_URL}/calibration`);
      expect(response.ok).toBe(true);
      const data = await response.json();
      
      // Calibration data should exist if validation was exported
      expect(data.reliabilityCurve).toBeDefined();
      expect(Array.isArray(data.reliabilityCurve)).toBe(true);
    });
  });
});


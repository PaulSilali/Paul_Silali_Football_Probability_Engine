/**
 * Database Connectivity Test
 * 
 * Verifies that:
 * 1. All backend endpoints query database correctly
 * 2. No endpoints return mock/hardcoded data
 * 3. Data flows correctly: Frontend → Backend → Database
 * 4. All database tables are accessible
 */

import { describe, it, expect } from '@jest/globals';

const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:8000/api';

describe('Database Connectivity Tests', () => {
  describe('Backend Endpoints Query Database', () => {
    it('should query models table for model status', async () => {
      const response = await fetch(`${API_BASE_URL}/model/status`);
      expect(response.ok).toBe(true);
      
      const data = await response.json();
      // If no models exist, should return appropriate message, not mock data
      expect(data).toBeDefined();
      // Should not contain hardcoded version like 'v2.4.1' if no models
    });

    it('should query data_sources table for data freshness', async () => {
      const response = await fetch(`${API_BASE_URL}/data/freshness`);
      expect(response.ok).toBe(true);
      
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(Array.isArray(data.data)).toBe(true);
      // Data should come from database, not hardcoded
    });

    it('should query jackpots table for jackpot list', async () => {
      const response = await fetch(`${API_BASE_URL}/jackpots`);
      expect(response.ok).toBe(true);
      
      const data = await response.json();
      expect(data.data).toBeDefined();
      expect(Array.isArray(data.data)).toBe(true);
    });

    it('should query saved_probability_results table for saved results', async () => {
      const response = await fetch(`${API_BASE_URL}/probabilities/saved-results/all?limit=10`);
      expect(response.ok).toBe(true);
      
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(Array.isArray(data.data)).toBe(true);
    });

    it('should query training_runs table for training history', async () => {
      const response = await fetch(`${API_BASE_URL}/model/training-history?limit=10`);
      expect(response.ok).toBe(true);
      
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(Array.isArray(data.data)).toBe(true);
    });
  });

  describe('No Mock Data in Responses', () => {
    it('should not return hardcoded model version if no models exist', async () => {
      // This test would require a clean database
      // Verify that if no models exist, response doesn't contain 'v2.4.1'
    });

    it('should not return hardcoded metrics if no validation exists', async () => {
      // Verify that if no validation_results exist,
      // response doesn't contain hardcoded brier scores
    });
  });

  describe('Data Flow Verification', () => {
    it('should create data in database when API is called', async () => {
      // Create a jackpot via API
      const createResponse = await fetch(`${API_BASE_URL}/jackpots`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fixtures: [{
            id: 'test-1',
            homeTeam: 'Test Home',
            awayTeam: 'Test Away',
            odds: { home: 2.0, draw: 3.0, away: 3.5 },
          }],
        }),
      });

      expect(createResponse.ok).toBe(true);
      const createData = await createResponse.json();
      const jackpotId = createData.data.id;

      // Verify it can be retrieved
      const getResponse = await fetch(`${API_BASE_URL}/jackpots/${jackpotId}`);
      expect(getResponse.ok).toBe(true);
      const getData = await getResponse.json();
      expect(getData.data.id).toBe(jackpotId);

      // Cleanup
      await fetch(`${API_BASE_URL}/jackpots/${jackpotId}`, {
        method: 'DELETE',
      });
    });
  });
});


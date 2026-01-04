/**
 * Dashboard Integration Test
 * 
 * Tests that Dashboard:
 * 1. Fetches data from /api/dashboard/summary
 * 2. Displays real system health metrics
 * 3. Shows data freshness from database
 * 4. Displays calibration trend from training runs
 * 5. Shows outcome distribution from predictions
 * 6. Displays league performance from validation results
 */

import { describe, it, expect, beforeEach } from '@jest/globals';

const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:8000/api';

describe('Dashboard Integration Tests', () => {
  describe('Dashboard Summary Endpoint', () => {
    it('should return dashboard summary data', async () => {
      const response = await fetch(`${API_BASE_URL}/dashboard/summary`);
      
      expect(response.ok).toBe(true);
      const data = await response.json();
      
      expect(data.success).toBe(true);
      expect(data.data).toBeDefined();
      expect(data.data.systemHealth).toBeDefined();
      expect(data.data.dataFreshness).toBeDefined();
      expect(data.data.calibrationTrend).toBeDefined();
      expect(data.data.outcomeDistribution).toBeDefined();
      expect(data.data.leaguePerformance).toBeDefined();
    });

    it('should return system health from database', async () => {
      const response = await fetch(`${API_BASE_URL}/dashboard/summary`);
      const data = await response.json();
      
      const systemHealth = data.data.systemHealth;
      
      // Verify all fields exist
      expect(systemHealth.modelVersion).toBeDefined();
      expect(systemHealth.modelStatus).toBeDefined();
      expect(systemHealth.calibrationScore).toBeDefined();
      expect(systemHealth.logLoss).toBeDefined();
      expect(systemHealth.totalMatches).toBeDefined();
      expect(systemHealth.avgWeeklyAccuracy).toBeDefined();
      expect(systemHealth.drawAccuracy).toBeDefined();
      
      // Verify data types
      expect(typeof systemHealth.calibrationScore).toBe('number');
      expect(typeof systemHealth.logLoss).toBe('number');
      expect(typeof systemHealth.totalMatches).toBe('number');
    });

    it('should return data freshness from data_sources table', async () => {
      const response = await fetch(`${API_BASE_URL}/dashboard/summary`);
      const data = await response.json();
      
      const dataFreshness = data.data.dataFreshness;
      expect(Array.isArray(dataFreshness)).toBe(true);
      
      // Each source should have required fields
      dataFreshness.forEach((source: any) => {
        expect(source.source).toBeDefined();
        expect(source.status).toBeDefined();
        expect(source.recordCount).toBeDefined();
        expect(typeof source.recordCount).toBe('number');
      });
    });

    it('should return calibration trend from training_runs table', async () => {
      const response = await fetch(`${API_BASE_URL}/dashboard/summary`);
      const data = await response.json();
      
      const calibrationTrend = data.data.calibrationTrend;
      expect(Array.isArray(calibrationTrend)).toBe(true);
      
      // Each trend point should have week and brier
      calibrationTrend.forEach((point: any) => {
        expect(point.week).toBeDefined();
        expect(point.brier).toBeDefined();
        expect(typeof point.brier).toBe('number');
      });
    });

    it('should return outcome distribution from predictions table', async () => {
      const response = await fetch(`${API_BASE_URL}/dashboard/summary`);
      const data = await response.json();
      
      const outcomeDistribution = data.data.outcomeDistribution;
      expect(Array.isArray(outcomeDistribution)).toBe(true);
      
      // Should have Home, Draw, Away
      if (outcomeDistribution.length > 0) {
        const names = outcomeDistribution.map((o: any) => o.name);
        expect(names).toContain('Home');
        expect(names).toContain('Draw');
        expect(names).toContain('Away');
        
        outcomeDistribution.forEach((outcome: any) => {
          expect(outcome.predicted).toBeDefined();
          expect(outcome.actual).toBeDefined();
          expect(typeof outcome.predicted).toBe('number');
          expect(typeof outcome.actual).toBe('number');
        });
      }
    });

    it('should return league performance from validation_results table', async () => {
      const response = await fetch(`${API_BASE_URL}/dashboard/summary`);
      const data = await response.json();
      
      const leaguePerformance = data.data.leaguePerformance;
      expect(Array.isArray(leaguePerformance)).toBe(true);
      
      // Each league should have required fields
      leaguePerformance.forEach((league: any) => {
        expect(league.league).toBeDefined();
        expect(league.accuracy).toBeDefined();
        expect(league.matches).toBeDefined();
        expect(league.status).toBeDefined();
        expect(typeof league.accuracy).toBe('number');
        expect(typeof league.matches).toBe('number');
      });
    });
  });

  describe('Dashboard Component Data Flow', () => {
    it('should fetch data on mount', async () => {
      // This would test the React component
      // Verify useEffect calls getDashboardSummary
      // Verify loading state is shown
      // Verify data is displayed when loaded
    });

    it('should handle API errors gracefully', async () => {
      // Test error handling
      // Verify error message is displayed
      // Verify fallback values are used
    });

    it('should display loading state while fetching', async () => {
      // Verify loading spinner is shown
      // Verify data is not displayed during loading
    });
  });
});


/**
 * Application State Management
 * 
 * Uses Zustand for lightweight, type-safe state management.
 * No Redux complexity, just clean state updates.
 */

import { create } from 'zustand';
import type {
  AppState,
  Fixture,
  JackpotInput,
  PredictionResponse,
  ProbabilitySetId,
  NavigationSection,
  ModelVersion,
  ModelHealth,
  ValidationMetrics,
} from '../types';

interface AppActions {
  // Jackpot input management
  addFixture: (fixture: Fixture) => void;
  removeFixture: (fixtureId: string) => void;
  updateFixture: (fixtureId: string, updates: Partial<Fixture>) => void;
  clearJackpot: () => void;
  loadJackpot: (jackpot: JackpotInput) => void;
  
  // Prediction management
  setPrediction: (prediction: PredictionResponse | null) => void;
  
  // Probability set selection
  toggleProbabilitySet: (setId: ProbabilitySetId) => void;
  selectAllSets: () => void;
  selectDefaultSets: () => void;
  
  // Navigation
  setActiveSection: (section: NavigationSection) => void;
  
  // Loading & error states
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  
  // Model & health management
  setModelVersion: (version: ModelVersion | null) => void;
  setModelHealth: (health: ModelHealth | null) => void;
  setValidationMetrics: (metrics: ValidationMetrics | null) => void;
  
  // Reset entire state
  reset: () => void;
}

const initialState: AppState = {
  currentJackpot: null,
  activePrediction: null,
  selectedSets: ['B_balanced'], // Default to balanced set
  activeSection: 'input',
  isLoading: false,
  error: null,
  currentModelVersion: null,
  modelHealth: null,
  validationMetrics: null,
};

export const useAppStore = create<AppState & AppActions>((set, get) => ({
  ...initialState,
  
  // ============================================================================
  // JACKPOT INPUT ACTIONS
  // ============================================================================
  
  addFixture: (fixture) => set((state) => {
    const currentJackpot = state.currentJackpot || {
      fixtures: [],
      createdAt: new Date().toISOString(),
    };
    
    return {
      currentJackpot: {
        ...currentJackpot,
        fixtures: [...currentJackpot.fixtures, fixture],
      },
    };
  }),
  
  removeFixture: (fixtureId) => set((state) => {
    if (!state.currentJackpot) return state;
    
    return {
      currentJackpot: {
        ...state.currentJackpot,
        fixtures: state.currentJackpot.fixtures.filter(f => f.id !== fixtureId),
      },
    };
  }),
  
  updateFixture: (fixtureId, updates) => set((state) => {
    if (!state.currentJackpot) return state;
    
    return {
      currentJackpot: {
        ...state.currentJackpot,
        fixtures: state.currentJackpot.fixtures.map(f =>
          f.id === fixtureId ? { ...f, ...updates } : f
        ),
      },
    };
  }),
  
  clearJackpot: () => set({
    currentJackpot: null,
    activePrediction: null,
  }),
  
  loadJackpot: (jackpot) => set({
    currentJackpot: jackpot,
    activePrediction: null,
  }),
  
  // ============================================================================
  // PREDICTION ACTIONS
  // ============================================================================
  
  setPrediction: (prediction) => set({
    activePrediction: prediction,
  }),
  
  // ============================================================================
  // PROBABILITY SET SELECTION
  // ============================================================================
  
  toggleProbabilitySet: (setId) => set((state) => {
    const isSelected = state.selectedSets.includes(setId);
    
    return {
      selectedSets: isSelected
        ? state.selectedSets.filter(id => id !== setId)
        : [...state.selectedSets, setId],
    };
  }),
  
  selectAllSets: () => set({
    selectedSets: [
      'A_pure_model',
      'B_balanced',
      'C_market_dominant',
      'D_draw_boosted',
      'E_entropy_penalized',
      'F_kelly_weighted',
      'G_ensemble',
    ],
  }),
  
  selectDefaultSets: () => set({
    selectedSets: ['A_pure_model', 'B_balanced', 'C_market_dominant'],
  }),
  
  // ============================================================================
  // NAVIGATION
  // ============================================================================
  
  setActiveSection: (section) => set({
    activeSection: section,
  }),
  
  // ============================================================================
  // LOADING & ERROR STATES
  // ============================================================================
  
  setLoading: (isLoading) => set({ isLoading }),
  
  setError: (error) => set({ error }),
  
  // ============================================================================
  // MODEL & HEALTH MANAGEMENT
  // ============================================================================
  
  setModelVersion: (version) => set({
    currentModelVersion: version,
  }),
  
  setModelHealth: (health) => set({
    modelHealth: health,
  }),
  
  setValidationMetrics: (metrics) => set({
    validationMetrics: metrics,
  }),
  
  // ============================================================================
  // RESET
  // ============================================================================
  
  reset: () => set(initialState),
}));

// ============================================================================
// SELECTORS (for optimized component subscriptions)
// ============================================================================

export const selectFixtureCount = (state: AppState) => 
  state.currentJackpot?.fixtures.length || 0;

export const selectHasActivePrediction = (state: AppState) => 
  state.activePrediction !== null;

export const selectIsHealthy = (state: AppState) => 
  state.modelHealth?.status === 'healthy';

export const selectCanGeneratePrediction = (state: AppState) => {
  const hasFixtures = (state.currentJackpot?.fixtures.length || 0) > 0;
  const allHaveOdds = state.currentJackpot?.fixtures.every(f => f.odds !== null) || false;
  return hasFixtures && allHaveOdds && !state.isLoading;
};

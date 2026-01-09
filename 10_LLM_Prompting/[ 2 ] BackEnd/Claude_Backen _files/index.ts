/**
 * API Service Layer
 * 
 * Handles all communication with the backend API.
 * Type-safe, with proper error handling and retry logic.
 */

import type {
  ApiResponse,
  JackpotInput,
  PredictionResponse,
  ModelVersion,
  ModelHealth,
  ValidationMetrics,
  DataRefreshTask,
  LeagueCoverage,
} from '../types';

// ============================================================================
// CONFIGURATION
// ============================================================================

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
};

// ============================================================================
// ERROR HANDLING
// ============================================================================

export class ApiError extends Error {
  constructor(
    message: string,
    public code: string,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({
      code: 'UNKNOWN_ERROR',
      message: 'An unexpected error occurred',
    }));
    
    throw new ApiError(
      error.message || 'API request failed',
      error.code || `HTTP_${response.status}`,
      error.details
    );
  }
  
  const data = await response.json();
  return data.data || data;
}

// ============================================================================
// PREDICTION API
// ============================================================================

export async function generatePrediction(
  jackpot: JackpotInput
): Promise<PredictionResponse> {
  const response = await fetch(`${API_BASE_URL}/predictions`, {
    method: 'POST',
    headers: DEFAULT_HEADERS,
    body: JSON.stringify(jackpot),
  });
  
  return handleResponse<PredictionResponse>(response);
}

export async function getPrediction(
  predictionId: string
): Promise<PredictionResponse> {
  const response = await fetch(`${API_BASE_URL}/predictions/${predictionId}`, {
    headers: DEFAULT_HEADERS,
  });
  
  return handleResponse<PredictionResponse>(response);
}

// ============================================================================
// MODEL MANAGEMENT API
// ============================================================================

export async function getModelVersion(): Promise<ModelVersion> {
  const response = await fetch(`${API_BASE_URL}/model/status`, {
    headers: DEFAULT_HEADERS,
  });
  
  return handleResponse<ModelVersion>(response);
}

export async function listModelVersions(): Promise<ModelVersion[]> {
  const response = await fetch(`${API_BASE_URL}/model/versions`, {
    headers: DEFAULT_HEADERS,
  });
  
  return handleResponse<ModelVersion[]>(response);
}

export async function trainModel(): Promise<{ taskId: string }> {
  const response = await fetch(`${API_BASE_URL}/model/train`, {
    method: 'POST',
    headers: DEFAULT_HEADERS,
  });
  
  return handleResponse<{ taskId: string }>(response);
}

// ============================================================================
// MODEL HEALTH API
// ============================================================================

export async function getModelHealth(): Promise<ModelHealth> {
  const response = await fetch(`${API_BASE_URL}/health/model`, {
    headers: DEFAULT_HEADERS,
  });
  
  return handleResponse<ModelHealth>(response);
}

// ============================================================================
// VALIDATION & CALIBRATION API
// ============================================================================

export async function getValidationMetrics(): Promise<ValidationMetrics> {
  const response = await fetch(`${API_BASE_URL}/validation/metrics`, {
    headers: DEFAULT_HEADERS,
  });
  
  return handleResponse<ValidationMetrics>(response);
}

// ============================================================================
// DATA MANAGEMENT API
// ============================================================================

export async function getDataCoverage(): Promise<LeagueCoverage[]> {
  const response = await fetch(`${API_BASE_URL}/data/coverage`, {
    headers: DEFAULT_HEADERS,
  });
  
  return handleResponse<LeagueCoverage[]>(response);
}

export async function refreshData(
  league: string,
  season: string,
  source: 'api' | 'csv' = 'api'
): Promise<{ taskId: string }> {
  const response = await fetch(`${API_BASE_URL}/data/refresh`, {
    method: 'POST',
    headers: DEFAULT_HEADERS,
    body: JSON.stringify({ league, season, source }),
  });
  
  return handleResponse<{ taskId: string }>(response);
}

export async function getTaskStatus(taskId: string): Promise<DataRefreshTask> {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
    headers: DEFAULT_HEADERS,
  });
  
  return handleResponse<DataRefreshTask>(response);
}

// ============================================================================
// TEAM SEARCH (for autocomplete)
// ============================================================================

export async function searchTeams(query: string): Promise<string[]> {
  const response = await fetch(
    `${API_BASE_URL}/teams/search?q=${encodeURIComponent(query)}`,
    { headers: DEFAULT_HEADERS }
  );
  
  return handleResponse<string[]>(response);
}

// ============================================================================
// EXPORT API
// ============================================================================

export async function exportPrediction(
  predictionId: string,
  format: 'csv' | 'pdf' | 'json'
): Promise<Blob> {
  const response = await fetch(
    `${API_BASE_URL}/predictions/${predictionId}/export?format=${format}`,
    { headers: DEFAULT_HEADERS }
  );
  
  if (!response.ok) {
    throw new ApiError(
      'Export failed',
      `HTTP_${response.status}`
    );
  }
  
  return response.blob();
}

// ============================================================================
// POLLING UTILITIES (for background tasks)
// ============================================================================

export async function pollTaskUntilComplete(
  taskId: string,
  onProgress?: (progress: number) => void,
  intervalMs: number = 1000,
  timeoutMs: number = 300000 // 5 minutes
): Promise<DataRefreshTask> {
  const startTime = Date.now();
  
  while (true) {
    const task = await getTaskStatus(taskId);
    
    if (onProgress) {
      onProgress(task.progress);
    }
    
    if (task.status === 'complete') {
      return task;
    }
    
    if (task.status === 'failed') {
      throw new ApiError(
        task.error || 'Task failed',
        'TASK_FAILED',
        task.details
      );
    }
    
    if (Date.now() - startTime > timeoutMs) {
      throw new ApiError(
        'Task timeout',
        'TASK_TIMEOUT'
      );
    }
    
    await new Promise(resolve => setTimeout(resolve, intervalMs));
  }
}

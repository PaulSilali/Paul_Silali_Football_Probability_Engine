// API Service Layer for Football Jackpot Probability Engine

import type {
  AuthResponse,
  LoginCredentials,
  Jackpot,
  Fixture,
  ProbabilitySet,
  CalibrationData,
  FeatureContribution,
  ModelHealth,
  ModelVersion,
  ModelStatus,
  TaskStatus,
  DataUpdate,
  AuditEntry,
  ApiResponse,
  PaginatedResponse,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
      signal: options.signal, // Support AbortController signal
    });

    if (!response.ok) {
      if (response.status === 401) {
        // Token expired or invalid
        this.token = null;
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
      }
      
      // Try to parse error message from response
      let errorMessage = `API Error: ${response.status} ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = typeof errorData.detail === 'string' 
            ? errorData.detail 
            : JSON.stringify(errorData.detail);
        } else if (errorData.message) {
          errorMessage = errorData.message;
        } else if (errorData.error) {
          errorMessage = errorData.error;
        }
      } catch (e) {
        // If JSON parsing fails, use default message
      }
      
      const error = new Error(errorMessage);
      (error as any).status = response.status;
      throw error;
    }

    return response.json();
  }

  // Auth endpoints
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    this.token = response.token;
    return response;
  }

  async logout(): Promise<void> {
    await this.request('/auth/logout', { method: 'POST' });
    this.token = null;
  }

  async refreshToken(): Promise<AuthResponse> {
    return this.request<AuthResponse>('/auth/refresh', { method: 'POST' });
  }

  async getCurrentUser(): Promise<ApiResponse<{ user: { id: string; email: string; name: string } }>> {
    return this.request('/auth/me');
  }

  // Jackpot endpoints
  async getJackpots(): Promise<PaginatedResponse<Jackpot>> {
    return this.request('/jackpots');
  }

  async getJackpot(id: string): Promise<ApiResponse<Jackpot>> {
    return this.request(`/jackpots/${id}`);
  }

  async createJackpot(fixtures: Fixture[]): Promise<ApiResponse<Jackpot>> {
    return this.request('/jackpots', {
      method: 'POST',
      body: JSON.stringify({ fixtures }),
    });
  }

  async updateJackpot(id: string, fixtures: Fixture[]): Promise<ApiResponse<Jackpot>> {
    return this.request(`/jackpots/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ fixtures }),
    });
  }

  async deleteJackpot(id: string): Promise<void> {
    await this.request(`/jackpots/${id}`, { method: 'DELETE' });
  }

  async submitJackpot(id: string): Promise<ApiResponse<Jackpot>> {
    return this.request(`/jackpots/${id}/submit`, { method: 'POST' });
  }

  // Saved Templates endpoints
  async saveTemplate(name: string, description: string | null, fixtures: Fixture[]): Promise<ApiResponse<any>> {
    return this.request('/jackpots/templates', {
      method: 'POST',
      body: JSON.stringify({ name, description, fixtures }),
    });
  }

  async getTemplates(limit: number = 50): Promise<ApiResponse<any>> {
    return this.request(`/jackpots/templates?limit=${limit}`);
  }

  async getTemplate(templateId: number): Promise<ApiResponse<any>> {
    return this.request(`/jackpots/templates/${templateId}`);
  }

  async deleteTemplate(templateId: number): Promise<ApiResponse<any>> {
    return this.request(`/jackpots/templates/${templateId}`, { method: 'DELETE' });
  }

  async calculateFromTemplate(templateId: number): Promise<ApiResponse<Jackpot>> {
    return this.request(`/jackpots/templates/${templateId}/calculate`, { method: 'POST' });
  }

  // Probability endpoints
  async getProbabilities(jackpotId: string): Promise<ApiResponse<any>> {
    return this.request(`/probabilities/${jackpotId}/probabilities`);
  }

  async getProbabilitySet(jackpotId: string, setId: string): Promise<ApiResponse<ProbabilitySet>> {
    return this.request(`/probabilities/${jackpotId}/probabilities/${setId}`);
  }

  // Saved probability results endpoints
  async saveProbabilityResult(
    jackpotId: string,
    data: {
      name: string;
      description?: string;
      selections: Record<string, Record<string, string>>;
      actual_results?: Record<string, string>;
      scores?: Record<string, { correct: number; total: number }>;
    }
  ): Promise<ApiResponse<any>> {
    console.log('=== API CLIENT: saveProbabilityResult ===');
    console.log('Endpoint:', `/probabilities/${jackpotId}/save-result`);
    console.log('Request data:', {
      name: data.name,
      nameType: typeof data.name,
      nameLength: data.name?.length,
      description: data.description,
      selectionsKeys: Object.keys(data.selections || {}),
      actualResultsKeys: data.actual_results ? Object.keys(data.actual_results) : [],
      scoresKeys: data.scores ? Object.keys(data.scores) : [],
    });
    console.log('Full request payload:', JSON.stringify(data, null, 2));
    
    try {
      const response = await this.request(`/probabilities/${jackpotId}/save-result`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
      
      console.log('API Response:', {
        success: response.success,
        message: response.message,
        data: response.data,
      });
      
      return response;
    } catch (error: any) {
      console.error('API Request Error:', {
        error,
        message: error?.message,
        status: error?.status,
        detail: error?.detail,
      });
      throw error;
    }
  }

  async getSavedResults(jackpotId: string): Promise<ApiResponse<any>> {
    return this.request(`/probabilities/${jackpotId}/saved-results`);
  }

  async getLatestSavedResult(): Promise<ApiResponse<any>> {
    return this.request(`/probabilities/saved-results/latest`);
  }

  async getAllSavedResults(limit: number = 100): Promise<ApiResponse<any>> {
    return this.request(`/probabilities/saved-results/all?limit=${limit}`);
  }

  async getSavedResult(resultId: number): Promise<ApiResponse<any>> {
    return this.request(`/probabilities/saved-results/${resultId}`);
  }

  async updateActualResults(
    resultId: number,
    actualResults: Record<string, string>
  ): Promise<ApiResponse<any>> {
    return this.request(`/probabilities/saved-results/${resultId}/actual-results`, {
      method: 'PUT',
      body: JSON.stringify(actualResults),
    });
  }

  async exportValidationToTraining(validationIds: string[]): Promise<ApiResponse<any>> {
    return this.request(`/probabilities/validation/export`, {
      method: 'POST',
      body: JSON.stringify({ validation_ids: validationIds }),
    });
  }

  // Calibration endpoints
  async getCalibrationData(params?: {
    league?: string;
    startDate?: string;
    endDate?: string;
  }): Promise<ApiResponse<CalibrationData>> {
    const queryParams = new URLSearchParams();
    if (params?.league) queryParams.set('league', params.league);
    if (params?.startDate) queryParams.set('startDate', params.startDate);
    if (params?.endDate) queryParams.set('endDate', params.endDate);
    
    const query = queryParams.toString();
    return this.request(`/calibration${query ? `?${query}` : ''}`);
  }

  // Explainability endpoints
  async getFeatureContributions(jackpotId: string): Promise<ApiResponse<FeatureContribution[]>> {
    return this.request(`/jackpots/${jackpotId}/contributions`);
  }

  // Model Health endpoints
  async getModelHealth(): Promise<ApiResponse<ModelHealth>> {
    return this.request('/model/health');
  }

  async getModelVersions(): Promise<ApiResponse<ModelVersion[]>> {
    return this.request('/model/versions');
  }

  async setActiveModelVersion(versionId: string): Promise<ApiResponse<ModelVersion>> {
    return this.request(`/model/versions/${versionId}/activate`, { method: 'POST' });
  }

  async getModelStatus(): Promise<ApiResponse<ModelStatus>> {
    return this.request('/model/status');
  }

  async trainModel(params?: {
    modelType?: 'poisson' | 'blending' | 'calibration' | 'full';
    leagues?: string[];
    seasons?: string[];
    dateFrom?: string;
    dateTo?: string;
  }): Promise<ApiResponse<{ taskId: string; status: string; message: string }>> {
    return this.request('/model/train', {
      method: 'POST',
      body: JSON.stringify(params || {}),
    });
  }

  async getTaskStatus(taskId: string): Promise<ApiResponse<TaskStatus>> {
    return this.request(`/tasks/${taskId}`);
  }

  async cancelTask(taskId: string): Promise<ApiResponse<{ success: boolean; message: string }>> {
    return this.request(`/tasks/${taskId}/cancel`, { method: 'POST' });
  }

  // Data Management endpoints
  async getDataUpdates(): Promise<PaginatedResponse<DataUpdate>> {
    return this.request('/data/updates');
  }

  async triggerDataUpdate(source: string): Promise<ApiResponse<DataUpdate>> {
    return this.request('/data/updates', {
      method: 'POST',
      body: JSON.stringify({ source }),
    });
  }

  async getDataFreshness(): Promise<ApiResponse<{
    source: string;
    lastUpdated: string;
    recordCount: number;
  }[]>> {
    return this.request('/data/freshness');
  }

  async refreshData(source: string, leagueCode: string, season: string, signal?: AbortSignal): Promise<ApiResponse<{
    id: string;
    batchNumber: number;
    source: string;
    leagueCode: string;
    season: string;
    status: string;
    progress: number;
    startedAt: string;
    completedAt: string;
    stats: {
      processed: number;
      inserted: number;
      updated: number;
      skipped: number;
      errors: number;
    };
  }>> {
    return this.request('/data/refresh', {
      method: 'POST',
      body: JSON.stringify({ source, league_code: leagueCode, season }),
      signal,
    });
  }

  async batchDownload(source: string, leagues: Array<{code: string, season?: string}>, season?: string, signal?: AbortSignal): Promise<ApiResponse<{
    batchId: string;
    source: string;
    totalStats: {
      processed: number;
      inserted: number;
      updated: number;
      skipped: number;
      errors: number;
    };
    results: Array<{
      leagueCode: string;
      season: string;
      stats: any;
      batchNumber?: number;
    }>;
    completedAt: string;
  }>> {
    return this.request('/data/batch-download', {
      method: 'POST',
      body: JSON.stringify({ source, leagues, season }),
      signal,
    });
  }

  async getBatchHistory(limit: number = 50): Promise<ApiResponse<{
    batches: Array<{
      id: string;
      batchNumber: number;
      source: string;
      status: string;
      startedAt: string | null;
      completedAt: string | null;
      recordsProcessed: number;
      recordsInserted: number;
      recordsUpdated: number;
      recordsSkipped: number;
      hasFiles: boolean;
      fileInfo?: {
        batchNumber: number;
        folderName: string;
        csvCount: number;
        leagues: string[];
        seasons: string[];
        files: string[];
      };
      leagueCode?: string;
      season?: string;
    }>;
    summary: {
      totalBatches: number;
      totalRecords: number;
      totalFiles: number;
      uniqueLeagues: number;
      leagues: string[];
    };
  }>> {
    return this.request(`/data/batches?limit=${limit}`);
  }

  async prepareTrainingData(params?: {
    league_codes?: string[];
    format?: "csv" | "parquet" | "both";
  }): Promise<ApiResponse<{
    total_leagues?: number;
    successful?: number;
    failed?: number;
    total_matches?: number;
    leagues?: Array<{
      league_code: string;
      league_name: string;
      matches_count: number;
      seasons: string[];
      date_range: {
        start: string | null;
        end: string | null;
      };
      files_created: string[];
    }>;
    output_directory?: string;
  }>> {
    return this.request("/data/prepare-training-data", {
      method: "POST",
      body: JSON.stringify({
        league_codes: params?.league_codes,
        format: params?.format || "both",
      }),
    });
  }

  // Audit endpoints
  async getAuditLog(params?: {
    page?: number;
    pageSize?: number;
    jackpotId?: string;
  }): Promise<PaginatedResponse<AuditEntry>> {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.set('page', String(params.page));
    if (params?.pageSize) queryParams.set('pageSize', String(params.pageSize));
    if (params?.jackpotId) queryParams.set('jackpotId', params.jackpotId);
    
    const query = queryParams.toString();
    return this.request(`/audit${query ? `?${query}` : ''}`);
  }

  // Validation endpoints
  async validateTeamName(teamName: string): Promise<ApiResponse<{
    isValid: boolean;
    suggestions?: string[];
    normalizedName?: string;
  }>> {
    return this.request('/validation/team', {
      method: 'POST',
      body: JSON.stringify({ teamName }),
    });
  }

  // Teams endpoints
  async getAllTeams(leagueId?: number): Promise<ApiResponse<{
    id: number;
    name: string;
    canonicalName: string;
    leagueId: number;
    leagueName: string | null;
  }[]>> {
    const query = leagueId ? `?league_id=${leagueId}` : '';
    return this.request(`/teams/all${query}`);
  }

  async searchTeams(params: {
    q: string;
    leagueId?: number;
    limit?: number;
  }): Promise<ApiResponse<{
    id: number;
    name: string;
    canonicalName: string;
    leagueId: number;
    similarity: number;
  }[]>> {
    const queryParams = new URLSearchParams();
    queryParams.set('q', params.q);
    if (params.leagueId) queryParams.set('league_id', String(params.leagueId));
    if (params.limit) queryParams.set('limit', String(params.limit));
    return this.request(`/teams/search?${queryParams.toString()}`);
  }

  // Model Training endpoints
  async getModelVersions(): Promise<ApiResponse<Array<{
    id: string;
    version: string;
    modelType: string;
    status: string;
    trainedAt: string | null;
    brierScore: number | null;
    logLoss: number | null;
    drawAccuracy: number | null;
    trainingMatches: number | null;
    trainingLeagues: string[] | null;
    trainingSeasons: string[] | null;
    isActive: boolean;
  }>>> {
    return this.request('/model/versions');
  }

  async getTrainingHistory(limit: number = 50): Promise<ApiResponse<Array<{
    id: string;
    modelId: string | null;
    runType: string;
    status: string;
    startedAt: string | null;
    completedAt: string | null;
    matchCount: number | null;
    dateFrom: string | null;
    dateTo: string | null;
    brierScore: number | null;
    logLoss: number | null;
    validationAccuracy: number | null;
    errorMessage: string | null;
    duration: number | null;
  }>>> {
    return this.request(`/model/training-history?limit=${limit}`);
  }

  async getLeagues(): Promise<ApiResponse<Array<{
    code: string;
    name: string;
    country: string;
    tier: number;
  }>>> {
    return this.request('/model/leagues');
  }

  // Ticket generation endpoints
  async generateTickets(
    jackpotId: string,
    setKeys: string[] = ['B'],
    nTickets?: number,
    leagueCode?: string
  ): Promise<ApiResponse<{
    tickets: Array<{
      id: string;
      picks: string[];
      drawCount: number;
      setKey: string;
    }>;
    coverage: {
      home_pct: number;
      draw_pct: number;
      away_pct: number;
      warnings: string[];
      total_picks: number;
      total_tickets: number;
    };
  }>> {
    return this.request('/tickets/generate', {
      method: 'POST',
      body: JSON.stringify({
        jackpot_id: jackpotId,
        set_keys: setKeys,
        n_tickets: nTickets,
        league_code: leagueCode
      }),
    });
  }

  async getDrawDiagnostics(
    league: string,
    season?: string
  ): Promise<ApiResponse<{
    league: string;
    season: string | null;
    drawRate: number;
    totalMatches: number;
    draws: number;
  }>> {
    const params = new URLSearchParams({ league });
    if (season) params.append('season', season);
    return this.request(`/tickets/draw-diagnostics?${params.toString()}`);
  }
}

export const apiClient = new ApiClient();
export default apiClient;

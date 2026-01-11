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
  async getJackpots(page?: number, pageSize?: number): Promise<PaginatedResponse<Jackpot>> {
    const params = new URLSearchParams();
    if (page) params.set('page', page.toString());
    if (pageSize) params.set('page_size', pageSize.toString());
    const queryString = params.toString();
    return this.request(`/jackpots${queryString ? `?${queryString}` : ''}`);
  }

  async getJackpot(id: string): Promise<ApiResponse<Jackpot>> {
    return this.request(`/jackpots/${id}`);
  }

  async createJackpot(fixtures: Fixture[], jackpotId?: string): Promise<ApiResponse<Jackpot>> {
    const body: any = { fixtures };
    if (jackpotId) {
      body.jackpot_id = jackpotId;
    }
    return this.request('/jackpots', {
      method: 'POST',
      body: JSON.stringify(body),
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

  async deleteSavedResult(resultId: number): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>(`/probabilities/saved-results/${resultId}`, {
      method: 'DELETE',
    });
  }

  async getImportedJackpots(): Promise<ApiResponse<{
    jackpots: Array<{
      id: string;
      jackpotId: string;
      date: string | null;
      matches: number;
      status: 'validated' | 'imported' | 'pending';
      correctPredictions?: number;
    }>;
  }>> {
    return this.request('/probabilities/imported-jackpots');
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

  async getValidationExportStatus(): Promise<ApiResponse<{
    exported_validations: Record<string, { exported: boolean; exported_at: string | null; validation_result_id: number }>;
    total_exported: number;
  }>> {
    return this.request(`/probabilities/validation/export-status`);
  }

  async retrainCalibrationFromValidation(params?: {
    validation_result_ids?: number[];
    use_all_validation?: boolean;
    base_model_id?: number;
    min_validation_matches?: number;
  }): Promise<ApiResponse<{
    modelId: number;
    version: string;
    metrics: {
      brierScore: number;
      logLoss: number;
    };
    matchCount: number;
    validationResultCount: number;
    trainingRunId: number;
  }>> {
    return this.request(`/probabilities/validation/retrain-calibration`, {
      method: 'POST',
      body: JSON.stringify(params || {}),
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

  // Versioned Calibration Jobs endpoints
  async fitCalibration(params: {
    model_version: string;
    league?: string;
    start_date?: string;
    end_date?: string;
    min_samples?: number;
  }): Promise<ApiResponse<{
    calibration_ids: string[];
    model_version: string;
    league: string | null;
  }>> {
    const queryParams = new URLSearchParams();
    queryParams.set('model_version', params.model_version);
    if (params.league) queryParams.set('league', params.league);
    if (params.start_date) queryParams.set('start_date', params.start_date);
    if (params.end_date) queryParams.set('end_date', params.end_date);
    if (params.min_samples) queryParams.set('min_samples', params.min_samples.toString());
    
    return this.request(`/calibration/fit?${queryParams.toString()}`, {
      method: 'POST',
    });
  }

  async activateCalibration(calibrationId: string): Promise<ApiResponse<{
    calibration_id: string;
  }>> {
    return this.request(`/calibration/activate/${calibrationId}`, {
      method: 'POST',
    });
  }

  async getActiveCalibrations(params: {
    model_version: string;
    league?: string;
  }): Promise<ApiResponse<{
    model_version: string;
    league: string | null;
    calibrations: Record<string, {
      calibration_id: string;
      samples_used: number;
      created_at: string;
      valid_from: string;
    }>;
  }>> {
    const queryParams = new URLSearchParams();
    queryParams.set('model_version', params.model_version);
    if (params.league) queryParams.set('league', params.league);
    
    return this.request(`/calibration/active?${queryParams.toString()}`);
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

  // Ticket analysis endpoints
  async analyzeTicketPerformance(data: {
    tickets: Array<{ picks: string[]; setKey: string; id: string }>;
    actual_results: string[];
    fixtures: Array<{ homeTeam: string; awayTeam: string; odds?: any; id: string }>;
    ticket_performance: Array<{ correct: number; total: number; accuracy: number }>;
  }): Promise<ApiResponse<{
    analysis: string;
    best_performing_sets?: string[];
    worst_performing_sets?: string[];
    common_mistakes?: string[];
    recommendations?: string[];
  }>> {
    return this.request('/tickets/analyze-performance', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async trainModel(params?: {
    modelType?: 'poisson' | 'blending' | 'calibration' | 'full';
    leagues?: string[];
    seasons?: string[];
    dateFrom?: string;
    dateTo?: string;
    baseModelWindowYears?: number;
    drawModelWindowYears?: number;
    oddsCalibrationWindowYears?: number;
    excludePreCovid?: boolean;
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

  async getLeagueStats(): Promise<ApiResponse<Record<string, {
    name: string;
    recordCount: number;
    lastUpdated: string | null;
  }>>> {
    return this.request('/data/league-stats');
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
  async validateTeamName(teamName: string, leagueId?: number, checkTraining?: boolean): Promise<ApiResponse<{
    isValid: boolean;
    suggestions?: string[];
    normalizedName?: string;
    teamId?: number;
    isTrained?: boolean;
    strengthSource?: 'model' | 'database' | 'default';
  }>> {
    return this.request('/validation/team', {
      method: 'POST',
      body: JSON.stringify({ teamName, leagueId, checkTraining }),
    });
  }

  // Pipeline endpoints
  async checkTeamsStatus(teamNames: string[], leagueId?: number): Promise<ApiResponse<{
    validated_teams: string[];
    missing_teams: string[];
    trained_teams: number[];
    untrained_teams: number[];
    team_details: Record<string, {
      team_id: number | null;
      isValid: boolean;
      isTrained: boolean;
      league_code: string | null;
      league_id: number | null;
    }>;
  }>> {
    return this.request('/pipeline/check-status', {
      method: 'POST',
      body: JSON.stringify({ team_names: teamNames, league_id: leagueId }),
    });
  }

  async runPipeline(params: {
    team_names: string[];
    league_id?: number;
    auto_download?: boolean;
    auto_train?: boolean;
    auto_recompute?: boolean;
    jackpot_id?: string;
    seasons?: string[];
    max_seasons?: number;
    base_model_window_years?: number;  // Recent data focus: 2, 3, or 4 years (default: 4)
  }): Promise<ApiResponse<{
    taskId: string;
    status: string;
    message: string;
  }>> {
    return this.request('/pipeline/run', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async getPipelineStatus(taskId: string): Promise<ApiResponse<{
    taskId: string;
    status: 'queued' | 'running' | 'completed' | 'failed';
    progress: number;
    phase: string;
    startedAt: string;
    completedAt?: string;
    steps?: Record<string, any>;
    error?: string;
  }>> {
    return this.request(`/pipeline/status/${taskId}`);
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

  async saveTickets(
    jackpotId: string,
    name: string,
    description: string | undefined,
    tickets: Array<{
      id: string;
      setKey: string;
      picks: string[];
      probability?: number;
      combinedOdds?: number;
    }>
  ): Promise<ApiResponse<{
    id: number;
    name: string;
    description: string | null;
    jackpotId: string;
    tickets: Array<any>;
    modelVersion: string | null;
    totalFixtures: number;
    createdAt: string;
    updatedAt: string;
  }>> {
    return this.request('/tickets/save', {
      method: 'POST',
      body: JSON.stringify({
        jackpot_id: jackpotId,
        name,
        description,
        tickets
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

  // Model Health endpoints
  async getModelHealth(): Promise<ApiResponse<{
    status: string;
    lastChecked: string;
    lastValidationDate: string | null;
    metrics: {
      brierScore: number | null;
      logLoss: number | null;
      accuracy: number | null;
    };
    alerts: string[];
    driftIndicators: Array<{
      league: string;
      driftScore: number;
      signal: 'normal' | 'elevated' | 'high';
      accuracy: number;
      matches: number;
    }>;
    oddsDistribution: Array<{
      bucket: string;
      divergence: number;
    }>;
    leagueDrift: Array<{
      league: string;
      driftScore: number;
      signal: 'normal' | 'elevated' | 'high';
      accuracy: number;
      matches: number;
    }>;
  }>> {
    return this.request('/model/health');
  }

  // Feature Store endpoints
  async getFeatureStoreStats(): Promise<ApiResponse<{
    stats: {
      status: string;
      total_features: number;
      team_features: number;
      match_features: number;
      memory_usage_mb: number;
    };
  }>> {
    return this.request('/feature-store/stats');
  }

  async getTeamFeatures(teamId?: number): Promise<ApiResponse<{
    teams: Array<{
      team_id: number;
      team_name: string;
      league: string;
      features: {
        attack?: number;
        defense?: number;
        [key: string]: any;
      };
      updated_at: string | null;
      data_quality: string;
    }>;
    total: number;
  }>> {
    const query = teamId ? `?team_id=${teamId}` : '';
    return this.request(`/feature-store/teams${query}`);
  }

  // Draw Ingestion endpoints
  async ingestLeagueDrawPriors(leagueCode: string, season?: string, csvPath?: string): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/league-priors', {
      method: 'POST',
      body: JSON.stringify({ league_code: leagueCode, season: season || 'ALL', csv_path: csvPath }),
    });
  }

  async batchIngestLeagueDrawPriors(
    options: {
      leagueCodes?: string[];
      season?: string;
      useAllLeagues?: boolean;
      useAllSeasons?: boolean;
      maxYears?: number;
    }
  ): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/league-priors/batch', {
      method: 'POST',
      body: JSON.stringify({
        league_codes: options.leagueCodes,
        season: options.season || 'ALL',
        use_all_leagues: options.useAllLeagues || false,
        use_all_seasons: options.useAllSeasons || false,
        max_years: options.maxYears,
      }),
    });
  }

  async getLeaguePriorsSummary(): Promise<ApiResponse<{
    total_priors: number;
    leagues_with_priors: number;
    total_leagues: number;
    unique_seasons: number;
    last_updated: string | null;
    by_league: Array<{
      code: string;
      name: string;
      count: number;
    }>;
  }>> {
    return this.request('/draw-ingestion/league-priors/summary', {
      method: 'GET',
    });
  }

  async getH2HStatsSummary(): Promise<ApiResponse<{
    total_records: number;
    leagues_with_stats: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{
      code: string;
      name: string;
      count: number;
    }>;
  }>> {
    return this.request('/draw-ingestion/h2h-stats/summary', {
      method: 'GET',
    });
  }

  async getEloRatingsSummary(): Promise<ApiResponse<{
    total_records: number;
    leagues_with_elo: number;
    total_leagues: number;
    unique_dates: number;
    last_updated: string | null;
    by_league: Array<{
      code: string;
      name: string;
      count: number;
    }>;
  }>> {
    return this.request('/draw-ingestion/elo-ratings/summary', {
      method: 'GET',
    });
  }

  async getWeatherSummary(): Promise<ApiResponse<{
    total_records: number;
    leagues_with_weather: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{
      code: string;
      name: string;
      count: number;
    }>;
  }>> {
    return this.request('/draw-ingestion/weather/summary', {
      method: 'GET',
    });
  }

  async getRefereeSummary(): Promise<ApiResponse<{
    total_records: number;
    last_updated: string | null;
    by_league: Array<{
      code: string;
      name: string;
      count: number;
    }>;
  }>> {
    return this.request('/draw-ingestion/referee/summary', {
      method: 'GET',
    });
  }

  async getRestDaysSummary(): Promise<ApiResponse<{
    total_records: number;
    leagues_with_rest_days: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{
      code: string;
      name: string;
      count: number;
    }>;
  }>> {
    return this.request('/draw-ingestion/rest-days/summary', {
      method: 'GET',
    });
  }

  async getOddsMovementSummary(): Promise<ApiResponse<{
    total_records: number;
    leagues_with_odds: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{
      code: string;
      name: string;
      count: number;
    }>;
  }>> {
    return this.request('/draw-ingestion/odds-movement/summary', {
      method: 'GET',
    });
  }

  async ingestH2HStats(homeTeamId: number, awayTeamId: number, useApi: boolean = false): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/h2h', {
      method: 'POST',
      body: JSON.stringify({ home_team_id: homeTeamId, away_team_id: awayTeamId, use_api: useApi }),
    });
  }

  async batchIngestH2HStats(options: {
    leagueCodes?: string[];
    season?: string;
    useAllLeagues?: boolean;
    useAllSeasons?: boolean;
    maxYears?: number;
    saveCsv?: boolean;
  }): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/h2h/batch', {
      method: 'POST',
      body: JSON.stringify({
        league_codes: options.leagueCodes,
        season: options.season || 'ALL',
        use_all_leagues: options.useAllLeagues || false,
        use_all_seasons: options.useAllSeasons || false,
        max_years: options.maxYears,
        save_csv: options.saveCsv !== false,
      }),
    });
  }

  async ingestEloRatings(teamId?: number, csvPath?: string, calculateFromMatches: boolean = false): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/elo', {
      method: 'POST',
      body: JSON.stringify({ team_id: teamId, csv_path: csvPath, calculate_from_matches: calculateFromMatches }),
    });
  }

  async ingestWeather(fixtureId: number, latitude: number, longitude: number, matchDatetime: string): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/weather', {
      method: 'POST',
      body: JSON.stringify({ fixture_id: fixtureId, latitude, longitude, match_datetime: matchDatetime }),
    });
  }

  async ingestRefereeStats(refereeId: number, refereeName?: string): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/referee', {
      method: 'POST',
      body: JSON.stringify({ referee_id: refereeId, referee_name: refereeName }),
    });
  }

  async ingestRestDays(fixtureId: number, homeTeamId?: number, awayTeamId?: number): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/rest-days', {
      method: 'POST',
      body: JSON.stringify({ fixture_id: fixtureId, home_team_id: homeTeamId, away_team_id: awayTeamId }),
    });
  }

  async ingestOddsMovement(fixtureId: number, drawOdds?: number): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/odds-movement', {
      method: 'POST',
      body: JSON.stringify({ fixture_id: fixtureId, draw_odds: drawOdds }),
    });
  }

  async batchIngestEloRatings(options: {
    leagueCodes?: string[];
    season?: string;
    useAllLeagues?: boolean;
    useAllSeasons?: boolean;
    maxYears?: number;
    saveCsv?: boolean;
  }): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/elo/batch', {
      method: 'POST',
      body: JSON.stringify({
        league_codes: options.leagueCodes,
        season: options.season || 'ALL',
        use_all_leagues: options.useAllLeagues || false,
        use_all_seasons: options.useAllSeasons || false,
        max_years: options.maxYears || 10,
        save_csv: options.saveCsv !== false,
      }),
    });
  }

  async batchIngestRefereeStats(options: {
    leagueCodes?: string[];
    season?: string;
    useAllLeagues?: boolean;
    useAllSeasons?: boolean;
    maxYears?: number;
    saveCsv?: boolean;
  }): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/referee/batch', {
      method: 'POST',
      body: JSON.stringify({
        league_codes: options.leagueCodes,
        season: options.season || 'ALL',
        use_all_leagues: options.useAllLeagues || false,
        use_all_seasons: options.useAllSeasons || false,
        max_years: options.maxYears || 10,
        save_csv: options.saveCsv !== false,
      }),
    });
  }

  async batchIngestRestDays(options: {
    leagueCodes?: string[];
    season?: string;
    useAllLeagues?: boolean;
    useAllSeasons?: boolean;
    maxYears?: number;
    saveCsv?: boolean;
  }): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/rest-days/batch', {
      method: 'POST',
      body: JSON.stringify({
        league_codes: options.leagueCodes,
        season: options.season || 'ALL',
        use_all_leagues: options.useAllLeagues || false,
        use_all_seasons: options.useAllSeasons || false,
        max_years: options.maxYears || 10,
        save_csv: options.saveCsv !== false,
      }),
    });
  }

  async batchIngestOddsMovement(options: {
    leagueCodes?: string[];
    season?: string;
    useAllLeagues?: boolean;
    useAllSeasons?: boolean;
    maxYears?: number;
    saveCsv?: boolean;
  }): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/odds-movement/batch', {
      method: 'POST',
      body: JSON.stringify({
        league_codes: options.leagueCodes,
        season: options.season || 'ALL',
        use_all_leagues: options.useAllLeagues || false,
        use_all_seasons: options.useAllSeasons || false,
        max_years: options.maxYears || 10,
        save_csv: options.saveCsv !== false,
      }),
    });
  }

  async ingestLeagueStructure(
    leagueCode: string,
    season: string,
    options?: {
      totalTeams?: number;
      relegationZones?: number;
      promotionZones?: number;
      playoffZones?: number;
      saveCsv?: boolean;
    }
  ): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/league-structure', {
      method: 'POST',
      body: JSON.stringify({
        league_code: leagueCode,
        season: season,
        total_teams: options?.totalTeams,
        relegation_zones: options?.relegationZones,
        promotion_zones: options?.promotionZones,
        playoff_zones: options?.playoffZones,
        save_csv: options?.saveCsv !== false,
      }),
    });
  }

  async batchIngestLeagueStructure(options: {
    leagueCodes?: string[];
    season?: string;
    useAllLeagues?: boolean;
    useAllSeasons?: boolean;
    maxYears?: number;
    saveCsv?: boolean;
  }): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/league-structure/batch', {
      method: 'POST',
      body: JSON.stringify({
        league_codes: options.leagueCodes,
        season: options.season || 'ALL',
        use_all_leagues: options.useAllLeagues || false,
        use_all_seasons: options.useAllSeasons || false,
        max_years: options.maxYears || 10,
        save_csv: options.saveCsv !== false,
      }),
    });
  }

  async getLeagueStructureSummary(): Promise<ApiResponse<{
    total_records: number;
    leagues_with_structure: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{ code: string; name: string; count: number }>;
  }>> {
    return this.request('/draw-ingestion/league-structure/summary');
  }

  async batchIngestWeather(options: {
    leagueCodes?: string[];
    season?: string;
    useAllLeagues?: boolean;
    useAllSeasons?: boolean;
    maxYears?: number;
    saveCsv?: boolean;
  }): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/weather/batch', {
      method: 'POST',
      body: JSON.stringify({
        league_codes: options.leagueCodes,
        season: options.season || 'ALL',
        use_all_leagues: options.useAllLeagues || false,
        use_all_seasons: options.useAllSeasons || false,
        max_years: options.maxYears || 10,
        save_csv: options.saveCsv !== false,
      }),
    });
  }

  async batchIngestTeamForm(options: {
    leagueCodes?: string[];
    season?: string;
    useAllLeagues?: boolean;
    useAllSeasons?: boolean;
    maxYears?: number;
    saveCsv?: boolean;
    matchesCount?: number;
  }): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/team-form/batch', {
      method: 'POST',
      body: JSON.stringify({
        league_codes: options.leagueCodes,
        season: options.season || (options.useAllSeasons ? 'ALL' : undefined),
        use_all_leagues: options.useAllLeagues || false,
        use_all_seasons: options.useAllSeasons || false,
        max_years: options.maxYears || 10,
        save_csv: options.saveCsv !== false,
        matches_count: options.matchesCount || 5,
      }),
    });
  }

  async batchIngestTeamInjuries(options: {
    leagueCodes?: string[];
    useAllLeagues?: boolean;
    saveCsv?: boolean;
    fixtureIds?: number[];
  }): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/team-injuries/batch', {
      method: 'POST',
      body: JSON.stringify({
        league_codes: options.leagueCodes,
        use_all_leagues: options.useAllLeagues || false,
        save_csv: options.saveCsv !== false,
        fixture_ids: options.fixtureIds,
      }),
    });
  }

  async importTeamInjuriesFromCsv(file: File): Promise<ApiResponse<any>> {
    const formData = new FormData();
    formData.append('file', file);
    
    const headers: HeadersInit = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    // Don't set Content-Type for FormData - browser will set it with boundary
    
    const response = await fetch(`${API_BASE_URL}/draw-ingestion/team-injuries/import-csv`, {
      method: 'POST',
      body: formData,
      headers,
    });

    if (!response.ok) {
      if (response.status === 401) {
        this.token = null;
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
      }
      
      let errorMessage = `API Error: ${response.status} ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = typeof errorData.detail === 'string' 
            ? errorData.detail 
            : JSON.stringify(errorData.detail);
        } else if (errorData.message) {
          errorMessage = errorData.message;
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

  async downloadTeamInjuries(options: {
    fixtureIds?: number[];
    leagueCodes?: string[];
    useAllLeagues?: boolean;
    source?: string;
  }): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/team-injuries/download', {
      method: 'POST',
      body: JSON.stringify({
        fixture_ids: options.fixtureIds,
        league_codes: options.leagueCodes,
        use_all_leagues: options.useAllLeagues || false,
        source: options.source || 'api-football',
      }),
    });
  }

  async ingestXGData(fixtureId?: number, matchId?: number, xgHome: number, xgAway: number): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/xg-data', {
      method: 'POST',
      body: JSON.stringify({
        fixture_id: fixtureId,
        match_id: matchId,
        xg_home: xgHome,
        xg_away: xgAway,
      }),
    });
  }

  async batchIngestXGData(options: {
    leagueCodes?: string[];
    season?: string;
    useAllLeagues?: boolean;
    useAllSeasons?: boolean;
    maxYears?: number;
    saveCsv?: boolean;
  }): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/xg-data/batch', {
      method: 'POST',
      body: JSON.stringify({
        league_codes: options.leagueCodes,
        season: options.season || 'ALL',
        use_all_leagues: options.useAllLeagues || false,
        use_all_seasons: options.useAllSeasons || false,
        max_years: options.maxYears || 10,
        save_csv: options.saveCsv !== false,
      }),
    });
  }

  async getXGDataSummary(): Promise<ApiResponse<{
    total_records: number;
    leagues_with_xg: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{ code: string; name: string; count: number }>;
  }>> {
    return this.request('/draw-ingestion/xg-data/summary');
  }

  async getTeamFormSummary(): Promise<ApiResponse<{
    total_records: number;
    fixture_records: number;
    historical_records: number;
    leagues_with_form: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{ code: string; name: string; count: number }>;
  }>> {
    return this.request('/draw-ingestion/team-form/summary');
  }

  async getTeamInjuriesSummary(): Promise<ApiResponse<{
    total_records: number;
    leagues_with_injuries: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{ code: string; name: string; count: number }>;
  }>> {
    return this.request('/draw-ingestion/team-injuries/summary');
  }

  async importAllDrawStructuralData(options: {
    useAllLeagues?: boolean;
    useAllSeasons?: boolean;
    maxYears?: number;
    leagueCodes?: string[];
    useHybridImport?: boolean;
  }): Promise<ApiResponse<{
    results: Record<string, any>;
    summary: {
      total_successful: number;
      total_failed: number;
      all_completed: boolean;
    };
  }>> {
    const body: any = {
      use_all_leagues: options.useAllLeagues !== false,
      use_all_seasons: options.useAllSeasons !== false,
      max_years: options.maxYears || 10,
      use_hybrid_import: options.useHybridImport !== false,
    };
    
    // Only include league_codes if it's provided and not empty
    if (options.leagueCodes && options.leagueCodes.length > 0) {
      body.league_codes = options.leagueCodes;
    }
    
    return this.request('/draw-ingestion/import-all', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  // Draw Diagnostics endpoints
  async getDrawDiagnostics(modelId?: number): Promise<ApiResponse<{
    brier_score: number | null;
    reliability_curve: Array<{
      predicted_prob: number;
      observed_frequency: number;
      sample_count: number;
      bin_low: number;
      bin_high: number;
    }>;
    sample_count: number;
    mean_predicted: number;
    mean_actual: number;
    calibration_error: number;
  }>> {
    const query = modelId ? `?model_id=${modelId}` : '';
    return this.request(`/draw/diagnostics${query}`);
  }

  async getDrawComponents(fixtureId: number): Promise<ApiResponse<{
    league_prior: number;
    elo_symmetry: number;
    h2h: number;
    weather: number;
    fatigue: number;
    referee: number;
    odds_drift: number;
    total_multiplier: number;
  }>> {
    return this.request(`/draw/components/${fixtureId}`);
  }

  async getDrawStats(): Promise<ApiResponse<{
    avg_multiplier: number | null;
    total_predictions: number;
    with_components: number;
    distribution: Array<{ category: string; count: number }>;
  }>> {
    return this.request('/draw/stats');
  }

  async trainDrawCalibrator(modelId?: number): Promise<ApiResponse<{
    is_fitted: boolean;
    message: string;
  }>> {
    const query = modelId ? `?model_id=${modelId}` : '';
    return this.request(`/draw/calibrate${query}`, { method: 'POST' });
  }

  // Dashboard endpoints
  async getDashboardSummary(): Promise<ApiResponse<{
    systemHealth: {
      modelVersion: string;
      modelStatus: string;
      lastRetrain: string | null;
      calibrationScore: number;
      logLoss: number;
      totalMatches: number;
      avgWeeklyAccuracy: number;
      drawAccuracy: number;
      leagueCount: number;
      seasonCount: number;
    };
    dataFreshness: Array<{
      source: string;
      lastUpdated: string | null;
      status: string;
      recordCount: number;
    }>;
    calibrationTrend: Array<{
      week: string;
      brier: number;
    }>;
    outcomeDistribution: Array<{
      name: string;
      predicted: number;
      actual: number;
    }>;
    leaguePerformance: Array<{
      league: string;
      accuracy: number;
      matches: number;
      status: string;
    }>;
  }>> {
    return this.request('/dashboard/summary');
  }

  // Injury Tracking Endpoints
  async recordInjuries(params: {
    team_id: number;
    fixture_id: number;
    key_players_missing?: number;
    injury_severity?: number;  // 0.0-1.0
    attackers_missing?: number;
    midfielders_missing?: number;
    defenders_missing?: number;
    goalkeepers_missing?: number;
    notes?: string;
  }): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/injuries', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async getInjuries(fixtureId: number, teamId: number): Promise<ApiResponse<any>> {
    return this.request(`/draw-ingestion/injuries/${fixtureId}/${teamId}`);
  }

  async batchRecordInjuries(injuries: Array<{
    team_id: number;
    fixture_id: number;
    key_players_missing?: number;
    injury_severity?: number;
    attackers_missing?: number;
    midfielders_missing?: number;
    defenders_missing?: number;
    goalkeepers_missing?: number;
    notes?: string;
  }>): Promise<ApiResponse<any>> {
    return this.request('/draw-ingestion/injuries/batch', {
      method: 'POST',
      body: JSON.stringify({ injuries }),
    });
  }

  // Sure Bet endpoints
  async validateSureBetGames(data: {
    games: Array<{
      id: string;
      homeTeam: string;
      awayTeam: string;
      draw?: string;
    }>;
  }): Promise<ApiResponse<{
    validatedGames: Array<{
      id: string;
      homeTeam: string;
      awayTeam: string;
      isValidated: boolean;
      needsTraining?: boolean;
      isTrained?: boolean;
      hasData?: boolean;
    }>;
  }>> {
    return this.request('/sure-bet/validate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async trainSureBetGames(data: {
    gameIds: string[];
  }): Promise<ApiResponse<{
    trained: number;
    failed: number;
  }>> {
    return this.request('/sure-bet/train', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async analyzeSureBets(data: {
    games: Array<{
      id: string;
      homeTeam: string;
      awayTeam: string;
    }>;
    maxResults?: number;
  }): Promise<ApiResponse<{
    sureBets: Array<{
      id: string;
      homeTeam: string;
      awayTeam: string;
      predictedOutcome: '1' | 'X' | '2';
      confidence: number;
      homeProbability: number;
      drawProbability: number;
      awayProbability: number;
      homeOdds?: number;
      drawOdds?: number;
      awayOdds?: number;
    }>;
  }>> {
    return this.request('/sure-bet/analyze', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async downloadAndValidateSureBetGames(data: {
    games: Array<{
      id: string;
      homeTeam: string;
      awayTeam: string;
      homeOdds?: number;
      drawOdds?: number;
      awayOdds?: number;
    }>;
  }): Promise<ApiResponse<{
    validatedGames: Array<{
      id: string;
      homeTeam: string;
      awayTeam: string;
      isValidated: boolean;
      needsTraining?: boolean;
      isTrained?: boolean;
      hasData?: boolean;
    }>;
    removedGames: Array<{
      id: string;
      homeTeam: string;
      awayTeam: string;
      reason: string;
    }>;
    downloaded: number;
    retrained: number;
  }>> {
    return this.request('/sure-bet/download-and-validate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async saveSureBetList(data: {
    name: string;
    description?: string;
    games: any[];
    betAmountKshs?: number;
    selectedGameIds?: string[];
    totalOdds?: number;
    totalProbability?: number;
    expectedAmountKshs?: number;
    weightedAmountKshs?: number;
  }): Promise<ApiResponse<{
    id: number;
    name: string;
    description?: string;
    createdAt: string;
  }>> {
    return this.request('/sure-bet/save-list', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getSavedSureBetLists(): Promise<ApiResponse<{
    savedLists: Array<{
      id: number;
      name: string;
      description?: string;
      betAmountKshs?: number;
      selectedGameIds: string[];
      totalOdds?: number;
      totalProbability?: number;
      expectedAmountKshs?: number;
      weightedAmountKshs?: number;
      createdAt: string;
      updatedAt: string;
    }>;
  }>> {
    return this.request('/sure-bet/saved-lists');
  }

  async getSavedSureBetList(listId: number): Promise<ApiResponse<{
    id: number;
    name: string;
    description?: string;
    games: any[];
    betAmountKshs?: number;
    selectedGameIds: string[];
    totalOdds?: number;
    totalProbability?: number;
    expectedAmountKshs?: number;
    weightedAmountKshs?: number;
    createdAt: string;
    updatedAt: string;
  }>> {
    return this.request(`/sure-bet/saved-lists/${listId}`);
  }

  async deleteSavedSureBetList(listId: number): Promise<ApiResponse<{}>> {
    return this.request(`/sure-bet/saved-lists/${listId}`, {
      method: 'DELETE',
    });
  }

  async importPDFGames(file: File): Promise<ApiResponse<{
    games: Array<{
      id: string;
      gameId: string;
      homeTeam: string;
      awayTeam: string;
      homeOdds?: number;
      drawOdds?: number;
      awayOdds?: number;
      doubleChance1X?: number;
      doubleChance12?: number;
      doubleChanceX2?: number;
    }>;
  }>> {
    const formData = new FormData();
    formData.append('file', file);
    
    const headers: HeadersInit = {};
    // Don't set Content-Type - browser will set it with boundary for FormData
    
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/sure-bet/import-pdf`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        if (response.status === 401) {
          this.token = null;
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        const errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
        throw new Error(errorMessage);
      }

      const data = await response.json();
      return data;
    } catch (error: any) {
      console.error('PDF import API error:', error);
      throw error;
    }
  }
}

export const apiClient = new ApiClient();
export default apiClient;

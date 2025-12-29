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
    });

    if (!response.ok) {
      if (response.status === 401) {
        // Token expired or invalid
        this.token = null;
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
      }
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
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

  // Probability endpoints
  async getProbabilities(jackpotId: string): Promise<ApiResponse<ProbabilitySet[]>> {
    return this.request(`/jackpots/${jackpotId}/probabilities`);
  }

  async getProbabilitySet(jackpotId: string, setId: string): Promise<ApiResponse<ProbabilitySet>> {
    return this.request(`/jackpots/${jackpotId}/probabilities/${setId}`);
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
}

export const apiClient = new ApiClient();
export default apiClient;

import {
  TokenResponse,
  User,
  Incident,
  AMCase,
  PMCase,
  TopCandidatesResponse,
  ReconciliationResponse,
  ReportResponse,
  AuditLogItem,
  AuditVerifyResponse,
  EvaluationMetrics,
  EvidenceGraphData,
  ImageEvidence,
} from '../types';


const API_BASE = '/api';

class ApiService {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('dvi_token');
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('dvi_token', token);
    } else {
      localStorage.removeItem('dvi_token');
    }
  }

  getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem('dvi_token');
    }
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    headers.set('Content-Type', 'application/json');

    const token = this.getToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      // Clear token on auth failure
      this.setToken(null);
    }

    if (!response.ok) {
      let errorMsg = `HTTP Error ${response.status}`;
      try {
        const errorJson = await response.json();
        errorMsg = errorJson.detail || errorJson.message || errorMsg;
      } catch (e) {
        // ignore
      }
      throw new Error(errorMsg);
    }

    return response.json();
  }

  // Auth
  async login(username: string, password: string): Promise<TokenResponse> {
    const res = await this.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    this.setToken(res.access_token);
    return res;
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  async listUsers(): Promise<User[]> {
    return this.request<User[]>('/auth/users');
  }

  // Incidents
  async getIncidents(): Promise<Incident[]> {
    return this.request<Incident[]>('/incidents');
  }

  async getIncident(id: string): Promise<Incident> {
    return this.request<Incident>(`/incidents/${id}`);
  }

  async createIncident(data: { name: string; location: string; description?: string }): Promise<Incident> {
    return this.request<Incident>('/incidents', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Ante-Mortem (AM)
  async listAMCases(incidentId?: string, search?: string): Promise<AMCase[]> {
    const params = new URLSearchParams();
    if (incidentId) params.append('incident_id', incidentId);
    if (search) params.append('search', search);
    return this.request<AMCase[]>(`/am?${params.toString()}`);
  }

  async getAMCase(id: string): Promise<AMCase> {
    return this.request<AMCase>(`/am/${id}`);
  }

  async createAMCase(data: any): Promise<AMCase> {
    return this.request<AMCase>('/am', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateAMCase(id: string, data: any): Promise<AMCase> {
    return this.request<AMCase>(`/am/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async extractAM(text: string, incidentId: string): Promise<any> {
    return this.request<any>('/am/extract', {
      method: 'POST',
      body: JSON.stringify({ text, incident_id: incidentId }),
    });
  }

  async reviewAM(submission: any): Promise<AMCase> {
    return this.request<AMCase>('/am/review', {
      method: 'POST',
      body: JSON.stringify(submission),
    });
  }

  // Post-Mortem (PM)
  async listPMCases(incidentId?: string, search?: string): Promise<PMCase[]> {
    const params = new URLSearchParams();
    if (incidentId) params.append('incident_id', incidentId);
    if (search) params.append('search', search);
    return this.request<PMCase[]>(`/pm?${params.toString()}`);
  }

  async getPMCase(id: string): Promise<PMCase> {
    return this.request<PMCase>(`/pm/${id}`);
  }

  async createPMCase(data: any): Promise<PMCase> {
    return this.request<PMCase>('/pm', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updatePMCase(id: string, data: any): Promise<PMCase> {
    return this.request<PMCase>(`/pm/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async extractPM(text: string, incidentId: string): Promise<any> {
    return this.request<any>('/pm/extract', {
      method: 'POST',
      body: JSON.stringify({ text, incident_id: incidentId }),
    });
  }

  async reviewPM(submission: any): Promise<PMCase> {
    return this.request<PMCase>('/pm/review', {
      method: 'POST',
      body: JSON.stringify(submission),
    });
  }

  // Matching & Reconciliation
  async getCandidates(pmId: string, limit: number = 3): Promise<TopCandidatesResponse> {
    return this.request<TopCandidatesResponse>(`/matching/${pmId}/candidates?limit=${limit}`);
  }

  async recalculateCandidates(pmId: string, limit: number = 3): Promise<TopCandidatesResponse> {
    return this.request<TopCandidatesResponse>(`/matching/${pmId}/recalculate?limit=${limit}`, {
      method: 'POST',
    });
  }

  async getMatchVersions(pmId: string): Promise<any[]> {
    return this.request<any[]>(`/matching/versions/${pmId}`);
  }

  async submitReconciliation(data: {
    pm_id: string;
    am_id: string;
    decision: string;
    reason: string;
    coordinator_comment?: string;
  }): Promise<ReconciliationResponse> {
    return this.request<ReconciliationResponse>('/reconciliation', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Evidence & Provenance
  async getEvidenceGraph(matchId: string): Promise<EvidenceGraphData> {
    return this.request<EvidenceGraphData>(`/evidence/${matchId}/graph`);
  }

  async getEvidenceProvenance(matchId: string): Promise<any> {
    return this.request<any>(`/evidence/${matchId}/provenance`);
  }

  // IBM Bob AI
  async getBobStatus(): Promise<{ configured: boolean; endpoint: string; fallback_active: boolean; mode: string; message: string }> {
    return this.request<any>('/bob/status');
  }

  async chatCopilot(data: { query: string; incident_id: string; context_pm_id?: string; context_am_id?: string }): Promise<any> {
    return this.request<any>('/bob/chat', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Reports
  async listReports(incidentId?: string): Promise<ReportResponse[]> {
    const params = incidentId ? `?incident_id=${incidentId}` : '';
    return this.request<ReportResponse[]>(`/reports${params}`);
  }

  async generateReport(data: { incident_id: string; pm_id: string; am_id: string; title?: string }): Promise<ReportResponse> {
    return this.request<ReportResponse>('/reports', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Audit
  async listAuditEvents(limit: number = 100): Promise<AuditLogItem[]> {
    return this.request<AuditLogItem[]>(`/audit?limit=${limit}`);
  }

  async verifyAuditChain(): Promise<AuditVerifyResponse> {
    return this.request<AuditVerifyResponse>('/audit/verify');
  }

  // Image Evidence & Gemini Vision
  async uploadImage(formData: FormData): Promise<ImageEvidence> {
    const headers = new Headers();
    const token = this.getToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const response = await fetch(`${API_BASE}/images/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      let errorMsg = `HTTP Error ${response.status}`;
      try {
        const errorJson = await response.json();
        errorMsg = errorJson.detail || errorJson.message || errorMsg;
      } catch (e) {
        // ignore
      }
      throw new Error(errorMsg);
    }

    return response.json();
  }

  async batchUploadImages(formData: FormData): Promise<ImageEvidence[]> {
    const headers = new Headers();
    const token = this.getToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const response = await fetch(`${API_BASE}/images/batch-upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      let errorMsg = `HTTP Error ${response.status}`;
      try {
        const errorJson = await response.json();
        errorMsg = errorJson.detail || errorJson.message || errorMsg;
      } catch (e) {
        // ignore
      }
      throw new Error(errorMsg);
    }

    return response.json();
  }

  async analyzeImage(imageId: string): Promise<any> {
    return this.request<any>(`/images/${imageId}/analyze`, {
      method: 'POST',
    });
  }

  async getImageAnalysis(imageId: string): Promise<ImageEvidence> {
    return this.request<ImageEvidence>(`/images/${imageId}/analysis`);
  }

  async reviewImage(
    imageId: string,
    decision: 'APPROVED' | 'MODIFIED_AND_APPROVED' | 'REJECTED',
    approvedObservations: any,
    notes?: string,
    options: {
      amId?: string;
      pmId?: string;
      incidentId?: string;
      autoCreateCase?: boolean;
      recordType?: 'AM' | 'PM';
    } = {}
  ): Promise<ImageEvidence> {
    return this.request<ImageEvidence>(`/images/${imageId}/review`, {
      method: 'POST',
      body: JSON.stringify({
        decision,
        approved_observations: approvedObservations,
        notes,
        am_id: options.amId,
        pm_id: options.pmId,
        incident_id: options.incidentId,
        auto_create_case: options.autoCreateCase,
        record_type: options.recordType,
      }),
    });
  }

  async listImages(params: { incidentId?: string; amId?: string; pmId?: string } = {}): Promise<ImageEvidence[]> {
    const query = new URLSearchParams();
    if (params.incidentId) query.append('incident_id', params.incidentId);
    if (params.amId) query.append('am_id', params.amId);
    if (params.pmId) query.append('pm_id', params.pmId);
    const queryString = query.toString() ? `?${query.toString()}` : '';
    return this.request<ImageEvidence[]>(`/images${queryString}`);
  }

  getImageFileUrl(imageId: string): string {
    const token = this.getToken();
    const query = token ? `?token=${encodeURIComponent(token)}` : '';
    return `${API_BASE}/images/${imageId}/file${query}`;
  }

  // Evaluation
  async getEvaluationMetrics(): Promise<EvaluationMetrics> {
    return this.request<EvaluationMetrics>('/evaluation');
  }
}

export const api = new ApiService();


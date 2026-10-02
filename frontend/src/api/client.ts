import type {
  AuditLog,
  CollectionResponse,
  DashboardResponse,
  DemoUser,
  Facility,
  ForecastPoint,
  ForecastEvaluation,
  ForecastExplanation,
  RiskExplanation,
  RecommendationExplanation,
  ForecastRun,
  InventoryBalance,
  InventoryTransaction,
  MLModelVersion,
  Medicine,
  RedistributionRecommendation,
  RedistributionTransfer,
  RiskAssessment,
  TokenResponse,
  User,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

export class APIClientError extends Error {
  code: string;
  status: number;
  details?: Record<string, any>;

  constructor(message: string, code: string = 'API_ERROR', status: number = 500, details?: Record<string, any>) {
    super(message);
    this.name = 'APIClientError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData: any;
    try {
      errorData = await response.json();
    } catch {
      // Ignored if non-json error
    }

    let message = response.statusText || 'An unexpected error occurred';
    let code = `HTTP_${response.status}`;
    let details: Record<string, any> | undefined = undefined;

    if (errorData) {
      if (typeof errorData.detail === 'string') {
        message = errorData.detail;
      } else if (errorData.detail?.error) {
        message = errorData.detail.error.message || message;
        code = errorData.detail.error.code || code;
        details = errorData.detail.error.details;
      } else if (errorData.error) {
        message = errorData.error.message || message;
        code = errorData.error.code || code;
        details = errorData.error.details;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
      }
    }

    if (response.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.dispatchEvent(new Event('auth-expired'));
    }

    throw new APIClientError(message, code, response.status, details);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // Auth
  login: async (credentials: { email?: string; username?: string; password?: string }) => {
    const email = credentials.email || credentials.username || '';
    const password = credentials.password || '';

    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      let err: any;
      try {
        err = await res.json();
      } catch {
        // Ignored
      }
      const message = typeof err?.detail === 'string' ? err.detail : 'Invalid login credentials';
      throw new APIClientError(message, 'AUTH_FAILED', res.status);
    }

    return res.json() as Promise<TokenResponse>;
  },

  getCurrentUser: () => request<User>('/auth/me'),
  getDemoUsers: () => request<DemoUser[]>('/users/demo'),

  // Dashboard
  getDashboard: (params?: {
    facility_id?: string;
    medicine_id?: string;
    risk_level?: string;
    transfer_status?: string;
    recommendation_status?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.facility_id) query.append('facility_id', params.facility_id);
    if (params?.medicine_id) query.append('medicine_id', params.medicine_id);
    if (params?.risk_level) query.append('risk_level', params.risk_level);
    if (params?.transfer_status) query.append('transfer_status', params.transfer_status);
    if (params?.recommendation_status) query.append('recommendation_status', params.recommendation_status);

    const qStr = query.toString() ? `?${query.toString()}` : '';
    return request<DashboardResponse>(`/dashboard${qStr}`);
  },

  // Facilities
  getFacilities: (page = 1, pageSize = 50) =>
    request<CollectionResponse<Facility>>(`/facilities?page=${page}&page_size=${pageSize}`),
  getFacility: (id: string) => request<Facility>(`/facilities/${id}`),

  // Medicines
  getMedicines: (page = 1, pageSize = 200) =>
    request<CollectionResponse<Medicine>>(`/medicines?page=${page}&page_size=${pageSize}`),
  getMedicine: async (id: string) => {
    // This API exposes the catalog as a list; resolve details from its real paginated data.
    let page = 1;
    while (true) {
      const result = await request<CollectionResponse<Medicine>>(`/medicines?page=${page}&page_size=200`);
      const medicine = result.data.find((item) => item.id === id);
      if (medicine) return medicine;
      if (page >= result.pagination.total_pages) {
        throw new APIClientError('Medicine was not found in the catalog.', 'NOT_FOUND', 404);
      }
      page += 1;
    }
  },

  // Inventory
  getInventoryBalances: (facilityId?: string, medicineId?: string, page = 1, pageSize = 50) => {
    const query = new URLSearchParams();
    if (facilityId) query.append('facility_id', facilityId);
    if (medicineId) query.append('medicine_id', medicineId);
    query.append('page', page.toString());
    query.append('page_size', pageSize.toString());
    return request<CollectionResponse<InventoryBalance>>(`/inventory?${query.toString()}`);
  },

  getInventoryTransactions: (facilityId?: string, medicineId?: string, page = 1, pageSize = 50) => {
    const query = new URLSearchParams();
    if (facilityId) query.append('facility_id', facilityId);
    if (medicineId) query.append('medicine_id', medicineId);
    query.append('page', page.toString());
    query.append('page_size', pageSize.toString());
    return request<CollectionResponse<InventoryTransaction>>(`/inventory/transactions?${query.toString()}`);
  },

  createTransaction: (data: {
    facility_id: string;
    medicine_id: string;
    transaction_type: string;
    quantity: number;
    transaction_date?: string;
    reference_number?: string;
    notes?: string;
  }) =>
    request<InventoryTransaction>('/inventory/transactions', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Risk Assessments
  getRiskAssessments: (params?: { facility_id?: string; medicine_id?: string; risk_level?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.facility_id) query.append('facility_id', params.facility_id);
    if (params?.medicine_id) query.append('medicine_id', params.medicine_id);
    if (params?.risk_level) query.append('risk_level', params.risk_level);
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());
    return request<CollectionResponse<RiskAssessment>>(`/risk-assessments?${query.toString()}`);
  },

  getRiskAssessment: (id: string) => request<RiskAssessment>(`/risk-assessments/${id}`),

  generateRiskAssessment: (data: { facility_id: string; medicine_id: string; forecast_run_id?: string }) =>
    request<RiskAssessment>('/risk-assessments/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Forecasts & Models
  getForecastRuns: (facilityId?: string, medicineId?: string, page = 1, pageSize = 50) => {
    const query = new URLSearchParams();
    if (facilityId) query.append('facility_id', facilityId);
    if (medicineId) query.append('medicine_id', medicineId);
    query.append('page', page.toString());
    query.append('page_size', pageSize.toString());
    return request<CollectionResponse<ForecastRun>>(`/forecasts?${query.toString()}`);
  },

  getForecastSummary: (runId: string) =>
    request<{ run: ForecastRun; points: ForecastPoint[] }>(`/forecasts/${runId}`),

  generateForecast: (data: {
    facility_id: string;
    medicine_id: string;
    model_code?: string;
    horizon_days?: number;
    lookback_days?: number;
  }) =>
    request<{ run: ForecastRun; points: ForecastPoint[] }>('/forecasts/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getForecastEvaluation: (params?: { facility_id?: string; medicine_id?: string; start_date?: string; end_date?: string; limit?: number }) => {
    const query = new URLSearchParams();
    Object.entries(params || {}).forEach(([key, value]) => { if (value !== undefined && value !== '') query.set(key, String(value)); });
    return request<ForecastEvaluation>(`/forecast-evaluation?${query.toString()}`);
  },
  getForecastExplanation: (id: string) => request<ForecastExplanation>(`/forecasts/${id}/explanation`),
  getRiskExplanation: (id: string) => request<RiskExplanation>(`/risk-assessments/${id}/explanation`),
  getRecommendationExplanation: (id: string) =>
    request<RecommendationExplanation>(`/redistributions/recommendations/${id}/explanation`),

  getModels: () => request<MLModelVersion[]>('/models'),

  // Redistribution Recommendations
  getRecommendations: (params?: {
    status?: string;
    source_facility_id?: string;
    destination_facility_id?: string;
    medicine_id?: string;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.source_facility_id) query.append('source_facility_id', params.source_facility_id);
    if (params?.destination_facility_id) query.append('destination_facility_id', params.destination_facility_id);
    if (params?.medicine_id) query.append('medicine_id', params.medicine_id);
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());
    return request<CollectionResponse<RedistributionRecommendation>>(`/redistributions/recommendations?${query.toString()}`);
  },

  getRecommendation: (id: string) =>
    request<RedistributionRecommendation>(`/redistributions/recommendations/${id}`),

  generateRecommendation: (data: {
    destination_facility_id: string;
    medicine_id: string;
    planning_horizon_days?: number;
    source_facility_id?: string;
    forecast_run_id?: string;
  }) =>
    request<RedistributionRecommendation>('/redistributions/recommendations/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  approveRecommendation: (id: string, note?: string) =>
    request<RedistributionRecommendation>(`/redistributions/recommendations/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),

  rejectRecommendation: (id: string, note?: string) =>
    request<RedistributionRecommendation>(`/redistributions/recommendations/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),

  getSurplusCandidates: (medicineId: string, horizonDays = 14) =>
    request<CollectionResponse<any>>(`/redistributions/inventory/surplus?medicine_id=${medicineId}&planning_horizon_days=${horizonDays}`),

  getShortageCandidates: (medicineId: string, horizonDays = 14) =>
    request<CollectionResponse<any>>(`/redistributions/inventory/shortages?medicine_id=${medicineId}&planning_horizon_days=${horizonDays}`),

  // Transfers
  getTransfers: (params?: {
    status?: string;
    source_facility_id?: string;
    destination_facility_id?: string;
    medicine_id?: string;
    recommendation_id?: string;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.source_facility_id) query.append('source_facility_id', params.source_facility_id);
    if (params?.destination_facility_id) query.append('destination_facility_id', params.destination_facility_id);
    if (params?.medicine_id) query.append('medicine_id', params.medicine_id);
    if (params?.recommendation_id) query.append('recommendation_id', params.recommendation_id);
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());
    return request<CollectionResponse<RedistributionTransfer>>(`/transfers?${query.toString()}`);
  },

  getTransfer: (id: string) => request<RedistributionTransfer>(`/transfers/${id}`),

  createTransfer: (data: { recommendation_id: string; batch_id?: string; quantity: number }) =>
    request<RedistributionTransfer>('/transfers', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  dispatchTransfer: (id: string) =>
    request<RedistributionTransfer>(`/transfers/${id}/dispatch`, {
      method: 'POST',
    }),

  completeTransfer: (id: string) =>
    request<RedistributionTransfer>(`/transfers/${id}/complete`, {
      method: 'POST',
    }),

  cancelTransfer: (id: string, reason?: string) =>
    request<RedistributionTransfer>(`/transfers/${id}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  // Audit Logs
  getAuditLogs: (params?: { action?: string; entity_type?: string; entity_id?: string; user_id?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.action) query.append('action', params.action);
    if (params?.entity_type) query.append('entity_type', params.entity_type);
    if (params?.entity_id) query.append('entity_id', params.entity_id);
    if (params?.user_id) query.append('user_id', params.user_id);
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());
    return request<CollectionResponse<AuditLog>>(`/audit?${query.toString()}`);
  },
};

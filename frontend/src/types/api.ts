export type RoleCode = 'ADMINISTRATOR' | 'INVENTORY_OFFICER' | 'SUPPLY_CHAIN_MANAGER';

export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type RedistributionRecommendationStatus =
  | 'PENDING_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'EXPIRED'
  | 'CANCELLED';

export type RedistributionTransferStatus =
  | 'APPROVED'
  | 'IN_TRANSIT'
  | 'COMPLETED'
  | 'CANCELLED';

export type InventoryTransactionType =
  | 'RECEIPT'
  | 'CONSUMPTION'
  | 'ADJUSTMENT_IN'
  | 'ADJUSTMENT_OUT'
  | 'TRANSFER_IN'
  | 'TRANSFER_OUT';

export type DataClassification = 'CONFIRMED' | 'DERIVED' | 'PREDICTED' | 'RECOMMENDED';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: {
    id: string;
    code: RoleCode;
    name: string;
  };
  is_active: boolean;
  title?: string;
  facility_id?: string;
  last_login_at?: string;
  is_demo_user?: boolean;
  created_at: string;
}

export interface DemoUser {
  id: string;
  email: string;
  full_name: string;
  title?: string;
  facility_id?: string;
  facility_name?: string;
  role_code: RoleCode;
  role_name: string;
  is_active: boolean;
  last_login_at?: string;
  is_demo_user: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Facility {
  id: string;
  code: string;
  name: string;
  county?: string;
  sub_county?: string;
  ward?: string;
  facility_type?: string;
  official_name?: string;
  display_name?: string;
  kmhfr_code?: string;
  latitude?: number;
  longitude?: number;
  keph_level?: string;
  ownership_category?: string;
  operational_status?: string;
  service_24_hour?: boolean;
  weekend_service?: boolean;
  bed_capacity?: number;
  maternity_beds?: number;
  icu_beds?: number;
  hdu_beds?: number;
  emergency_beds?: number;
  cots?: number;
  key_services?: string[];
  reference_note?: string;
  transfer_eligible?: boolean;
  source_name?: string;
  source_url?: string;
  source_type?: string;
  source_record_id?: string;
  source_version?: string;
  retrieved_at?: string;
  verification_status?: string;
  is_active: boolean;
  created_at: string;
}

export interface Medicine {
  id: string;
  code: string;
  generic_name: string;
  strength?: string;
  dosage_form?: string;
  category?: string;
  keml_section?: string;
  level_of_use?: number;
  aware_classification?: string;
  restricted?: boolean;
  keml_notes?: string;
  source_name?: string;
  source_url?: string;
  source_type?: string;
  source_record_id?: string;
  source_version?: string;
  retrieved_at?: string;
  verification_status?: string;
  unit_of_measure: string;
  is_active: boolean;
  created_at: string;
}

export interface FacilityMedicinePolicy {
  id: string;
  facility_id: string;
  medicine_id: string;
  safety_stock: number;
  reorder_point: number;
  lead_time_days: number;
}

export interface InventoryBalance {
  id: string;
  facility_id: string;
  medicine_id: string;
  quantity_on_hand: number;
  updated_at?: string;
}

export interface InventoryTransaction {
  id: string;
  facility_id: string;
  medicine_id: string;
  transaction_type: InventoryTransactionType;
  quantity: number;
  transaction_date: string;
  reference_number?: string;
  notes?: string;
  created_by: string;
  created_at: string;
}

export interface Batch {
  id: string;
  facility_id: string;
  medicine_id: string;
  batch_number: string;
  expiry_date: string;
  quantity: number;
}

export interface ForecastPoint {
  id: string;
  forecast_run_id: string;
  target_date: string;
  predicted_demand: number;
  lower_bound?: number;
  upper_bound?: number;
}

export interface ForecastRun {
  id: string;
  facility_id: string;
  medicine_id: string;
  model_version_id: string;
  generated_at: string;
  forecast_start_date: string;
  horizon_days: number;
  mae?: number;
  status: string;
}

export interface EvaluationRow {
  facility_id: string;
  medicine_id: string;
  facility_name?: string | null;
  medicine_name?: string | null;
  model: 'MOVING_AVERAGE_7D' | 'RANDOM_FOREST';
  training_start: string;
  training_end: string | null;
  holdout_start: string | null;
  holdout_end: string | null;
  training_observations: number | null;
  observations: number;
  mae: number | null;
  rmse: number | null;
  wape: number | null;
  status: 'MEASURED' | 'INSUFFICIENT_DATA';
  reason: string | null;
}

export interface ForecastEvaluation {
  start_date: string;
  end_date: string;
  evaluated_series: number;
  methodology: string;
  data_note: string;
  results: EvaluationRow[];
}

export interface ForecastExplanation {
  forecast_run_id: string;
  model: string;
  training_start: string;
  training_end: string;
  training_observations: number;
  forecast_start: string;
  horizon_days: number;
  features: { name: string; description: string }[];
  feature_importance: null;
  note: string;
}

export interface RiskExplanation {
  assessment_id: string;
  current_stock: number;
  safety_stock: number;
  forecasted_demand: number;
  forecast_days: number;
  projected_inventory: number;
  days_to_breach: number | null;
  projected_breach_date: string | null;
  projected_stockout_date: string | null;
  risk_level: RiskLevel;
  confirmed_incoming_quantity: number;
  projected_shortage: number;
  feasible_donor_facility_id: string | null;
  feasible_donor_surplus: number | null;
  recommendation_id: string | null;
  recommended_quantity: number | null;
  human_action: string;
  note: string;
}

export interface RecommendationExplanation {
  recommendation_id: string;
  source_facility: string;
  destination_facility: string;
  medicine: string;
  source_current_stock: number;
  source_usable_surplus: number;
  destination_current_stock: number;
  destination_projected_shortage: number;
  source_safety_stock: number;
  destination_safety_stock: number;
  source_projected_after_transfer: number;
  recommended_quantity: number;
  status: RedistributionRecommendationStatus;
  reason: string;
  note: string;
}

export interface MLModelVersion {
  id: string;
  code: string;
  name: string;
  algorithm: string;
  version: string;
  is_active: boolean;
}

export interface RiskAssessment {
  id: string;
  facility_id: string;
  medicine_id: string;
  forecast_run_id: string;
  assessed_at: string;
  risk_level: RiskLevel;
  currently_out_of_stock: boolean;
  days_to_breach?: number;
  projected_breach_date?: string;
  projected_stockout_date?: string;
  projected_shortage_units: number;
  inventory_on_hand: number;
  safety_stock: number;
  reorder_point: number;
}

export interface RedistributionRecommendation {
  id: string;
  source_facility_id: string;
  destination_facility_id: string;
  medicine_id: string;
  status: RedistributionRecommendationStatus;
  planning_horizon_days: number;
  source_surplus_units: number;
  destination_shortage_units: number;
  recommended_quantity: number;
  source_inventory_before: number;
  destination_inventory_before: number;
  source_safety_stock: number;
  destination_safety_stock: number;
  source_projected_end_inventory: number;
  destination_projected_end_inventory: number;
  constraint_results: Record<string, any>;
  expires_at: string;
  created_by: string;
  reviewed_by?: string;
  reviewed_at?: string;
  review_note?: string;
  created_at: string;
}

export interface RedistributionTransfer {
  id: string;
  recommendation_id: string;
  source_facility_id: string;
  destination_facility_id: string;
  medicine_id: string;
  batch_id?: string;
  quantity: number;
  status: RedistributionTransferStatus;
  approved_by: string;
  approved_at: string;
  dispatched_by?: string;
  dispatched_at?: string;
  received_by?: string;
  received_at?: string;
  cancelled_by?: string;
  cancelled_at?: string;
  cancellation_reason?: string;
  created_at: string;
}

export interface AuditLog {
  id: string;
  user_id?: string;
  action: string;
  entity_type: string;
  entity_id: string;
  previous_state?: Record<string, any>;
  new_state?: Record<string, any>;
  details?: Record<string, any>;
  timestamp: string;
}

export interface DashboardSummary {
  facilities_count: number;
  medicines_tracked: number;
  active_stockouts: number;
  critical_risk_count: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  pending_redistribution_count: number;
  in_transit_transfer_count: number;
  inventory_health: {
    healthy_count: number;
    at_risk_count: number;
    stockout_count: number;
  };
  data_timestamp: string;
}

export interface DashboardRiskItem {
  facility_id: string;
  facility_code: string;
  facility_name: string;
  medicine_id: string;
  medicine_code: string;
  generic_name: string;
  current_stock: number;
  safety_stock: number;
  days_until_breach?: number;
  projected_stockout_date?: string;
  risk_level: RiskLevel;
  forecast_run_id?: string;
  assessed_at: string;
  data_classification: DataClassification;
}

export interface DashboardRedistributionItem {
  recommendation_id: string;
  source_facility_id: string;
  source_facility_name: string;
  destination_facility_id: string;
  destination_facility_name: string;
  medicine_id: string;
  medicine_name: string;
  recommended_quantity: number;
  source_surplus_units: number;
  destination_shortage_units: number;
  status: RedistributionRecommendationStatus;
  created_at: string;
  expires_at: string;
  data_classification: DataClassification;
}

export interface DashboardTransferItem {
  transfer_id: string;
  recommendation_id: string;
  source_facility_id: string;
  source_facility_name: string;
  destination_facility_id: string;
  destination_facility_name: string;
  medicine_id: string;
  medicine_name: string;
  quantity: number;
  status: RedistributionTransferStatus;
  created_at: string;
  dispatched_at?: string;
  received_at?: string;
  data_classification: DataClassification;
}

export interface DashboardFacilitySummary {
  facility_id: string;
  facility_code: string;
  facility_name: string;
  tracked_medicines: number;
  active_stockouts: number;
  critical_high_risk_count: number;
  pending_redistributions: number;
  in_transit_transfers: number;
  healthy_count: number;
  at_risk_count: number;
  stockout_count: number;
}

export interface DashboardResponse {
  summary: DashboardSummary;
  risk_worklist: DashboardRiskItem[];
  redistribution_queue: DashboardRedistributionItem[];
  recent_transfers: DashboardTransferItem[];
  facility_summaries: DashboardFacilitySummary[];
}

export interface CollectionResponse<T> {
  data: T[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

export interface APIError {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
}

export interface ScenarioParameters {
  facility_id: string; medicine_id: string; demand_adjustment_pct: number;
  inventory_adjustment_pct: number; lead_time_adjustment_days: number; horizon_days: number;
}
export interface ScenarioOutcome {
  daily_demand: number; current_stock: number; days_to_breach: number | null;
  risk_level: string; projected_shortage: number; incoming_quantity: number;
  feasible_donor: string | null; recommended_quantity: number; redistribution_feasible: boolean;
  trajectory: { date: string; projected_stock: number; daily_demand: number }[];
}
export interface ScenarioResult {
  id: string; created_at: string; fingerprint: string; label: string; parameters: ScenarioParameters;
  context: { assessment_date: string; medicine_name: string; destination: { facility_name: string; forecast_run_id: string }; excluded_donors: {facility: string; reason: string}[] };
  baseline: ScenarioOutcome; scenario: ScenarioOutcome;
  differences: Record<string, number | string | null>; explanations: string[];
}
export interface ModelMetrics { model: string; evaluated_series: number; observations: number; mae: number; rmse: number; wape: number | null }
export interface AggregateEvaluation {
  id: string; created_at: string; fingerprint: string; parameters: {start_date: string; end_date: string};
  overall: ModelMetrics[]; by_facility: {id: string; name: string; metrics: ModelMetrics[]}[];
  by_medicine: {id: string; name: string; metrics: ModelMetrics[]}[]; series_count: number;
  methodology: string; data_note: string;
}
export interface DecisionAnalytics {
  inventory: {stock: {facility_id: string; medicine_id: string; facility: string; medicine: string; quantity: number; unit: string}[]; active_stockouts: number; low_stock_items: number; surplus_items: number; projected_shortage_items: number; position_coverage: number};
  forecasting: {runs: number; evaluation: AggregateEvaluation | null};
  risk: Record<string, number>; redistribution: Record<string, number>; transfers: Record<string, number>;
  activity: {date: string; recommendations: number; transfers: number}[]; note: string;
}

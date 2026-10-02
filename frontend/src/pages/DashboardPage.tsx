import type { AggregateEvaluation } from '../types/analytics';
import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { DashboardResponse, RiskLevel } from '../types/api';
import { DataBadge } from '../components/common/DataBadge';
import {
  AlertTriangle,
  ArrowRightLeft,
  Truck,
  Package,
  RefreshCw,
  Building2,
} from 'lucide-react';

interface DashboardPageProps {
  onNavigate: (tab: string, param?: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [evaluation, setEvaluation] = useState<AggregateEvaluation | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.getDashboard();
      setData(res);
      api.getAggregateEvaluation().then(setEvaluation).catch(() => setEvaluation(null));
    } catch (err: any) {
      setError(err?.message || 'Failed to load dashboard operational read model.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  if (isLoading) {
    return (
      <div className="p-8 space-y-6 animate-pulse">
        <div className="h-8 bg-slate-100 rounded w-64"></div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-slate-100 rounded-xl"></div>
          ))}
        </div>
        <div className="h-64 bg-slate-100 rounded-xl"></div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center">
        <div className="inline-flex p-4 rounded-full bg-red-50/60 text-red-700 mb-3">
          <AlertTriangle className="w-8 h-8" />
        </div>
        <h3 className="text-lg font-semibold text-slate-900">Operational Data Error</h3>
        <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">{error}</p>
        <button
          onClick={loadDashboard}
          className="mt-4 px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-900 text-xs font-semibold inline-flex items-center gap-2"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry Data Fetch</span>
        </button>
      </div>
    );
  }

  const { summary, risk_worklist, redistribution_queue, recent_transfers, facility_summaries } = data;

  const getRiskBadge = (level: RiskLevel) => {
    switch (level) {
      case 'CRITICAL':
        return <span className="px-2 py-0.5 rounded text-xs font-bold bg-red-50 text-red-700 border border-red-500/50">CRITICAL</span>;
      case 'HIGH':
        return <span className="px-2 py-0.5 rounded text-xs font-bold bg-amber-50 text-amber-700 border border-amber-500/50">HIGH</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 rounded text-xs font-bold bg-yellow-50 text-yellow-700 border border-yellow-500/50">MEDIUM</span>;
      case 'LOW':
        return <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-500/50">LOW</span>;
    }
  };

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Operational Control Dashboard</h2>
          <p className="text-xs text-slate-500 mt-1">
            Aggregated Supply Chain Read Model — Last generated at {new Date(summary.data_timestamp).toLocaleTimeString()}
          </p>
        </div>

        <button
          onClick={loadDashboard}
          className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium inline-flex items-center gap-1.5 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Data</span>
        </button>
      </div>

      <div className="flex flex-wrap gap-3">
        <button onClick={() => onNavigate('scenario')} className="rounded-lg border border-indigo-200 bg-white px-4 py-2 text-sm font-semibold text-indigo-700">Open Scenario Analysis</button>
        <button onClick={() => onNavigate('reports')} className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700">View Decision Analytics</button>
      </div>
      {/* Priority Summary Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          onClick={() => onNavigate('risk')}
          className="p-5 rounded-xl bg-white border border-red-200/40 hover:border-red-600/50 cursor-pointer transition-all shadow-lg"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Critical & High Stockout Risk</span>
            <AlertTriangle className="w-5 h-5 text-red-700" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-red-700">
              {summary.critical_risk_count + summary.high_risk_count}
            </span>
            <span className="text-xs text-slate-500">
              ({summary.critical_risk_count} Critical, {summary.high_risk_count} High)
            </span>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px]">
            <span className="text-slate-500">Active Stockouts: {summary.active_stockouts}</span>
            <DataBadge type="DERIVED" label="DERIVED / RISK" />
          </div>
        </div>

        <div
          onClick={() => onNavigate('redistribution')}
          className="p-5 rounded-xl bg-white border border-amber-200/40 hover:border-amber-600/50 cursor-pointer transition-all shadow-lg"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Pending Redistribution Queue</span>
            <ArrowRightLeft className="w-5 h-5 text-amber-700" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-amber-700">{summary.pending_redistribution_count}</span>
            <span className="text-xs text-slate-500">Actionable recommendations</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px]">
            <span className="text-slate-500">Requires human review</span>
            <DataBadge type="RECOMMENDED" />
          </div>
        </div>

        <div
          onClick={() => onNavigate('transfers')}
          className="p-5 rounded-xl bg-white border border-indigo-200/40 hover:border-indigo-600/50 cursor-pointer transition-all shadow-lg"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">In-Transit Transfers</span>
            <Truck className="w-5 h-5 text-indigo-700" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-indigo-700">{summary.in_transit_transfer_count}</span>
            <span className="text-xs text-slate-500">Physical transfers dispatched</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px]">
            <span className="text-slate-500">Awaiting destination receipt</span>
            <DataBadge type="CONFIRMED" label="CONFIRMED STATE" />
          </div>
        </div>

        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Inventory Health Breakdown</span>
            <Package className="w-5 h-5 text-emerald-700" />
          </div>
          <div className="mt-3 flex items-center gap-3">
            <div className="text-center">
              <span className="text-lg font-bold text-emerald-700">{summary.inventory_health.healthy_count}</span>
              <p className="text-[10px] text-slate-500">Healthy</p>
            </div>
            <div className="text-center">
              <span className="text-lg font-bold text-amber-700">{summary.inventory_health.at_risk_count}</span>
              <p className="text-[10px] text-slate-500">At Risk</p>
            </div>
            <div className="text-center">
              <span className="text-lg font-bold text-red-700">{summary.inventory_health.stockout_count}</span>
              <p className="text-[10px] text-slate-500">Stockout</p>
            </div>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px]">
            <span className="text-slate-500">{summary.medicines_tracked} medicines tracked</span>
            <DataBadge type="DERIVED" />
          </div>
        </div>
      </div>

      <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div><h3 className="text-sm font-bold text-slate-900">Forecasting performance</h3>
            <p className="text-xs text-slate-500">Measured 14-day temporal holdout across eligible recorded series; synthetic demo data, not future accuracy.</p></div>
          <button onClick={() => onNavigate('forecasts')} className="text-xs font-semibold text-indigo-700">View evaluation →</button>
        </div>
        {evaluation ? <div className="flex flex-wrap gap-3 mt-3">{evaluation.overall.map((row) =>
          <div key={row.model} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs min-w-40">
            <strong className="block text-slate-900">{row.model === 'MOVING_AVERAGE_7D' ? 'Moving Average' : 'Random Forest'}</strong>
            <span className="block text-slate-500 mb-1">{row.evaluated_series} evaluated series</span>
            <span>MAE {row.mae.toFixed(2)} · RMSE {row.rmse.toFixed(2)} · WAPE {row.wape?.toFixed(2) ?? "—"}% · n={row.observations}</span>
          </div>)}</div> : <p className="mt-3 text-xs text-slate-500">Evaluation unavailable.</p>}
      </section>

      {/* Stockout Risk Worklist */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-slate-900">Priority Stockout Risk Worklist</h3>
            <p className="text-xs text-slate-500">Ordered by breach urgency and risk level</p>
          </div>
          <button
            onClick={() => onNavigate('risk')}
            className="text-xs font-medium text-blue-700 hover:text-blue-800"
          >
            View All Risk Items →
          </button>
        </div>

        {risk_worklist.length === 0 ? (
          <div className="p-6 text-center text-slate-500 text-xs">
            No stockout risk items detected. All facilities maintain sufficient inventory.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 text-slate-500 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Facility</th>
                  <th className="py-3 px-4">Medicine</th>
                  <th className="py-3 px-4">Current Stock</th>
                  <th className="py-3 px-4">Safety Stock</th>
                  <th className="py-3 px-4">Days to Breach</th>
                  <th className="py-3 px-4">Projected Stockout</th>
                  <th className="py-3 px-4">Classification</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {risk_worklist.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-100/40 transition-colors">
                    <td className="py-3 px-4">{getRiskBadge(item.risk_level)}</td>
                    <td className="py-3 px-4 font-medium text-slate-900">{item.facility_name}</td>
                    <td className="py-3 px-4 text-slate-700">{item.generic_name}</td>
                    <td className="py-3 px-4 font-semibold text-slate-900">{item.current_stock}</td>
                    <td className="py-3 px-4 text-slate-500">{item.safety_stock}</td>
                    <td className="py-3 px-4 font-bold text-amber-700">
                      {item.days_until_breach !== null && item.days_until_breach !== undefined
                        ? `${item.days_until_breach} days`
                        : item.current_stock <= 0 ? 'Active stockout' : 'No breach projected'}
                    </td>
                    <td className="py-3 px-4 text-slate-500">{item.projected_stockout_date || 'N/A'}</td>
                    <td className="py-3 px-4">
                      <DataBadge type={item.data_classification} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Redistribution & Transfer Side-by-Side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Redistribution Queue */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">Redistribution Queue</h3>
              <p className="text-xs text-slate-500">Decision-support recommendations requiring review</p>
            </div>
            <button
              onClick={() => onNavigate('redistribution')}
              className="text-xs font-medium text-amber-700 hover:text-amber-700"
            >
              Manage Queue →
            </button>
          </div>

          {redistribution_queue.length === 0 ? (
            <div className="p-6 text-center text-slate-500 text-xs">
              No pending redistribution recommendations in queue.
            </div>
          ) : (
            <div className="space-y-3">
              {redistribution_queue.slice(0, 5).map((item) => (
                <div
                  key={item.recommendation_id}
                  onClick={() => onNavigate('redistribution')}
                  className="p-3 rounded-lg bg-slate-50/60 border border-slate-200 hover:border-amber-500/40 cursor-pointer transition-all"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-xs text-slate-900">{item.medicine_name}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-600/40">
                      {item.status}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 flex items-center gap-2">
                    <span>{item.source_facility_name}</span>
                    <span>→</span>
                    <span>{item.destination_facility_name}</span>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500">
                    <span>Rec Qty: <strong className="text-slate-700">{item.recommended_quantity}</strong></span>
                    <DataBadge type={item.data_classification} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Transfer Activity */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">Recent Transfer Tracking</h3>
              <p className="text-xs text-slate-500">Physical inventory transfers</p>
            </div>
            <button
              onClick={() => onNavigate('transfers')}
              className="text-xs font-medium text-indigo-700 hover:text-indigo-700"
            >
              View Tracking →
            </button>
          </div>

          {recent_transfers.length === 0 ? (
            <div className="p-6 text-center text-slate-500 text-xs">No active transfer movements recorded.</div>
          ) : (
            <div className="space-y-3">
              {recent_transfers.slice(0, 5).map((item) => (
                <div
                  key={item.transfer_id}
                  onClick={() => onNavigate('transfers')}
                  className="p-3 rounded-lg bg-slate-50/60 border border-slate-200 hover:border-indigo-500/40 cursor-pointer transition-all"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-xs text-slate-900">{item.medicine_name}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-600/40">
                      {item.status}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 flex items-center gap-2">
                    <span>{item.source_facility_name}</span>
                    <span>→</span>
                    <span>{item.destination_facility_name}</span>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500">
                    <span>Qty: <strong className="text-slate-700">{item.quantity}</strong></span>
                    <DataBadge type={item.data_classification} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Facility Summary Breakdown */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <h3 className="text-base font-bold text-slate-900 mb-1">Facility Inventory Breakdown</h3>
        <p className="text-xs text-slate-500 mb-4">Operational status across registered health facilities</p>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Facility Name</th>
                <th className="py-3 px-4">Tracked Medicines</th>
                <th className="py-3 px-4">Active Stockouts</th>
                <th className="py-3 px-4">Critical / High Risk</th>
                <th className="py-3 px-4">Pending Recommendations</th>
                <th className="py-3 px-4">In-Transit Transfers</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {facility_summaries.map((fac) => (
                <tr key={fac.facility_id} className="hover:bg-slate-100/40 transition-colors">
                  <td className="py-3 px-4 font-semibold text-slate-900 flex items-center gap-2">
                    <Building2 className="w-3.5 h-3.5 text-blue-700" />
                    <span>{fac.facility_name} ({fac.facility_code})</span>
                  </td>
                  <td className="py-3 px-4 text-slate-700">{fac.tracked_medicines}</td>
                  <td className="py-3 px-4">
                    {fac.active_stockouts > 0 ? (
                      <span className="font-bold text-red-700">{fac.active_stockouts}</span>
                    ) : (
                      <span className="text-slate-500">0</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    {fac.critical_high_risk_count > 0 ? (
                      <span className="font-bold text-amber-700">{fac.critical_high_risk_count}</span>
                    ) : (
                      <span className="text-slate-500">0</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-slate-700">{fac.pending_redistributions}</td>
                  <td className="py-3 px-4 text-slate-700">{fac.in_transit_transfers}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

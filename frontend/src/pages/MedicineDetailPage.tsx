import { medicineLabel } from '../utils/labels';
import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type {
  Facility,
  InventoryBalance,
  InventoryTransaction,
  Medicine,
  RiskAssessment,
  ForecastPoint,
} from '../types/api';
import { DataBadge } from '../components/common/DataBadge';
import { ArrowLeft, CheckCircle2, Sparkles, Building2 } from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';

interface MedicineDetailPageProps {
  medicineId: string;
  onBack: () => void;
}

export const MedicineDetailPage: React.FC<MedicineDetailPageProps> = ({ medicineId, onBack }) => {
  const [medicine, setMedicine] = useState<Medicine | null>(null);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedFacilityId, setSelectedFacilityId] = useState<string>('');
  const [balance, setBalance] = useState<InventoryBalance | null>(null);
  const [transactions, setTransactions] = useState<InventoryTransaction[]>([]);
  const [risk, setRisk] = useState<RiskAssessment | null>(null);
  const [points, setPoints] = useState<ForecastPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadInit = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [medRes, facRes] = await Promise.all([api.getMedicine(medicineId), api.getFacilities()]);
        setMedicine(medRes);
        setFacilities(facRes.data);
        if (facRes.data.length > 0) setSelectedFacilityId((facRes.data.find((f) => f.transfer_eligible) || facRes.data[0]).id);
      } catch (err: any) {
        setError(err?.message || 'Unable to load medicine details.');
      } finally {
        setIsLoading(false);
      }
    };
    loadInit();
  }, [medicineId]);

  useEffect(() => {
    if (!selectedFacilityId || !medicineId) return;

    const loadFacilityData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const balRes = await api.getInventoryBalances(selectedFacilityId, medicineId);
        setBalance(balRes.data[0] || null);

        const txRes = await api.getInventoryTransactions(selectedFacilityId, medicineId);
        setTransactions(txRes.data);

        const riskRes = await api.getRiskAssessments({
          facility_id: selectedFacilityId,
          medicine_id: medicineId,
        });
        setRisk(riskRes.data[0] || null);

        const runsRes = await api.getForecastRuns(selectedFacilityId, medicineId);
        if (runsRes.data.length > 0) {
          const ptsRes = await api.getForecastSummary(runsRes.data[0].id);
          setPoints(ptsRes.points);
        } else {
          setPoints([]);
        }
      } catch (err: any) {
        setError(err?.message || 'Unable to load facility medicine data.');
      } finally {
        setIsLoading(false);
      }
    };

    loadFacilityData();
  }, [selectedFacilityId, medicineId]);

  if (error) {
    return <div className="m-8 rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-800" role="alert">
      <p>{error}</p>
      <button onClick={onBack} className="mt-3 rounded-lg border border-red-200 bg-white px-3 py-2 font-semibold">Back to medicines</button>
    </div>;
  }

  if (isLoading || !medicine) {
    return <div className="p-8 text-slate-500 text-sm">Loading Medicine Detail workspace...</div>;
  }

  // Construct chart data combining historical consumption (Zone 1) & forecast projection (Zone 2)
  const chartData = [
    // Historical consumption points
    ...transactions.slice(0, 7).reverse().map((tx) => ({
      date: tx.transaction_date,
      value: tx.quantity,
      type: 'Historical',
    })),
    // Forecast points
    ...points.map((pt) => ({
      date: pt.target_date,
      forecast: pt.predicted_demand,
      type: 'Forecast',
    })),
  ];

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-700"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h2 className="text-2xl font-bold text-slate-900">{medicineLabel(medicine)}</h2>
            <p className="text-xs text-slate-500">
              KEML 2023 · Level of Use {medicine.level_of_use ?? '—'} · Code: <span className="font-mono text-slate-700">{medicine.code}</span> • Unit: {medicine.unit_of_measure}
            </p>
          </div>
        </div>

        {/* Facility Selector */}
        <div className="flex items-center gap-2">
          <Building2 className="w-4 h-4 text-slate-500" />
          <select
            value={selectedFacilityId}
            onChange={(e) => setSelectedFacilityId(e.target.value)}
            className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-indigo-500"
          >
            {facilities.map((fac) => (
              <option key={fac.id} value={fac.id}>
                {fac.name} ({fac.code})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Two-Zone Operational Architecture */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* ZONE 1: SIMULATED LEDGER (CONFIRMED IN DEMO) */}
        <div className="bg-white border-2 border-emerald-500/30 rounded-2xl p-6 shadow-sm space-y-6">
          <div className="flex items-center justify-between border-b border-slate-200 pb-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-700" />
              <h3 className="text-lg font-bold text-slate-900">Zone 1: Simulated Ledger</h3>
            </div>
            <DataBadge type="CONFIRMED" label="CONFIRMED IN DEMO" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-xs text-slate-500 font-medium">Current Stock Balance</span>
              <p className="text-2xl font-extrabold text-emerald-700 mt-1">
                {balance ? balance.quantity_on_hand : '—'} {balance ? medicine.unit_of_measure + 's' : ''}
              </p>
              <p className="text-[10px] text-slate-500 mt-1">{balance ? 'Computed from synthetic transaction ledger' : 'No synthetic profile for this facility'}</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-xs text-slate-500 font-medium">Safety Stock Policy</span>
              <p className="text-2xl font-extrabold text-slate-900 mt-1">
                {risk ? risk.safety_stock : '—'} {medicine.unit_of_measure}s
              </p>
              <p className="text-[10px] text-slate-500 mt-1">Synthetic safety-stock policy</p>
            </div>
          </div>

          {/* Transaction Ledger History */}
          <div>
            <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-3">
              Recent Inventory Ledger Transactions
            </h4>
            {transactions.length === 0 ? (
              <p className="text-xs text-slate-500">No ledger transactions recorded for this facility.</p>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-slate-200">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-3">Date</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Quantity</th>
                      <th className="py-2.5 px-3">Reference</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {transactions.slice(0, 5).map((tx) => (
                      <tr key={tx.id}>
                        <td className="py-2 px-3 text-slate-700">{tx.transaction_date}</td>
                        <td className="py-2 px-3 font-semibold text-blue-700">{tx.transaction_type}</td>
                        <td className="py-2 px-3 text-slate-900">{tx.quantity}</td>
                        <td className="py-2 px-3 text-slate-500 font-mono text-[11px]">
                          {tx.reference_number || 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* ZONE 2: MODEL PROJECTION (PREDICTED ML DATA) */}
        <div className="bg-white border-2 border-dashed border-indigo-500/40 rounded-2xl p-6 shadow-sm space-y-6">
          <div className="flex items-center justify-between border-b border-slate-200 pb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-700" />
              <h3 className="text-lg font-bold text-slate-900">Zone 2: Model Projection</h3>
            </div>
            <DataBadge type="PREDICTED" label="PREDICTED ML" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 border border-indigo-200/40">
              <span className="text-xs text-slate-500 font-medium">Stockout Risk Level</span>
              <p className="text-2xl font-extrabold text-amber-700 mt-1">
                {risk ? risk.risk_level : 'Not assessed'}
              </p>
              <p className="text-[10px] text-slate-500 mt-1">
                {risk?.days_to_breach !== undefined && risk?.days_to_breach !== null
                  ? `${risk.days_to_breach} days to breach`
                  : 'Sufficient inventory'}
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-indigo-200/40">
              <span className="text-xs text-slate-500 font-medium">Projected Stockout Date</span>
              <p className="text-2xl font-extrabold text-indigo-700 mt-1">
                {risk?.projected_stockout_date || 'No Breach'}
              </p>
              <p className="text-[10px] text-slate-500 mt-1">14-day daily forecast trajectory</p>
            </div>
          </div>

          {/* Time Series Chart with TODAY Divider */}
          <div>
            <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-3">
              Daily Demand Forecast (Historical Consumption vs Forecast Points)
            </h4>
            <div className="h-56 bg-slate-50 rounded-xl p-4 border border-slate-200">
              {chartData.length === 0 ? (
                <div className="h-full flex items-center justify-center text-xs text-slate-500">
                  No daily forecast points generated yet.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} />
                    <YAxis stroke="#94a3b8" fontSize={10} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                    />
                    <ReferenceLine x={dateToString(new Date())} stroke="#ef4444" strokeDasharray="4 4" label="TODAY" />
                    <Line type="monotone" dataKey="value" name="Historical" stroke="#10b981" strokeWidth={2} />
                    <Line
                      type="monotone"
                      dataKey="forecast"
                      name="Forecast (Predicted)"
                      stroke="#818cf8"
                      strokeDasharray="5 5"
                      strokeWidth={2}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

function dateToString(d: Date): string {
  return d.toISOString().split('T')[0];
}

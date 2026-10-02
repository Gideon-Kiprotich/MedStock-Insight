import { medicineLabel } from '../utils/labels';
import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Facility, Medicine, RiskAssessment, RiskExplanation, RiskLevel } from '../types/api';
import { DataBadge } from '../components/common/DataBadge';
import { AlertTriangle, Filter, Building2, Pill } from 'lucide-react';

export const StockoutRiskPage: React.FC = () => {
  const [assessments, setAssessments] = useState<RiskAssessment[]>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [selectedFacility, setSelectedFacility] = useState<string>('');
  const [selectedRiskLevel, setSelectedRiskLevel] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [explanation, setExplanation] = useState<RiskExplanation | null>(null);
  const [explainLoading, setExplainLoading] = useState(false);
  const [explainError, setExplainError] = useState('');

  useEffect(() => {
    Promise.all([api.getFacilities(), api.getMedicines()]).then(([fRes, mRes]) => {
      setFacilities(fRes.data);
      setMedicines(mRes.data);
    });
  }, []);

  useEffect(() => {
    setIsLoading(true);
    api
      .getRiskAssessments({
        facility_id: selectedFacility || undefined,
        risk_level: selectedRiskLevel || undefined,
      })
      .then((res) => {
        setAssessments(res.data);
        setError('');
        setIsLoading(false);
      }).catch((err) => {
        setError(err.message || 'Risk assessments could not be loaded.');
        setIsLoading(false);
      });
  }, [selectedFacility, selectedRiskLevel]);

  const explainRisk = async (id: string) => {
    setExplainLoading(true);
    setExplainError('');
    setExplanation(null);
    try { setExplanation(await api.getRiskExplanation(id)); }
    catch (err: any) { setExplainError(err.message || 'Risk explanation unavailable.'); }
    finally { setExplainLoading(false); }
  };

  const getFacilityName = (id: string) => facilities.find((f) => f.id === id)?.name || id;
  const getMedicineName = (id: string) => (() => { const medicine = medicines.find((m) => m.id === id); return medicine ? medicineLabel(medicine) : id; })();

  const getRiskBadge = (level: RiskLevel) => {
    switch (level) {
      case 'CRITICAL':
        return <span className="px-2.5 py-1 rounded text-xs font-bold bg-red-50 text-red-700 border border-red-500/50">CRITICAL</span>;
      case 'HIGH':
        return <span className="px-2.5 py-1 rounded text-xs font-bold bg-amber-50 text-amber-700 border border-amber-500/50">HIGH</span>;
      case 'MEDIUM':
        return <span className="px-2.5 py-1 rounded text-xs font-bold bg-yellow-50 text-yellow-700 border border-yellow-500/50">MEDIUM</span>;
      case 'LOW':
        return <span className="px-2.5 py-1 rounded text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-500/50">LOW</span>;
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Stockout Risk Assessment Worklist</h2>
          <p className="text-xs text-slate-500 mt-1">
            Deterministic stockout risk analysis based on projected daily inventory trajectories
          </p>
        </div>
        <DataBadge type="PREDICTED" label="STOCKOUT RISK TAXONOMY" />
      </div>

      {/* Filter Toolbar */}
      <div className="flex items-center gap-4 p-4 rounded-xl bg-white border border-slate-200">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
          <Filter className="w-4 h-4 text-blue-700" />
          <span>Filters:</span>
        </div>

        <select
          value={selectedFacility}
          onChange={(e) => setSelectedFacility(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Facilities</option>
          {facilities.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </select>

        <select
          value={selectedRiskLevel}
          onChange={(e) => setSelectedRiskLevel(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Risk Severity Levels</option>
          <option value="CRITICAL">CRITICAL (Breach within 5 days)</option>
          <option value="HIGH">HIGH (Breach in 6–10 days)</option>
          <option value="MEDIUM">MEDIUM (Breach in 11–15 days)</option>
          <option value="LOW">LOW (No breach in horizon)</option>
        </select>
      </div>

      {error && <p role="alert" className="p-3 rounded-lg bg-red-50 text-red-700 text-xs">{error}</p>}
      {isLoading ? (
        <div className="p-8 text-center text-slate-500 text-xs">Analyzing stockout risk trajectories...</div>
      ) : assessments.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-xl border border-slate-200">
          <AlertTriangle className="w-8 h-8 text-slate-500 mx-auto mb-2" />
          <h4 className="text-sm font-semibold text-slate-700">No Risk Records Found</h4>
          <p className="text-xs text-slate-500 mt-1">No stockout risk assessments match the selected filter criteria.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Risk Severity</th>
                <th className="py-3 px-4">Facility</th>
                <th className="py-3 px-4">Medicine</th>
                <th className="py-3 px-4">Current Stock</th>
                <th className="py-3 px-4">Safety Stock</th>
                <th className="py-3 px-4">Days to Breach</th>
                <th className="py-3 px-4">Projected Stockout Date</th>
                <th className="py-3 px-4">Classification</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {assessments.map((item) => (
                <tr key={item.id} className="hover:bg-slate-100/40 transition-colors">
                  <td className="py-3 px-4"><div className="flex flex-col items-start gap-2">{getRiskBadge(item.risk_level)}<button onClick={() => explainRisk(item.id)} className="font-semibold text-indigo-700 hover:underline">Explain Risk</button></div></td>
                  <td className="py-3 px-4 font-semibold text-slate-900">
                    <div className="flex items-center gap-1.5">
                      <Building2 className="w-3.5 h-3.5 text-slate-500" />
                      <span>{getFacilityName(item.facility_id)}</span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-slate-700">
                    <div className="flex items-center gap-1.5">
                      <Pill className="w-3.5 h-3.5 text-blue-700" />
                      <span>{getMedicineName(item.medicine_id)}</span>
                    </div>
                  </td>
                  <td className="py-3 px-4 font-bold text-slate-900">{item.inventory_on_hand}</td>
                  <td className="py-3 px-4 text-slate-500">{item.safety_stock}</td>
                  <td className="py-3 px-4 font-bold text-amber-700">
                    {item.days_to_breach !== undefined && item.days_to_breach !== null ? `${item.days_to_breach} days` : 'Stockout'}
                  </td>
                  <td className="py-3 px-4 text-slate-500">{item.projected_stockout_date || 'N/A'}</td>
                  <td className="py-3 px-4"><DataBadge type="PREDICTED" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {(explainLoading || explainError || explanation) && <div className="fixed inset-0 z-50 bg-slate-950/55 flex items-center justify-center p-4" role="dialog" aria-label="Risk explanation">
        <div className="bg-white rounded-xl shadow-2xl p-6 max-w-xl w-full max-h-[90vh] overflow-y-auto">
          <div className="flex justify-between items-center mb-4"><h3 className="text-lg font-bold text-slate-900">Explain Risk</h3><button aria-label="Close risk explanation" onClick={() => { setExplanation(null); setExplainError(''); setExplainLoading(false); }} className="text-slate-600 text-xl">×</button></div>
          {explainLoading ? <p role="status">Loading explanation…</p> : explainError ? <p role="alert" className="text-red-700">{explainError}</p> : explanation && <>
            <p className="text-sm font-semibold">{getFacilityName(assessments.find((a) => a.id === explanation.assessment_id)?.facility_id || '')} · {getMedicineName(assessments.find((a) => a.id === explanation.assessment_id)?.medicine_id || '')}</p>
            <div className="grid grid-cols-2 gap-3 my-4 text-xs">
              <p>Current stock: <strong>{explanation.current_stock} units</strong></p><p>Safety stock: <strong>{explanation.safety_stock} units</strong></p>
              <p>Forecasted demand: <strong>{explanation.forecasted_demand} units / {explanation.forecast_days} days</strong></p>
              <p>Projected inventory: <strong>{explanation.projected_inventory} units</strong></p>
              <p>Days to breach: <strong>{explanation.days_to_breach ?? 'Beyond horizon'}</strong></p>
              <p>Projected stockout: <strong>{explanation.projected_stockout_date ?? 'Not projected'}</strong></p>
              <p>Risk: <strong>{explanation.risk_level}</strong></p>
              <p>Confirmed incoming: <strong>{explanation.confirmed_incoming_quantity} units</strong></p>
            </div>
            <div className="border-t border-slate-200 pt-3 space-y-2 text-xs text-slate-700">
              <p><strong>Current situation:</strong> {explanation.current_stock} units on hand against {explanation.safety_stock} safety stock.</p>
              <p><strong>Forecast:</strong> {explanation.forecasted_demand} units over {explanation.forecast_days} days.</p>
              <p><strong>Risk:</strong> {explanation.risk_level}; breach {explanation.projected_breach_date ?? 'not projected in horizon'}.</p>
              <p><strong>Available response:</strong> {explanation.feasible_donor_facility_id ? `${getFacilityName(explanation.feasible_donor_facility_id)} has ${explanation.feasible_donor_surplus} usable units` : 'No feasible donor identified for this planning horizon'}.</p>
              <p><strong>Recommendation:</strong> {explanation.recommended_quantity === null ? 'No pending recommendation' : `${explanation.recommended_quantity} units pending review`}.</p>
              <p><strong>Human action:</strong> {explanation.human_action}</p>
              <p className="text-slate-500">{explanation.note}</p>
            </div>
          </>}
        </div>
      </div>}
    </div>
  );
};

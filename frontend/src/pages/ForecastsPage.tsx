import { AggregateEvaluationPanel } from '../components/common/AggregateEvaluationPanel';
import { medicineLabel } from '../utils/labels';
import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type {
  Facility,
  ForecastPoint,
  ForecastRun,
  ForecastExplanation,
  MLModelVersion,
  Medicine,
} from '../types/api';
import { DataBadge } from '../components/common/DataBadge';
import { ForecastEvaluationPanel } from '../components/common/ForecastEvaluationPanel';
import { useAuth } from '../context/AuthContext';
import {
  TrendingUp,
  Cpu,
  Plus,
  Building2,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';

export const ForecastsPage: React.FC = () => {
  const { user } = useAuth();
  const [runs, setRuns] = useState<ForecastRun[]>([]);
  const [models, setModels] = useState<MLModelVersion[]>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [explanation, setExplanation] = useState<ForecastExplanation | null>(null);
  const [explanationError, setExplanationError] = useState('');
  const [selectedRun, setSelectedRun] = useState<{ run: ForecastRun; points: ForecastPoint[] } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Generate modal state
  const [showGenModal, setShowGenModal] = useState(false);
  const [genFacilityId, setGenFacilityId] = useState('');
  const [genMedicineId, setGenMedicineId] = useState('');
  const [genModelCode, setGenModelCode] = useState('MOVING_AVERAGE_7D');
  const [genHorizon, setGenHorizon] = useState(14);
  const [genLookback, setGenLookback] = useState(90);

  const canGenerate =
    user?.role?.code === 'ADMINISTRATOR' || user?.role?.code === 'SUPPLY_CHAIN_MANAGER';

  const loadData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [facRes, medRes, runRes, modelRes] = await Promise.all([
        api.getFacilities(),
        api.getMedicines(),
        api.getForecastRuns(),
        api.getModels(),
      ]);
      setFacilities(facRes.data);
      setMedicines(medRes.data);
      setRuns(runRes.data);
      setModels(modelRes);
      if (runRes.data.length > 0 && !selectedRun) {
        const summary = await api.getForecastSummary(runRes.data[0].id);
        setSelectedRun(summary);
      }
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to load demand forecasts.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!selectedRun) { setExplanation(null); return; }
    let active = true;
    setExplanation(null);
    setExplanationError('');
    api.getForecastExplanation(selectedRun.run.id)
      .then((value) => { if (active) setExplanation(value); })
      .catch((err) => { if (active) setExplanationError(err.message || 'Explanation unavailable.'); });
    return () => { active = false; };
  }, [selectedRun?.run.id]);

  const getFacilityName = (id: string) => facilities.find((f) => f.id === id)?.name || id;
  const getMedicineName = (id: string) => (() => { const medicine = medicines.find((m) => m.id === id); return medicine ? medicineLabel(medicine) : id; })();

  const handleSelectRun = async (runId: string) => {
    try {
      const summary = await api.getForecastSummary(runId);
      setSelectedRun(summary);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to load forecast details.');
    }
  };

  const handleGenerateForecast = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!genFacilityId || !genMedicineId) {
      setErrorMsg('Please select facility and medicine.');
      return;
    }
    setActionLoading(true);
    setErrorMsg(null);
    try {
      const result = await api.generateForecast({
        facility_id: genFacilityId,
        medicine_id: genMedicineId,
        model_code: genModelCode,
        horizon_days: Number(genHorizon),
        lookback_days: Number(genLookback),
      });
      setShowGenModal(false);
      setSelectedRun(result);
      await loadData();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to generate forecast run.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Demand Forecast Runs</h2>
          <p className="text-xs text-slate-500 mt-1">
            Persisted daily demand forecast runs and technical ML model metadata
          </p>
        </div>

        <div className="flex items-center gap-3">
          {canGenerate && (
            <button
              onClick={() => setShowGenModal(true)}
              className="px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold inline-flex items-center gap-2 shadow-lg shadow-indigo-900/30"
            >
              <Plus className="w-4 h-4" />
              <span>Generate Forecast Run</span>
            </button>
          )}

          <button
            onClick={loadData}
            className="p-2 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-100"
            title="Refresh Forecasts"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <DataBadge type="PREDICTED" label="PREDICTED ML DEMAND" />
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-50/60 border border-red-500/50 text-red-700 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-700 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-red-700 font-bold ml-4">×</button>
        </div>
      )}

      {!isLoading && selectedRun && <ForecastEvaluationPanel
        key={selectedRun.run.id}
        facilities={facilities} medicines={medicines}
        initialFacilityId={selectedRun.run.facility_id}
        initialMedicineId={selectedRun.run.medicine_id}
      />}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Forecast Runs List */}
        <div className="lg:col-span-1 space-y-3">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Forecast Runs ({runs.length})
          </h3>

          {isLoading ? (
            <div className="p-8 text-center text-slate-500 text-xs">Loading forecast runs...</div>
          ) : runs.length === 0 ? (
            <div className="p-8 text-center bg-white rounded-xl border border-slate-200 text-slate-500 text-xs">
              No forecast runs generated yet.
            </div>
          ) : (
            <div className="space-y-3 max-h-[700px] overflow-y-auto pr-1">
              {runs.map((r) => {
                const isSelected = selectedRun?.run.id === r.id;
                return (
                  <div
                    key={r.id}
                    onClick={() => handleSelectRun(r.id)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-indigo-50/40 border-indigo-500/80 shadow-lg'
                        : 'bg-white border-slate-200 hover:border-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-xs text-slate-900">{getMedicineName(r.medicine_id)}</span>
                      <span className="text-[10px] font-mono text-indigo-700 bg-indigo-50/80 px-2 py-0.5 rounded border border-indigo-600/40">
                        {r.horizon_days}d Horizon
                      </span>
                    </div>

                    <div className="text-xs text-slate-500 space-y-0.5">
                      <div className="flex items-center gap-1">
                        <Building2 className="w-3.5 h-3.5 text-slate-500" />
                        <span>{getFacilityName(r.facility_id)}</span>
                      </div>
                      <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-200/60 mt-1 flex justify-between">
                        <span>Run: {new Date(r.generated_at).toLocaleString()}</span>
                        <span>{r.status}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Forecast Points & Technical Details */}
        <div className="lg:col-span-2">
          {!selectedRun ? (
            <div className="p-12 text-center bg-white rounded-xl border border-slate-200 text-slate-500 text-xs">
              Select a forecast run to view projected daily demand points and technical ML model parameters.
            </div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
              {/* Run Header */}
              <div className="flex items-center justify-between border-b border-slate-200 pb-4">
                <div>
                  <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-indigo-700" />
                    <span>{getMedicineName(selectedRun.run.medicine_id)}</span>
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Facility: <strong className="text-slate-900">{getFacilityName(selectedRun.run.facility_id)}</strong> • Generated: {new Date(selectedRun.run.generated_at).toLocaleString()}
                  </p>
                </div>
                <DataBadge type="PREDICTED" label="FORECAST POINTS" />
              </div>

              {/* Technical Model Metadata (Secondary Technical Section) */}
              <div className="p-4 rounded-xl bg-slate-50 border border-indigo-200/40 space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-indigo-700 uppercase tracking-wider">
                  <Cpu className="w-4 h-4 text-indigo-700" />
                  <span>Technical ML Model Metadata</span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-slate-700">
                  <div>
                    <span className="text-slate-500 block text-[10px]">Model Version ID</span>
                    <span className="font-mono text-[11px] text-slate-700">{selectedRun.run.model_version_id}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Horizon Days</span>
                    <span className="font-bold text-slate-900">{selectedRun.run.horizon_days} days</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Forecast Start Date</span>
                    <span className="font-semibold text-slate-900">{selectedRun.run.forecast_start_date}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Run Status</span>
                    <span className="font-bold text-emerald-700">{selectedRun.run.status}</span>
                  </div>
                </div>
              </div>

              <section className="p-4 rounded-xl border border-slate-200 bg-slate-50">
                <h4 className="font-semibold text-sm text-slate-900 mb-2">Explain Forecast</h4>
                {explanationError ? <p role="alert" className="text-xs text-red-700">{explanationError}</p>
                  : !explanation ? <p className="text-xs text-slate-500">Loading model features…</p>
                  : <>
                    <p className="text-xs text-slate-700 mb-2">{explanation.model} · trained {explanation.training_start} to {explanation.training_end} on {explanation.training_observations} daily observations.</p>
                    <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">{explanation.features.map((feature) =>
                      <li key={feature.name} className="bg-white border border-slate-200 rounded-lg p-2"><strong className="block text-slate-900">{feature.name.replaceAll('_', ' ')}</strong>{feature.description}</li>)}</ul>
                    <p className="text-[11px] text-slate-500 mt-2">{explanation.note}</p>
                  </>}
              </section>

              {/* Daily Forecast Points Table */}
              <div>
                <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-3">
                  Projected Daily Demand Points ({selectedRun.points.length})
                </h4>

                <div className="overflow-x-auto rounded-xl border border-slate-200">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                      <tr>
                        <th className="py-2.5 px-3">Target Date</th>
                        <th className="py-2.5 px-3">Predicted Daily Demand</th>
                        <th className="py-2.5 px-3">Lower Bound</th>
                        <th className="py-2.5 px-3">Upper Bound</th>
                        <th className="py-2.5 px-3">Classification</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {selectedRun.points.map((pt) => (
                        <tr key={pt.id} className="hover:bg-slate-100/40">
                          <td className="py-2 px-3 font-semibold text-slate-900">{pt.target_date}</td>
                          <td className="py-2 px-3 font-extrabold text-indigo-700">{pt.predicted_demand} units</td>
                          <td className="py-2 px-3 text-slate-500">{pt.lower_bound ?? '—'}</td>
                          <td className="py-2 px-3 text-slate-500">{pt.upper_bound ?? '—'}</td>
                          <td className="py-2 px-3">
                            <DataBadge type="PREDICTED" />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Generate Modal */}
      {showGenModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/55 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Generate Forecast Run</h3>
            <p className="text-xs text-slate-500 mb-4">
              Select facility, medicine, and forecasting model to generate daily predictions.
            </p>

            <form onSubmit={handleGenerateForecast} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Facility</label>
                <select
                  required
                  value={genFacilityId}
                  onChange={(e) => setGenFacilityId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select Facility</option>
                  {facilities.map((f) => (
                    <option key={f.id} value={f.id}>{f.name} ({f.code})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Medicine</label>
                <select
                  required
                  value={genMedicineId}
                  onChange={(e) => setGenMedicineId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select Medicine</option>
                  {medicines.map((m) => (
                    <option key={m.id} value={m.id}>{medicineLabel(m)}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Algorithm Model</label>
                <select
                  value={genModelCode}
                  onChange={(e) => setGenModelCode(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-indigo-500"
                >
                  {models.map((m) => (
                    <option key={m.code} value={m.code}>{m.name} ({m.code})</option>
                  ))}
                  {models.length === 0 && (
                    <>
                      <option value="MOVING_AVERAGE_7D">7-Day Moving Average</option>
                      <option value="RANDOM_FOREST">Random Forest</option>
                    </>
                  )}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Horizon (Days)</label>
                  <input
                    type="number"
                    min={1}
                    max={90}
                    value={genHorizon}
                    onChange={(e) => setGenHorizon(Number(e.target.value))}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Lookback (Days)</label>
                  <input
                    type="number"
                    min={7}
                    max={365}
                    value={genLookback}
                    onChange={(e) => setGenLookback(Number(e.target.value))}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowGenModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50"
                >
                  {actionLoading ? 'Generating...' : 'Run Forecast'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    <AggregateEvaluationPanel />
      </div>
  );
};

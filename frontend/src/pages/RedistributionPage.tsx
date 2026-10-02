import { medicineLabel } from '../utils/labels';
import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type {
  Facility,
  Medicine,
  RedistributionRecommendation,
  RecommendationExplanation,
  RedistributionRecommendationStatus,
} from '../types/api';
import { DataBadge } from '../components/common/DataBadge';
import { useAuth } from '../context/AuthContext';
import {
  ArrowRightLeft,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Building2,
  Pill,
  RefreshCw,
  Plus,
  ShieldAlert,
} from 'lucide-react';

interface RedistributionPageProps {
  onNavigateToTransfer?: (recommendationId: string) => void;
}

export const RedistributionPage: React.FC<RedistributionPageProps> = ({ onNavigateToTransfer }) => {
  const { user } = useAuth();
  const [recommendations, setRecommendations] = useState<RedistributionRecommendation[]>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [recExplanation, setRecExplanation] = useState<RecommendationExplanation | null>(null);
  const [recExplainError, setRecExplainError] = useState('');
  const [recExplainLoading, setRecExplainLoading] = useState(false);
  const [selectedRec, setSelectedRec] = useState<RedistributionRecommendation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [decisionNote, setDecisionNote] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showGenerateModal, setShowGenerateModal] = useState(false);

  // Generate form state
  const [genDestId, setGenDestId] = useState('');
  const [genMedId, setGenMedId] = useState('');
  const [genHorizon, setGenHorizon] = useState(14);

  const canApprove =
    user?.role?.code === 'ADMINISTRATOR' || user?.role?.code === 'SUPPLY_CHAIN_MANAGER';

  const loadData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [facRes, medRes, recRes] = await Promise.all([
        api.getFacilities(),
        api.getMedicines(),
        api.getRecommendations({ status: selectedStatus || undefined }),
      ]);
      setFacilities(facRes.data);
      setMedicines(medRes.data);
      setRecommendations(recRes.data);
      if (selectedRec) {
        const updated = recRes.data.find((r) => r.id === selectedRec.id);
        if (updated) setSelectedRec(updated);
      }
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to load redistribution recommendations.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedStatus]);

  const getFacilityName = (id: string) => facilities.find((f) => f.id === id)?.name || id;
  const getMedicineName = (id: string) => (() => { const medicine = medicines.find((m) => m.id === id); return medicine ? medicineLabel(medicine) : id; })();

  const explainRecommendation = async (id: string) => {
    setRecExplainLoading(true);
    setRecExplainError('');
    setRecExplanation(null);
    try { setRecExplanation(await api.getRecommendationExplanation(id)); }
    catch (err: any) { setRecExplainError(err.message || 'Explanation unavailable.'); }
    finally { setRecExplainLoading(false); }
  };

  const handleApprove = async (id: string) => {
    if (!canApprove) {
      setErrorMsg('Unauthorized: Only Administrators and Supply Chain Managers can approve recommendations.');
      return;
    }
    setActionLoading(true);
    setErrorMsg(null);
    try {
      const updated = await api.approveRecommendation(id, decisionNote);
      setSelectedRec(updated);
      setDecisionNote('');
      await loadData();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to approve recommendation.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (id: string) => {
    if (!canApprove) {
      setErrorMsg('Unauthorized: Only Administrators and Supply Chain Managers can reject recommendations.');
      return;
    }
    setActionLoading(true);
    setErrorMsg(null);
    try {
      const updated = await api.rejectRecommendation(id, decisionNote);
      setSelectedRec(updated);
      setDecisionNote('');
      await loadData();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to reject recommendation.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!genDestId || !genMedId) {
      setErrorMsg('Please select a destination facility and medicine.');
      return;
    }
    setActionLoading(true);
    setErrorMsg(null);
    try {
      await api.generateRecommendation({
        destination_facility_id: genDestId,
        medicine_id: genMedId,
        planning_horizon_days: Number(genHorizon),
      });
      setShowGenerateModal(false);
      setGenDestId('');
      setGenMedId('');
      await loadData();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to generate redistribution recommendation.');
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (status: RedistributionRecommendationStatus) => {
    switch (status) {
      case 'PENDING_REVIEW':
        return <span className="px-2.5 py-1 rounded text-xs font-bold bg-amber-50 text-amber-700 border border-amber-500/50">PENDING REVIEW</span>;
      case 'APPROVED':
        return <span className="px-2.5 py-1 rounded text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-500/50">APPROVED</span>;
      case 'REJECTED':
        return <span className="px-2.5 py-1 rounded text-xs font-bold bg-red-50 text-red-700 border border-red-500/50">REJECTED</span>;
      case 'EXPIRED':
        return <span className="px-2.5 py-1 rounded text-xs font-bold bg-slate-100 text-slate-500 border border-slate-200">EXPIRED</span>;
      case 'CANCELLED':
        return <span className="px-2.5 py-1 rounded text-xs font-bold bg-slate-100 text-slate-500 border border-slate-200">CANCELLED</span>;
    }
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Redistribution Recommendation Queue</h2>
          <p className="text-xs text-slate-500 mt-1">
            Feasible redistribution recommendations requiring human review and approval
          </p>
        </div>

        <div className="flex items-center gap-3">
          {canApprove && (
            <button
              onClick={() => setShowGenerateModal(true)}
              className="px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold inline-flex items-center gap-2 shadow-lg shadow-amber-900/30"
            >
              <Plus className="w-4 h-4" />
              <span>Generate Recommendation</span>
            </button>
          )}

          <button
            onClick={loadData}
            className="p-2 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-100"
            title="Refresh Recommendations"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <DataBadge type="RECOMMENDED" label="FEASIBLE RECOMMENDATION" />
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

      {/* Human Authority Notice */}
      <div className="p-3.5 rounded-xl bg-amber-50/30 border border-amber-500/40 text-amber-700 text-xs flex items-center gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-700 shrink-0" />
        <div>
          <span className="font-semibold text-amber-700 uppercase tracking-wide">Human Authority Required: </span>
          <span>Recommendation requires human review and approval before transfer execution.</span>
        </div>
      </div>

      {/* Status Filter */}
      <div className="flex items-center gap-2 text-xs">
        <span className="text-slate-500 font-semibold">Filter Status:</span>
        {['', 'PENDING_REVIEW', 'APPROVED', 'REJECTED', 'EXPIRED'].map((st) => (
          <button
            key={st}
            onClick={() => setSelectedStatus(st)}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
              selectedStatus === st
                ? 'bg-amber-600 text-white shadow-sm'
                : 'bg-white text-slate-500 border border-slate-200 hover:text-slate-900'
            }`}
          >
            {st ? st.replace('_', ' ') : 'ALL'}
          </button>
        ))}
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recommendation List */}
        <div className="lg:col-span-1 space-y-3">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Recommendations ({recommendations.length})
          </h3>

          {isLoading ? (
            <div className="p-8 text-center text-slate-500 text-xs">Loading queue...</div>
          ) : recommendations.length === 0 ? (
            <div className="p-8 text-center bg-white rounded-xl border border-slate-200 text-slate-500 text-xs">
              No pending redistribution recommendations in queue.
            </div>
          ) : (
            <div className="space-y-3 max-h-[700px] overflow-y-auto pr-1">
              {recommendations.map((rec) => {
                const isSelected = selectedRec?.id === rec.id;
                return (
                  <div
                    key={rec.id}
                    onClick={() => setSelectedRec(rec)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-amber-50/40 border-amber-500/80 shadow-lg'
                        : 'bg-white border-slate-200 hover:border-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      {getStatusBadge(rec.status)}
                      <span className="text-[10px] text-slate-500 font-mono">
                        {new Date(rec.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 font-bold text-slate-900 text-sm mb-1">
                      <Pill className="w-4 h-4 text-blue-700 shrink-0" />
                      <span>{getMedicineName(rec.medicine_id)}</span>
                    </div>

                    <div className="text-xs text-slate-500 space-y-0.5 mt-2">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Source:</span>
                        <span className="font-medium text-slate-700">{getFacilityName(rec.source_facility_id)}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Destination:</span>
                        <span className="font-medium text-slate-700">{getFacilityName(rec.destination_facility_id)}</span>
                      </div>
                      <div className="flex items-center justify-between pt-1 border-t border-slate-200/60 mt-1">
                        <span className="text-slate-500">Rec Quantity:</span>
                        <span className="font-bold text-amber-700">{rec.recommended_quantity} units</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recommendation Detail (Source / Destination Symmetry) */}
        <div className="lg:col-span-2">
          {!selectedRec ? (
            <div className="p-12 text-center bg-white rounded-xl border border-slate-200 text-slate-500 text-xs">
              Select a recommendation from the queue to view full source/destination symmetry, constraint checks, and action controls.
            </div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
              {/* Header */}
              <div className="flex items-center justify-between border-b border-slate-200 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-slate-900">
                      Recommendation #{selectedRec.id.slice(0, 8)}
                    </h3>
                    {getStatusBadge(selectedRec.status)}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Medicine: <strong className="text-slate-900">{getMedicineName(selectedRec.medicine_id)}</strong> • Planning Horizon: {selectedRec.planning_horizon_days} days
                  </p>
                </div>
                <DataBadge type="RECOMMENDED" label="FEASIBLE RECOMMENDATION" />
              </div>

              <div>
                <button onClick={() => explainRecommendation(selectedRec.id)} className="text-xs font-semibold text-indigo-700 hover:underline">Explain Recommendation</button>
                {(recExplainLoading || recExplainError || recExplanation?.recommendation_id === selectedRec.id) && <div className="mt-3 p-4 rounded-xl bg-indigo-50 border border-indigo-100 text-xs text-slate-700 space-y-2">
                  {recExplainLoading ? <p role="status">Loading explanation…</p> : recExplainError ? <p role="alert" className="text-red-700">{recExplainError}</p> : recExplanation && <>
                    <p className="font-semibold">{recExplanation.reason}</p>
                    <p>{recExplanation.source_facility} → {recExplanation.destination_facility} · {recExplanation.medicine}</p>
                    <div className="grid grid-cols-2 gap-2">
                      <p>Source current stock: {recExplanation.source_current_stock}</p><p>Usable surplus: {recExplanation.source_usable_surplus}</p>
                      <p>Destination current stock: {recExplanation.destination_current_stock}</p><p>Projected shortage: {recExplanation.destination_projected_shortage}</p>
                      <p>Source safety stock: {recExplanation.source_safety_stock}</p><p>Projected after transfer: {recExplanation.source_projected_after_transfer}</p>
                      <p>Recommended quantity: {recExplanation.recommended_quantity}</p><p>Status: {recExplanation.status}</p>
                    </div>
                    <p className="text-slate-500">{recExplanation.note}</p>
                  </>}
                </div>}
              </div>

              {/* Source/Destination Symmetry Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Source Facility */}
                <div className="p-5 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                  <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
                    <Building2 className="w-4 h-4 text-emerald-700" />
                    <h4 className="font-bold text-xs text-slate-900 uppercase tracking-wide">
                      Source Facility (Surplus Provider)
                    </h4>
                  </div>
                  <p className="font-semibold text-sm text-emerald-700">{getFacilityName(selectedRec.source_facility_id)}</p>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2 rounded bg-white border border-slate-200">
                      <span className="text-slate-500 block text-[10px]">Current Stock</span>
                      <strong className="text-slate-900">{selectedRec.source_inventory_before}</strong>
                    </div>
                    <div className="p-2 rounded bg-white border border-slate-200">
                      <span className="text-slate-500 block text-[10px]">Safety Stock</span>
                      <strong className="text-slate-900">{selectedRec.source_safety_stock}</strong>
                    </div>
                    <div className="p-2 rounded bg-white border border-slate-200">
                      <span className="text-slate-500 block text-[10px]">Available Surplus</span>
                      <strong className="text-emerald-700">{selectedRec.source_surplus_units}</strong>
                    </div>
                    <div className="p-2 rounded bg-white border border-slate-200">
                      <span className="text-slate-500 block text-[10px]">Projected Position After</span>
                      <strong className="text-slate-900">{selectedRec.source_projected_end_inventory}</strong>
                    </div>
                  </div>
                </div>

                {/* Destination Facility */}
                <div className="p-5 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                  <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
                    <Building2 className="w-4 h-4 text-amber-700" />
                    <h4 className="font-bold text-xs text-slate-900 uppercase tracking-wide">
                      Destination Facility (Shortage Recipient)
                    </h4>
                  </div>
                  <p className="font-semibold text-sm text-amber-700">{getFacilityName(selectedRec.destination_facility_id)}</p>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2 rounded bg-white border border-slate-200">
                      <span className="text-slate-500 block text-[10px]">Current Stock</span>
                      <strong className="text-slate-900">{selectedRec.destination_inventory_before}</strong>
                    </div>
                    <div className="p-2 rounded bg-white border border-slate-200">
                      <span className="text-slate-500 block text-[10px]">Safety Stock</span>
                      <strong className="text-slate-900">{selectedRec.destination_safety_stock}</strong>
                    </div>
                    <div className="p-2 rounded bg-white border border-slate-200">
                      <span className="text-slate-500 block text-[10px]">Projected Shortage</span>
                      <strong className="text-red-700">{selectedRec.destination_shortage_units}</strong>
                    </div>
                    <div className="p-2 rounded bg-white border border-slate-200">
                      <span className="text-slate-500 block text-[10px]">Projected Position After</span>
                      <strong className="text-slate-900">{selectedRec.destination_projected_end_inventory}</strong>
                    </div>
                  </div>
                </div>
              </div>

              {/* Recommended Quantity Highlight */}
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-500/50 flex items-center justify-between">
                <div>
                  <span className="text-xs text-amber-700 font-semibold uppercase tracking-wider">
                    Feasible Recommended Transfer Quantity
                  </span>
                  <p className="text-xs text-slate-500">Calculated based on source surplus & destination shortage bounds</p>
                </div>
                <span className="text-3xl font-extrabold text-amber-700">
                  {selectedRec.recommended_quantity} units
                </span>
              </div>

              {/* Constraint Verification Checklist */}
              {selectedRec.constraint_results && (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                  <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                    Constraint Revalidation Checklist
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                    {Object.entries(selectedRec.constraint_results).map(([k, v]) => (
                      <div key={k} className="flex items-center gap-1.5 text-slate-700">
                        {v ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700 shrink-0" /> : <XCircle className="w-3.5 h-3.5 text-red-700 shrink-0" />}
                        <span className="font-mono text-[11px]">{k}: {String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Decision Note & Action Controls */}
              {selectedRec.status === 'PENDING_REVIEW' && (
                <div className="p-5 rounded-xl bg-slate-50 border border-slate-200 space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Reviewer Note (Optional)
                    </label>
                    <input
                      type="text"
                      value={decisionNote}
                      onChange={(e) => setDecisionNote(e.target.value)}
                      placeholder="Add operational justification or notes for this decision..."
                      className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-amber-500"
                    />
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleApprove(selectedRec.id)}
                      disabled={actionLoading || !canApprove}
                      className="flex-1 py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-semibold text-white text-xs shadow-lg shadow-emerald-900/30 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Approve Recommendation</span>
                    </button>

                    <button
                      onClick={() => handleReject(selectedRec.id)}
                      disabled={actionLoading || !canApprove}
                      className="flex-1 py-2.5 px-4 rounded-lg bg-red-600 hover:bg-red-500 font-semibold text-white text-xs shadow-lg shadow-red-900/30 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                    >
                      <XCircle className="w-4 h-4" />
                      <span>Reject Recommendation</span>
                    </button>
                  </div>
                  {!canApprove && (
                    <p className="text-[11px] text-amber-700 text-center">
                      Note: Approval/Rejection requires Administrator or Supply Chain Manager role.
                    </p>
                  )}
                </div>
              )}

              {selectedRec.status === 'APPROVED' && onNavigateToTransfer && (
                <div className="p-4 rounded-xl bg-emerald-50/40 border border-emerald-500/50 flex items-center justify-between">
                  <div className="text-xs text-emerald-700">
                    <strong className="block text-emerald-700 font-bold">Approved Recommendation</strong>
                    <span>Ready for physical transfer creation and dispatch tracking.</span>
                  </div>
                  <button
                    onClick={() => onNavigateToTransfer(selectedRec.id)}
                    className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold inline-flex items-center gap-1.5"
                  >
                    <ArrowRightLeft className="w-4 h-4" />
                    <span>Proceed to Transfer Tracking →</span>
                  </button>
                </div>
              )}

              {/* Review History */}
              {selectedRec.reviewed_at && (
                <div className="text-xs text-slate-500 pt-3 border-t border-slate-200 flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-slate-500" />
                  <span>Reviewed on {new Date(selectedRec.reviewed_at).toLocaleString()}</span>
                  {selectedRec.review_note && (
                    <span className="italic text-slate-700">• Note: "{selectedRec.review_note}"</span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Generate Modal */}
      {showGenerateModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/55 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Generate Redistribution Recommendation</h3>
            <p className="text-xs text-slate-500 mb-4">
              Select destination shortage facility and medicine to generate a surplus recommendation.
            </p>

            <form onSubmit={handleGenerate} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Destination Facility</label>
                <select
                  required
                  value={genDestId}
                  onChange={(e) => setGenDestId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-amber-500"
                >
                  <option value="">Select Destination Facility</option>
                  {facilities.filter((f) => f.transfer_eligible !== false).map((f) => (
                    <option key={f.id} value={f.id}>{f.name} ({f.code})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Medicine</label>
                <select
                  required
                  value={genMedId}
                  onChange={(e) => setGenMedId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-amber-500"
                >
                  <option value="">Select Medicine</option>
                  {medicines.map((m) => (
                    <option key={m.id} value={m.id}>{medicineLabel(m)}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Planning Horizon (Days)</label>
                <input
                  type="number"
                  min={1}
                  max={90}
                  value={genHorizon}
                  onChange={(e) => setGenHorizon(Number(e.target.value))}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowGenerateModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold disabled:opacity-50"
                >
                  {actionLoading ? 'Generating...' : 'Generate Recommendation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

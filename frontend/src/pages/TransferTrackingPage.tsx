import { medicineLabel } from '../utils/labels';
import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type {
  Facility,
  Medicine,
  RedistributionRecommendation,
  RedistributionTransfer,
  RedistributionTransferStatus,
} from '../types/api';
import { DataBadge } from '../components/common/DataBadge';
import {
  Truck,
  Send,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Plus,
  Building2,
  Pill,
} from 'lucide-react';

interface TransferTrackingPageProps {
  initialRecommendationId?: string;
}

export const TransferTrackingPage: React.FC<TransferTrackingPageProps> = ({ initialRecommendationId }) => {
  const [transfers, setTransfers] = useState<RedistributionTransfer[]>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [approvedRecs, setApprovedRecs] = useState<RedistributionRecommendation[]>([]);
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Creation modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedRecId, setSelectedRecId] = useState(initialRecommendationId || '');
  const [createQty, setCreateQty] = useState<number>(0);

  // Cancel modal state
  const [cancelTransferId, setCancelTransferId] = useState<string | null>(null);
  const [cancelReason, setCancelReason] = useState('');

  const loadData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [facRes, medRes, transRes, recRes] = await Promise.all([
        api.getFacilities(),
        api.getMedicines(),
        api.getTransfers({ status: selectedStatus || undefined }),
        api.getRecommendations({ status: 'APPROVED' }),
      ]);
      setFacilities(facRes.data);
      setMedicines(medRes.data);
      setTransfers(transRes.data);
      setApprovedRecs(recRes.data);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to load physical transfer tracking data.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedStatus]);

  useEffect(() => {
    if (initialRecommendationId && approvedRecs.length > 0) {
      const target = approvedRecs.find((r) => r.id === initialRecommendationId);
      if (target) {
        setSelectedRecId(target.id);
        setCreateQty(target.recommended_quantity);
        setShowCreateModal(true);
      }
    }
  }, [initialRecommendationId, approvedRecs]);

  const getFacilityName = (id: string) => facilities.find((f) => f.id === id)?.name || id;
  const getMedicineName = (id: string) => (() => { const medicine = medicines.find((m) => m.id === id); return medicine ? medicineLabel(medicine) : id; })();

  const handleCreateTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRecId || createQty <= 0) {
      setErrorMsg('Please select an approved recommendation and specify quantity.');
      return;
    }
    setActionLoading(true);
    setErrorMsg(null);
    try {
      await api.createTransfer({
        recommendation_id: selectedRecId,
        quantity: Number(createQty),
      });
      setShowCreateModal(false);
      setSelectedRecId('');
      setCreateQty(0);
      await loadData();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to create transfer.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDispatch = async (id: string) => {
    setActionLoading(true);
    setErrorMsg(null);
    try {
      await api.dispatchTransfer(id);
      await loadData();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to dispatch transfer.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleComplete = async (id: string) => {
    setActionLoading(true);
    setErrorMsg(null);
    try {
      await api.completeTransfer(id);
      await loadData();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to complete transfer.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!cancelTransferId) return;
    setActionLoading(true);
    setErrorMsg(null);
    try {
      await api.cancelTransfer(cancelTransferId, cancelReason);
      setCancelTransferId(null);
      setCancelReason('');
      await loadData();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to cancel transfer.');
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (status: RedistributionTransferStatus) => {
    switch (status) {
      case 'APPROVED':
        return <span className="px-2.5 py-1 rounded text-xs font-bold bg-amber-50 text-amber-700 border border-amber-500/50">APPROVED</span>;
      case 'IN_TRANSIT':
        return <span className="px-2.5 py-1 rounded text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-500/50">IN TRANSIT</span>;
      case 'COMPLETED':
        return <span className="px-2.5 py-1 rounded text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-500/50">COMPLETED</span>;
      case 'CANCELLED':
        return <span className="px-2.5 py-1 rounded text-xs font-bold bg-slate-100 text-slate-500 border border-slate-200">CANCELLED</span>;
    }
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Physical Transfer Tracking Workspace</h2>
          <p className="text-xs text-slate-500 mt-1">
            Synthetic transfer lifecycle: APPROVED → IN TRANSIT → COMPLETED
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold inline-flex items-center gap-2 shadow-lg shadow-indigo-900/30"
          >
            <Plus className="w-4 h-4" />
            <span>Create Transfer</span>
          </button>

          <button
            onClick={loadData}
            className="p-2 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-100"
            title="Refresh Transfers"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <DataBadge type="CONFIRMED" label="DEMO TRANSFERS" />
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

      {/* Filter Toolbar */}
      <div className="flex items-center gap-2 text-xs">
        <span className="text-slate-500 font-semibold">Filter Status:</span>
        {['', 'APPROVED', 'IN_TRANSIT', 'COMPLETED', 'CANCELLED'].map((st) => (
          <button
            key={st}
            onClick={() => setSelectedStatus(st)}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
              selectedStatus === st
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-white text-slate-500 border border-slate-200 hover:text-slate-900'
            }`}
          >
            {st ? st.replace('_', ' ') : 'ALL'}
          </button>
        ))}
      </div>

      {/* Transfers Table */}
      {isLoading ? (
        <div className="p-8 text-center text-slate-500 text-xs">Loading physical transfer tracking...</div>
      ) : transfers.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-xl border border-slate-200">
          <Truck className="w-8 h-8 text-slate-500 mx-auto mb-2" />
          <h4 className="text-sm font-semibold text-slate-700">No Physical Transfers Found</h4>
          <p className="text-xs text-slate-500 mt-1">No transfer movements recorded for the selected status filter.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Medicine</th>
                <th className="py-3 px-4">Source Facility</th>
                <th className="py-3 px-4">Destination Facility</th>
                <th className="py-3 px-4">Quantity</th>
                <th className="py-3 px-4">Timestamps & Actors</th>
                <th className="py-3 px-4 text-right">Operational Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {transfers.map((tx) => (
                <tr key={tx.id} className="hover:bg-slate-100/40 transition-colors">
                  <td className="py-3.5 px-4">{getStatusBadge(tx.status)}</td>

                  <td className="py-3.5 px-4 font-bold text-slate-900">
                    <div className="flex items-center gap-1.5">
                      <Pill className="w-3.5 h-3.5 text-blue-700 shrink-0" />
                      <span>{getMedicineName(tx.medicine_id)}</span>
                    </div>
                  </td>

                  <td className="py-3.5 px-4 text-slate-700">
                    <div className="flex items-center gap-1.5">
                      <Building2 className="w-3.5 h-3.5 text-emerald-700 shrink-0" />
                      <span>{getFacilityName(tx.source_facility_id)}</span>
                    </div>
                  </td>

                  <td className="py-3.5 px-4 text-slate-700">
                    <div className="flex items-center gap-1.5">
                      <Building2 className="w-3.5 h-3.5 text-amber-700 shrink-0" />
                      <span>{getFacilityName(tx.destination_facility_id)}</span>
                    </div>
                  </td>

                  <td className="py-3.5 px-4 font-extrabold text-indigo-700">
                    {tx.quantity} units
                  </td>

                  <td className="py-3.5 px-4 text-[11px] text-slate-500 space-y-0.5">
                    <div>
                      <span className="text-slate-500">Approved:</span> {new Date(tx.approved_at).toLocaleDateString()}
                    </div>
                    {tx.dispatched_at && (
                      <div className="text-indigo-700">
                        <span className="text-slate-500">Dispatched:</span> {new Date(tx.dispatched_at).toLocaleTimeString()}
                      </div>
                    )}
                    {tx.received_at && (
                      <div className="text-emerald-700">
                        <span className="text-slate-500">Received:</span> {new Date(tx.received_at).toLocaleTimeString()}
                      </div>
                    )}
                    {tx.cancelled_at && (
                      <div className="text-red-700">
                        <span className="text-slate-500">Cancelled:</span> {new Date(tx.cancelled_at).toLocaleDateString()}
                      </div>
                    )}
                  </td>

                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {tx.status === 'APPROVED' && (
                        <>
                          <button
                            onClick={() => handleDispatch(tx.id)}
                            disabled={actionLoading}
                            className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold inline-flex items-center gap-1 text-xs shadow-sm disabled:opacity-50"
                          >
                            <Send className="w-3.5 h-3.5" />
                            <span>Dispatch</span>
                          </button>

                          <button
                            onClick={() => setCancelTransferId(tx.id)}
                            disabled={actionLoading}
                            className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-red-50 text-red-700 border border-slate-200 hover:border-red-500/50 font-semibold inline-flex items-center gap-1 text-xs disabled:opacity-50"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            <span>Cancel</span>
                          </button>
                        </>
                      )}

                      {tx.status === 'IN_TRANSIT' && (
                        <button
                          onClick={() => handleComplete(tx.id)}
                          disabled={actionLoading}
                          className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold inline-flex items-center gap-1 text-xs shadow-sm disabled:opacity-50"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Complete Receipt</span>
                        </button>
                      )}

                      {tx.status === 'COMPLETED' && (
                        <span className="text-emerald-700 font-semibold inline-flex items-center gap-1">
                          <CheckCircle2 className="w-4 h-4" /> Received
                        </span>
                      )}

                      {tx.status === 'CANCELLED' && (
                        <span className="text-slate-500 italic">Cancelled</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Transfer Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/55 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Create Physical Transfer</h3>
            <p className="text-xs text-slate-500 mb-4">
              Physical transfers can only be created from human-approved redistribution recommendations.
            </p>

            <form onSubmit={handleCreateTransfer} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Approved Recommendation</label>
                <select
                  required
                  value={selectedRecId}
                  onChange={(e) => {
                    setSelectedRecId(e.target.value);
                    const rec = approvedRecs.find((r) => r.id === e.target.value);
                    if (rec) setCreateQty(rec.recommended_quantity);
                  }}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select Approved Recommendation</option>
                  {approvedRecs.map((r) => (
                    <option key={r.id} value={r.id}>
                      {getMedicineName(r.medicine_id)}: {getFacilityName(r.source_facility_id)} → {getFacilityName(r.destination_facility_id)} ({r.recommended_quantity} units)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Transfer Quantity</label>
                <input
                  type="number"
                  required
                  min={1}
                  value={createQty}
                  onChange={(e) => setCreateQty(Number(e.target.value))}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50"
                >
                  {actionLoading ? 'Creating...' : 'Create Transfer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Cancel Transfer Reason Modal */}
      {cancelTransferId && (
        <div className="fixed inset-0 z-50 bg-slate-950/55 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Cancel Approved Transfer</h3>
            <p className="text-xs text-slate-500 mb-4">
              Only APPROVED transfers can be cancelled before dispatch.
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Cancellation Reason</label>
                <input
                  type="text"
                  required
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder="Provide reason for cancelling this transfer..."
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-red-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setCancelTransferId(null)}
                  className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium"
                >
                  Close
                </button>

                <button
                  type="button"
                  onClick={handleCancel}
                  disabled={actionLoading || !cancelReason.trim()}
                  className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-semibold disabled:opacity-50"
                >
                  {actionLoading ? 'Cancelling...' : 'Confirm Cancellation'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

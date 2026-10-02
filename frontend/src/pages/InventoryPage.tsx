import { medicineLabel } from '../utils/labels';
import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Facility, InventoryBalance, InventoryTransaction, Medicine } from '../types/api';
import { DataBadge } from '../components/common/DataBadge';
import { Package, History, Building2, Pill, Filter, Plus, AlertTriangle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const InventoryPage: React.FC = () => {
  const { user } = useAuth();
  const [balances, setBalances] = useState<InventoryBalance[]>([]);
  const [transactions, setTransactions] = useState<InventoryTransaction[]>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [selectedFacility, setSelectedFacility] = useState<string>('');
  const [selectedMedicine, setSelectedMedicine] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'balances' | 'transactions'>('balances');

  // Transaction Form state
  const [showTxModal, setShowTxModal] = useState(false);
  const [txFacilityId, setTxFacilityId] = useState('');
  const [txMedicineId, setTxMedicineId] = useState('');
  const [txType, setTxType] = useState('RECEIPT');
  const [txQty, setTxQty] = useState<number>(0);
  const [txRef, setTxRef] = useState('');
  const [txNotes, setTxNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const canRecordTx =
    user?.role?.code === 'ADMINISTRATOR' || user?.role?.code === 'INVENTORY_OFFICER';

  const loadData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [facRes, medRes, balRes, txRes] = await Promise.all([
        api.getFacilities(),
        api.getMedicines(),
        api.getInventoryBalances(selectedFacility || undefined, selectedMedicine || undefined, 1, 200),
        api.getInventoryTransactions(selectedFacility || undefined, selectedMedicine || undefined),
      ]);
      setFacilities(facRes.data);
      setMedicines(medRes.data);
      const allBalances = [...balRes.data];
      for (let page = 2; page <= balRes.pagination.total_pages; page += 1) {
        const next = await api.getInventoryBalances(selectedFacility || undefined, selectedMedicine || undefined, page, 200);
        allBalances.push(...next.data);
      }
      setBalances(allBalances);
      setTransactions(txRes.data);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to load inventory balances.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedFacility, selectedMedicine]);

  const getFacilityName = (id: string) => facilities.find((f) => f.id === id)?.name || id;
  const getMedicineName = (id: string) => (() => { const medicine = medicines.find((m) => m.id === id); return medicine ? medicineLabel(medicine) : id; })();
  const getMedicineUnit = (id: string) => medicines.find((m) => m.id === id)?.unit_of_measure || 'units';

  const handleRecordTransaction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!txFacilityId || !txMedicineId || txQty <= 0) {
      setErrorMsg('Please select facility, medicine, and enter valid quantity.');
      return;
    }
    setActionLoading(true);
    setErrorMsg(null);
    try {
      await api.createTransaction({
        facility_id: txFacilityId,
        medicine_id: txMedicineId,
        transaction_type: txType,
        quantity: Number(txQty),
        reference_number: txRef || undefined,
        notes: txNotes || undefined,
      });
      setShowTxModal(false);
      setTxQty(0);
      setTxRef('');
      setTxNotes('');
      await loadData();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to record transaction.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Synthetic Inventory Balances & Ledger</h2>
          <p className="text-xs text-slate-500 mt-1">
            Confirmed within the synthetic demonstration ledger
          </p>
        </div>

        <div className="flex items-center gap-3">
          {canRecordTx && (
            <button
              onClick={() => setShowTxModal(true)}
              className="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold inline-flex items-center gap-2 shadow-lg shadow-emerald-900/30"
            >
              <Plus className="w-4 h-4" />
              <span>Record Inventory Transaction</span>
            </button>
          )}
          <DataBadge type="CONFIRMED" label="DEMO LEDGER" />
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

      {/* Filter & View Switcher Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-white border border-slate-200">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('balances')}
            className={`px-4 py-2 rounded-lg text-xs font-semibold inline-flex items-center gap-2 transition-all ${
              activeTab === 'balances'
                ? 'bg-indigo-600 text-white shadow'
                : 'bg-slate-50 text-slate-500 hover:text-slate-900'
            }`}
          >
            <Package className="w-4 h-4" />
            <span>Stock Balances ({balances.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('transactions')}
            className={`px-4 py-2 rounded-lg text-xs font-semibold inline-flex items-center gap-2 transition-all ${
              activeTab === 'transactions'
                ? 'bg-indigo-600 text-white shadow'
                : 'bg-slate-50 text-slate-500 hover:text-slate-900'
            }`}
          >
            <History className="w-4 h-4" />
            <span>Recent Transactions ({transactions.length})</span>
          </button>
        </div>

        <div className="flex items-center gap-3">
          <Filter className="w-4 h-4 text-slate-500" />
          <select
            value={selectedFacility}
            onChange={(e) => setSelectedFacility(e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-emerald-500"
          >
            <option value="">All Facilities</option>
            {facilities.map((f) => (
              <option key={f.id} value={f.id}>{f.name}</option>
            ))}
          </select>

          <select
            value={selectedMedicine}
            onChange={(e) => setSelectedMedicine(e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-emerald-500"
          >
            <option value="">All Medicines</option>
            {medicines.map((m) => (
              <option key={m.id} value={m.id}>{medicineLabel(m)}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Table */}
      {isLoading ? (
        <div className="p-8 text-center text-slate-500 text-xs">Loading inventory ledger...</div>
      ) : activeTab === 'balances' ? (
        balances.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-xl border border-slate-200 text-slate-500 text-xs">
            No stock balances found matching filter criteria.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Facility</th>
                  <th className="py-3 px-4">Medicine</th>
                  <th className="py-3 px-4">Quantity on Hand</th>
                  <th className="py-3 px-4">Unit of Measure</th>
                  <th className="py-3 px-4">Last Updated</th>
                  <th className="py-3 px-4">Classification</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {balances.map((b) => (
                  <tr key={b.id} className="hover:bg-slate-100/40 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-900">
                      <div className="flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5 text-slate-500" />
                        <span>{getFacilityName(b.facility_id)}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-700">
                      <div className="flex items-center gap-1.5">
                        <Pill className="w-3.5 h-3.5 text-blue-700" />
                        <span>{getMedicineName(b.medicine_id)}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-extrabold text-emerald-700">{b.quantity_on_hand}</td>
                    <td className="py-3 px-4 text-slate-500">{getMedicineUnit(b.medicine_id)}</td>
                    <td className="py-3 px-4 text-slate-500">{b.updated_at ? new Date(b.updated_at).toLocaleString() : '—'}</td>
                    <td className="py-3 px-4">
                      <DataBadge type="CONFIRMED" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : transactions.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-xl border border-slate-200 text-slate-500 text-xs">
          No ledger transactions found matching filter criteria.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Transaction Date</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Facility</th>
                <th className="py-3 px-4">Medicine</th>
                <th className="py-3 px-4">Quantity</th>
                <th className="py-3 px-4">Reference Number</th>
                <th className="py-3 px-4">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {transactions.map((tx) => (
                <tr key={tx.id} className="hover:bg-slate-100/40 transition-colors">
                  <td className="py-3 px-4 text-slate-700">{tx.transaction_date}</td>
                  <td className="py-3 px-4 font-bold text-blue-700">{tx.transaction_type}</td>
                  <td className="py-3 px-4 text-slate-900">{getFacilityName(tx.facility_id)}</td>
                  <td className="py-3 px-4 text-slate-700">{getMedicineName(tx.medicine_id)}</td>
                  <td className="py-3 px-4 font-bold text-slate-900">{tx.quantity}</td>
                  <td className="py-3 px-4 font-mono text-[11px] text-slate-500">{tx.reference_number || '—'}</td>
                  <td className="py-3 px-4 text-slate-500">{tx.notes || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Record Transaction Modal */}
      {showTxModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/55 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Record Inventory Transaction</h3>
            <p className="text-xs text-slate-500 mb-4">
              Add receipt, consumption, or manual ledger adjustment.
            </p>

            <form onSubmit={handleRecordTransaction} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Facility</label>
                <select
                  required
                  value={txFacilityId}
                  onChange={(e) => setTxFacilityId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-emerald-500"
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
                  value={txMedicineId}
                  onChange={(e) => setTxMedicineId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-emerald-500"
                >
                  <option value="">Select Medicine</option>
                  {medicines.map((m) => (
                    <option key={m.id} value={m.id}>{medicineLabel(m)}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Transaction Type</label>
                  <select
                    value={txType}
                    onChange={(e) => setTxType(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="RECEIPT">RECEIPT</option>
                    <option value="CONSUMPTION">CONSUMPTION</option>
                    <option value="ADJUSTMENT_IN">ADJUSTMENT IN</option>
                    <option value="ADJUSTMENT_OUT">ADJUSTMENT OUT</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Quantity</label>
                  <input
                    type="number"
                    required
                    min={1}
                    value={txQty}
                    onChange={(e) => setTxQty(Number(e.target.value))}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Reference Number</label>
                <input
                  type="text"
                  value={txRef}
                  onChange={(e) => setTxRef(e.target.value)}
                  placeholder="e.g. PO-9871, REC-441"
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Notes</label>
                <input
                  type="text"
                  value={txNotes}
                  onChange={(e) => setTxNotes(e.target.value)}
                  placeholder="Operational context or ledger comments..."
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowTxModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold disabled:opacity-50"
                >
                  {actionLoading ? 'Recording...' : 'Record Transaction'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

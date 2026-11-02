import React, { useEffect, useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Activity, AlertTriangle, Building2, CalendarDays, CheckCircle2, Plus, RefreshCw } from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type {
  ConsumptionResponse,
  Facility,
  Medicine,
  SystemSettings,
} from '../types/api';
import { medicineLabel } from '../utils/labels';
import { DataBadge } from '../components/common/DataBadge';

const inputDate = (date: Date) => {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
};

const daysAgo = (days: number) => {
  const value = new Date();
  value.setDate(value.getDate() - days);
  return inputDate(value);
};

const number = (value?: number) => (value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 });

export const ConsumptionLogPage: React.FC = () => {
  const { user } = useAuth();
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [result, setResult] = useState<ConsumptionResponse | null>(null);
  const [facilityId, setFacilityId] = useState('');
  const [medicineId, setMedicineId] = useState('');
  const [search, setSearch] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [sortBy, setSortBy] = useState('transaction_date');
  const [sortOrder, setSortOrder] = useState('desc');
  const [page, setPage] = useState(1);
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  const [showRecord, setShowRecord] = useState(false);
  const [txFacilityId, setTxFacilityId] = useState('');
  const [txMedicineId, setTxMedicineId] = useState('');
  const [txQuantity, setTxQuantity] = useState('');
  const [txDate, setTxDate] = useState(inputDate(new Date()));
  const [txReference, setTxReference] = useState('');
  const [txNotes, setTxNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [recordError, setRecordError] = useState('');

  const isOfficer = user?.role.code === 'INVENTORY_OFFICER';
  const canRecord = isOfficer || user?.role.code === 'ADMINISTRATOR';

  useEffect(() => {
    let active = true;
    Promise.all([
      api.getFacilities(),
      api.getMedicines(),
      api.getSettings().catch(() => null),
    ]).then(([facilityResult, medicineResult, settingResult]) => {
      if (!active) return;
      setFacilities(facilityResult.data);
      setMedicines(medicineResult.data);
      setSettings(settingResult);
      const reportingDays = settingResult?.reporting_default_days ?? 30;
      setStartDate(daysAgo(reportingDays - 1));
      setEndDate(inputDate(new Date()));
      if (user?.role.code === 'INVENTORY_OFFICER' && user.facility_id) {
        setFacilityId(user.facility_id);
        setTxFacilityId(user.facility_id);
      }
      setReady(true);
    }).catch((err: unknown) => {
      if (active) setError(err instanceof Error ? err.message : 'Consumption metadata could not be loaded.');
    });
    return () => { active = false; };
  }, [user?.facility_id, user?.role.code]);

  useEffect(() => {
    if (!ready) return;
    let active = true;
    setLoading(true);
    setError('');
    api.getConsumptionLog({
      facility_id: facilityId || undefined,
      medicine_id: medicineId || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      search: search || undefined,
      sort_by: sortBy,
      sort_order: sortOrder,
      page,
      page_size: 25,
    }).then((value) => {
      if (active) setResult(value);
    }).catch((err: unknown) => {
      if (active) setError(err instanceof Error ? err.message : 'Consumption ledger could not be loaded.');
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [ready, facilityId, medicineId, startDate, endDate, search, sortBy, sortOrder, page, reloadKey]);

  const resetPeriod = () => {
    const reportingDays = settings?.reporting_default_days ?? 30;
    setStartDate(daysAgo(reportingDays - 1));
    setEndDate(inputDate(new Date()));
    setPage(1);
  };

  const openRecord = () => {
    setTxFacilityId(isOfficer ? user?.facility_id || '' : '');
    setTxMedicineId('');
    setTxQuantity('');
    setTxDate(inputDate(new Date()));
    setTxReference('');
    setTxNotes('');
    setRecordError('');
    setShowRecord(true);
  };

  const saveConsumption = async (event: React.FormEvent) => {
    event.preventDefault();
    const quantity = Number(txQuantity);
    if (!txFacilityId || !txMedicineId || !Number.isFinite(quantity) || quantity <= 0) {
      setRecordError('Select a facility and medicine, then enter a positive quantity.');
      return;
    }
    setSaving(true);
    setRecordError('');
    setSuccess('');
    try {
      const medicine = medicines.find((item) => item.id === txMedicineId);
      const facility = facilities.find((item) => item.id === txFacilityId);
      await api.createTransaction({
        facility_id: txFacilityId,
        medicine_id: txMedicineId,
        transaction_type: 'CONSUMPTION',
        quantity,
        transaction_date: txDate,
        reference_number: txReference || undefined,
        notes: txNotes || undefined,
      });
      let balanceNote = '';
      try {
        const balanceResult = await api.getInventoryBalances(txFacilityId, txMedicineId, 1, 1);
        const balance = balanceResult.data[0]?.quantity_on_hand;
        if (balance !== undefined) {
          balanceNote = ` Updated balance: ${number(Number(balance))} ${medicine?.unit_of_measure || 'units'}.`;
        }
      } catch {
        balanceNote = ' Inventory balance could not be refreshed; reload the page to confirm it.';
      }
      setSuccess(
        `Recorded ${number(quantity)} ${medicine?.unit_of_measure || 'units'} of `
        + `${medicine ? medicineLabel(medicine) : 'the selected medicine'} at `
        + `${facility?.name || 'the selected facility'}.${balanceNote}`,
      );
      setShowRecord(false);
      setReloadKey((value) => value + 1);
    } catch (err: unknown) {
      setRecordError(err instanceof Error ? err.message : 'Consumption could not be recorded.');
    } finally {
      setSaving(false);
    }
  };

  const summary = result?.summary;
  const totalPages = result?.pagination.total_pages ?? 0;

  return (
    <div className="p-4 md:p-8 space-y-6 max-w-7xl mx-auto">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Consumption Log</h1>
          <p className="mt-2 text-sm text-slate-500">
            Confirmed dispensing movements derived from the inventory transaction ledger.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <DataBadge type="CONFIRMED" label="CONFIRMED LEDGER" />
          {canRecord && (
            <button
              onClick={openRecord}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
            >
              <Plus className="h-4 w-4" /> Record Consumption
            </button>
          )}
        </div>
      </header>

      {error && (
        <div role="alert" className="flex items-center justify-between rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <span className="flex items-center gap-2"><AlertTriangle className="h-4 w-4" />{error}</span>
          <button onClick={() => setReloadKey((value) => value + 1)} className="font-semibold">Retry</button>
        </div>
      )}
      {success && (
        <div role="status" className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          <CheckCircle2 className="h-4 w-4" /> {success}
        </div>
      )}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5" aria-label="Consumption summary">
        {[
          ['Units consumed', number(summary?.total_quantity)],
          ['Consumption records', number(summary?.transaction_count)],
          ['Distinct medicines', number(summary?.distinct_medicines)],
          ['Average per day', number(summary?.daily_average)],
          ['Days covered', number(summary?.days_covered)],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
            <p className="mt-2 text-2xl font-bold tabular-nums text-slate-900">{value}</p>
          </div>
        ))}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <label className="text-xs font-semibold text-slate-600">
            Facility
            <select
              value={facilityId}
              onChange={(event) => { setFacilityId(event.target.value); setPage(1); }}
              disabled={isOfficer}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-900 disabled:opacity-70"
            >
              {!isOfficer && <option value="">All facilities</option>}
              {facilities
                .filter((facility) => !isOfficer || facility.id === user?.facility_id)
                .map((facility) => <option key={facility.id} value={facility.id}>{facility.name}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Medicine
            <select
              value={medicineId}
              onChange={(event) => { setMedicineId(event.target.value); setPage(1); }}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-900"
            >
              <option value="">All medicines</option>
              {medicines.map((medicine) => (
                <option key={medicine.id} value={medicine.id}>{medicineLabel(medicine)}</option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-600 xl:col-span-2">
            Search
            <input
              value={search}
              onChange={(event) => { setSearch(event.target.value); setPage(1); }}
              placeholder="Facility, medicine, reference, notes, or recording user"
              className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-900"
            />
          </label>
          <label className="text-xs font-semibold text-slate-600">
            From
            <input
              type="date"
              value={startDate}
              onChange={(event) => { setStartDate(event.target.value); setPage(1); }}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-900"
            />
          </label>
          <label className="text-xs font-semibold text-slate-600">
            To
            <input
              type="date"
              value={endDate}
              onChange={(event) => { setEndDate(event.target.value); setPage(1); }}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-900"
            />
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Sort by
            <select
              value={sortBy}
              onChange={(event) => { setSortBy(event.target.value); setPage(1); }}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-900"
            >
              <option value="transaction_date">Transaction date</option>
              <option value="quantity">Quantity</option>
              <option value="facility_name">Facility</option>
              <option value="medicine_name">Medicine</option>
              <option value="created_at">Recorded at</option>
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Direction
            <select
              value={sortOrder}
              onChange={(event) => { setSortOrder(event.target.value); setPage(1); }}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-900"
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </label>
          <div className="flex items-end gap-2 xl:col-span-4">
            <button
              onClick={resetPeriod}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              <CalendarDays className="h-4 w-4" /> Default period
            </button>
            <button
              onClick={() => setReloadKey((value) => value + 1)}
              aria-label="Refresh consumption log"
              className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>
        {settings && (
          <p className="mt-3 text-[11px] text-slate-500">
            Default reporting period: last {settings.reporting_default_days} days. All metrics and the trend derive from the selected confirmed ledger filters.
          </p>
        )}
      </section>

      {!loading && !!result?.trend.length && (
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-bold text-slate-900">Daily consumption trend</h2>
              <p className="text-xs text-slate-500">Recorded CONSUMPTION quantities for the active filters.</p>
            </div>
            <DataBadge type="DERIVED" label="DERIVED FROM LEDGER" />
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={result.trend.map((point) => ({ date: point.date, quantity: point.quantity }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tickFormatter={(value: string) => value.slice(5)} minTickGap={24} />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="quantity" name="Consumption" stroke="#4f46e5" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {loading ? (
        <p role="status" className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
          Loading confirmed consumption records…
        </p>
      ) : !result?.data.length ? (
        <p className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
          No consumption records match the selected filters.
        </p>
      ) : (
        <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 font-semibold text-slate-600">
                <tr>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Facility</th>
                  <th className="px-4 py-3">Medicine</th>
                  <th className="px-4 py-3 text-right">Quantity</th>
                  <th className="px-4 py-3">Reference</th>
                  <th className="px-4 py-3">Notes</th>
                  <th className="px-4 py-3">Recorded by</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {result.data.map((entry) => (
                  <tr key={entry.id} className="hover:bg-slate-50">
                    <td className="whitespace-nowrap px-4 py-3 text-slate-700">{entry.transaction_date}</td>
                    <td className="px-4 py-3 font-medium text-slate-900">
                      <span className="inline-flex items-center gap-1.5"><Building2 className="h-3.5 w-3.5 text-slate-400" />{entry.facility_name}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-700">
                      <span className="inline-flex items-center gap-1.5"><Activity className="h-3.5 w-3.5 text-indigo-500" />{entry.medicine_name}</span>
                    </td>
                    <td className="px-4 py-3 text-right font-bold tabular-nums text-slate-900">
                      {number(entry.quantity)} <span className="font-normal text-slate-500">{entry.unit_of_measure}</span>
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-slate-500">{entry.reference_number || '—'}</td>
                    <td className="max-w-xs px-4 py-3 text-slate-500">{entry.notes || '—'}</td>
                    <td className="px-4 py-3 text-slate-700">{entry.recorded_by_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 text-xs text-slate-500">
            <span>
              Page {result.pagination.page} of {Math.max(totalPages, 1)} · {result.pagination.total} records
            </span>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
                className="rounded-lg border border-slate-200 px-3 py-1.5 font-semibold disabled:opacity-40"
              >
                Previous
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((value) => value + 1)}
                className="rounded-lg border border-slate-200 px-3 py-1.5 font-semibold disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </section>
      )}

      {showRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-sm">
          <form
            aria-label="Record consumption form"
            onSubmit={saveConsumption}
            className="w-full max-w-md space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl"
          >
            <div>
              <h2 className="text-lg font-bold text-slate-900">Record Consumption</h2>
              <p className="mt-1 text-xs text-slate-500">
                This creates a confirmed CONSUMPTION movement in the inventory ledger.
              </p>
            </div>
            {recordError && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-xs text-rose-800">{recordError}</p>}
            <label className="block text-xs font-semibold text-slate-600">
              Facility
              <select
                required
                value={txFacilityId}
                onChange={(event) => setTxFacilityId(event.target.value)}
                disabled={isOfficer}
                className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs disabled:opacity-70"
              >
                <option value="">Select facility</option>
                {facilities
                  .filter((facility) => !isOfficer || facility.id === user?.facility_id)
                  .map((facility) => <option key={facility.id} value={facility.id}>{facility.name}</option>)}
              </select>
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Medicine
              <select
                required
                value={txMedicineId}
                onChange={(event) => setTxMedicineId(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs"
              >
                <option value="">Select medicine</option>
                {medicines.map((medicine) => (
                  <option key={medicine.id} value={medicine.id}>{medicineLabel(medicine)}</option>
                ))}
              </select>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block text-xs font-semibold text-slate-600">
                Quantity
                <input
                  required
                  min="0.01"
                  step="0.01"
                  type="number"
                  value={txQuantity}
                  onChange={(event) => setTxQuantity(event.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs"
                />
              </label>
              <label className="block text-xs font-semibold text-slate-600">
                Date
                <input
                  required
                  type="date"
                  value={txDate}
                  onChange={(event) => setTxDate(event.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs"
                />
              </label>
            </div>
            <label className="block text-xs font-semibold text-slate-600">
              Reference
              <input
                value={txReference}
                onChange={(event) => setTxReference(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs"
                placeholder="Dispensing sheet or requisition number"
              />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Notes
              <textarea
                value={txNotes}
                onChange={(event) => setTxNotes(event.target.value)}
                rows={2}
                className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs"
              />
            </label>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowRecord(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-700"
              >
                Cancel
              </button>
              <button
                disabled={saving}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
              >
                {saving ? 'Recording…' : 'Record Consumption'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

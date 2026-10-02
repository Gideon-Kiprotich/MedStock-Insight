import { useEffect, useState } from 'react';
import { api } from '../../api/client';
import type { Facility, ForecastEvaluation, Medicine } from '../../types/api';
import { medicineLabel } from '../../utils/labels';

export function ForecastEvaluationPanel({ facilities, medicines, initialFacilityId = '', initialMedicineId = '' }: {
  facilities: Facility[]; medicines: Medicine[]; initialFacilityId?: string; initialMedicineId?: string;
}) {
  const [facilityId, setFacilityId] = useState(initialFacilityId);
  const [medicineId, setMedicineId] = useState(initialMedicineId);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [result, setResult] = useState<ForecastEvaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    api.getForecastEvaluation({
      facility_id: facilityId || undefined, medicine_id: medicineId || undefined,
      start_date: startDate || undefined, end_date: endDate || undefined,
    }).then((data) => { if (active) setResult(data); })
      .catch((err) => { if (active) setError(err.message || 'Evaluation could not be loaded.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [facilityId, medicineId, startDate, endDate]);
  const format = (value: number | null) => value === null ? '—' : value.toFixed(2);
  return (
    <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm" aria-label="Forecast Evaluation">
      <div className="flex flex-wrap justify-between gap-3 mb-4">
        <div>
          <h3 className="text-base font-bold text-slate-900">Forecast Evaluation</h3>
          <p className="text-xs text-slate-500">Measured temporal holdout results on recorded consumption. These are not guarantees of future accuracy.</p>
        </div>
        <span className="text-xs text-slate-500">{loading ? 'Evaluating…' : `${result?.evaluated_series ?? 0} evaluated series`}</span>
      </div>
      <div className="flex flex-wrap gap-2 mb-4">
        <select aria-label="Evaluation facility" value={facilityId} onChange={(e) => setFacilityId(e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs">
          <option value="">All facilities</option>{facilities.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
        </select>
        <select aria-label="Evaluation medicine" value={medicineId} onChange={(e) => setMedicineId(e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs">
          <option value="">All medicines</option>{medicines.map((m) => <option key={m.id} value={m.id}>{medicineLabel(m)}</option>)}
        </select>
        <label className="text-xs text-slate-600">From <input aria-label="Evaluation start date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="rounded-lg border border-slate-200 px-2 py-1.5" /></label>
        <label className="text-xs text-slate-600">To <input aria-label="Evaluation end date" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="rounded-lg border border-slate-200 px-2 py-1.5" /></label>
      </div>
      {loading ? <p role="status" className="text-xs text-slate-500">Evaluating models…</p>
        : error ? <p role="alert" className="text-xs text-red-700">{error}</p>
        : !result?.results.length ? <p className="text-xs text-slate-500">No consumption series in this date range.</p>
        : <div className="overflow-x-auto"><table className="w-full text-xs text-left">
          <thead className="bg-slate-50 text-slate-600"><tr>
            <th className="p-2">Facility / Medicine</th><th className="p-2">Model</th><th className="p-2">Holdout</th>
            <th className="p-2 text-right">MAE</th><th className="p-2 text-right">RMSE</th>
            <th className="p-2 text-right">WAPE</th><th className="p-2 text-right">Observations</th>
          </tr></thead>
          <tbody className="divide-y divide-slate-100">{result.results.map((row) => <tr key={`${row.facility_id}-${row.medicine_id}-${row.model}`} className="hover:bg-slate-50">
            <td className="p-2 font-medium">{facilities.find((f) => f.id === row.facility_id)?.name || row.facility_id}<br /><span className="font-normal text-slate-500">{(() => { const med = medicines.find((m) => m.id === row.medicine_id); return med ? medicineLabel(med) : row.medicine_id; })()}</span></td>
            <td className="p-2">{row.model === 'MOVING_AVERAGE_7D' ? 'Moving Average (7d)' : 'Random Forest'}</td>
            <td className="p-2">{row.holdout_start ? `${row.holdout_start} – ${row.holdout_end}` : 'Insufficient data'}</td>
            <td className="p-2 text-right tabular-nums">{format(row.mae)}</td><td className="p-2 text-right tabular-nums">{format(row.rmse)}</td>
            <td className="p-2 text-right tabular-nums">{row.wape === null ? '—' : `${format(row.wape)}%`}</td>
            <td className="p-2 text-right tabular-nums">{row.observations}</td>
          </tr>)}</tbody>
        </table></div>}
      {result && <p className="mt-3 text-[11px] text-slate-500">{result.methodology} {result.data_note}</p>}
    </section>
  );
}

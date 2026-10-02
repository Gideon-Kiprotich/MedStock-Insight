import { useEffect, useState } from 'react';
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { api } from '../api/client';
import type { Facility, Medicine } from '../types/api';
import type { ScenarioParameters, ScenarioResult } from '../types/analytics';
import { medicineLabel } from '../utils/labels';
import { DataBadge } from '../components/common/DataBadge';

const format = (value: unknown) => value == null ? 'None within horizon' : typeof value === 'number' ? value.toLocaleString(undefined, {maximumFractionDigits: 2}) : String(value);
const riskClass = (risk: string) => ({CRITICAL:'bg-rose-100 text-rose-800',HIGH:'bg-orange-100 text-orange-800',MEDIUM:'bg-amber-100 text-amber-800',LOW:'bg-emerald-100 text-emerald-800'}[risk] || '');

export function ScenarioAnalysisPage() {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [params, setParams] = useState<ScenarioParameters>({facility_id:'',medicine_id:'',demand_adjustment_pct:0,inventory_adjustment_pct:0,lead_time_adjustment_days:0,horizon_days:14});
  useEffect(() => {
    let active = true;
    Promise.all([api.getFacilities(), api.getMedicines()]).then(([f,m]) => {
      if (!active) return;
      setFacilities(f.data); setMedicines(m.data);
    }).catch(e => {if(active) setError(e.message);}).finally(() => {if(active) setLoading(false);});
    return () => {active=false;};
  }, []);
  const update = (field: keyof ScenarioParameters, value: string | number) => {
    setParams(p => ({...p,[field]:value})); setResult(null); setError('');
  };
  const run = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError(''); setResult(null);
    try {setResult(await api.simulateScenario(params));} catch(e) {setError(e instanceof Error ? e.message : 'Simulation failed');} finally {setBusy(false);}
  };
  const rows = result ? [
    ['Daily demand','daily_demand','PREDICTED'],['Current stock','current_stock','DERIVED'],
    ['Days to breach','days_to_breach','PREDICTED'],['Projected shortage','projected_shortage','PREDICTED'],
    ['Risk level','risk_level','PREDICTED'],['Feasible donor','feasible_donor','RECOMMENDED'],
    ['Recommended quantity','recommended_quantity','RECOMMENDED'],['Incoming within horizon','incoming_quantity','DERIVED'],
  ] as const : [];
  const chart = result?.baseline.trajectory.map((p,i) => ({date:p.date,baseline:p.projected_stock,scenario:result.scenario.trajectory[i].projected_stock}));
  return <div className="p-4 md:p-8 space-y-6 max-w-7xl mx-auto">
    <header><h1 className="text-2xl font-bold text-slate-900">Scenario Analysis</h1><p className="text-sm text-slate-500 mt-2">Compare controlled assumptions against a saved forecast and current ledger snapshot.</p></header>
    <div className="rounded-lg border border-amber-300 bg-amber-50 text-amber-900 p-4 text-sm font-semibold">SIMULATION — NOT LIVE INVENTORY</div>
    {loading ? <p role="status">Loading scenario controls…</p> : <form onSubmit={run} className="bg-white border rounded-xl p-5 space-y-5 shadow-sm border-slate-200">
      <fieldset disabled={busy} className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 disabled:opacity-60">
        <label className="text-sm font-medium">Facility<select aria-label="Facility" required value={params.facility_id} onChange={e=>update('facility_id',e.target.value)} className="mt-2 w-full border rounded-lg p-2.5 border-slate-200"><option value="">Select facility</option>{facilities.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select></label>
        <label className="text-sm font-medium">Medicine<select aria-label="Medicine" required value={params.medicine_id} onChange={e=>update('medicine_id',e.target.value)} className="mt-2 w-full border rounded-lg p-2.5 border-slate-200"><option value="">Select medicine</option>{medicines.map(m=><option key={m.id} value={m.id}>{medicineLabel(m)}</option>)}</select></label>
        <label className="text-sm font-medium">Demand adjustment<select aria-label="Demand adjustment" value={params.demand_adjustment_pct} onChange={e=>update('demand_adjustment_pct',Number(e.target.value))} className="mt-2 w-full border rounded-lg p-2.5 border-slate-200">{[-20,-10,0,10,20,30].map(n=><option key={n} value={n}>{n>0?'+':''}{n}%</option>)}</select></label>
        <label className="text-sm font-medium">Inventory adjustment<select aria-label="Inventory adjustment" value={params.inventory_adjustment_pct} onChange={e=>update('inventory_adjustment_pct',Number(e.target.value))} className="mt-2 w-full border rounded-lg p-2.5 border-slate-200">{[0,-10,-20,-30].map(n=><option key={n} value={n}>{n}%</option>)}</select></label>
        <label className="text-sm font-medium">Delivery delay<select aria-label="Delivery delay" value={params.lead_time_adjustment_days} onChange={e=>update('lead_time_adjustment_days',Number(e.target.value))} className="mt-2 w-full border rounded-lg p-2.5 border-slate-200">{[0,3,7].map(n=><option key={n} value={n}>+{n} days</option>)}</select></label>
      </fieldset>
      <p className="text-xs text-slate-500">14-day horizon. Adjustments affect the selected destination only; donor stocks remain at baseline. Delivery delay moves confirmed purchase-order arrivals. Generate a current forecast in Demand Forecasts if one is unavailable.</p>
      <button disabled={busy || !params.facility_id || !params.medicine_id} className="bg-indigo-600 text-white rounded-lg px-5 py-2.5 font-semibold disabled:opacity-50">{busy?'Calculating…':'Apply scenario'}</button>
    </form>}
    {busy && <p role="status">Calculating baseline and scenario…</p>}
    {error && <div role="alert" className="border border-rose-200 bg-rose-50 text-rose-800 p-4 rounded-lg">{error}</div>}
    {!result && !busy && !loading && <p className="text-sm text-slate-500">Select a facility, medicine and assumptions to produce an analytical comparison.</p>}
    {result && <>
      <section className="bg-white border rounded-xl overflow-hidden border-slate-200"><div className="p-5 border-b border-slate-200"><h2 className="font-bold">Baseline versus scenario</h2><p className="text-sm text-slate-500 mt-1">{result.context.destination.facility_name} · {result.context.medicine_name}</p></div>
        <div className="overflow-x-auto"><table className="w-full text-sm"><thead className="bg-slate-50 text-slate-600"><tr>{['Metric','Classification','Baseline','Scenario','Change'].map((h,i)=><th key={h} className={i>=2?"text-right p-4":"text-left p-4"}>{h}</th>)}</tr></thead><tbody>{rows.map(([label,key,classification])=><tr key={key} className="border-t hover:bg-slate-50 border-slate-200"><th className="text-left p-4 font-medium">{label}</th><td className="p-4"><DataBadge type={classification}/></td>{[result.baseline[key],result.scenario[key]].map((v,i)=><td key={i} className="p-4 tabular-nums text-right">{key==='risk_level'?<span className={`rounded-full px-2.5 py-1 font-semibold text-xs ${riskClass(String(v))}`}>{String(v)}</span>:format(v)}</td>)}<td className="p-4 tabular-nums text-right">{result.differences[key] == null ? (key==='days_to_breach'?'Compare horizon breach above':'—') : format(result.differences[key])}</td></tr>)}</tbody></table></div>
      </section>
      <section className="bg-white border rounded-xl p-5 border-slate-200"><h2 className="font-bold mb-4">Projected inventory trajectory <DataBadge type="PREDICTED"/></h2><div className="h-64"><ResponsiveContainer width="100%" height="100%"><LineChart data={chart}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date" tickFormatter={d=>d.slice(5)}/><YAxis/><Tooltip/><Legend/><Line dataKey="baseline" stroke="#64748b" dot={false}/><Line dataKey="scenario" stroke="#4f46e5" dot={false}/></LineChart></ResponsiveContainer></div><p className="text-xs text-slate-500">Negative projected stock indicates unmet consumption; it is not a ledger balance.</p></section>
      <section className="bg-white border rounded-xl p-5 space-y-3 border-slate-200"><h2 className="font-bold">Why the outcome changed</h2>{result.explanations.map((text,i)=><p key={i} className="text-sm text-slate-600">{text}</p>)}{result.context.excluded_donors.length>0 && <details className="text-sm"><summary>Donors excluded for missing or stale forecasts ({result.context.excluded_donors.length})</summary>{result.context.excluded_donors.map(d=><p key={d.facility}>{d.facility}: {d.reason}</p>)}</details>}</section>
      <section className="bg-slate-100 rounded-xl p-5 text-xs space-y-2 break-all"><h2 className="font-bold text-sm">Reproducibility snapshot</h2><p>Scenario: {result.id} · Created: {new Date(result.created_at).toLocaleString()}</p><p>Base date: {result.context.assessment_date} · Forecast run: {result.context.destination.forecast_run_id}</p><p>Input fingerprint: {result.fingerprint}</p><p>Demand {result.parameters.demand_adjustment_pct}% · Inventory {result.parameters.inventory_adjustment_pct}% · Delivery +{result.parameters.lead_time_adjustment_days} days</p><button className="text-indigo-700 font-semibold" onClick={async()=>{setBusy(true);try {setResult(await api.replayScenario(result.id));setError('');}catch(e){setError(e instanceof Error?e.message:'Replay failed');}finally{setBusy(false);}}} disabled={busy}>Replay saved inputs</button></section>
    </>}
  </div>;
}

import { useEffect, useState } from 'react';
import { api } from '../../api/client';
import type { AggregateEvaluation, ModelMetrics } from '../../types/analytics';
import { DataBadge } from './DataBadge';

const number = (n: number | null) => n == null ? '—' : n.toFixed(2);
function MetricsTable({rows}: {rows: ({name?: string} & ModelMetrics)[]}) {
  return <div className="overflow-auto max-h-96"><table className="w-full text-sm"><thead className="bg-slate-50 sticky top-0"><tr>{['Context','Model','Series','Observations','MAE','RMSE','WAPE %'].map((h,i)=><th className={i>=2?'p-3 text-right':'p-3 text-left'} key={h}>{h}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={i} className="border-t hover:bg-slate-50 border-slate-200"><td className="p-3">{r.name || 'Overall'}</td><td className="p-3">{r.model==='RANDOM_FOREST'?'Random Forest':'Moving Average (7 days)'}</td><td className="p-3 tabular-nums text-right">{r.evaluated_series}</td><td className="p-3 tabular-nums text-right">{r.observations}</td><td className="p-3 tabular-nums text-right">{number(r.mae)}</td><td className="p-3 tabular-nums text-right">{number(r.rmse)}</td><td className="p-3 tabular-nums text-right">{number(r.wape)}</td></tr>)}</tbody></table></div>;
}
export function AggregateEvaluationPanel() {
  const [evaluation,setEvaluation]=useState<AggregateEvaluation | null>(null);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [group,setGroup]=useState('overall');
  useEffect(()=>{let active=true;api.getAggregateEvaluation().then(r=>{if(active)setEvaluation(r);}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[]);
  const run=async()=>{setBusy(true);setError('');try{setEvaluation(await api.runAggregateEvaluation());}catch(e){setError(e instanceof Error?e.message:'Evaluation failed');}finally{setBusy(false);}};
  const groups=evaluation?(group==='facility'?evaluation.by_facility:group==='medicine'?evaluation.by_medicine:null):null;
  const rows=groups?groups.flatMap(g=>g.metrics.map(m=>({...m,name:g.name}))):evaluation?.overall || [];
  return <section className="bg-white rounded-xl border shadow-sm overflow-hidden border-slate-200"><div className="p-5 border-b space-y-3 border-slate-200"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-bold text-lg">Aggregate Forecast Evaluation <DataBadge type="DERIVED"/></h2><button className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50" disabled={busy || loading} onClick={run}>{busy?'Evaluating all series…':'Evaluate full network'}</button></div><p className="text-sm text-slate-500">Two-year window; final 14-day temporal holdout. Evaluation may take several minutes. This experiment does not create forecast runs.</p><label className="text-sm">Group results <select aria-label="Evaluation grouping" value={group} onChange={e=>setGroup(e.target.value)} className="ml-2 border rounded-lg p-2 border-slate-200"><option value="overall">Overall</option><option value="facility">By facility</option><option value="medicine">By medicine</option></select></label></div>
    {loading && <p role="status" className="p-5">Loading evaluation…</p>}{busy && <p role="status" className="p-5">Fitting models on historical training data and measuring the holdout…</p>}{error && <p role="alert" className="p-5 text-rose-700">{error}</p>}
    {evaluation?<><MetricsTable rows={rows}/><div className="p-5 text-xs text-slate-500 space-y-2"><p>{evaluation.parameters.start_date} – {evaluation.parameters.end_date} · {evaluation.series_count} recorded series · Saved {new Date(evaluation.created_at).toLocaleString()}</p><p>{evaluation.methodology}</p><p>{evaluation.data_note}</p><details><summary>Experiment metadata</summary><p className="break-all">ID {evaluation.id} · Fingerprint {evaluation.fingerprint}</p></details></div></>:!loading&&<p className="p-5 text-sm text-slate-500">No aggregate evaluation saved. Run the network experiment to measure eligible series. Insufficient histories are excluded from metrics.</p>}
  </section>;
}

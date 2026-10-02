import { useEffect, useState } from 'react';
import { BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { api } from '../api/client';
import type { DecisionAnalytics } from '../types/analytics';
import { DataBadge } from '../components/common/DataBadge';
import { AggregateEvaluationPanel } from '../components/common/AggregateEvaluationPanel';

export function DecisionAnalyticsPage() {
  const [data,setData]=useState<DecisionAnalytics | null>(null);
  const [error,setError]=useState('');
  const [filter,setFilter]=useState('');
  useEffect(()=>{let active=true;api.getDecisionAnalytics().then(r=>{if(active)setData(r);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[]);
  const sections=data?[
    {name:'Inventory',type:'DERIVED' as const,counts:{'Active stockouts':data.inventory.active_stockouts,'Low stock':data.inventory.low_stock_items,'Usable surplus':data.inventory.surplus_items,'Forecast positions':data.inventory.position_coverage}},
    {name:'Forecasting',type:'PREDICTED' as const,counts:{'Forecast runs':data.forecasting.runs,'Evaluated series':data.forecasting.evaluation?.overall[0]?.evaluated_series || 0}},
    {name:'Risk',type:'PREDICTED' as const,counts:data.risk},
    {name:'Redistribution',type:'RECOMMENDED' as const,counts:data.redistribution},
    {name:'Transfers',type:'CONFIRMED' as const,counts:Object.fromEntries(['APPROVED','IN_TRANSIT','COMPLETED','CANCELLED'].map(k=>[k,data.transfers[k]||0]))},
  ]:[];
  return <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6"><header><h1 className="text-2xl font-bold">Decision Analytics</h1><p className="text-sm text-slate-500 mt-2">Operational summaries from the demonstration backend.</p></header>
    {error&&<p role="alert" className="bg-rose-50 border rounded-lg text-rose-700 p-4 border-slate-200">{error}</p>}{!data&&!error&&<p role="status">Loading operational analytics…</p>}
    {data&&<><div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">{sections.map(s=><section key={s.name} className="bg-white border rounded-xl p-5 border-slate-200"><h2 className="font-bold mb-4">{s.name} <DataBadge type={s.type}/></h2><dl className="space-y-2">{Object.entries(s.counts).map(([key,value])=><div key={key} className="flex justify-between gap-4 text-sm"><dt className="text-slate-500 capitalize">{key.replaceAll('_',' ').toLowerCase()}</dt><dd className="font-bold tabular-nums">{value}</dd></div>)}</dl></section>)}</div><p className="text-xs text-slate-500">{data.note}</p>
    <div className="grid md:grid-cols-2 gap-5"><section className="bg-white rounded-xl border p-5 border-slate-200"><h2 className="font-bold mb-3">Latest risk distribution <DataBadge type="PREDICTED"/></h2><div className="h-56"><ResponsiveContainer width="100%" height="100%"><BarChart data={['CRITICAL','HIGH','MEDIUM','LOW'].map(level=>({level,count:data.risk[level]||0}))}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="level"/><YAxis allowDecimals={false}/><Tooltip/><Bar dataKey="count" fill="#4f46e5"/></BarChart></ResponsiveContainer></div></section><section className="bg-white rounded-xl border p-5 border-slate-200"><h2 className="font-bold mb-3">Recorded workflow activity <DataBadge type="DERIVED"/></h2>{data.activity.length?<div className="h-56"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.activity}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date"/><YAxis allowDecimals={false}/><Tooltip/><Legend/><Bar dataKey="recommendations" fill="#4f46e5"/><Bar dataKey="transfers" fill="#64748b"/></BarChart></ResponsiveContainer></div>:<p className="text-sm text-slate-500">No recorded workflow activity.</p>}</section></div>
    <section className="bg-white border rounded-xl overflow-hidden border-slate-200"><div className="p-5 flex flex-wrap gap-3 justify-between"><h2 className="font-bold">Current stock <DataBadge type="CONFIRMED"/></h2><input aria-label="Filter current stock" value={filter} onChange={e=>setFilter(e.target.value)} placeholder="Filter facility or medicine" className="border rounded-lg p-2 text-sm border-slate-200"/></div><div className="overflow-auto max-h-80"><table className="w-full text-sm"><thead className="bg-slate-50 sticky top-0"><tr>{['Facility','Medicine','Stock','Unit'].map((h,i)=><th key={h} className={i===2?"p-3 text-right":"p-3 text-left"}>{h}</th>)}</tr></thead><tbody>{data.inventory.stock.filter(r=>`${r.facility} ${r.medicine}`.toLowerCase().includes(filter.toLowerCase())).map(r=><tr key={`${r.facility_id}-${r.medicine_id}`} className="border-t hover:bg-slate-50 border-slate-200"><td className="p-3">{r.facility}</td><td className="p-3">{r.medicine}</td><td className="p-3 tabular-nums text-right">{Number(r.quantity).toLocaleString()}</td><td className="p-3">{r.unit}</td></tr>)}</tbody></table></div></section></>}
    <AggregateEvaluationPanel/>
  </div>;
}

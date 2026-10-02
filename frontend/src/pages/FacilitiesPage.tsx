import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Facility } from '../types/api';
import { DataBadge } from '../components/common/DataBadge';
import { Building2, MapPin, CheckCircle2, Search } from 'lucide-react';

export const FacilitiesPage: React.FC = () => {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    api.getFacilities()
      .then((res) => setFacilities(res.data))
      .catch((err) => setError(err?.message || 'Unable to load facilities.'))
      .finally(() => setIsLoading(false));
  }, [reloadKey]);

  const filtered = facilities.filter(
    (f) =>
      f.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (f.county && f.county.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Health Facilities Directory</h2>
          <p className="text-xs text-slate-500 mt-1">Nairobi KMHFR reference directory · transfer eligibility is prototype configuration</p>
        </div>
        <DataBadge type="CONFIRMED" label="FACILITY REGISTRY" />
      </div>

      <div className="relative max-w-md">
        <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search facility by name, code, or county..."
          className="w-full bg-white border border-slate-200 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-900 focus:outline-none focus:border-indigo-500"
        />
      </div>

      {error ? (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-800">
          <p>{error}</p>
          <button className="mt-3 rounded-lg bg-white px-3 py-2 font-semibold text-red-700 border border-red-200" onClick={() => { setIsLoading(true); setError(null); setReloadKey((key) => key + 1); }}>Retry</button>
        </div>
      ) : isLoading ? (
        <div className="space-y-3 animate-pulse">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-white rounded-lg"></div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">No facilities match your search.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((fac) => (
            <div
              key={fac.id}
              className="p-5 rounded-xl bg-white border border-slate-200 hover:border-indigo-300 transition-all shadow-sm flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-blue-700 font-bold">
                    {fac.code}
                  </span>
                  <span className={`flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded border ${fac.is_active ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : 'text-slate-600 bg-slate-100 border-slate-200'}`}>
                    <CheckCircle2 className="w-3 h-3" /> {fac.is_active ? 'ACTIVE' : 'INACTIVE'}
                  </span>
                </div>

                <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-slate-500" />
                  <span>{fac.display_name || fac.name}</span>
                </h3>

                <p className="text-xs text-slate-500 mt-2 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-blue-700 shrink-0" />
                  <span>{fac.county ? `${fac.county} County` : 'Kenya Health Sector'}</span>
                </p>

                <p className="text-[11px] text-slate-500 mt-1">
                  {fac.facility_type || 'Type not specified'} · KEPH Level {fac.keph_level || '—'}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-200 text-[11px] text-slate-500 space-y-2">
                <p>{fac.ownership_category || 'Ownership unknown'} · {fac.transfer_eligible ? 'Prototype transfer network' : 'Reference only'}</p>
                <details>
                  <summary className="cursor-pointer text-blue-700">Source and facility details</summary>
                  <div className="mt-2 space-y-1">
                    <p>Official KMHFR name: {fac.official_name || fac.name}</p>
                    <p>KMHFR code: {fac.kmhfr_code || fac.code} · {fac.sub_county || '—'} / {fac.ward || '—'}</p>
                    <p>Beds: {fac.bed_capacity ?? 'Not recorded'} · Cots: {fac.cots ?? 'Not recorded'}</p>
                    {fac.reference_note && <p>{fac.reference_note}</p>}
                    <p>{fac.source_name || 'Unverified source'} · Retrieved {fac.retrieved_at ? new Date(fac.retrieved_at).toLocaleDateString() : '—'}</p>
                    {fac.source_url && <a href={fac.source_url} target="_blank" rel="noreferrer" className="text-blue-700 underline">Open registry record</a>}
                  </div>
                </details>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

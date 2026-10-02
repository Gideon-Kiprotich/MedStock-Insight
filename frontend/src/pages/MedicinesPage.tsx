import { medicineLabel } from '../utils/labels';
import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Medicine } from '../types/api';
import { Pill, ChevronRight, Search } from 'lucide-react';
import { DataBadge } from '../components/common/DataBadge';

interface MedicinesPageProps {
  onSelectMedicine: (id: string) => void;
}

export const MedicinesPage: React.FC<MedicinesPageProps> = ({ onSelectMedicine }) => {
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    api.getMedicines()
      .then((res) => setMedicines(res.data))
      .catch((err) => setError(err?.message || 'Unable to load the medicine catalog.'))
      .finally(() => setIsLoading(false));
  }, [reloadKey]);

  const filtered = medicines.filter(
    (m) =>
      m.generic_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Medicine Catalog</h2>
          <p className="text-xs text-slate-500 mt-1">KEML 2023 reference catalogue · operational quantities are synthetic</p>
        </div>
        <DataBadge type="CONFIRMED" label="MASTER CATALOG" />
      </div>

      <div className="relative max-w-md">
        <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search by medicine name or code..."
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
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">No medicines match your search.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((med) => (
            <div
              key={med.id}
              onClick={() => onSelectMedicine(med.id)}
              className="p-5 rounded-xl bg-white border border-slate-200 hover:border-indigo-300 cursor-pointer transition-all shadow-sm flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-500">
                    {med.code}
                  </span>
                  <Pill className="w-4 h-4 text-blue-700" />
                </div>
                <h3 className="font-bold text-slate-900 text-sm">{medicineLabel(med)}</h3>
                <p className="text-xs text-slate-500 mt-1">
                  {med.category || 'Category not specified'} · Level of Use {med.level_of_use ?? 'not recorded'}
                </p>
              </div>

              <div className="mt-4 text-[11px] text-slate-500" onClick={(event) => event.stopPropagation()}>
                <details><summary className="cursor-pointer text-blue-700">Source and provenance</summary>
                  <p className="mt-2">{med.source_name || 'Unverified source'} · Section {med.keml_section || '—'} · Retrieved {med.retrieved_at ? new Date(med.retrieved_at).toLocaleDateString() : '—'}</p>
                  {med.aware_classification && <p>AWaRe: {med.aware_classification}</p>}
                  {med.source_url && <a href={med.source_url} target="_blank" rel="noreferrer" className="text-blue-700 underline">Open source</a>}
                </details>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-200 flex items-center justify-between text-xs text-blue-700 font-medium">
                <span>View simulated stock & forecast</span>
                <ChevronRight className="w-4 h-4" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

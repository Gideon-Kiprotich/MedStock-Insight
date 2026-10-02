import React from 'react';
import { Construction } from 'lucide-react';
import { DataBadge } from '../components/common/DataBadge';

interface PlaceholderPageProps {
  title: string;
  description: string;
}

export const PlaceholderPage: React.FC<PlaceholderPageProps> = ({ title, description }) => {
  return (
    <div className="p-12 text-center max-w-xl mx-auto my-12 bg-white border border-slate-200 rounded-2xl shadow-sm">
      <div className="inline-flex p-4 rounded-2xl bg-amber-50/60 border border-amber-500/40 text-amber-700 mb-4">
        <Construction className="w-10 h-10" />
      </div>

      <h2 className="text-xl font-bold text-slate-900">{title} Workspace</h2>
      <p className="text-xs text-slate-500 mt-2 leading-relaxed">{description}</p>

      <div className="mt-6 pt-4 border-t border-slate-200 flex items-center justify-center gap-2">
        <DataBadge type="DERIVED" label="PLANNED MODULE" />
        <span className="text-[11px] text-slate-500">
          Unfinished operational area — No simulated or fake data is rendered.
        </span>
      </div>
    </div>
  );
};

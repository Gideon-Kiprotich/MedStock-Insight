import React from 'react';
import type { DataClassification } from '../../types/api';
import { CheckCircle2, Calculator, Sparkles, ArrowRightLeft } from 'lucide-react';

interface DataBadgeProps {
  type: DataClassification;
  label?: string;
  className?: string;
}

export const DataBadge: React.FC<DataBadgeProps> = ({ type, label, className = '' }) => {
  switch (type) {
    case 'CONFIRMED':
      return (
        <span
          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 ${className}`}
          title="Confirmed within the demonstration dataset"
        >
          <CheckCircle2 className="w-3 h-3 text-emerald-700" />
          {label || 'CONFIRMED'}
        </span>
      );
    case 'DERIVED':
      return (
        <span
          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-300 ${className}`}
          title="Analytically derived operational summary"
        >
          <Calculator className="w-3 h-3 text-slate-400" />
          {label || 'DERIVED'}
        </span>
      );
    case 'PREDICTED':
      return (
        <span
          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-indigo-50 text-indigo-800 border border-dashed border-indigo-300 ${className}`}
          title="ML-projected estimation / forecast"
        >
          <Sparkles className="w-3 h-3 text-indigo-700" />
          {label || 'PREDICTED'}
        </span>
      );
    case 'RECOMMENDED':
      return (
        <span
          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-300 ${className}`}
          title="Decision-support recommendation"
        >
          <ArrowRightLeft className="w-3 h-3 text-amber-700" />
          {label || 'RECOMMENDED'}
        </span>
      );
  }
};

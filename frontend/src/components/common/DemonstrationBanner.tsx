import React from 'react';
import { AlertCircle } from 'lucide-react';

export const DemonstrationBanner: React.FC = () => {
  return (
    <div className="bg-indigo-50 border-b border-indigo-100 text-indigo-900 px-4 py-2 text-xs font-medium flex items-center justify-center gap-2">
      <AlertCircle className="w-4 h-4 text-indigo-600 shrink-0" />
      <span>
        DEMONSTRATION ENVIRONMENT — Data shown is simulated and does not represent live facility inventory.
      </span>
      <span className="hidden lg:inline text-indigo-600 border-l border-indigo-200 pl-2">Reference data: KMHFR / KEML 2023 · Operational data: Synthetic demonstration dataset</span>
    </div>
  );
};

import React from 'react';
import {
  LayoutDashboard,
  Package,
  Pill,
  TrendingUp,
  AlertTriangle,
  ArrowRightLeft,
  Truck,
  History,
  Building2,
  Activity,
  FileBarChart,
  Users,
  Settings,
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onTabChange }) => {
  const primaryNav = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'inventory', label: 'Inventory Balances', icon: Package },
    { id: 'medicines', label: 'Medicine Catalog', icon: Pill },
    { id: 'forecasts', label: 'Demand Forecasts', icon: TrendingUp },
    { id: 'risk', label: 'Stockout Risk', icon: AlertTriangle },
    { id: 'redistribution', label: 'Redistribution Queue', icon: ArrowRightLeft },
    { id: 'transfers', label: 'Transfer Tracking', icon: Truck },
    { id: 'facilities', label: 'Facilities Directory', icon: Building2 },
    { id: 'audit', label: 'Audit Trail', icon: History },
  ];

  const secondaryNav = [
    { id: 'consumption', label: 'Consumption Log', icon: Activity },
    { id: 'reports', label: 'Operational Reports', icon: FileBarChart },
    { id: 'users', label: 'User Management', icon: Users },
    { id: 'settings', label: 'System Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 h-full bg-slate-900 border-r border-slate-800 flex flex-col shrink-0 shadow-xl lg:shadow-none">
      <nav className="p-4 space-y-6 flex-1 overflow-y-auto">
        <div>
          <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Operational Workflows
          </div>
          <div className="space-y-1 mt-1">
            {primaryNav.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id || (currentTab === 'medicine-detail' && item.id === 'medicines');
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            System Modules
          </div>
          <div className="space-y-1 mt-1">
            {secondaryNav.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      <div className="p-4 border-t border-slate-800">
        <div className="rounded-lg bg-slate-800/60 border border-slate-700/50 p-3 text-xs text-slate-400">
          <p className="font-semibold text-slate-300">MedStock Insight v0.1.0</p>
          <p className="mt-1 text-[11px] text-slate-400">Decision Support System for Health Supply Chain</p>
        </div>
      </div>
    </aside>
  );
};

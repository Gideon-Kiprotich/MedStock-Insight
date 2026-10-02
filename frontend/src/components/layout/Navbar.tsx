import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { LogOut, User as UserIcon, Shield, Activity, Menu } from 'lucide-react';

export const Navbar: React.FC<{ onMenuToggle?: () => void }> = ({ onMenuToggle }) => {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 bg-slate-950 border-b border-slate-800 px-4 md:px-6 flex items-center justify-between sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <button type="button" onClick={onMenuToggle} aria-label="Open navigation" className="lg:hidden p-2 rounded-lg text-slate-200 hover:bg-slate-800"><Menu className="w-5 h-5" /></button>
        <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center">
          <Activity className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="font-bold text-slate-100 tracking-wide leading-none text-base">MedStock Insight</h1>
          <p className="hidden sm:block text-[11px] text-slate-400 font-medium">Kenyan Health Supply Chain Decision Support</p>
        </div>
      </div>

      {user && (
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60">
            <UserIcon className="w-4 h-4 text-cyan-400" />
            <div className="text-left">
              <p className="text-xs font-semibold text-slate-200 leading-tight">{user.full_name}</p>
              <div className="flex items-center gap-1">
                <Shield className="w-3 h-3 text-emerald-400" />
                <span className="text-[10px] text-slate-400 font-medium uppercase">{user.role?.name || user.role?.code}</span>
              </div>
            </div>
          </div>

          <button
            onClick={logout}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
            title="Sign Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      )}
    </header>
  );
};

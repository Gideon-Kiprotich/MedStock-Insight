import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { DemoUser } from '../types/api';
import { Users } from 'lucide-react';

export const UsersPage: React.FC = () => {
  const { user } = useAuth();
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user?.role.code !== 'ADMINISTRATOR') {
      setLoading(false);
      return;
    }
    api.getDemoUsers()
      .then(setUsers)
      .catch((err) => setError(err?.message || 'Unable to load demonstration users.'))
      .finally(() => setLoading(false));
  }, [user?.role.code]);

  return <div className="p-8 space-y-6">
    <div>
      <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2"><Users className="w-6 h-6 text-indigo-600" /> Demonstration Users</h2>
      <p className="text-sm text-slate-500 mt-1">Invented staff personas for testing role access. No real employee identities or credentials are used.</p>
    </div>
    {user?.role.code !== 'ADMINISTRATOR' ? (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">Administrator access is required to view demo accounts.</div>
    ) : error ? (
      <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-800">{error}</div>
    ) : loading ? (
      <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">Loading demonstration users…</div>
    ) : users.length === 0 ? (
      <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">No demonstration accounts are configured.</div>
    ) : (
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full min-w-[700px] text-sm text-left">
          <thead className="bg-slate-50 text-slate-600 text-xs uppercase tracking-wide"><tr>
            <th className="px-5 py-3">Demo user</th><th className="px-5 py-3">Assigned facility</th>
            <th className="px-5 py-3">Role</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Last login</th>
          </tr></thead>
          <tbody className="divide-y divide-slate-100">{users.map((person) => <tr key={person.id} className="hover:bg-slate-50">
            <td className="px-5 py-4"><div className="font-semibold text-slate-900">{person.full_name} — {person.title || person.role_name}</div><div className="text-xs text-slate-500 mt-1">{person.email} · Synthetic demo user</div></td>
            <td className="px-5 py-4 text-slate-700">{person.facility_name || 'Unassigned'}</td>
            <td className="px-5 py-4 text-slate-700">{person.role_name}</td>
            <td className="px-5 py-4"><span className={person.is_active ? 'rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700' : 'rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600'}>{person.is_active ? 'Active' : 'Inactive'}</span></td>
            <td className="px-5 py-4 text-slate-600">{person.last_login_at ? new Date(person.last_login_at).toLocaleString() : 'Never'}</td>
          </tr>)}</tbody>
        </table>
      </div>
    )}
  </div>;
};

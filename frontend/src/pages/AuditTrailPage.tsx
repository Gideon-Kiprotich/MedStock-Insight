import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { AuditLog } from '../types/api';
import { DataBadge } from '../components/common/DataBadge';
import { History, Shield, Filter, RefreshCw, Lock } from 'lucide-react';

export const AuditTrailPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [actionFilter, setActionFilter] = useState('');
  const [entityFilter, setEntityFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const loadLogs = async () => {
    setIsLoading(true);
    try {
      const res = await api.getAuditLogs({
        action: actionFilter || undefined,
        entity_type: entityFilter || undefined,
      });
      setLogs(res.data);
    } catch {
      // Ignored
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [actionFilter, entityFilter]);

  const getActionBadgeClass = (action: string) => {
    if (action.includes('APPROVED') || action.includes('COMPLETED')) {
      return 'bg-emerald-50 text-emerald-700 border-emerald-500/50';
    }
    if (action.includes('REJECTED') || action.includes('CANCELLED')) {
      return 'bg-red-50 text-red-700 border-red-500/50';
    }
    if (action.includes('DISPATCHED')) {
      return 'bg-indigo-50 text-indigo-700 border-indigo-500/50';
    }
    return 'bg-slate-100 text-slate-700 border-slate-200';
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2.5">
            <History className="w-6 h-6 text-blue-700" />
            <span>Immutable Audit Trail</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Demonstration audit log of synthetic decisions and inventory state changes
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadLogs}
            className="p-2 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-100"
            title="Refresh Audit Logs"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <DataBadge type="CONFIRMED" label="IMMUTABLE AUDIT LEDGER" />
        </div>
      </div>

      {/* Security & Governance Notice */}
      <div className="p-3.5 rounded-xl bg-white border border-slate-200 text-slate-500 text-xs flex items-center gap-3">
        <Lock className="w-4 h-4 text-blue-700 shrink-0" />
        <span>
          This log is read-only and immutable. Entries are permanently recorded by the system for statutory compliance and supply chain transparency. Edit/delete operations are disallowed.
        </span>
      </div>

      {/* Filter Toolbar */}
      <div className="flex items-center gap-4 p-4 rounded-xl bg-white border border-slate-200 text-xs">
        <div className="flex items-center gap-2 font-semibold text-slate-500">
          <Filter className="w-4 h-4 text-blue-700" />
          <span>Filters:</span>
        </div>

        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-slate-900 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Actions</option>
          <option value="RECOMMENDATION_APPROVED">RECOMMENDATION_APPROVED</option>
          <option value="RECOMMENDATION_REJECTED">RECOMMENDATION_REJECTED</option>
          <option value="TRANSFER_CREATED">TRANSFER_CREATED</option>
          <option value="TRANSFER_DISPATCHED">TRANSFER_DISPATCHED</option>
          <option value="TRANSFER_COMPLETED">TRANSFER_COMPLETED</option>
          <option value="TRANSFER_CANCELLED">TRANSFER_CANCELLED</option>
          <option value="INVENTORY_TRANSACTION_RECORDED">INVENTORY_TRANSACTION_RECORDED</option>
        </select>

        <select
          value={entityFilter}
          onChange={(e) => setEntityFilter(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-slate-900 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Entity Types</option>
          <option value="RedistributionRecommendation">RedistributionRecommendation</option>
          <option value="RedistributionTransfer">RedistributionTransfer</option>
          <option value="InventoryTransaction">InventoryTransaction</option>
        </select>
      </div>

      {/* Audit Table */}
      {isLoading ? (
        <div className="p-8 text-center text-slate-500 text-xs">Loading audit ledger...</div>
      ) : logs.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-xl border border-slate-200 text-slate-500 text-xs">
          No audit log entries match the selected filter criteria.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Actor ID</th>
                <th className="py-3 px-4">Entity Type</th>
                <th className="py-3 px-4">Entity ID</th>
                <th className="py-3 px-4">Event Details & Metadata</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-100/40 transition-colors">
                  <td className="py-3 px-4 text-slate-700 font-mono text-[11px]">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getActionBadgeClass(log.action)}`}>
                      {log.action}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-500 text-[11px]">
                    {log.user_id ? (
                      <span className="flex items-center gap-1 text-slate-700">
                        <Shield className="w-3 h-3 text-blue-700" />
                        <span>{log.user_id.slice(0, 8)}...</span>
                      </span>
                    ) : (
                      'SYSTEM'
                    )}
                  </td>
                  <td className="py-3 px-4 text-slate-700 font-medium">{log.entity_type}</td>
                  <td className="py-3 px-4 font-mono text-blue-700 text-[11px]">{log.entity_id.slice(0, 8)}...</td>
                  <td className="py-3 px-4 text-[11px] text-slate-500 max-w-xs truncate">
                    {log.details ? (
                      <span className="font-mono text-slate-700">{JSON.stringify(log.details)}</span>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

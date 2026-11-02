import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Cpu, Clock, Database, ShieldCheck } from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { MLModelVersion, SystemSettings } from '../types/api';
import { DataBadge } from '../components/common/DataBadge';

const dateTime = (value?: string) => value ? new Date(value).toLocaleString() : 'Not yet changed';

export const SystemSettingsPage: React.FC = () => {
  const { user } = useAuth();
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [models, setModels] = useState<MLModelVersion[]>([]);
  const [forecastHorizon, setForecastHorizon] = useState<7 | 14 | 30>(30);
  const [reportingDays, setReportingDays] = useState<7 | 30 | 90>(30);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const isAdmin = user?.role.code === 'ADMINISTRATOR';

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    Promise.all([api.getSettings(), api.getModels()]).then(([settingResult, modelResult]) => {
      if (!active) return;
      setSettings(settingResult);
      setModels(modelResult);
      setForecastHorizon(settingResult.forecast_default_horizon_days);
      setReportingDays(settingResult.reporting_default_days);
    }).catch((err: unknown) => {
      if (active) setError(err instanceof Error ? err.message : 'System settings could not be loaded.');
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, []);

  const reset = () => {
    if (!settings) return;
    setForecastHorizon(settings.forecast_default_horizon_days);
    setReportingDays(settings.reporting_default_days);
    setSuccess('');
    setError('');
  };

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const updated = await api.updateSettings({
        forecast_default_horizon_days: forecastHorizon,
        reporting_default_days: reportingDays,
      });
      setSettings(updated);
      setSuccess('System settings saved and audit event recorded.');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'System settings could not be saved.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">System Settings</h1>
          <p className="mt-2 text-sm text-slate-500">
            Persistent application defaults and read-only operational policy. Credentials and secrets are never displayed here.
          </p>
        </div>
        <DataBadge type="CONFIRMED" label="ADMIN CONTROLLED" />
      </header>

      {error && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <AlertTriangle className="h-4 w-4" /> {error}
        </div>
      )}
      {success && (
        <div role="status" className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          <CheckCircle2 className="h-4 w-4" /> {success}
        </div>
      )}

      {loading ? (
        <p role="status" className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
          Loading system settings…
        </p>
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Application information">
            {[
              ['Application', settings?.application_name ?? 'MedStock Insight API'],
              ['Version', settings?.application_version ?? '0.1.0'],
              ['Environment', settings?.environment ?? 'Unavailable'],
              ['Timezone', settings?.timezone ?? 'Africa/Nairobi'],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
                <p className="mt-2 break-words text-sm font-bold text-slate-900">{value}</p>
              </div>
            ))}
          </section>

          <form onSubmit={save} className="space-y-6">
            <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-200 p-5">
                <h2 className="flex items-center gap-2 text-base font-bold text-slate-900">
                  <Clock className="h-4 w-4 text-indigo-600" /> Application Defaults
                </h2>
                <p className="mt-1 text-xs text-slate-500">
                  These values pre-fill forecasting and reporting workflows. They do not alter historical records.
                </p>
              </div>
              <div className="grid gap-5 p-5 md:grid-cols-2">
                <label className="text-sm font-semibold text-slate-700">
                  Forecast default horizon
                  <select
                    aria-label="Forecast default horizon"
                    value={forecastHorizon}
                    disabled={!isAdmin}
                    onChange={(event) => {
                      setForecastHorizon(Number(event.target.value) as 7 | 14 | 30);
                      setSuccess('');
                    }}
                    className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm disabled:opacity-70"
                  >
                    <option value={7}>7 days</option>
                    <option value={14}>14 days</option>
                    <option value={30}>30 days</option>
                  </select>
                  <span className="mt-1 block text-[11px] font-normal text-slate-500">
                    Used when a forecast request omits a horizon and as the UI default.
                  </span>
                </label>
                <label className="text-sm font-semibold text-slate-700">
                  Default reporting period
                  <select
                    aria-label="Default reporting period"
                    value={reportingDays}
                    disabled={!isAdmin}
                    onChange={(event) => {
                      setReportingDays(Number(event.target.value) as 7 | 30 | 90);
                      setSuccess('');
                    }}
                    className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm disabled:opacity-70"
                  >
                    <option value={7}>7 days</option>
                    <option value={30}>30 days</option>
                    <option value={90}>90 days</option>
                  </select>
                  <span className="mt-1 block text-[11px] font-normal text-slate-500">
                    Initial date window for reporting views such as the consumption log.
                  </span>
                </label>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-5 py-4 text-xs text-slate-500">
                <span>
                  Last updated: {dateTime(settings?.updated_at)}
                  {settings?.updated_by_name ? ` by ${settings.updated_by_name}` : ''}
                </span>
                {isAdmin ? (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={reset}
                      disabled={saving || !settings}
                      className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 disabled:opacity-50"
                    >
                      Cancel
                    </button>
                    <button
                      disabled={saving || !settings}
                      className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                    >
                      {saving ? 'Saving…' : 'Save Settings'}
                    </button>
                  </div>
                ) : (
                  <span className="inline-flex items-center gap-1.5 font-semibold text-slate-600">
                    <ShieldCheck className="h-4 w-4" /> Administrator access required to change
                  </span>
                )}
              </div>
            </section>
          </form>

          <section className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="flex items-center gap-2 text-base font-bold text-slate-900">
                <Database className="h-4 w-4 text-emerald-600" /> Operational Policy
              </h2>
              <dl className="mt-4 space-y-3 text-sm">
                <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-3">
                  <dt className="text-slate-500">Timezone</dt>
                  <dd className="font-semibold text-slate-900">{settings?.timezone ?? 'Africa/Nairobi'}</dd>
                </div>
                <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-3">
                  <dt className="text-slate-500">Active stockout</dt>
                  <dd className="font-semibold text-slate-900">Critical</dd>
                </div>
                <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-3">
                  <dt className="text-slate-500">Critical breach</dt>
                  <dd className="font-semibold text-slate-900">
                    ≤ {settings?.stockout_thresholds.critical_days ?? 5} days
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-3">
                  <dt className="text-slate-500">High breach</dt>
                  <dd className="font-semibold text-slate-900">
                    ≤ {settings?.stockout_thresholds.high_days ?? 10} days
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-slate-500">Medium breach</dt>
                  <dd className="font-semibold text-slate-900">
                    ≤ {settings?.stockout_thresholds.medium_days ?? 15} days
                  </dd>
                </div>
              </dl>
              <p className="mt-4 text-[11px] text-slate-500">
                Risk thresholds are read-only in this release. They are derived from the server-side risk engine.
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="flex items-center gap-2 text-base font-bold text-slate-900">
                <ShieldCheck className="h-4 w-4 text-amber-600" /> Security Boundary
              </h2>
              <ul className="mt-4 space-y-3 text-sm text-slate-600">
                <li>Database connection strings and credentials are managed outside this workspace.</li>
                <li>JWT signing keys, API keys, and private keys are never returned by the settings API.</li>
                <li>Only administrators can change persisted defaults; every update writes an audit record.</li>
                <li>Read-only operational thresholds remain server-controlled for consistent risk classification.</li>
              </ul>
            </div>
          </section>

          <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-5">
              <div>
                <h2 className="flex items-center gap-2 text-base font-bold text-slate-900">
                  <Cpu className="h-4 w-4 text-indigo-600" /> ML Model Registry
                </h2>
                <p className="mt-1 text-xs text-slate-500">
                  Persisted model records used by forecasting. No invented model status is shown.
                </p>
                <p className="mt-1 text-[11px] text-slate-500">
                  Active models: {models.filter((model) => model.is_active).length} of {models.length}
                </p>
              </div>
              <DataBadge type="CONFIRMED" label="REGISTRY RECORDS" />
            </div>
            {!models.length ? (
              <p className="p-5 text-sm text-slate-500">No model versions are registered.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 font-semibold text-slate-600">
                    <tr>
                      <th className="px-5 py-3">Model</th>
                      <th className="px-5 py-3">Code</th>
                      <th className="px-5 py-3">Algorithm</th>
                      <th className="px-5 py-3">Version</th>
                      <th className="px-5 py-3">Training / evaluation metadata</th>
                      <th className="px-5 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {models.map((model) => (
                      <tr key={model.id} className="hover:bg-slate-50">
                        <td className="px-5 py-3 font-semibold text-slate-900">{model.name}</td>
                        <td className="px-5 py-3 font-mono text-[11px] text-slate-500">{model.code}</td>
                        <td className="px-5 py-3 text-slate-600">{model.algorithm}</td>
                        <td className="px-5 py-3 text-slate-600">{model.version}</td>
                        <td className="px-5 py-3 text-slate-600">
                          {model.hyperparameters || model.evaluation_metrics ? (
                            <details>
                              <summary className="cursor-pointer font-semibold text-indigo-700">View metadata</summary>
                              <pre className="mt-2 max-w-xs overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-[10px] text-slate-600">
                                {JSON.stringify({
                                  hyperparameters: model.hyperparameters,
                                  evaluation_metrics: model.evaluation_metrics,
                                  created_at: model.created_at,
                                }, null, 2)}
                              </pre>
                            </details>
                          ) : 'No metadata recorded'}
                        </td>
                        <td className="px-5 py-3">
                          <DataBadge
                            type={model.is_active ? 'CONFIRMED' : 'DERIVED'}
                            label={model.is_active ? 'ACTIVE' : 'INACTIVE'}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
};

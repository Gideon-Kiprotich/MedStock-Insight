import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type { ReactNode } from 'react';
import '@testing-library/jest-dom/vitest';
import { ConsumptionLogPage } from '../pages/ConsumptionLogPage';
import { SystemSettingsPage } from '../pages/SystemSettingsPage';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { ConsumptionResponse, SystemSettings } from '../types/api';

vi.mock('../api/client', () => ({
  api: {
    getFacilities: vi.fn(),
    getMedicines: vi.fn(),
    getSettings: vi.fn(),
    getConsumptionLog: vi.fn(),
    createTransaction: vi.fn(),
    getInventoryBalances: vi.fn(),
    updateSettings: vi.fn(),
    getModels: vi.fn(),
  },
}));

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }));

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  Line: () => null,
}));

const admin = {
  id: 'usr-admin',
  email: 'admin@test.example',
  full_name: 'Test Administrator',
  role: { id: 'r-1', code: 'ADMINISTRATOR' as const, name: 'Administrator' },
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
};

const manager = {
  ...admin,
  id: 'usr-manager',
  full_name: 'Test Manager',
  role: { id: 'r-2', code: 'SUPPLY_CHAIN_MANAGER' as const, name: 'Supply Chain Manager' },
};

const settings: SystemSettings = {
  application_name: 'MedStock Insight API',
  application_version: '0.1.0',
  environment: 'test',
  forecast_default_horizon_days: 30,
  reporting_default_days: 30,
  timezone: 'Africa/Nairobi',
  stockout_thresholds: {
    critical_days: 5,
    high_days: 10,
    medium_days: 15,
    out_of_stock_is_critical: true,
  },
  updated_at: '2026-11-02T12:00:00Z',
  updated_by_name: 'Test Administrator',
};

const consumption: ConsumptionResponse = {
  data: [{
    id: 'tx-1',
    facility_id: 'fac-1',
    facility_name: 'Test Facility',
    medicine_id: 'med-1',
    medicine_name: 'Amoxicillin 500 mg Capsule',
    unit_of_measure: 'capsules',
    quantity: 12,
    transaction_date: '2026-11-01',
    reference_number: 'REF-1',
    notes: 'Dispensed to ward',
    recorded_by: 'usr-officer',
    recorded_by_name: 'Test Officer',
    created_at: '2026-11-01T10:00:00Z',
  }],
  pagination: { page: 1, page_size: 25, total: 1, total_pages: 1 },
  summary: {
    total_quantity: 12,
    transaction_count: 1,
    distinct_medicines: 1,
    days_covered: 1,
    daily_average: 12,
    first_date: '2026-11-01',
    last_date: '2026-11-01',
  },
  trend: [{ date: '2026-11-01', quantity: 12, transaction_count: 1 }],
};

const facilities = {
  data: [{ id: 'fac-1', code: 'F1', name: 'Test Facility', is_active: true, created_at: '' }],
  pagination: { page: 1, page_size: 50, total: 1, total_pages: 1 },
};
const medicines = {
  data: [{
    id: 'med-1',
    code: 'M1',
    generic_name: 'Amoxicillin',
    strength: '500 mg',
    dosage_form: 'Capsule',
    unit_of_measure: 'capsules',
    is_active: true,
    created_at: '',
  }],
  pagination: { page: 1, page_size: 200, total: 1, total_pages: 1 },
};
const models = [{
  id: 'model-1',
  code: 'RANDOM_FOREST',
  name: 'Random Forest',
  algorithm: 'RandomForestRegressor',
  version: '1.0',
  is_active: true,
  hyperparameters: { n_estimators: 200 },
  evaluation_metrics: { mae: 1.2 },
  created_at: '2026-10-01T00:00:00Z',
}];

beforeEach(() => {
  cleanup();
  vi.resetAllMocks();
  vi.mocked(useAuth).mockReturnValue({ user: admin } as never);
  vi.mocked(api.getFacilities).mockResolvedValue(facilities as never);
  vi.mocked(api.getMedicines).mockResolvedValue(medicines as never);
  vi.mocked(api.getSettings).mockResolvedValue(settings);
  vi.mocked(api.getConsumptionLog).mockResolvedValue(consumption);
  vi.mocked(api.getModels).mockResolvedValue(models as never);
});

afterEach(() => cleanup());

describe('Consumption Log workspace', () => {
  it('renders loading, confirmed records, analytics and the derived trend', async () => {
    vi.mocked(api.getConsumptionLog).mockReturnValue(new Promise(() => {}));
    render(<ConsumptionLogPage />);
    expect(await screen.findByRole('status')).toHaveTextContent('Loading confirmed consumption records');
    cleanup();

    vi.mocked(api.getConsumptionLog).mockResolvedValue(consumption);
    render(<ConsumptionLogPage />);
    expect(await screen.findByText('REF-1')).toBeInTheDocument();
    expect(screen.getByText('Test Officer')).toBeInTheDocument();
    expect(screen.getByText('Dispensed to ward')).toBeInTheDocument();
    expect(screen.getByText('Distinct medicines')).toBeInTheDocument();
    expect(screen.getByText('Daily consumption trend')).toBeInTheDocument();
    expect(screen.getByText('DERIVED FROM LEDGER')).toBeInTheDocument();
  });

  it('sends facility, medicine, search, date and sorting filters to the backend', async () => {
    render(<ConsumptionLogPage />);
    await screen.findByText('REF-1');
    fireEvent.change(screen.getByLabelText('Facility'), { target: { value: 'fac-1' } });
    fireEvent.change(screen.getByLabelText('Medicine'), { target: { value: 'med-1' } });
    fireEvent.change(screen.getByLabelText('Search'), { target: { value: 'amox' } });
    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2026-10-01' } });
    fireEvent.change(screen.getByLabelText('To'), { target: { value: '2026-11-01' } });
    fireEvent.change(screen.getByLabelText('Sort by'), { target: { value: 'quantity' } });
    fireEvent.change(screen.getByLabelText('Direction'), { target: { value: 'asc' } });
    await waitFor(() => expect(api.getConsumptionLog).toHaveBeenLastCalledWith(
      expect.objectContaining({
        facility_id: 'fac-1',
        medicine_id: 'med-1',
        search: 'amox',
        start_date: '2026-10-01',
        end_date: '2026-11-01',
        sort_by: 'quantity',
        sort_order: 'asc',
      }),
    ));
  });

  it('records consumption, refreshes history and displays the updated balance', async () => {
    vi.mocked(api.createTransaction).mockResolvedValue({ id: 'tx-new' } as never);
    vi.mocked(api.getInventoryBalances).mockResolvedValue({
      data: [{ id: 'bal-1', facility_id: 'fac-1', medicine_id: 'med-1', quantity_on_hand: 88 }],
      pagination: { page: 1, page_size: 1, total: 1, total_pages: 1 },
    } as never);
    render(<ConsumptionLogPage />);
    await screen.findByText('REF-1');
    fireEvent.click(screen.getByRole('button', { name: /Record Consumption/i }));
    const form = screen.getByRole('form', { name: 'Record consumption form' });
    fireEvent.change(within(form).getByLabelText('Facility'), { target: { value: 'fac-1' } });
    fireEvent.change(within(form).getByLabelText('Medicine'), { target: { value: 'med-1' } });
    fireEvent.change(within(form).getByLabelText('Quantity'), { target: { value: '4' } });
    fireEvent.change(within(form).getByLabelText('Reference'), { target: { value: 'DISP-9' } });
    fireEvent.click(within(form).getByRole('button', { name: 'Record Consumption' }));

    await waitFor(() => expect(api.createTransaction).toHaveBeenCalledWith(expect.objectContaining({
      facility_id: 'fac-1',
      medicine_id: 'med-1',
      transaction_type: 'CONSUMPTION',
      quantity: 4,
      reference_number: 'DISP-9',
    })));
    expect(await screen.findByText(/Updated balance: 88 capsules/)).toBeInTheDocument();
    await waitFor(() => expect(api.getConsumptionLog).toHaveBeenCalledTimes(2));
  });

  it('shows server validation failures and empty and error states', async () => {
    vi.mocked(api.createTransaction).mockRejectedValue(new Error('Transaction would make inventory negative'));
    render(<ConsumptionLogPage />);
    await screen.findByText('REF-1');
    fireEvent.click(screen.getByRole('button', { name: /Record Consumption/i }));
    const form = screen.getByRole('form', { name: 'Record consumption form' });
    fireEvent.change(within(form).getByLabelText('Facility'), { target: { value: 'fac-1' } });
    fireEvent.change(within(form).getByLabelText('Medicine'), { target: { value: 'med-1' } });
    fireEvent.change(within(form).getByLabelText('Quantity'), { target: { value: '999' } });
    fireEvent.click(within(form).getByRole('button', { name: 'Record Consumption' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('inventory negative');
    cleanup();

    vi.mocked(api.getConsumptionLog).mockResolvedValue({
      ...consumption,
      data: [],
      pagination: { page: 1, page_size: 25, total: 0, total_pages: 0 },
      summary: {
        total_quantity: 0,
        transaction_count: 0,
        distinct_medicines: 0,
        days_covered: 0,
        daily_average: 0,
      },
      trend: [],
    });
    render(<ConsumptionLogPage />);
    expect(await screen.findByText('No consumption records match the selected filters.')).toBeInTheDocument();
    cleanup();

    vi.mocked(api.getConsumptionLog).mockRejectedValue(new Error('Ledger unavailable'));
    render(<ConsumptionLogPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Ledger unavailable');
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });
});

describe('System Settings workspace', () => {
  it('shows application, policy and model data to non-admin users as read-only', async () => {
    vi.mocked(useAuth).mockReturnValue({ user: manager } as never);
    render(<SystemSettingsPage />);
    expect(await screen.findByText('MedStock Insight API')).toBeInTheDocument();
    expect(screen.getByText('0.1.0')).toBeInTheDocument();
    expect(screen.getAllByText('Africa/Nairobi').length).toBeGreaterThan(0);
    expect(screen.getByText(/Administrator access required to change/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Save Settings' })).not.toBeInTheDocument();
    expect(screen.getByText('Random Forest')).toBeInTheDocument();
    expect(screen.getByText('View metadata')).toBeInTheDocument();
    expect(screen.queryByTitle(/secret/i)).not.toBeInTheDocument();
  });

  it('persists valid admin changes and reports success', async () => {
    vi.mocked(api.updateSettings).mockResolvedValue({
      ...settings,
      forecast_default_horizon_days: 7,
      reporting_default_days: 90,
    });
    render(<SystemSettingsPage />);
    await screen.findByText('MedStock Insight API');
    fireEvent.change(screen.getByLabelText('Forecast default horizon'), { target: { value: '7' } });
    fireEvent.change(screen.getByLabelText('Default reporting period'), { target: { value: '90' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save Settings' }));
    await waitFor(() => expect(api.updateSettings).toHaveBeenCalledWith({
      forecast_default_horizon_days: 7,
      reporting_default_days: 90,
    }));
    expect(await screen.findByText(/saved and audit event recorded/i)).toBeInTheDocument();
  });

  it('cancels unsaved changes and surfaces load failures', async () => {
    render(<SystemSettingsPage />);
    await screen.findByText('MedStock Insight API');
    const horizon = screen.getByLabelText('Forecast default horizon') as HTMLSelectElement;
    fireEvent.change(horizon, { target: { value: '7' } });
    expect(horizon.value).toBe('7');
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(horizon.value).toBe('30');
    expect(api.updateSettings).not.toHaveBeenCalled();
    cleanup();

    vi.mocked(api.getSettings).mockRejectedValue(new Error('Settings unavailable'));
    render(<SystemSettingsPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Settings unavailable');
  });
});

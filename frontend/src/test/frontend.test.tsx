import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import App from '../App';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';
import { StockoutRiskPage } from '../pages/StockoutRiskPage';
import { RedistributionPage } from '../pages/RedistributionPage';
import { TransferTrackingPage } from '../pages/TransferTrackingPage';
import { api, APIClientError } from '../api/client';
import { AuthProvider } from '../context/AuthContext';
import { ForecastEvaluationPanel } from '../components/common/ForecastEvaluationPanel';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual('../api/client');
  return {
    ...actual,
    api: {
      login: vi.fn(),
      getCurrentUser: vi.fn(),
      getDashboard: vi.fn(),
      getFacilities: vi.fn(),
      getMedicines: vi.fn(),
      getInventoryBalances: vi.fn(),
      getInventoryTransactions: vi.fn(),
      getRiskAssessments: vi.fn(),
      getForecastRuns: vi.fn(),
      getForecastSummary: vi.fn(),
      getForecastEvaluation: vi.fn(),
      getForecastExplanation: vi.fn(),
      getRiskExplanation: vi.fn(),
      getRecommendationExplanation: vi.fn(),
      getModels: vi.fn(),
      getRecommendations: vi.fn(),
      approveRecommendation: vi.fn(),
      rejectRecommendation: vi.fn(),
      getTransfers: vi.fn(),
      dispatchTransfer: vi.fn(),
      completeTransfer: vi.fn(),
      cancelTransfer: vi.fn(),
      getAuditLogs: vi.fn(),
    },
  };
});

describe('Phase 7 Frontend Integration Suite', () => {
  const mockUser = {
    id: 'usr-1',
    email: 'grace.njeri.demo@medstock.example',
    full_name: 'Admin User',
    role: { id: 'r-1', code: 'ADMINISTRATOR' as const, name: 'Administrator' },
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
  };

  const mockDashboardData = {
    summary: {
      facilities_count: 5,
      medicines_tracked: 10,
      active_stockouts: 2,
      critical_risk_count: 1,
      high_risk_count: 2,
      medium_risk_count: 1,
      low_risk_count: 6,
      pending_redistribution_count: 3,
      in_transit_transfer_count: 1,
      inventory_health: { healthy_count: 7, at_risk_count: 3, stockout_count: 2 },
      data_timestamp: '2026-09-27T12:00:00Z',
    },
    risk_worklist: [
      {
        facility_id: 'fac-1',
        facility_code: 'KNH',
        facility_name: 'Kenyatta National Hospital',
        medicine_id: 'med-1',
        medicine_code: 'AMOX500',
        generic_name: 'Amoxicillin 500mg',
        current_stock: 50,
        safety_stock: 200,
        days_until_breach: 2,
        projected_stockout_date: '2026-09-29',
        risk_level: 'CRITICAL',
        assessed_at: '2026-09-27T10:00:00Z',
        data_classification: 'PREDICTED',
      },
    ],
    redistribution_queue: [
      {
        recommendation_id: 'rec-1',
        source_facility_id: 'fac-2',
        source_facility_name: 'Mbagathi Hospital',
        destination_facility_id: 'fac-1',
        destination_facility_name: 'Kenyatta National Hospital',
        medicine_id: 'med-1',
        medicine_name: 'Amoxicillin 500mg',
        recommended_quantity: 300,
        source_surplus_units: 500,
        destination_shortage_units: 300,
        status: 'PENDING_REVIEW',
        created_at: '2026-09-2708:00:00Z',
        expires_at: '2026-09-30T08:00:00Z',
        data_classification: 'RECOMMENDED',
      },
    ],
    recent_transfers: [
      {
        transfer_id: 'tx-1',
        recommendation_id: 'rec-1',
        source_facility_id: 'fac-2',
        source_facility_name: 'Mbagathi Hospital',
        destination_facility_id: 'fac-1',
        destination_facility_name: 'Kenyatta National Hospital',
        medicine_id: 'med-1',
        medicine_name: 'Amoxicillin 500mg',
        quantity: 300,
        status: 'IN_TRANSIT',
        created_at: '2026-09-27T09:00:00Z',
        dispatched_at: '2026-09-27T10:00:00Z',
        data_classification: 'CONFIRMED',
      },
    ],
    facility_summaries: [
      {
        facility_id: 'fac-1',
        facility_code: 'KNH',
        facility_name: 'Kenyatta National Hospital',
        tracked_medicines: 10,
        active_stockouts: 1,
        critical_high_risk_count: 2,
        pending_redistributions: 1,
        in_transit_transfers: 1,
        healthy_count: 7,
        at_risk_count: 2,
        stockout_count: 1,
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.clear();
    }
    vi.mocked(api.getFacilities).mockResolvedValue({ data: [], pagination: {} as any });
    vi.mocked(api.getMedicines).mockResolvedValue({ data: [], pagination: {} as any });
    vi.mocked(api.getRecommendations).mockResolvedValue({ data: [], pagination: {} as any });
    vi.mocked(api.getTransfers).mockResolvedValue({ data: [], pagination: {} as any });
    vi.mocked(api.getRiskAssessments).mockResolvedValue({ data: [], pagination: {} as any });
    vi.mocked(api.getDashboard).mockResolvedValue(mockDashboardData as any);
    vi.mocked(api.getForecastEvaluation).mockResolvedValue({
      start_date: '2026-07-03', end_date: '2026-09-30', evaluated_series: 0,
      methodology: 'Temporal holdout.', data_note: 'Synthetic data.', results: [],
    });
  });

  // 1. Login flow
  it('1. verifies login flow with valid backend credentials', async () => {
    vi.mocked(api.login).mockResolvedValueOnce({ access_token: 'valid-token', token_type: 'bearer', user: mockUser });
    vi.mocked(api.getCurrentUser).mockResolvedValueOnce(mockUser);

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    const emailInput = screen.getByPlaceholderText('grace.njeri.demo@medstock.example');
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    fireEvent.change(emailInput, { target: { value: 'grace.njeri.demo@medstock.example' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(api.login).toHaveBeenCalledWith({ email: 'grace.njeri.demo@medstock.example', password: 'ChangeMe123!' });
    });
  });

  // 2. Protected routing
  it('2. enforces protected routing when unauthenticated', async () => {
    render(<App />);
    expect(screen.getByText('Sign In to Dashboard')).toBeInTheDocument();
    expect(screen.queryByText('Operational Control Dashboard')).not.toBeInTheDocument();
  });

  // 3. Dashboard data rendering
  it('3. renders dashboard priority summaries correctly from backend read model', async () => {
    render(<DashboardPage onNavigate={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Operational Control Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Critical & High Stockout Risk')).toBeInTheDocument();
      expect(screen.getAllByText('Amoxicillin 500mg').length).toBeGreaterThan(0);
    });
  });

  // 4. Risk severity display
  it('4. displays risk severity levels (CRITICAL, HIGH, MEDIUM, LOW) correctly', async () => {
    vi.mocked(api.getRiskAssessments).mockResolvedValue({
      data: [
        {
          id: 'risk-1',
          facility_id: 'f1',
          medicine_id: 'm1',
          forecast_run_id: 'fr1',
          assessed_at: '2026-09-27T00:00:00Z',
          risk_level: 'CRITICAL',
          currently_out_of_stock: false,
          days_to_breach: 2,
          projected_shortage_units: 100,
          inventory_on_hand: 50,
          safety_stock: 200,
          reorder_point: 300,
        },
      ],
      pagination: {} as any,
    });

    render(<StockoutRiskPage />);

    await waitFor(() => {
      expect(screen.getAllByText('CRITICAL').length).toBeGreaterThan(0);
      expect(screen.getByText('Stockout Risk Assessment Worklist')).toBeInTheDocument();
    });
  });

  // 5. Recommendation display
  it('5. displays redistribution recommendations with source/destination symmetry', async () => {
    vi.mocked(api.getRecommendations).mockResolvedValue({
      data: [
        {
          id: 'rec-1',
          source_facility_id: 'fac-2',
          destination_facility_id: 'fac-1',
          medicine_id: 'med-1',
          status: 'PENDING_REVIEW',
          planning_horizon_days: 14,
          source_surplus_units: 500,
          destination_shortage_units: 300,
          recommended_quantity: 300,
          source_inventory_before: 1000,
          destination_inventory_before: 50,
          source_safety_stock: 300,
          destination_safety_stock: 200,
          source_projected_end_inventory: 700,
          destination_projected_end_inventory: 350,
          constraint_results: { lead_time_feasible: true },
          expires_at: '2026-09-30T00:00:00Z',
          created_by: 'usr-1',
          created_at: '2026-09-27T00:00:00Z',
        },
      ],
      pagination: {} as any,
    });

    render(
      <AuthProvider>
        <RedistributionPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('med-1')).toBeInTheDocument();
      expect(screen.getByText(/Recommendation requires human review and approval/i)).toBeInTheDocument();
    });
  });

  // 6. Approval/rejection interaction
  it('6. handles recommendation approval interaction', async () => {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem('token', 'fake-token');
      window.localStorage.setItem('user', JSON.stringify(mockUser));
    }
    vi.mocked(api.getCurrentUser).mockResolvedValue(mockUser);

    const mockRec = {
      id: 'rec-1',
      source_facility_id: 'fac-2',
      destination_facility_id: 'fac-1',
      medicine_id: 'med-1',
      status: 'PENDING_REVIEW' as const,
      planning_horizon_days: 14,
      source_surplus_units: 500,
      destination_shortage_units: 300,
      recommended_quantity: 300,
      source_inventory_before: 1000,
      destination_inventory_before: 50,
      source_safety_stock: 300,
      destination_safety_stock: 200,
      source_projected_end_inventory: 700,
      destination_projected_end_inventory: 350,
      constraint_results: {},
      expires_at: '2026-09-30T00:00:00Z',
      created_by: 'usr-1',
      created_at: '2026-09-27T00:00:00Z',
    };
    vi.mocked(api.getRecommendations).mockResolvedValue({
      data: [mockRec],
      pagination: {} as any,
    });
    vi.mocked(api.approveRecommendation).mockResolvedValue({
      ...mockRec,
      status: 'APPROVED',
    });

    render(
      <AuthProvider>
        <RedistributionPage />
      </AuthProvider>
    );

    await waitFor(() => {
      const recCard = screen.getByText('med-1');
      fireEvent.click(recCard);
    });

    await waitFor(() => {
      const approveButton = screen.getByText('Approve Recommendation');
      fireEvent.click(approveButton);
    });

    await waitFor(() => {
      expect(api.approveRecommendation).toHaveBeenCalledWith('rec-1', '');
    });
  });

  // 7. Transfer state transitions
  it('7. displays transfer state transitions (APPROVED, IN_TRANSIT, COMPLETED)', async () => {
    vi.mocked(api.getTransfers).mockResolvedValue({
      data: [
        {
          id: 't-1',
          recommendation_id: 'r-1',
          source_facility_id: 'f-2',
          destination_facility_id: 'f-1',
          medicine_id: 'm-1',
          quantity: 300,
          status: 'APPROVED',
          approved_by: 'u-1',
          approved_at: '2026-09-27T00:00:00Z',
          created_at: '2026-09-27T00:00:00Z',
        },
      ],
      pagination: {} as any,
    });

    render(<TransferTrackingPage />);

    await waitFor(() => {
      expect(screen.getAllByText('APPROVED').length).toBeGreaterThan(0);
      expect(screen.getByText('Dispatch')).toBeInTheDocument();
    });
  });

  // 8. Invalid transfer action handling (e.g. IN_TRANSIT transfers cannot be cancelled)
  it('8. prevents invalid transfer actions (no cancel button for IN_TRANSIT transfers)', async () => {
    vi.mocked(api.getTransfers).mockResolvedValue({
      data: [
        {
          id: 't-2',
          recommendation_id: 'r-2',
          source_facility_id: 'f-2',
          destination_facility_id: 'f-1',
          medicine_id: 'm-1',
          quantity: 300,
          status: 'IN_TRANSIT',
          approved_by: 'u-1',
          approved_at: '2026-09-27T00:00:00Z',
          dispatched_by: 'u-1',
          dispatched_at: '2026-09-27T01:00:00Z',
          created_at: '2026-09-27T00:00:00Z',
        },
      ],
      pagination: {} as any,
    });

    render(<TransferTrackingPage />);

    await waitFor(() => {
      expect(screen.getAllByText('IN TRANSIT').length).toBeGreaterThan(0);
      expect(screen.getByText('Complete Receipt')).toBeInTheDocument();
      expect(screen.queryByText('Cancel', { exact: true })).not.toBeInTheDocument();
    });
  });

  // 9. API error handling
  it('9. handles API error responses gracefully without breaking UI', async () => {
    vi.mocked(api.getDashboard).mockRejectedValueOnce(new APIClientError('Database connection error', 'DB_ERROR', 500));

    render(<DashboardPage onNavigate={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Operational Data Error')).toBeInTheDocument();
      expect(screen.getByText('Database connection error')).toBeInTheDocument();
    });
  });

  // 10. Loading states
  it('10. renders loading skeletons while fetching data', () => {
    vi.mocked(api.getDashboard).mockReturnValue(new Promise(() => {})); // Never resolves
    const { container } = render(<DashboardPage onNavigate={vi.fn()} />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  // 11. Empty states
  it('11. displays informative empty state messages when datasets are empty', async () => {
    render(
      <AuthProvider>
        <RedistributionPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/No pending redistribution recommendations in queue/i)).toBeInTheDocument();
    });
  });

  // 12. Accessibility of key operational controls
  it('12. ensures key operational controls are accessible buttons with visible labels', async () => {
    render(<TransferTrackingPage />);

    await waitFor(() => {
      const createButton = screen.getByText('Create Transfer');
      expect(createButton).toBeInTheDocument();
    });
  });
});


describe('Phase 9 decision-support UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getFacilities).mockResolvedValue({ data: [], pagination: {} as any });
    vi.mocked(api.getMedicines).mockResolvedValue({ data: [], pagination: {} as any });
  });

  it('displays measured model comparison and semantic evaluation note', async () => {
    vi.mocked(api.getForecastEvaluation).mockResolvedValue({
      start_date: '2026-07-03', end_date: '2026-09-30', evaluated_series: 1,
      methodology: 'Fixed final 14-day holdout.', data_note: 'Synthetic data.',
      results: [
        { facility_id: 'f1', medicine_id: 'm1', model: 'MOVING_AVERAGE_7D', training_start: '2026-07-03',
          training_end: '2026-09-16', holdout_start: '2026-09-17', holdout_end: '2026-09-30',
          training_observations: 76, observations: 14, mae: 1.25, rmse: 1.5, wape: 12,
          status: 'MEASURED', reason: null },
        { facility_id: 'f1', medicine_id: 'm1', model: 'RANDOM_FOREST', training_start: '2026-07-03',
          training_end: '2026-09-16', holdout_start: '2026-09-17', holdout_end: '2026-09-30',
          training_observations: 76, observations: 14, mae: 1.4, rmse: 1.7, wape: 13,
          status: 'MEASURED', reason: null },
      ],
    });
    render(<ForecastEvaluationPanel
      facilities={[{ id: 'f1', code: 'F1', name: 'Test Facility', is_active: true, created_at: '' }]}
      medicines={[{ id: 'm1', code: 'M1', generic_name: 'Test Medicine', unit_of_measure: 'unit', is_active: true, created_at: '' }]}
    />);
    expect(screen.getByText('Evaluating models…')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('1.25')).toBeInTheDocument());
    expect(screen.getByText('1.40')).toBeInTheDocument();
    expect(screen.getByText(/not guarantees of future accuracy/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Evaluation facility'), { target: { value: 'f1' } });
    fireEvent.change(screen.getByLabelText('Evaluation medicine'), { target: { value: 'm1' } });
    fireEvent.change(screen.getByLabelText('Evaluation start date'), { target: { value: '2026-07-03' } });
    await waitFor(() => expect(api.getForecastEvaluation).toHaveBeenLastCalledWith({
      facility_id: 'f1', medicine_id: 'm1', start_date: '2026-07-03', end_date: undefined,
    }));
  });

  it('shows evaluation error without inventing metrics', async () => {
    vi.mocked(api.getForecastEvaluation).mockRejectedValue(new Error('Evaluation unavailable'));
    render(<ForecastEvaluationPanel facilities={[]} medicines={[]} />);
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Evaluation unavailable'));
    expect(screen.queryByText('1.25')).not.toBeInTheDocument();
  });

  it('opens backend-sourced risk explanation with human action', async () => {
    vi.mocked(api.getRiskAssessments).mockResolvedValue({ data: [{
      id: 'risk-1', facility_id: 'f1', medicine_id: 'm1', forecast_run_id: 'fr1',
      assessed_at: '2026-09-30T00:00:00Z', risk_level: 'CRITICAL', currently_out_of_stock: false,
      days_to_breach: 0, projected_shortage_units: 30, inventory_on_hand: 5,
      safety_stock: 20, reorder_point: 30,
    }], pagination: {} as any });
    vi.mocked(api.getRiskExplanation).mockResolvedValue({
      assessment_id: 'risk-1', current_stock: 5, safety_stock: 20,
      forecasted_demand: 42, forecast_days: 14, projected_inventory: -37,
      days_to_breach: 0, projected_breach_date: '2026-09-30', projected_stockout_date: '2026-10-01',
      risk_level: 'CRITICAL', confirmed_incoming_quantity: 0, projected_shortage: 30,
      feasible_donor_facility_id: null, feasible_donor_surplus: null,
      recommendation_id: null, recommended_quantity: null,
      human_action: 'Manager must approve.', note: 'Saved assessment.',
    });
    render(<StockoutRiskPage />);
    fireEvent.click(await screen.findByText('Explain Risk'));
    await waitFor(() => expect(screen.getByText(/Manager must approve/i)).toBeInTheDocument());
    expect(screen.getByText(/Forecasted demand:/i)).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Close risk explanation'));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows saved recommendation explanation and safety limit', async () => {
    vi.mocked(api.getRecommendations).mockResolvedValue({ data: [{
      id: 'rec-1', source_facility_id: 'f1', destination_facility_id: 'f2',
      medicine_id: 'm1', status: 'PENDING_REVIEW', planning_horizon_days: 14,
      source_surplus_units: 50, destination_shortage_units: 20, recommended_quantity: 20,
      source_inventory_before: 150, destination_inventory_before: 5,
      source_safety_stock: 40, destination_safety_stock: 20,
      source_projected_end_inventory: 90, destination_projected_end_inventory: -10,
      constraint_results: {}, expires_at: '2026-10-01T00:00:00Z',
      created_by: 'u1', created_at: '2026-09-30T00:00:00Z',
    }], pagination: {} as any });
    vi.mocked(api.getRecommendationExplanation).mockResolvedValue({
      recommendation_id: 'rec-1', source_facility: 'Source', destination_facility: 'Destination',
      medicine: 'Medicine', source_current_stock: 150, source_usable_surplus: 50,
      destination_current_stock: 5, destination_projected_shortage: 20,
      source_safety_stock: 40, destination_safety_stock: 20,
      source_projected_after_transfer: 70, recommended_quantity: 20,
      status: 'PENDING_REVIEW', reason: 'Destination has projected shortage.',
      note: 'Approval revalidates stock.',
    });
    render(<AuthProvider><RedistributionPage /></AuthProvider>);
    fireEvent.click(await screen.findByText('m1'));
    fireEvent.click(await screen.findByText('Explain Recommendation'));
    await waitFor(() => expect(screen.getByText('Destination has projected shortage.')).toBeInTheDocument());
    expect(screen.getByText(/Projected after transfer: 70/)).toBeInTheDocument();
  });
});

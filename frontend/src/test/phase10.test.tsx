import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { ScenarioAnalysisPage } from '../pages/ScenarioAnalysisPage';
import { AggregateEvaluationPanel } from '../components/common/AggregateEvaluationPanel';
import { api } from '../api/client';

vi.mock('../api/client',()=>({api:{getFacilities:vi.fn(),getMedicines:vi.fn(),simulateScenario:vi.fn(),replayScenario:vi.fn(),getAggregateEvaluation:vi.fn(),runAggregateEvaluation:vi.fn()}}));
vi.mock('recharts',()=>({ResponsiveContainer:({children}: {children:React.ReactNode})=><div>{children}</div>,LineChart:()=>null,Line:()=>null,CartesianGrid:()=>null,XAxis:()=>null,YAxis:()=>null,Tooltip:()=>null,Legend:()=>null}));
const outcome={daily_demand:5,current_stock:100,days_to_breach:null,risk_level:'LOW',projected_shortage:0,incoming_quantity:0,feasible_donor:null,recommended_quantity:0,redistribution_feasible:false,trajectory:[]};
const result={id:'scenario-1',created_at:'2026-10-02T12:00:00Z',fingerprint:'hash',label:'SIMULATION — NOT LIVE INVENTORY',parameters:{demand_adjustment_pct:30,inventory_adjustment_pct:-30,lead_time_adjustment_days:7},context:{assessment_date:'2026-10-02',medicine_name:'Paracetamol 500 mg Tablet',destination:{facility_name:'Mbagathi',forecast_run_id:'run-1'},excluded_donors:[]},baseline:outcome,scenario:{...outcome,daily_demand:6.5,current_stock:70,days_to_breach:8,risk_level:'HIGH',projected_shortage:41,feasible_donor:'Kenyatta',recommended_quantity:41},differences:{daily_demand:1.5,risk_level:'LOW → HIGH',recommended_quantity:41},explanations:['Stock is lower and demand is higher.']};
async function selectInputs() {
  await screen.findByRole('combobox',{name:'Facility'});
  fireEvent.change(screen.getByRole('combobox',{name:'Facility'}),{target:{value:'f'}});
  fireEvent.change(screen.getByRole('combobox',{name:'Medicine'}),{target:{value:'m'}});
}
beforeEach(()=>{cleanup();vi.resetAllMocks();vi.mocked(api.getFacilities).mockResolvedValue({data:[{id:'f',name:'Mbagathi'}]} as never);vi.mocked(api.getMedicines).mockResolvedValue({data:[{id:'m',generic_name:'Paracetamol',strength:'500 mg',dosage_form:'Tablet'}]} as never);});
describe('Phase 10 scenario analysis',()=>{
  it('shows controls loading and disables incomplete submissions',async()=>{
    render(<ScenarioAnalysisPage/>);expect(screen.getByRole('status')).toHaveTextContent('Loading scenario controls');
    await screen.findByRole('combobox',{name:'Facility'});expect(screen.getByRole('button',{name:'Apply scenario'})).toBeDisabled();
    expect(screen.getByText('SIMULATION — NOT LIVE INVENTORY')).toBeInTheDocument();
  });
  it('sends selected assumptions and renders baseline, scenario, classifications and metadata',async()=>{
    vi.mocked(api.simulateScenario).mockResolvedValue(result as never);
    render(<ScenarioAnalysisPage/>);await selectInputs();
    fireEvent.change(screen.getByLabelText('Demand adjustment'),{target:{value:'30'}});
    fireEvent.change(screen.getByLabelText('Inventory adjustment'),{target:{value:'-30'}});
    fireEvent.change(screen.getByLabelText('Delivery delay'),{target:{value:'7'}});
    fireEvent.click(screen.getByRole('button',{name:'Apply scenario'}));
    expect(api.simulateScenario).toHaveBeenCalledWith({facility_id:'f',medicine_id:'m',demand_adjustment_pct:30,inventory_adjustment_pct:-30,lead_time_adjustment_days:7,horizon_days:14});
    expect(await screen.findByText('Baseline versus scenario')).toBeInTheDocument();
    expect(screen.getByText('LOW')).toBeInTheDocument();expect(screen.getByText('HIGH')).toBeInTheDocument();
    expect(screen.getByText('LOW → HIGH')).toBeInTheDocument();expect(screen.getAllByText('RECOMMENDED').length).toBe(2);
    expect(screen.getAllByText('PREDICTED').length).toBeGreaterThan(0);expect(screen.getByText(/Scenario: scenario-1/)).toBeInTheDocument();
    expect(screen.getByText('Stock is lower and demand is higher.')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Demand adjustment'),{target:{value:'10'}});
    expect(screen.queryByText('Baseline versus scenario')).not.toBeInTheDocument();
  });
  it('shows pending calculation and prevents duplicate submissions',async()=>{
    let finish!: (value: never)=>void;
    vi.mocked(api.simulateScenario).mockReturnValue(new Promise(resolve=>{finish=resolve;}));
    render(<ScenarioAnalysisPage/>);await selectInputs();fireEvent.click(screen.getByText('Apply scenario'));
    expect(screen.getByRole('status')).toHaveTextContent('Calculating baseline and scenario');
    expect(screen.getByRole('button',{name:'Calculating…'})).toBeDisabled();finish(result as never);
    await screen.findByText('Baseline versus scenario');
  });
  it('renders backend validation errors without inventing results',async()=>{
    vi.mocked(api.simulateScenario).mockRejectedValue(new Error('Forecast is stale. Generate a current forecast first.'));
    render(<ScenarioAnalysisPage/>);await selectInputs();fireEvent.click(screen.getByText('Apply scenario'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Forecast is stale');
    expect(screen.queryByText('Baseline versus scenario')).not.toBeInTheDocument();
  });
  it('replays saved inputs through the backend',async()=>{
    vi.mocked(api.simulateScenario).mockResolvedValue(result as never);vi.mocked(api.replayScenario).mockResolvedValue(result as never);
    render(<ScenarioAnalysisPage/>);await selectInputs();fireEvent.click(screen.getByText('Apply scenario'));
    fireEvent.click(await screen.findByText('Replay saved inputs'));await waitFor(()=>expect(api.replayScenario).toHaveBeenCalledWith('scenario-1'));
  });
  it('shows directory loading failures',async()=>{
    vi.mocked(api.getFacilities).mockRejectedValue(new Error('Directory unavailable'));
    render(<ScenarioAnalysisPage/>);expect(await screen.findByRole('alert')).toHaveTextContent('Directory unavailable');
  });
});
describe('Aggregate evaluation',()=>{
  it('shows insufficient or absent evaluation without metrics',async()=>{
    vi.mocked(api.getAggregateEvaluation).mockResolvedValue(null);
    render(<AggregateEvaluationPanel/>);await screen.findByText(/No aggregate evaluation saved/);
    expect(screen.queryByText('Random Forest')).not.toBeInTheDocument();
  });
  it('groups backend metrics by facility without ranking models',async()=>{
    const metrics=[{model:'RANDOM_FOREST',evaluated_series:1,observations:14,mae:1,rmse:2,wape:10}];
    vi.mocked(api.getAggregateEvaluation).mockResolvedValue({id:'eval',created_at:'2026-10-02',fingerprint:'hash',parameters:{start_date:'2024-10-03',end_date:'2026-10-02'},overall:metrics,by_facility:[{id:'f',name:'Mbagathi',metrics}],by_medicine:[],series_count:1,methodology:'Temporal holdout',data_note:'Synthetic'});
    render(<AggregateEvaluationPanel/>);await screen.findByText('Random Forest');
    fireEvent.change(screen.getByLabelText('Evaluation grouping'),{target:{value:'facility'}});
    expect(screen.getByText('Mbagathi')).toBeInTheDocument();expect(screen.getByText('14')).toBeInTheDocument();
    expect(screen.queryByText(/best model/i)).not.toBeInTheDocument();
  });
});

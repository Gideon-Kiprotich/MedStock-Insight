import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor, cleanup } from '@testing-library/react';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { api } from '../api/client';
import { consumptionChartPoints } from '../utils/consumption';

vi.mock('../api/client', () => ({api: {login: vi.fn(), getCurrentUser: vi.fn()}}));
function Probe() {
  const {isAuthenticated, login} = useAuth();
  return <><p>{isAuthenticated ? 'Authorized' : 'Anonymous'}</p><button onClick={() => void login('demo@test.example','unused-test-input').catch(() => {})}>Login</button></>;
}
beforeEach(() => {cleanup(); localStorage.clear(); vi.resetAllMocks();});
describe('Phase 11 truthfulness and authentication', () => {
  it('ignores corrupted cached identity and verifies the token with the backend', async () => {
    localStorage.setItem('user','{broken'); localStorage.setItem('token','expired');
    vi.mocked(api.getCurrentUser).mockRejectedValue(new Error('Expired'));
    render(<AuthProvider><Probe/></AuthProvider>);
    await waitFor(() => expect(localStorage.getItem('token')).toBeNull());
    expect(screen.getByText('Anonymous')).toBeInTheDocument();
  });
  it('does not retain a login token when identity verification fails', async () => {
    vi.mocked(api.login).mockResolvedValue({access_token:'test-token',token_type:'bearer'});
    vi.mocked(api.getCurrentUser).mockRejectedValue(new Error('Unavailable'));
    render(<AuthProvider><Probe/></AuthProvider>); fireEvent.click(screen.getByText('Login'));
    await waitFor(() => expect(api.getCurrentUser).toHaveBeenCalledOnce());
    await waitFor(() => expect(localStorage.getItem('token')).toBeNull());
    expect(screen.getByText('Anonymous')).toBeInTheDocument();
  });
  it('verifies the user once per successful login', async () => {
    vi.mocked(api.login).mockResolvedValue({access_token:'test-token',token_type:'bearer'});
    vi.mocked(api.getCurrentUser).mockResolvedValue({id:'test',role:{code:'ADMINISTRATOR'}} as never);
    render(<AuthProvider><Probe/></AuthProvider>);fireEvent.click(screen.getByText('Login'));
    await screen.findByText('Authorized'); expect(api.getCurrentUser).toHaveBeenCalledOnce();
  });
  it('charts consumption only, aggregates dates and does not invent missing dates', () => {
    const rows = [{transaction_date:'2026-10-01',transaction_type:'RECEIPT',quantity:'100'},
      {transaction_date:'2026-10-02',transaction_type:'CONSUMPTION',quantity:'2'},
      {transaction_date:'2026-10-02',transaction_type:'CONSUMPTION',quantity:'3'},
      {transaction_date:'2026-10-03',transaction_type:'TRANSFER_OUT',quantity:'50'}];
    expect(consumptionChartPoints(rows as never)).toEqual([{date:'2026-10-02',value:5,type:'Recorded consumption'}]);
  });
});

import type { InventoryTransaction } from '../types/api';

// Show only observed consumption from the loaded ledger page. Missing dates are unknown.
export function consumptionChartPoints(transactions: InventoryTransaction[]) {
  const daily = new Map<string, number>();
  for (const transaction of transactions) {
    if (transaction.transaction_type === 'CONSUMPTION') {
      daily.set(transaction.transaction_date, (daily.get(transaction.transaction_date) || 0) + Number(transaction.quantity));
    }
  }
  return [...daily].sort(([a], [b]) => a.localeCompare(b)).slice(-7)
    .map(([date, value]) => ({ date, value, type: 'Recorded consumption' }));
}

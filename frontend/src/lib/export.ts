import type { Position, Trade } from '@/types';

/**
 * Convert data to CSV string
 */
function toCSV<T extends object>(
  data: T[],
  columns: { key: keyof T; header: string }[]
): string {
  const headers = columns.map((c) => c.header).join(',');
  const rows = data.map((row) =>
    columns
      .map((c) => {
        const value = row[c.key];
        // Escape quotes and wrap in quotes if contains comma
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value ?? '';
      })
      .join(',')
  );
  return [headers, ...rows].join('\n');
}

/**
 * Download a string as a file
 */
function downloadFile(content: string, filename: string, mimeType = 'text/csv') {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export positions to CSV
 */
export function exportPositionsToCSV(positions: Position[]): void {
  const columns: { key: keyof Position; header: string }[] = [
    { key: 'symbol', header: 'Symbol' },
    { key: 'quantity', header: 'Quantity' },
    { key: 'avg_cost', header: 'Avg Cost' },
    { key: 'current_price', header: 'Current Price' },
    { key: 'market_value', header: 'Market Value' },
    { key: 'unrealized_pnl', header: 'Unrealized P&L' },
    { key: 'unrealized_pnl_pct', header: 'Unrealized P&L %' },
    { key: 'sector', header: 'Sector' },
  ];

  const csv = toCSV(positions, columns);
  const date = new Date().toISOString().split('T')[0];
  downloadFile(csv, `positions_${date}.csv`);
}

/**
 * Export trades to CSV
 */
export function exportTradesToCSV(trades: Trade[]): void {
  const columns: { key: keyof Trade; header: string }[] = [
    { key: 'executed_at', header: 'Date' },
    { key: 'symbol', header: 'Symbol' },
    { key: 'side', header: 'Side' },
    { key: 'quantity', header: 'Quantity' },
    { key: 'price', header: 'Price' },
  ];

  // Add computed total column
  const dataWithTotal = trades.map((trade) => ({
    ...trade,
    total: trade.quantity * trade.price,
  }));

  const columnsWithTotal = [
    ...columns,
    { key: 'total' as keyof typeof dataWithTotal[0], header: 'Total' },
  ];

  const csv = toCSV(dataWithTotal, columnsWithTotal as any);
  const date = new Date().toISOString().split('T')[0];
  downloadFile(csv, `trades_${date}.csv`);
}


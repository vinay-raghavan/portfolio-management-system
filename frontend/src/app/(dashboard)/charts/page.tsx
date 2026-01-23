'use client';

import { MultiChartLayout } from '@/components/charts';

export default function ChartsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Multi-Chart View</h1>
        <p className="text-muted-foreground">Monitor multiple instruments simultaneously</p>
      </div>

      <MultiChartLayout
        defaultSymbols={['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META']}
      />
    </div>
  );
}


'use client';

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Grid2x2, GitCompare } from 'lucide-react';
import { MultiChartLayout, ComparisonChart } from '@/components/charts';

export default function ChartsPage() {
  const [activeTab, setActiveTab] = useState('multi');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Charts & Comparison</h1>
        <p className="text-muted-foreground">Monitor multiple instruments and compare performance</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="multi" className="flex items-center gap-2">
            <Grid2x2 className="h-4 w-4" />
            Multi-Chart View
          </TabsTrigger>
          <TabsTrigger value="compare" className="flex items-center gap-2">
            <GitCompare className="h-4 w-4" />
            Symbol Comparison
          </TabsTrigger>
        </TabsList>

        <TabsContent value="multi" className="mt-4">
          <MultiChartLayout
            defaultSymbols={['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN']}
          />
        </TabsContent>

        <TabsContent value="compare" className="mt-4">
          <ComparisonChart
            initialSymbols={['RELIANCE', 'TCS', 'INFY']}
            height={500}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}


'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Search, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  UniverseSelector,
  FilterBuilder,
  ScreenerResults,
  PresetSelector,
  SavedScreenersList,
  type UniverseType,
} from '@/components/screener';
import {
  screenerApi,
  type FilterConfig,
  type ScreenerPresetType,
  type ScreenerResultItem,
  type CustomScreener,
} from '@/lib/api';
import { useNotificationStore, useTradingStore } from '@/store';
import { useRouter } from 'next/navigation';

export default function ScreenerPage() {
  const router = useRouter();
  const { addNotification } = useNotificationStore();
  const { quickBuy, quickSell } = useTradingStore();

  // State
  const [universe, setUniverse] = useState<UniverseType>('NIFTY500');
  const [filters, setFilters] = useState<FilterConfig[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<ScreenerPresetType | null>(null);
  const [results, setResults] = useState<ScreenerResultItem[]>([]);
  const [totalScreened, setTotalScreened] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [activeTab, setActiveTab] = useState<'custom' | 'preset'>('preset');

  // Run custom screener
  const runCustomMutation = useMutation({
    mutationFn: () =>
      screenerApi.runScreener({
        universe,
        filters,
        min_score: 0.5,
        top_n: 50,
      }),
    onSuccess: (res) => {
      setResults(res.data.results);
      setTotalScreened(res.data.total_screened);
      setDuration(res.data.duration_ms);
      addNotification({ type: 'success', title: 'Screener Complete', message: `Found ${res.data.passed_count} stocks` });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Screener Failed',
        message: error.response?.data?.detail || 'Failed to run screener',
      });
    },
  });

  // Run preset screener
  const runPresetMutation = useMutation({
    mutationFn: (preset: ScreenerPresetType) =>
      screenerApi.runPreset({
        preset,
        universe,
        min_score: 0.5,
        top_n: 50,
      }),
    onSuccess: (res) => {
      setResults(res.data.results);
      setTotalScreened(res.data.total_screened);
      setDuration(res.data.duration_ms);
      addNotification({ type: 'success', title: 'Screener Complete', message: `Found ${res.data.passed_count} stocks` });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Screener Failed',
        message: error.response?.data?.detail || 'Failed to run screener',
      });
    },
  });

  const handlePresetSelect = (preset: ScreenerPresetType) => {
    setSelectedPreset(preset);
    runPresetMutation.mutate(preset);
  };

  const handleRunCustom = () => {
    if (filters.length === 0) {
      addNotification({ type: 'warning', title: 'No Filters', message: 'Add at least one filter before running' });
      return;
    }
    runCustomMutation.mutate();
  };

  const handleRunSavedScreener = (screener: CustomScreener) => {
    screenerApi
      .runCustomScreener(screener.id)
      .then((res) => {
        setResults(res.data.results);
        setTotalScreened(res.data.total_screened);
        setDuration(res.data.duration_ms);
        addNotification({ type: 'success', title: 'Screener Complete', message: `Found ${res.data.passed_count} stocks` });
      })
      .catch((error) => {
        addNotification({ type: 'error', title: 'Error', message: error.response?.data?.detail || 'Failed to run screener' });
      });
  };

  const handleLoadScreener = (screener: CustomScreener) => {
    setFilters(screener.filters);
    setUniverse(screener.universe as UniverseType);
    setActiveTab('custom');
    addNotification({ type: 'info', title: 'Screener Loaded', message: `Loaded "${screener.name}"` });
  };

  const handleAddToWatchlist = (symbol: string) => {
    addNotification({ type: 'info', title: 'Coming Soon', message: `Add ${symbol} to watchlist from quick action` });
  };

  const handleViewChart = (symbol: string) => {
    router.push(`/charts?symbol=${symbol}`);
  };

  const handleQuickTrade = (symbol: string, side: 'buy' | 'sell') => {
    if (side === 'buy') {
      quickBuy(symbol);
    } else {
      quickSell(symbol);
    }
  };

  // Create universe mutation
  const createUniverseMutation = useMutation({
    mutationFn: (data: { name: string; description?: string; symbols: string[]; screenerConfig?: object; isDynamic: boolean }) =>
      screenerApi.createUniverse({
        name: data.name,
        description: data.description,
        symbols: data.symbols,
        screener_config: data.screenerConfig,
        is_dynamic: data.isDynamic,
      }),
    onSuccess: (res) => {
      addNotification({
        type: 'success',
        title: 'Universe Created',
        message: `Created universe "${res.data.name}" with ${res.data.symbol_count} symbols`,
      });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to Create Universe',
        message: error.response?.data?.detail || 'Could not create universe',
      });
    },
  });

  const handleCreateUniverse = (data: { name: string; description?: string; symbols: string[]; screenerConfig?: object; isDynamic: boolean }) => {
    createUniverseMutation.mutate(data);
  };

  // Build current screener config for dynamic universe support
  const currentScreenerConfig = activeTab === 'preset' && selectedPreset
    ? { universe, preset: selectedPreset, min_score: 0.5, top_n: 50 }
    : { universe, filters, min_score: 0.5, top_n: 50 };

  const isLoading = runCustomMutation.isPending || runPresetMutation.isPending;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Search className="h-8 w-8" />
            Stock Screener
          </h1>
          <p className="text-muted-foreground">Discover stocks matching your criteria</p>
        </div>
        <UniverseSelector value={universe} onChange={setUniverse} disabled={isLoading} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* Sidebar */}
        <div className="space-y-4">
          <SavedScreenersList
            currentFilters={filters}
            currentUniverse={universe}
            onRunScreener={handleRunSavedScreener}
            onLoadScreener={handleLoadScreener}
          />
        </div>

        {/* Main Content */}
        <div className="space-y-4">
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'custom' | 'preset')}>
            <TabsList>
              <TabsTrigger value="preset">Quick Presets</TabsTrigger>
              <TabsTrigger value="custom">Custom Filters</TabsTrigger>
            </TabsList>

            <TabsContent value="preset" className="mt-4">
              <PresetSelector selectedPreset={selectedPreset} onSelect={handlePresetSelect} isLoading={isLoading} />
            </TabsContent>

            <TabsContent value="custom" className="mt-4 space-y-4">
              <FilterBuilder filters={filters} onChange={setFilters} disabled={isLoading} />
              <Button onClick={handleRunCustom} disabled={isLoading || filters.length === 0} className="w-full">
                <Play className="h-4 w-4 mr-2" />
                {isLoading ? 'Running...' : 'Run Screener'}
              </Button>
            </TabsContent>
          </Tabs>

          <ScreenerResults
            results={results}
            isLoading={isLoading}
            totalScreened={totalScreened}
            duration={duration}
            screenerConfig={currentScreenerConfig}
            onAddToWatchlist={handleAddToWatchlist}
            onViewChart={handleViewChart}
            onQuickTrade={handleQuickTrade}
            onCreateUniverse={handleCreateUniverse}
          />
        </div>
      </div>
    </div>
  );
}


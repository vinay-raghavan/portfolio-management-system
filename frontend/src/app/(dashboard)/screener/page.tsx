'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import {
  ScreenerConfig,
  ScreenerResults,
  SavedScreenersList,
  PerformanceWidget,
  type UniverseType,
} from '@/components/screener';
import {
  screenerApi,
  type FilterConfig,
  type ScreenerPresetType,
  type ScreenerResultItem,
  type CustomScreener,
  type StrictnessLevel,
  type InferStrategyResponse,
} from '@/lib/api';
import { useNotificationStore, useTradingStore, useUIStore } from '@/store';
import { useRouter } from 'next/navigation';

export default function ScreenerPage() {
  const router = useRouter();
  const { addNotification } = useNotificationStore();
  const { quickBuy, quickSell } = useTradingStore();
  const { setSelectedSymbol } = useUIStore();

  // State - Default to 'Nifty 50' which is the seeded universe name
  const [universe, setUniverse] = useState<UniverseType>('Nifty 50');
  const [filters, setFilters] = useState<FilterConfig[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<ScreenerPresetType | null>(null);
  const [strictness, setStrictness] = useState<StrictnessLevel>('moderate');
  const [results, setResults] = useState<ScreenerResultItem[]>([]);
  const [totalScreened, setTotalScreened] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [mode, setMode] = useState<'preset' | 'custom'>('preset');

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

  // Run preset screener with strictness
  const runPresetMutation = useMutation({
    mutationFn: ({ preset, level }: { preset: ScreenerPresetType; level: StrictnessLevel }) =>
      screenerApi.runPreset({
        preset,
        universe,
        strictness: level,
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
    runPresetMutation.mutate({ preset, level: strictness });
  };

  const handleStrictnessChange = (level: StrictnessLevel) => {
    setStrictness(level);
    // Re-run with new strictness if a preset is already selected
    if (selectedPreset) {
      runPresetMutation.mutate({ preset: selectedPreset, level });
    }
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
    setMode('custom');
    addNotification({ type: 'info', title: 'Screener Loaded', message: `Loaded "${screener.name}"` });
  };

  const handleAddToWatchlist = (symbol: string) => {
    addNotification({ type: 'info', title: 'Coming Soon', message: `Add ${symbol} to watchlist from quick action` });
  };

  const handleViewChart = (symbol: string) => {
    setSelectedSymbol(symbol);
    router.push('/analysis');
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

  // Strategy inference mutation
  const inferStrategyMutation = useMutation({
    mutationFn: (request: { filters?: FilterConfig[]; preset?: string }) =>
      screenerApi.inferStrategy(request),
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Inference Failed',
        message: error.response?.data?.detail || 'Could not analyze filters',
      });
    },
  });

  const handleInferStrategy = async (): Promise<InferStrategyResponse | null> => {
    try {
      // For preset mode, pass the preset name; for custom mode, pass filters
      if (mode === 'preset' && selectedPreset) {
        const res = await inferStrategyMutation.mutateAsync({ preset: selectedPreset });
        return res.data;
      } else if (mode === 'custom' && filters.length > 0) {
        const res = await inferStrategyMutation.mutateAsync({ filters });
        return res.data;
      } else {
        addNotification({
          type: 'warning',
          title: 'No Configuration',
          message: mode === 'preset'
            ? 'Please select a preset first.'
            : 'Please add custom filters first.',
        });
        return null;
      }
    } catch {
      return null;
    }
  };

  // Create smart strategy mutation
  const createSmartStrategyMutation = useMutation({
    mutationFn: (data: {
      name: string;
      strategyType: string;
      params: Record<string, unknown>;
      productType: 'DELIVERY' | 'INTRADAY' | 'MARGIN';
      symbols: string[];
      filters?: FilterConfig[];
      preset?: string;
      isDynamic: boolean;
      screenerConfig?: Record<string, unknown>;
    }) =>
      screenerApi.createSmartStrategy({
        name: data.name,
        symbols: data.symbols,
        filters: data.filters,
        preset: data.preset,
        strategy_type_override: data.strategyType,
        strategy_params_override: data.params,
        product_type: data.productType,
        is_dynamic_universe: data.isDynamic,
        screener_config: data.screenerConfig,
      }),
    onSuccess: (res) => {
      addNotification({
        type: 'success',
        title: 'Strategy Created',
        message: `Created "${res.data.strategy_name}" with ${res.data.symbol_count} symbols using ${res.data.inferred_strategy_type} strategy`,
      });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to Create Strategy',
        message: error.response?.data?.detail || 'Could not create strategy',
      });
    },
  });

  const handleCreateSmartStrategy = (data: {
    name: string;
    strategyType: string;
    params: Record<string, unknown>;
    productType: 'DELIVERY' | 'INTRADAY' | 'MARGIN';
    symbols: string[];
    filters?: FilterConfig[];
    preset?: string;
    isDynamic: boolean;
    screenerConfig?: Record<string, unknown>;
  }) => {
    createSmartStrategyMutation.mutate(data);
  };

  // Build current screener config for dynamic universe support
  const currentScreenerConfig = mode === 'preset' && selectedPreset
    ? { universe, preset: selectedPreset, min_score: 0.5, top_n: 50 }
    : { universe, filters, min_score: 0.5, top_n: 50 };

  const isLoading = runCustomMutation.isPending || runPresetMutation.isPending;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Search className="h-8 w-8" />
          Stock Screener
        </h1>
        <p className="text-muted-foreground">Discover stocks matching your criteria</p>
      </div>

      {/* Main Layout */}
      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        {/* Main Content */}
        <div className="space-y-4">
          <ScreenerConfig
            universe={universe}
            onUniverseChange={setUniverse}
            mode={mode}
            onModeChange={setMode}
            selectedPreset={selectedPreset}
            onSelectPreset={handlePresetSelect}
            strictness={strictness}
            onStrictnessChange={handleStrictnessChange}
            filters={filters}
            onFiltersChange={setFilters}
            onRunCustom={handleRunCustom}
            isLoading={isLoading}
          />

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
            onInferStrategy={handleInferStrategy}
            onCreateSmartStrategy={handleCreateSmartStrategy}
            isInferring={inferStrategyMutation.isPending}
            isCreatingStrategy={createSmartStrategyMutation.isPending}
          />
        </div>

        {/* Sidebar - moved to right */}
        <div className="space-y-4 lg:order-last">
          <SavedScreenersList
            currentFilters={filters}
            currentUniverse={universe}
            onRunScreener={handleRunSavedScreener}
            onLoadScreener={handleLoadScreener}
          />
          <PerformanceWidget days={30} compact />
        </div>
      </div>
    </div>
  );
}


'use client';

import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useQueries } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, Activity, Settings2, Check } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { marketDataApi } from '@/lib/api';
import { formatPercent, cn } from '@/lib/utils';
import { useUIStore, AVAILABLE_INDICES } from '@/store';

interface IndexQuote {
  symbol: string;
  name: string;
  price: number | null;
  change: number | null;
  changePct: number | null;
  isLoading: boolean;
  error: boolean;
}

export function MarketOverview() {
  const [mounted, setMounted] = useState(false);
  const router = useRouter();
  const { selectedMarketIndices, toggleMarketIndex, setSelectedSymbol } = useUIStore();

  const handleNavigateToAnalysis = (symbol: string) => {
    setSelectedSymbol(symbol);
    router.push('/analysis');
  };

  // Prevent hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);

  // Get the selected indices from the store - stable reference for useQueries
  const selectedIndices = useMemo(() => {
    if (!mounted) {
      return AVAILABLE_INDICES.slice(0, 4); // Show first 4 during SSR
    }
    return AVAILABLE_INDICES.filter((idx) => selectedMarketIndices.includes(idx.symbol));
  }, [mounted, selectedMarketIndices]);

  // Fetch quotes for selected indices using useQueries (handles dynamic arrays)
  const queryResults = useQueries({
    queries: selectedIndices.map((index) => ({
      queryKey: ['quote', index.symbol],
      queryFn: () => marketDataApi.getQuote(index.symbol).then((res) => res.data),
      refetchInterval: 60000, // Refresh every minute
      staleTime: 30000,
      retry: 1,
    })),
  });

  const indices: IndexQuote[] = selectedIndices.map((idx, i) => ({
    symbol: idx.symbol,
    name: idx.name,
    price: queryResults[i]?.data?.price ?? null,
    change: queryResults[i]?.data?.change ?? null,
    changePct: queryResults[i]?.data?.change_pct ?? null,
    isLoading: queryResults[i]?.isLoading ?? true,
    error: !!queryResults[i]?.error,
  }));

  // Group available indices by market
  const indianIndices = AVAILABLE_INDICES.filter((idx) => idx.market === 'IN');
  const usIndices = AVAILABLE_INDICES.filter((idx) => idx.market === 'US');

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity className="h-4 w-4" />
            Market Overview
          </CardTitle>
          {mounted && (
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="ghost" size="icon" className="h-7 w-7">
                  <Settings2 className="h-4 w-4" />
                  <span className="sr-only">Select indices</span>
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-64" align="end">
                <div className="space-y-4">
                  <div className="font-medium text-sm">Select Indices to Monitor</div>

                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-2">
                      Indian Markets
                    </div>
                    <div className="space-y-1">
                      {indianIndices.map((idx) => (
                        <button
                          key={idx.symbol}
                          onClick={() => toggleMarketIndex(idx.symbol)}
                          className={cn(
                            'flex items-center justify-between w-full px-2 py-1.5 text-sm rounded-md hover:bg-muted transition-colors',
                            selectedMarketIndices.includes(idx.symbol) && 'bg-muted'
                          )}
                        >
                          <span>{idx.name}</span>
                          {selectedMarketIndices.includes(idx.symbol) && (
                            <Check className="h-4 w-4 text-primary" />
                          )}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-2">
                      US Markets
                    </div>
                    <div className="space-y-1">
                      {usIndices.map((idx) => (
                        <button
                          key={idx.symbol}
                          onClick={() => toggleMarketIndex(idx.symbol)}
                          className={cn(
                            'flex items-center justify-between w-full px-2 py-1.5 text-sm rounded-md hover:bg-muted transition-colors',
                            selectedMarketIndices.includes(idx.symbol) && 'bg-muted'
                          )}
                        >
                          <span>{idx.name}</span>
                          {selectedMarketIndices.includes(idx.symbol) && (
                            <Check className="h-4 w-4 text-primary" />
                          )}
                        </button>
                      ))}
                    </div>
                  </div>

                  {selectedMarketIndices.length === 0 && (
                    <p className="text-xs text-muted-foreground text-center py-2">
                      Select at least one index to display
                    </p>
                  )}
                </div>
              </PopoverContent>
            </Popover>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {indices.length === 0 ? (
          <div className="text-center py-6 text-muted-foreground">
            <p className="text-sm">No indices selected</p>
            <p className="text-xs mt-1">Click the settings icon to add indices</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {indices.map((index) => (
              <button
                key={index.symbol}
                onClick={() => handleNavigateToAnalysis(index.symbol)}
                className="p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors cursor-pointer text-left"
              >
                {index.isLoading ? (
                  <div className="animate-pulse space-y-2">
                    <div className="h-4 w-20 bg-muted rounded" />
                    <div className="h-5 w-24 bg-muted rounded" />
                  </div>
                ) : index.error ? (
                  <div className="text-sm text-muted-foreground">
                    <div className="font-medium">{index.name}</div>
                    <div className="text-xs">Unable to load</div>
                  </div>
                ) : (
                  <>
                    <div className="text-sm text-muted-foreground mb-1">
                      {index.name}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold">
                        {index.price !== null
                          ? index.price.toLocaleString(undefined, { maximumFractionDigits: 2 })
                          : '--'}
                      </span>
                      {index.changePct !== null && (
                        <span
                          className={cn(
                            'flex items-center gap-1 text-sm font-medium',
                            index.changePct >= 0 ? 'text-profit' : 'text-loss'
                          )}
                        >
                          {index.changePct >= 0 ? (
                            <TrendingUp className="h-3 w-3" />
                          ) : (
                            <TrendingDown className="h-3 w-3" />
                          )}
                          {formatPercent(index.changePct)}
                        </span>
                      )}
                    </div>
                  </>
                )}
              </button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}


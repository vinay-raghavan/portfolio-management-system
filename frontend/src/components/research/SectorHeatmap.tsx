'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { TrendingUp, TrendingDown, BarChart3, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';
import { researchApi } from '@/lib/api';
import { cn } from '@/lib/utils';
import type { SectorPerformance, SectorStock } from '@/types';

type Timeframe = '1D' | '1W' | '1M' | '3M' | '1Y';

interface SectorHeatmapProps {
  className?: string;
  compact?: boolean;
}

export function SectorHeatmap({ className, compact = false }: SectorHeatmapProps) {
  const [timeframe, setTimeframe] = useState<Timeframe>('1D');
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  // Fetch sectors
  const { data: sectorsData, isLoading, error, refetch } = useQuery({
    queryKey: ['research-sectors', timeframe],
    queryFn: () => researchApi.getSectors(),
    staleTime: 5 * 60 * 1000,
  });

  // Fetch sector stocks when a sector is selected
  const { data: sectorStocksData, isLoading: stocksLoading } = useQuery({
    queryKey: ['research-sector-stocks', selectedSector],
    queryFn: () => researchApi.getSectorStocks(selectedSector!),
    enabled: !!selectedSector,
    staleTime: 5 * 60 * 1000,
  });

  const sectors = sectorsData?.data?.sectors || [];

  const handleSectorClick = (sector: string) => {
    setSelectedSector(sector);
    setSheetOpen(true);
  };

  // Get the change value based on selected timeframe
  const getChangeForTimeframe = (sector: SectorPerformance): number | null => {
    switch (timeframe) {
      case '1D': return sector.change_1d ?? null;
      case '1W': return sector.change_1w ?? null;
      case '1M': return sector.change_1m ?? null;
      case '3M': return sector.change_3m ?? null;
      case '1Y': return sector.change_1y ?? null;
      default: return sector.change_1d ?? null;
    }
  };

  // Sort sectors and get top 3 gainers and bottom 3 losers
  const { topGainers, topLosers, remainingSectors } = useMemo(() => {
    if (!sectors.length) return { topGainers: [], topLosers: [], remainingSectors: [] };

    // Sort by change percentage for the selected timeframe
    const sortedSectors = [...sectors].sort((a, b) => {
      const aChange = getChangeForTimeframe(a) ?? 0;
      const bChange = getChangeForTimeframe(b) ?? 0;
      return bChange - aChange; // Descending order
    });

    // Get top 3 gainers (positive change)
    const gainers = sortedSectors.filter(s => (getChangeForTimeframe(s) ?? 0) > 0).slice(0, 3);

    // Get bottom 3 losers (negative change)
    const losers = sortedSectors.filter(s => (getChangeForTimeframe(s) ?? 0) < 0).slice(-3).reverse();

    // Remaining sectors (excluding top 3 and bottom 3)
    const topGainerNames = new Set(gainers.map(s => s.sector));
    const topLoserNames = new Set(losers.map(s => s.sector));
    const remaining = sortedSectors.filter(
      s => !topGainerNames.has(s.sector) && !topLoserNames.has(s.sector)
    );

    return {
      topGainers: gainers,
      topLosers: losers,
      remainingSectors: remaining,
    };
  }, [sectors, timeframe]);

  const getColorClass = (changePct: number | null): string => {
    if (changePct == null) return 'bg-gray-200 text-gray-700';
    if (changePct >= 3) return 'bg-green-600 text-white';
    if (changePct >= 2) return 'bg-green-500 text-white';
    if (changePct >= 1) return 'bg-green-400 text-white';
    if (changePct >= 0.5) return 'bg-green-300 text-green-900';
    if (changePct > 0) return 'bg-green-200 text-green-900';
    if (changePct === 0) return 'bg-gray-200 text-gray-700';
    if (changePct > -0.5) return 'bg-red-200 text-red-900';
    if (changePct > -1) return 'bg-red-300 text-red-900';
    if (changePct > -2) return 'bg-red-400 text-white';
    if (changePct > -3) return 'bg-red-500 text-white';
    return 'bg-red-600 text-white';
  };

  const formatPercent = (value: number | null | undefined): string => {
    if (value == null) return '-';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  const formatNumber = (value: number | null | undefined): string => {
    if (value == null) return '-';
    if (value >= 1e12) return `₹${(value / 1e12).toFixed(1)}T`;
    if (value >= 1e9) return `₹${(value / 1e9).toFixed(1)}B`;
    if (value >= 1e7) return `₹${(value / 1e7).toFixed(1)}Cr`;
    if (value >= 1e5) return `₹${(value / 1e5).toFixed(1)}L`;
    return `₹${value.toLocaleString()}`;
  };

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <div className="text-center text-muted-foreground">
            Failed to load sector data
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card className={className}>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Sector Heatmap
          </CardTitle>
          <div className="flex items-center gap-2">
            {/* Timeframe Toggle */}
            <div className="flex rounded-md border">
              {(['1D', '1W', '1M', '3M', '1Y'] as Timeframe[]).map((tf) => (
                <Button
                  key={tf}
                  variant={timeframe === tf ? 'default' : 'ghost'}
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={() => setTimeframe(tf)}
                >
                  {tf}
                </Button>
              ))}
            </div>
            <Button variant="ghost" size="icon" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : (
            <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
              {/* Summary View: Top 3 Gainers + Bottom 3 Losers */}
              <div className="space-y-4">
                {/* Top Gainers & Losers Row */}
                <div className={cn(
                  'grid gap-2',
                  compact ? 'grid-cols-3' : 'grid-cols-3 md:grid-cols-6'
                )}>
                  {/* Top 3 Gainers */}
                  {topGainers.map((sector: SectorPerformance) => {
                    const changePct = getChangeForTimeframe(sector);
                    return (
                      <button
                        key={sector.sector}
                        onClick={() => handleSectorClick(sector.sector)}
                        className={cn(
                          'p-3 rounded-lg transition-all hover:scale-105 cursor-pointer text-left',
                          getColorClass(changePct)
                        )}
                      >
                        <div className="font-medium text-sm truncate">{sector.sector}</div>
                        <div className="flex items-center gap-1 mt-1">
                          <TrendingUp className="h-3 w-3" />
                          <span className="text-sm font-bold">
                            {formatPercent(changePct)}
                          </span>
                        </div>
                        {!compact && (
                          <div className="text-xs opacity-80 mt-1">
                            {sector.stock_count} stocks
                          </div>
                        )}
                      </button>
                    );
                  })}

                  {/* Bottom 3 Losers */}
                  {topLosers.map((sector: SectorPerformance) => {
                    const changePct = getChangeForTimeframe(sector);
                    return (
                      <button
                        key={sector.sector}
                        onClick={() => handleSectorClick(sector.sector)}
                        className={cn(
                          'p-3 rounded-lg transition-all hover:scale-105 cursor-pointer text-left',
                          getColorClass(changePct)
                        )}
                      >
                        <div className="font-medium text-sm truncate">{sector.sector}</div>
                        <div className="flex items-center gap-1 mt-1">
                          <TrendingDown className="h-3 w-3" />
                          <span className="text-sm font-bold">
                            {formatPercent(changePct)}
                          </span>
                        </div>
                        {!compact && (
                          <div className="text-xs opacity-80 mt-1">
                            {sector.stock_count} stocks
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>

                {/* Expand/Collapse Button */}
                {remainingSectors.length > 0 && (
                  <CollapsibleTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full flex items-center justify-center gap-1 text-muted-foreground hover:text-foreground"
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp className="h-4 w-4" />
                          Show Less
                        </>
                      ) : (
                        <>
                          <ChevronDown className="h-4 w-4" />
                          Show All {sectors.length} Sectors
                        </>
                      )}
                    </Button>
                  </CollapsibleTrigger>
                )}

                {/* Expanded Content: All Remaining Sectors */}
                <CollapsibleContent>
                  <div className={cn(
                    'grid gap-2 pt-2',
                    compact ? 'grid-cols-3' : 'grid-cols-3 md:grid-cols-4 lg:grid-cols-5'
                  )}>
                    {remainingSectors.map((sector: SectorPerformance) => {
                      const changePct = getChangeForTimeframe(sector);
                      return (
                        <button
                          key={sector.sector}
                          onClick={() => handleSectorClick(sector.sector)}
                          className={cn(
                            'p-3 rounded-lg transition-all hover:scale-105 cursor-pointer text-left',
                            getColorClass(changePct)
                          )}
                        >
                          <div className="font-medium text-sm truncate">{sector.sector}</div>
                          <div className="flex items-center gap-1 mt-1">
                            {(changePct ?? 0) >= 0 ? (
                              <TrendingUp className="h-3 w-3" />
                            ) : (
                              <TrendingDown className="h-3 w-3" />
                            )}
                            <span className="text-sm font-bold">
                              {formatPercent(changePct)}
                            </span>
                          </div>
                          {!compact && (
                            <div className="text-xs opacity-80 mt-1">
                              {sector.stock_count} stocks
                            </div>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </CollapsibleContent>
              </div>
            </Collapsible>
          )}
        </CardContent>
      </Card>

      {/* Sector Drill-down Sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="w-[600px] sm:max-w-[600px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              {selectedSector} Stocks
            </SheetTitle>
          </SheetHeader>
          <div className="mt-4">
            {stocksLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 10 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead className="text-right">Price</TableHead>
                    <TableHead className="text-right">Change %</TableHead>
                    <TableHead className="text-right">Volume</TableHead>
                    <TableHead className="text-right">Market Cap</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(sectorStocksData?.data?.stocks || []).map((stock: SectorStock) => (
                    <TableRow key={stock.symbol}>
                      <TableCell className="font-medium">{stock.symbol}</TableCell>
                      <TableCell className="max-w-[150px] truncate">
                        {stock.name}
                      </TableCell>
                      <TableCell className="text-right">
                        ₹{stock.close.toFixed(2)}
                      </TableCell>
                      <TableCell className={cn(
                        'text-right font-medium',
                        stock.change_pct >= 0 ? 'text-green-600' : 'text-red-600'
                      )}>
                        {formatPercent(stock.change_pct)}
                      </TableCell>
                      <TableCell className="text-right">
                        {stock.volume?.toLocaleString() || '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatNumber(stock.market_cap)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
            {sectorStocksData?.data?.total_count === 0 && !stocksLoading && (
              <div className="text-center text-muted-foreground py-8">
                No stocks found in this sector
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}

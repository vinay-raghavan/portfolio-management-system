'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ChevronDown, ChevronUp, Filter, TrendingUp, TrendingDown } from 'lucide-react';
import { researchApi } from '@/lib/api';
import { cn, formatNumber, formatPercent } from '@/lib/utils';
import type { UniverseStock, UniverseFilterParams } from '@/types';

const UNIVERSES = ['NIFTY50', 'NIFTYNEXT50', 'BANKNIFTY', 'NIFTYIT', 'NIFTYPHARMA', 'NIFTYAUTO', 'NIFTYFMCG'];

interface FundamentalScreenerProps {
  compact?: boolean;
}

export function FundamentalScreener({ compact = false }: FundamentalScreenerProps) {
  const [universe, setUniverse] = useState('NIFTY50');
  const [filters, setFilters] = useState<UniverseFilterParams>({});
  const [showFilters, setShowFilters] = useState(false);
  const [sortField, setSortField] = useState<string>('fundamental_score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const { data, isLoading, error } = useQuery({
    queryKey: ['universe-research', universe, filters],
    queryFn: () => researchApi.getUniverseResearch(universe, filters),
    staleTime: 5 * 60 * 1000,
  });

  const stocks = data?.data?.stocks || [];

  // Sort stocks
  const sortedStocks = [...stocks].sort((a, b) => {
    const aVal = a[sortField as keyof UniverseStock] ?? 0;
    const bVal = b[sortField as keyof UniverseStock] ?? 0;
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
    }
    return 0;
  });

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const SortIcon = ({ field }: { field: string }) => {
    if (sortField !== field) return null;
    return sortDir === 'asc' ? (
      <ChevronUp className="h-4 w-4 inline" />
    ) : (
      <ChevronDown className="h-4 w-4 inline" />
    );
  };

  const getScoreColor = (score: number | null | undefined) => {
    if (!score) return 'text-muted-foreground';
    if (score >= 75) return 'text-green-600 font-semibold';
    if (score >= 60) return 'text-green-500';
    if (score >= 40) return 'text-yellow-600';
    return 'text-red-500';
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Fundamental Screener
            </CardTitle>
            <CardDescription>Screen stocks by fundamental metrics</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Select value={universe} onValueChange={setUniverse}>
              <SelectTrigger className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {UNIVERSES.map((u) => (
                  <SelectItem key={u} value={u}>
                    {u}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter className="h-4 w-4 mr-1" />
              Filters
            </Button>
          </div>
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4 p-3 bg-muted/50 rounded-lg">
            <div>
              <label className="text-xs text-muted-foreground">Max P/E</label>
              <Input
                type="number"
                placeholder="e.g., 25"
                value={filters.max_pe || ''}
                onChange={(e) => setFilters({ ...filters, max_pe: e.target.value ? Number(e.target.value) : undefined })}
                className="h-8"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Min ROE %</label>
              <Input
                type="number"
                placeholder="e.g., 15"
                value={filters.min_roe || ''}
                onChange={(e) => setFilters({ ...filters, min_roe: e.target.value ? Number(e.target.value) : undefined })}
                className="h-8"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Max Debt/Eq</label>
              <Input
                type="number"
                placeholder="e.g., 1"
                value={filters.max_debt || ''}
                onChange={(e) => setFilters({ ...filters, max_debt: e.target.value ? Number(e.target.value) : undefined })}
                className="h-8"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Min Div Yield %</label>
              <Input
                type="number"
                placeholder="e.g., 2"
                value={filters.min_dividend || ''}
                onChange={(e) => setFilters({ ...filters, min_dividend: e.target.value ? Number(e.target.value) : undefined })}
                className="h-8"
              />
            </div>
            <div className="flex items-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setFilters({})}
              >
                Clear
              </Button>
            </div>
          </div>
        )}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: compact ? 5 : 10 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : error ? (
          <div className="text-center text-red-500 py-8">Failed to load data</div>
        ) : sortedStocks.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            No stocks match your criteria
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="cursor-pointer" onClick={() => handleSort('symbol')}>
                    Symbol <SortIcon field="symbol" />
                  </TableHead>
                  <TableHead className="cursor-pointer text-right" onClick={() => handleSort('current_price')}>
                    Price <SortIcon field="current_price" />
                  </TableHead>
                  <TableHead className="cursor-pointer text-right" onClick={() => handleSort('price_change_pct')}>
                    Change <SortIcon field="price_change_pct" />
                  </TableHead>
                  <TableHead className="cursor-pointer text-right" onClick={() => handleSort('pe_ratio')}>
                    P/E <SortIcon field="pe_ratio" />
                  </TableHead>
                  <TableHead className="cursor-pointer text-right" onClick={() => handleSort('pb_ratio')}>
                    P/B <SortIcon field="pb_ratio" />
                  </TableHead>
                  <TableHead className="cursor-pointer text-right" onClick={() => handleSort('roe')}>
                    ROE <SortIcon field="roe" />
                  </TableHead>
                  <TableHead className="cursor-pointer text-right" onClick={() => handleSort('debt_to_equity')}>
                    D/E <SortIcon field="debt_to_equity" />
                  </TableHead>
                  <TableHead className="cursor-pointer text-right" onClick={() => handleSort('dividend_yield')}>
                    Div% <SortIcon field="dividend_yield" />
                  </TableHead>
                  <TableHead className="cursor-pointer text-right" onClick={() => handleSort('fundamental_score')}>
                    Score <SortIcon field="fundamental_score" />
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(compact ? sortedStocks.slice(0, 10) : sortedStocks).map((stock) => (
                  <TableRow key={stock.symbol} className="hover:bg-muted/50">
                    <TableCell className="font-medium">
                      <div>
                        <span>{stock.symbol}</span>
                        {stock.sector && (
                          <Badge variant="outline" className="ml-2 text-xs">
                            {stock.sector}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {stock.current_price ? `₹${formatNumber(stock.current_price)}` : '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      {stock.price_change_pct != null ? (
                        <span className={cn(
                          'flex items-center justify-end gap-1',
                          stock.price_change_pct >= 0 ? 'text-green-600' : 'text-red-600'
                        )}>
                          {stock.price_change_pct >= 0 ? (
                            <TrendingUp className="h-3 w-3" />
                          ) : (
                            <TrendingDown className="h-3 w-3" />
                          )}
                          {formatPercent(stock.price_change_pct / 100)}
                        </span>
                      ) : '-'}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {stock.pe_ratio?.toFixed(1) ?? '-'}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {stock.pb_ratio?.toFixed(2) ?? '-'}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {stock.roe ? `${stock.roe.toFixed(1)}%` : '-'}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {stock.debt_to_equity?.toFixed(2) ?? '-'}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {stock.dividend_yield ? `${stock.dividend_yield.toFixed(1)}%` : '-'}
                    </TableCell>
                    <TableCell className={cn('text-right font-semibold', getScoreColor(stock.fundamental_score))}>
                      {stock.fundamental_score?.toFixed(0) ?? '-'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {/* Summary footer */}
        {!isLoading && sortedStocks.length > 0 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t text-sm text-muted-foreground">
            <span>Showing {compact ? Math.min(10, sortedStocks.length) : sortedStocks.length} of {data?.data?.total_count || sortedStocks.length} stocks</span>
            {data?.data?.by_sector && (
              <div className="flex gap-2">
                {Object.entries(data.data.by_sector).slice(0, 3).map(([sector, count]) => (
                  <Badge key={sector} variant="secondary" className="text-xs">
                    {sector}: {count}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}


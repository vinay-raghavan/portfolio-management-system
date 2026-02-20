'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  TrendingDown,
  TrendingUp,
  ChevronLeft,
  ChevronRight,
  Download,
  Calendar,
  PieChart,
} from 'lucide-react';
import { format } from 'date-fns';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
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
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { reportsApi } from '@/lib/api';
import { useCurrency } from '@/hooks/useCurrency';
import { cn } from '@/lib/utils';
import type { TaxType } from '@/types';

// Generate financial year options (current + last 5 years)
const generateFYOptions = () => {
  const options: { value: string; label: string }[] = [];
  const currentDate = new Date();
  const currentYear = currentDate.getFullYear();
  const currentMonth = currentDate.getMonth(); // 0-indexed

  // FY in India runs Apr-Mar. If we're in Jan-Mar, current FY started last year
  const currentFYStart = currentMonth >= 3 ? currentYear : currentYear - 1;

  for (let i = 0; i < 6; i++) {
    const fyStart = currentFYStart - i;
    const fyEnd = (fyStart + 1) % 100;
    options.push({
      value: `${fyStart}-${fyEnd.toString().padStart(2, '0')}`,
      label: `FY ${fyStart}-${fyEnd.toString().padStart(2, '0')}`,
    });
  }
  return options;
};

const FY_OPTIONS = generateFYOptions();
const TAX_TYPES: { value: TaxType | 'ALL'; label: string; color: string }[] = [
  { value: 'ALL', label: 'All', color: '' },
  { value: 'STCG', label: 'Short Term', color: 'bg-amber-500/10 text-amber-600' },
  { value: 'LTCG', label: 'Long Term', color: 'bg-emerald-500/10 text-emerald-600' },
  { value: 'SPECULATIVE', label: 'Speculative', color: 'bg-purple-500/10 text-purple-600' },
];

export default function CapitalGainsPage() {
  const { format: formatCurrency } = useCurrency();
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [financialYear, setFinancialYear] = useState(FY_OPTIONS[0].value);
  const [taxType, setTaxType] = useState<TaxType | 'ALL'>('ALL');
  const [activeTab, setActiveTab] = useState('details');

  // Fetch gains summary
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['gains-summary', financialYear],
    queryFn: () =>
      reportsApi.getGainsSummary({ financial_year: financialYear }).then((res) => res.data),
  });

  // Fetch gains list
  const { data: gainsData, isLoading: gainsLoading } = useQuery({
    queryKey: ['realized-gains', financialYear, taxType, page, pageSize],
    queryFn: () =>
      reportsApi
        .getRealizedGains({
          financial_year: financialYear,
          tax_type: taxType === 'ALL' ? undefined : taxType,
          page,
          page_size: pageSize,
        })
        .then((res) => res.data),
  });

  // Fetch gains by symbol
  const { data: bySymbolData, isLoading: bySymbolLoading } = useQuery({
    queryKey: ['gains-by-symbol', financialYear],
    queryFn: () =>
      reportsApi.getGainsBySymbol({ financial_year: financialYear }).then((res) => res.data),
    enabled: activeTab === 'by-symbol',
  });

  const gains = gainsData?.gains ?? [];
  const totalCount = gainsData?.total ?? 0;
  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  const formatDate = (dateString: string) => {
    return format(new Date(dateString), 'MMM dd, yyyy');
  };

  const getTaxTypeColor = (type: string) => {
    const t = TAX_TYPES.find((x) => x.value === type);
    return t?.color ?? '';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <TrendingDown className="h-8 w-8 text-amber-500" />
            Capital Gains Report
          </h1>
          <p className="text-muted-foreground">
            Tax report with STCG/LTCG breakdown for ITR filing
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={financialYear} onValueChange={(v) => {
            setFinancialYear(v);
            setPage(1);
          }}>
            <SelectTrigger className="w-[140px]">
              <Calendar className="h-4 w-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FY_OPTIONS.map((fy) => (
                <SelectItem key={fy.value} value={fy.value}>
                  {fy.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" disabled>
            <Download className="h-4 w-4 mr-2" />
            Export for ITR
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Net Gain/Loss</CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <p className={cn(
                "text-2xl font-bold",
                (summary?.net_gain_loss ?? 0) >= 0 ? "text-emerald-600" : "text-red-600"
              )}>
                {formatCurrency(summary?.net_gain_loss ?? 0)}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Badge variant="outline" className="bg-amber-500/10 text-amber-600">STCG</Badge>
              Short Term
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <div>
                <p className={cn(
                  "text-xl font-bold",
                  (summary?.stcg ?? 0) >= 0 ? "text-emerald-600" : "text-red-600"
                )}>
                  {formatCurrency(summary?.stcg ?? 0)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {summary?.stcg_count ?? 0} trades
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600">LTCG</Badge>
              Long Term
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <div>
                <p className={cn(
                  "text-xl font-bold",
                  (summary?.ltcg ?? 0) >= 0 ? "text-emerald-600" : "text-red-600"
                )}>
                  {formatCurrency(summary?.ltcg ?? 0)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {summary?.ltcg_count ?? 0} trades
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Badge variant="outline" className="bg-purple-500/10 text-purple-600">SPEC</Badge>
              Speculative
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <div>
                <p className={cn(
                  "text-xl font-bold",
                  (summary?.speculative ?? 0) >= 0 ? "text-emerald-600" : "text-red-600"
                )}>
                  {formatCurrency(summary?.speculative ?? 0)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {summary?.speculative_count ?? 0} trades
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="details">Detailed Gains</TabsTrigger>
          <TabsTrigger value="by-symbol">By Symbol</TabsTrigger>
        </TabsList>

        <TabsContent value="details" className="space-y-4">
          {/* Filter by Tax Type */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Filter:</span>
            {TAX_TYPES.map((t) => (
              <Button
                key={t.value}
                variant={taxType === t.value ? 'default' : 'outline'}
                size="sm"
                onClick={() => {
                  setTaxType(t.value);
                  setPage(1);
                }}
              >
                {t.label}
              </Button>
            ))}
          </div>

          {/* Gains Table */}
          <Card>
            <CardHeader>
              <CardTitle>Realized Gains ({totalCount})</CardTitle>
              <CardDescription>Individual sale transactions with gain/loss</CardDescription>
            </CardHeader>
            <CardContent>
              {gainsLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : gains.length === 0 ? (
                <p className="text-muted-foreground text-center py-8">
                  No realized gains for this period
                </p>
              ) : (
                <>
                  <div className="rounded-md border overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Symbol</TableHead>
                          <TableHead>Buy Date</TableHead>
                          <TableHead>Sell Date</TableHead>
                          <TableHead>Days</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead className="text-right">Qty</TableHead>
                          <TableHead className="text-right">Cost</TableHead>
                          <TableHead className="text-right">Proceeds</TableHead>
                          <TableHead className="text-right">Gain/Loss</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {gains.map((gain) => (
                          <TableRow key={gain.id}>
                            <TableCell className="font-medium">{gain.symbol}</TableCell>
                            <TableCell>{formatDate(gain.purchase_date)}</TableCell>
                            <TableCell>{formatDate(gain.sale_date)}</TableCell>
                            <TableCell>{gain.holding_days}</TableCell>
                            <TableCell>
                              <Badge variant="outline" className={getTaxTypeColor(gain.tax_type)}>
                                {gain.tax_type}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">{gain.quantity}</TableCell>
                            <TableCell className="text-right">{formatCurrency(gain.cost_basis)}</TableCell>
                            <TableCell className="text-right">{formatCurrency(gain.sale_proceeds)}</TableCell>
                            <TableCell className={cn(
                              "text-right font-medium",
                              gain.gain_loss >= 0 ? "text-emerald-600" : "text-red-600"
                            )}>
                              {gain.gain_loss >= 0 ? '+' : ''}{formatCurrency(gain.gain_loss)}
                              <span className="text-xs text-muted-foreground ml-1">
                                ({gain.gain_loss_pct >= 0 ? '+' : ''}{gain.gain_loss_pct.toFixed(1)}%)
                              </span>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  {/* Pagination */}
                  <div className="flex items-center justify-between mt-4">
                    <p className="text-sm text-muted-foreground">
                      Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, totalCount)} of {totalCount}
                    </p>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={page === 1}
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </Button>
                      <span className="text-sm">Page {page} of {totalPages}</span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="by-symbol">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PieChart className="h-5 w-5" />
                Gains by Symbol
              </CardTitle>
              <CardDescription>Aggregated gains/losses per stock</CardDescription>
            </CardHeader>
            <CardContent>
              {bySymbolLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : (bySymbolData?.gains?.length ?? 0) === 0 ? (
                <p className="text-muted-foreground text-center py-8">
                  No gains data for this period
                </p>
              ) : (
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Symbol</TableHead>
                        <TableHead className="text-right">Trades</TableHead>
                        <TableHead className="text-right">Quantity</TableHead>
                        <TableHead className="text-right">Total Gain/Loss</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {bySymbolData?.gains?.map((item) => (
                        <TableRow key={item.symbol}>
                          <TableCell className="font-medium">{item.symbol}</TableCell>
                          <TableCell className="text-right">{item.trade_count}</TableCell>
                          <TableCell className="text-right">{item.total_quantity}</TableCell>
                          <TableCell className={cn(
                            "text-right font-medium",
                            item.total_gain >= 0 ? "text-emerald-600" : "text-red-600"
                          )}>
                            {item.total_gain >= 0 ? '+' : ''}{formatCurrency(item.total_gain)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}


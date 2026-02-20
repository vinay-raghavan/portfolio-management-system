'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Receipt,
  ChevronLeft,
  ChevronRight,
  Download,
  Filter,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import { format, subDays } from 'date-fns';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { reportsApi } from '@/lib/api';
import { useCurrency } from '@/hooks/useCurrency';
import { cn } from '@/lib/utils';
import type { TransactionType } from '@/types';

const TRANSACTION_TYPES: { value: TransactionType | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'All Types' },
  { value: 'DEPOSIT', label: 'Deposit' },
  { value: 'WITHDRAWAL', label: 'Withdrawal' },
  { value: 'BUY', label: 'Buy' },
  { value: 'SELL', label: 'Sell' },
  { value: 'DIVIDEND', label: 'Dividend' },
  { value: 'FEE', label: 'Fee' },
  { value: 'TAX', label: 'Tax' },
  { value: 'INTEREST', label: 'Interest' },
];

export default function StatementPage() {
  const { format: formatCurrency } = useCurrency();
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [transactionType, setTransactionType] = useState<TransactionType | 'ALL'>('ALL');
  const [symbol, setSymbol] = useState('');
  const [startDate, setStartDate] = useState(
    format(subDays(new Date(), 30), 'yyyy-MM-dd')
  );
  const [endDate, setEndDate] = useState(format(new Date(), 'yyyy-MM-dd'));

  const { data, isLoading } = useQuery({
    queryKey: ['ledger', page, pageSize, transactionType, symbol, startDate, endDate],
    queryFn: () =>
      reportsApi
        .getLedger({
          page,
          page_size: pageSize,
          transaction_type: transactionType === 'ALL' ? undefined : transactionType,
          symbol: symbol || undefined,
          start_date: startDate ? `${startDate}T00:00:00` : undefined,
          end_date: endDate ? `${endDate}T23:59:59` : undefined,
        })
        .then((res) => res.data),
  });

  const entries = data?.entries ?? [];
  const totalCount = data?.total_count ?? 0;
  const totalPages = Math.ceil(totalCount / pageSize) || 1;
  const totalIn = data?.total_in ?? 0;
  const totalOut = data?.total_out ?? 0;

  const formatDate = (dateString: string) => {
    return format(new Date(dateString), 'MMM dd, yyyy HH:mm');
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'DEPOSIT':
      case 'SELL':
      case 'DIVIDEND':
      case 'INTEREST':
        return 'text-emerald-600 bg-emerald-500/10';
      case 'WITHDRAWAL':
      case 'BUY':
      case 'FEE':
      case 'TAX':
        return 'text-red-600 bg-red-500/10';
      default:
        return 'text-muted-foreground bg-muted';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Receipt className="h-8 w-8 text-blue-500" />
          Account Statement
        </h1>
        <p className="text-muted-foreground">
          Transaction ledger with filtering and export
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <ArrowUpRight className="h-4 w-4 text-emerald-500" />
              Total In
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <p className="text-2xl font-bold text-emerald-600">
                +{formatCurrency(totalIn)}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <ArrowDownRight className="h-4 w-4 text-red-500" />
              Total Out
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <p className="text-2xl font-bold text-red-600">
                -{formatCurrency(totalOut)}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Net Change</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <p className={cn(
                "text-2xl font-bold",
                totalIn - totalOut >= 0 ? "text-emerald-600" : "text-red-600"
              )}>
                {formatCurrency(totalIn - totalOut)}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-2">
              <Label>Start Date</Label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => {
                  setStartDate(e.target.value);
                  setPage(1);
                }}
              />
            </div>
            <div className="space-y-2">
              <Label>End Date</Label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => {
                  setEndDate(e.target.value);
                  setPage(1);
                }}
              />
            </div>
            <div className="space-y-2">
              <Label>Transaction Type</Label>
              <Select
                value={transactionType}
                onValueChange={(v) => {
                  setTransactionType(v as TransactionType | 'ALL');
                  setPage(1);
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TRANSACTION_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Symbol</Label>
              <Input
                placeholder="e.g., RELIANCE"
                value={symbol}
                onChange={(e) => {
                  setSymbol(e.target.value.toUpperCase());
                  setPage(1);
                }}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Ledger Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Transactions ({totalCount})</CardTitle>
            <CardDescription>All account transactions</CardDescription>
          </div>
          <Button variant="outline" size="sm" disabled>
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : entries.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No transactions found
            </p>
          ) : (
            <>
              <div className="rounded-md border overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Symbol</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead className="text-right">Balance</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {entries.map((entry) => (
                      <TableRow key={entry.id}>
                        <TableCell className="whitespace-nowrap">
                          {formatDate(entry.transaction_date)}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className={cn(getTypeColor(entry.transaction_type))}>
                            {entry.transaction_type}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate">
                          {entry.description}
                        </TableCell>
                        <TableCell>{entry.symbol || '-'}</TableCell>
                        <TableCell className={cn(
                          "text-right font-medium",
                          entry.amount >= 0 ? "text-emerald-600" : "text-red-600"
                        )}>
                          {entry.amount >= 0 ? '+' : ''}{formatCurrency(entry.amount)}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(entry.running_cash_balance)}
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
                  <span className="text-sm">
                    Page {page} of {totalPages}
                  </span>
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
    </div>
  );
}


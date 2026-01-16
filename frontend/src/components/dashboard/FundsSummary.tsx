'use client';

import { useQuery } from '@tanstack/react-query';
import { Wallet, CreditCard, PiggyBank, ArrowUpRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useCurrency } from '@/hooks/useCurrency';
import { portfolioApi } from '@/lib/api';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export function FundsSummary() {
  const { format: formatCurrency } = useCurrency();

  const { data: funds, isLoading } = useQuery({
    queryKey: ['funds'],
    queryFn: () => portfolioApi.getFunds().then((res) => res.data),
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Wallet className="h-4 w-4 text-emerald-500" />
            Funds
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-8 w-32" />
          <div className="grid grid-cols-2 gap-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const availableCash = funds?.available_cash ?? 0;
  const marginUsed = funds?.margin_used ?? 0;
  const totalBalance = funds?.total_balance ?? 0;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Wallet className="h-4 w-4 text-emerald-500" />
            Funds
          </CardTitle>
          <Button variant="ghost" size="sm" asChild className="h-6 px-2 text-xs">
            <Link href="/portfolio?tab=funds">
              Manage
              <ArrowUpRight className="h-3 w-3 ml-1" />
            </Link>
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Total Balance */}
        <div>
          <p className="text-xs text-muted-foreground">Total Balance</p>
          <p className="text-2xl font-bold">{formatCurrency(totalBalance)}</p>
        </div>

        {/* Available Cash & Margin Used */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-2 rounded-md bg-emerald-500/10">
            <div className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
              <PiggyBank className="h-3 w-3" />
              Available
            </div>
            <p className="text-sm font-semibold mt-1">{formatCurrency(availableCash)}</p>
          </div>
          <div className={cn(
            "p-2 rounded-md",
            marginUsed > 0 ? "bg-amber-500/10" : "bg-muted"
          )}>
            <div className={cn(
              "flex items-center gap-1 text-xs",
              marginUsed > 0 ? "text-amber-600 dark:text-amber-400" : "text-muted-foreground"
            )}>
              <CreditCard className="h-3 w-3" />
              Margin Used
            </div>
            <p className="text-sm font-semibold mt-1">{formatCurrency(marginUsed)}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}


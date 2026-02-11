'use client';

import { useQuery } from '@tanstack/react-query';
import { Wallet, Bot, Briefcase } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { useCurrency } from '@/hooks/useCurrency';
import { portfolioApi, algoApi } from '@/lib/api';
import { cn } from '@/lib/utils';

export function TotalAccountValue() {
  const { format: formatCurrency } = useCurrency();

  const { data: funds, isLoading: fundsLoading } = useQuery({
    queryKey: ['funds'],
    queryFn: () => portfolioApi.getFunds().then((res) => res.data),
    refetchInterval: 30000,
  });

  const { data: portfolio, isLoading: portfolioLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: () => portfolioApi.getPortfolio().then((res) => res.data),
    refetchInterval: 30000,
  });

  const { data: algoPositions, isLoading: algoLoading } = useQuery({
    queryKey: ['algo-positions'],
    queryFn: () => algoApi.getPositions().then((res) => res.data),
    refetchInterval: 30000,
  });

  const isLoading = fundsLoading || portfolioLoading || algoLoading;

  if (isLoading) {
    return (
      <div className="flex items-center gap-2">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-5 w-48" />
      </div>
    );
  }

  const cashBalance = funds?.cash_balance ?? 0;
  const marginUsed = funds?.margin_used ?? 0;
  const totalCash = cashBalance + marginUsed;
  const manualPositionsValue = portfolio?.summary?.total_value ?? 0;

  const algoPositionsValue = algoPositions
    ?.filter((p) => p.status === 'OPEN')
    .reduce((sum, p) => {
      const price = p.current_price ?? p.entry_price;
      return sum + (p.remaining_quantity * price);
    }, 0) ?? 0;

  const totalAccountValue = totalCash + manualPositionsValue + algoPositionsValue;

  const breakdownItems = [
    { label: 'Cash', value: totalCash, icon: Wallet, color: 'text-emerald-600 dark:text-emerald-400' },
    { label: 'Manual', value: manualPositionsValue, icon: Briefcase, color: 'text-blue-600 dark:text-blue-400' },
    { label: 'Algo', value: algoPositionsValue, icon: Bot, color: 'text-purple-600 dark:text-purple-400' },
  ];

  const formatCompact = (value: number) => {
    if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)}Cr`;
    if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
    if (value >= 1000) return `₹${(value / 1000).toFixed(1)}K`;
    return formatCurrency(value);
  };

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold">{formatCurrency(totalAccountValue)}</span>
        <span className="text-sm text-muted-foreground">Total</span>
      </div>
      <div className="flex items-center gap-3 text-sm">
        {breakdownItems.map((item, idx) => (
          <div key={item.label} className="flex items-center gap-1">
            {idx > 0 && <span className="text-muted-foreground/50 mr-2">|</span>}
            <item.icon className={cn('h-3.5 w-3.5', item.color)} />
            <span className="text-muted-foreground">{item.label}</span>
            <span className="font-medium">{formatCompact(item.value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}


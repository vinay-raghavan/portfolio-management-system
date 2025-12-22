'use client';

import { useEffect, useRef, useState } from 'react';
import { TrendingUp, TrendingDown, DollarSign, Briefcase, Wallet } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatPercent, cn } from '@/lib/utils';
import type { PortfolioSummary as PortfolioSummaryType } from '@/types';

interface AnimatedNumberProps {
  value: number;
  format: (value: number) => string;
  className?: string;
}

function AnimatedNumber({ value, format, className }: AnimatedNumberProps) {
  const [displayValue, setDisplayValue] = useState(value);
  const previousValue = useRef(value);

  useEffect(() => {
    const startValue = previousValue.current;
    const endValue = value;
    const duration = 500;
    const startTime = Date.now();

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = startValue + (endValue - startValue) * eased;
      
      setDisplayValue(current);

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        previousValue.current = value;
      }
    };

    requestAnimationFrame(animate);
  }, [value]);

  return <span className={className}>{format(displayValue)}</span>;
}

interface PortfolioSummaryProps {
  summary: PortfolioSummaryType | undefined;
  isLoading?: boolean;
}

export function PortfolioSummary({ summary, isLoading }: PortfolioSummaryProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {[...Array(5)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="pb-2">
              <div className="h-4 w-24 bg-muted rounded" />
            </CardHeader>
            <CardContent>
              <div className="h-8 w-32 bg-muted rounded mb-2" />
              <div className="h-3 w-16 bg-muted rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const dayChange = summary?.day_change ?? 0;
  const dayChangePct = summary?.day_change_pct ?? 0;
  const totalPnl = summary?.total_pnl ?? 0;
  const totalPnlPct = summary?.total_pnl_pct ?? 0;

  const cards = [
    {
      title: 'Total Value',
      value: summary?.total_value ?? 0,
      format: formatCurrency,
      icon: DollarSign,
      iconColor: 'text-blue-500',
    },
    {
      title: "Day's P&L",
      value: dayChange,
      format: formatCurrency,
      subValue: dayChangePct,
      subFormat: formatPercent,
      icon: dayChange >= 0 ? TrendingUp : TrendingDown,
      iconColor: dayChange >= 0 ? 'text-profit' : 'text-loss',
      valueColor: dayChange >= 0 ? 'text-profit' : 'text-loss',
    },
    {
      title: 'Total P&L',
      value: totalPnl,
      format: formatCurrency,
      subValue: totalPnlPct,
      subFormat: formatPercent,
      icon: totalPnl >= 0 ? TrendingUp : TrendingDown,
      iconColor: totalPnl >= 0 ? 'text-profit' : 'text-loss',
      valueColor: totalPnl >= 0 ? 'text-profit' : 'text-loss',
    },
    {
      title: 'Positions',
      value: summary?.positions_count ?? 0,
      format: (v: number) => v.toString(),
      icon: Briefcase,
      iconColor: 'text-purple-500',
    },
    {
      title: 'Cash Balance',
      value: summary?.cash_balance ?? 0,
      format: formatCurrency,
      icon: Wallet,
      iconColor: 'text-emerald-500',
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
      {cards.map((card) => (
        <Card key={card.title} className="relative overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {card.title}
            </CardTitle>
            <card.icon className={cn('h-4 w-4', card.iconColor)} />
          </CardHeader>
          <CardContent>
            <AnimatedNumber
              value={card.value}
              format={card.format}
              className={cn('text-2xl font-bold', card.valueColor)}
            />
            {card.subValue !== undefined && (
              <p className={cn('text-xs mt-1', card.valueColor)}>
                {card.subFormat!(card.subValue)}
              </p>
            )}
          </CardContent>
          {/* Gradient decoration */}
          <div className={cn(
            'absolute bottom-0 left-0 right-0 h-1',
            card.valueColor === 'text-profit' && 'bg-gradient-to-r from-profit/20 to-profit/60',
            card.valueColor === 'text-loss' && 'bg-gradient-to-r from-loss/20 to-loss/60',
            !card.valueColor && 'bg-gradient-to-r from-primary/20 to-primary/60'
          )} />
        </Card>
      ))}
    </div>
  );
}


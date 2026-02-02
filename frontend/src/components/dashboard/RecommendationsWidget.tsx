'use client';

import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { TrendingUp, Zap, BarChart3, Layers, RefreshCw, ExternalLink, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { screenerApi, type RecommendationCategory, type RecommendationItem } from '@/lib/api';
import { useCurrency } from '@/hooks/useCurrency';
import { cn, formatPercent } from '@/lib/utils';

const CATEGORY_CONFIG: Record<RecommendationCategory, { icon: React.ReactNode; color: string }> = {
  momentum: { icon: <TrendingUp className="h-4 w-4" />, color: 'text-green-500' },
  breakout: { icon: <Zap className="h-4 w-4" />, color: 'text-blue-500' },
  pullback: { icon: <BarChart3 className="h-4 w-4" />, color: 'text-purple-500' },
  sector: { icon: <Layers className="h-4 w-4" />, color: 'text-cyan-500' },
};

interface RecommendationRowProps {
  item: RecommendationItem;
  onNavigate: (symbol: string) => void;
}

function RecommendationRow({ item, onNavigate }: RecommendationRowProps) {
  const { format: formatCurrency } = useCurrency();

  return (
    <button
      onClick={() => onNavigate(item.symbol)}
      className="flex items-center justify-between w-full hover:bg-muted/50 rounded-md px-2 py-2 -mx-2 transition-colors cursor-pointer text-left"
    >
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="w-6 h-6 p-0 flex items-center justify-center text-xs">
          {item.rank}
        </Badge>
        <div>
          <span className="font-medium">{item.symbol}</span>
          <p className="text-xs text-muted-foreground truncate max-w-[150px]">{item.reasons[0]}</p>
        </div>
      </div>
      <div className="text-right">
        <div className="text-sm font-medium">{formatCurrency(item.price_at_rec)}</div>
        <div className="flex gap-1 text-xs">
          {item.return_1d !== null && item.return_1d !== undefined && (
            <span className={cn(item.return_1d >= 0 ? 'text-profit' : 'text-loss')}>
              1D: {formatPercent(item.return_1d)}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

export function RecommendationsWidget() {
  const router = useRouter();

  const { data, isLoading, refetch, isFetching, dataUpdatedAt } = useQuery({
    queryKey: ['recommendations'],
    queryFn: () => screenerApi.getRecommendations().then((res) => res.data),
    refetchInterval: 5 * 60 * 1000, // Refresh every 5 minutes
    staleTime: 2 * 60 * 1000, // Consider stale after 2 minutes
  });

  const handleNavigate = (symbol: string) => {
    router.push(`/charts?symbol=${symbol}`);
  };

  const handleViewAll = () => {
    router.push('/screener');
  };

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (isLoading) {
    return (
      <Card className="col-span-full">
        <CardHeader className="pb-2">
          <div className="h-5 w-48 bg-muted rounded animate-pulse" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-muted rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const categories = data?.categories ?? [];

  return (
    <Card className="col-span-full">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Today&apos;s Picks
        </CardTitle>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {dataUpdatedAt ? formatTime(dataUpdatedAt) : '--:--'}
          </span>
          <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={cn('h-4 w-4', isFetching && 'animate-spin')} />
          </Button>
          <Button variant="ghost" size="sm" onClick={handleViewAll}>
            <ExternalLink className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {categories.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No recommendations available yet. Check back after market open.
          </p>
        ) : (
          <Tabs defaultValue={categories[0]?.category} className="w-full">
            <TabsList className="w-full justify-start">
              {categories.map((cat) => {
                const config = CATEGORY_CONFIG[cat.category];
                return (
                  <TabsTrigger key={cat.category} value={cat.category} className="gap-1">
                    <span className={config?.color}>{config?.icon}</span>
                    <span className="hidden sm:inline">{cat.title}</span>
                  </TabsTrigger>
                );
              })}
            </TabsList>
            {categories.map((cat) => (
              <TabsContent key={cat.category} value={cat.category} className="mt-3">
                <p className="text-xs text-muted-foreground mb-3">{cat.description}</p>
                <div className="space-y-1">
                  {cat.recommendations.slice(0, 5).map((item) => (
                    <RecommendationRow key={item.symbol} item={item} onNavigate={handleNavigate} />
                  ))}
                </div>
              </TabsContent>
            ))}
          </Tabs>
        )}
      </CardContent>
    </Card>
  );
}


'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/use-toast';

import {
  TrendingUp,
  TrendingDown,
  Target,
  BarChart3,
  Calendar,
  Trophy,
  Zap,
  Flame,
  Timer,
  CircleDot,
  ChevronDown,
  ChevronRight,
  Star,
  Eye,
  Bookmark,
} from 'lucide-react';
import { screenerApi, watchlistApi, RecommendationItem } from '@/lib/api';
import { cn } from '@/lib/utils';

interface PerformanceWidgetProps {
  days?: number;
  compact?: boolean;
}

export function PerformanceWidget({ days = 30, compact = false }: PerformanceWidgetProps) {
  const [showWatchlistDialog, setShowWatchlistDialog] = useState(false);
  const [watchlistName, setWatchlistName] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch performance stats
  const { data, isLoading, error } = useQuery({
    queryKey: ['screener-performance', days],
    queryFn: () => screenerApi.getPerformance(days),
    staleTime: 5 * 60 * 1000,
  });

  // Fetch actual recommendations to show stocks
  const { data: recommendationsData } = useQuery({
    queryKey: ['screener-recommendations'],
    queryFn: () => screenerApi.getRecommendations(),
    staleTime: 5 * 60 * 1000,
  });

  // Create watchlist mutation - create watchlist first, then add items
  const createWatchlistMutation = useMutation({
    mutationFn: async ({ name, symbols }: { name: string; symbols: string[] }) => {
      // First create the watchlist
      const response = await watchlistApi.createWatchlist({
        name,
        description: `Screener recommendations from ${selectedCategory}`
      });
      const watchlistId = response.data.id;

      // Then add each symbol
      for (const symbol of symbols) {
        await watchlistApi.addItem(watchlistId, symbol);
      }

      return response;
    },
    onSuccess: () => {
      toast({
        title: 'Watchlist Created',
        description: `Successfully created watchlist "${watchlistName}"`,
      });
      setShowWatchlistDialog(false);
      setWatchlistName('');
      setSelectedCategory(null);
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to create watchlist',
        variant: 'destructive',
      });
    },
  });

  const handleSaveAsWatchlist = (category: string, symbols: string[]) => {
    setSelectedCategory(category);
    setWatchlistName(`${category.charAt(0).toUpperCase() + category.slice(1)} Picks - ${new Date().toLocaleDateString()}`);
    setShowWatchlistDialog(true);
  };

  const confirmCreateWatchlist = () => {
    if (!selectedCategory || !recommendationsData?.data) return;
    const categoryData = recommendationsData.data.categories.find(c => c.category === selectedCategory);
    if (!categoryData) return;
    const symbols = categoryData.recommendations.map(r => r.symbol);
    createWatchlistMutation.mutate({ name: watchlistName, symbols });
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-32" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !data?.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Screener Performance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">Unable to load performance data</p>
        </CardContent>
      </Card>
    );
  }

  const stats = data.data;
  const recommendations = recommendationsData?.data?.categories || [];

  // Determine overall trend
  const overallTrend = stats.overall_avg_return_1m !== null && stats.overall_avg_return_1m > 0;

  return (
    <Card className={cn(
      "overflow-hidden",
      overallTrend
        ? "border-green-200 dark:border-green-900/50"
        : stats.total_recommendations > 0
          ? "border-red-200 dark:border-red-900/50"
          : ""
    )}>
      <CardHeader className={cn(
        "pb-3",
        overallTrend
          ? "bg-gradient-to-r from-green-50/50 to-transparent dark:from-green-950/20"
          : stats.total_recommendations > 0
            ? "bg-gradient-to-r from-red-50/50 to-transparent dark:from-red-950/20"
            : ""
      )}>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <div className={cn(
              "p-1.5 rounded-lg",
              overallTrend ? "bg-green-100 dark:bg-green-900/40" : "bg-muted"
            )}>
              <BarChart3 className={cn(
                "h-4 w-4",
                overallTrend ? "text-green-600 dark:text-green-400" : ""
              )} />
            </div>
            Screener Performance
          </CardTitle>
          {overallTrend && (
            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-400 dark:border-green-800">
              <TrendingUp className="h-3 w-3 mr-1" />
              Profitable
            </Badge>
          )}
        </div>
        <CardDescription className="flex items-center gap-2 mt-1">
          <Calendar className="h-3 w-3" />
          Last {days} days • {stats.total_recommendations} recommendations • {stats.unique_symbols} unique stocks
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        {stats.total_recommendations === 0 ? (
          <div className="text-center py-8">
            <CircleDot className="h-10 w-10 mx-auto text-muted-foreground/30 mb-3" />
            <p className="text-sm text-muted-foreground">No recommendations yet</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              Performance data will appear after daily recommendations are generated
            </p>
          </div>
        ) : (
          <>
            {/* Overall Stats with Progress Bars */}
            <div className="grid grid-cols-3 gap-3 mb-6">
              <WinRateCard
                label="1 Day"
                icon={<Zap className="h-3.5 w-3.5" />}
                winRate={stats.overall_win_rate_1d}
                avgReturn={stats.overall_avg_return_1d}
                color="blue"
              />
              <WinRateCard
                label="1 Week"
                icon={<Timer className="h-3.5 w-3.5" />}
                winRate={stats.overall_win_rate_1w}
                avgReturn={stats.overall_avg_return_1w}
                color="purple"
              />
              <WinRateCard
                label="1 Month"
                icon={<Flame className="h-3.5 w-3.5" />}
                winRate={stats.overall_win_rate_1m}
                avgReturn={stats.overall_avg_return_1m}
                color="orange"
              />
            </div>

            {!compact && stats.categories.length > 0 && (
              <Tabs defaultValue={stats.categories[0]?.category || 'momentum'}>
                <TabsList className="mb-4 w-full grid" style={{ gridTemplateColumns: `repeat(${stats.categories.length}, 1fr)` }}>
                  {stats.categories.map((cat) => (
                    <TabsTrigger
                      key={cat.category}
                      value={cat.category}
                      className="capitalize text-xs"
                    >
                      {getCategoryIcon(cat.category)}
                      <span className="ml-1.5">{cat.category}</span>
                    </TabsTrigger>
                  ))}
                </TabsList>
                {stats.categories.map((cat) => {
                  const categoryRecs = recommendations.find(r => r.category === cat.category);
                  return (
                    <TabsContent key={cat.category} value={cat.category}>
                      <CategoryStats
                        stats={cat}
                        recommendations={categoryRecs?.recommendations || []}
                        onSaveAsWatchlist={(symbols) => handleSaveAsWatchlist(cat.category, symbols)}
                      />
                    </TabsContent>
                  );
                })}
              </Tabs>
            )}
          </>
        )}
      </CardContent>

      {/* Save as Watchlist Dialog */}
      <Dialog open={showWatchlistDialog} onOpenChange={setShowWatchlistDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Bookmark className="h-5 w-5" />
              Save as Watchlist
            </DialogTitle>
            <DialogDescription>
              Create a watchlist from the {selectedCategory} recommendations to track their performance.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="watchlist-name">Watchlist Name</Label>
            <Input
              id="watchlist-name"
              value={watchlistName}
              onChange={(e) => setWatchlistName(e.target.value)}
              placeholder="Enter watchlist name"
              className="mt-2"
            />
            {selectedCategory && recommendationsData?.data && (
              <p className="text-sm text-muted-foreground mt-2">
                {recommendationsData.data.categories.find(c => c.category === selectedCategory)?.recommendations.length || 0} stocks will be added
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowWatchlistDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={confirmCreateWatchlist}
              disabled={!watchlistName.trim() || createWatchlistMutation.isPending}
            >
              {createWatchlistMutation.isPending ? 'Creating...' : 'Create Watchlist'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

// Helper to get category-specific icon
function getCategoryIcon(category: string) {
  switch (category.toLowerCase()) {
    case 'momentum':
      return <TrendingUp className="h-3.5 w-3.5" />;
    case 'breakout':
      return <Zap className="h-3.5 w-3.5" />;
    case 'pullback':
    case 'value':
      return <Target className="h-3.5 w-3.5" />;
    case 'sector':
      return <Flame className="h-3.5 w-3.5" />;
    default:
      return <CircleDot className="h-3.5 w-3.5" />;
  }
}

// Enhanced Win Rate Card with Progress Bar
function WinRateCard({
  label,
  icon,
  winRate,
  avgReturn,
  color,
}: {
  label: string;
  icon: React.ReactNode;
  winRate: number | null;
  avgReturn: number | null;
  color: 'blue' | 'purple' | 'orange';
}) {
  const formatPercent = (val: number | null) =>
    val !== null ? `${val >= 0 ? '+' : ''}${val.toFixed(2)}%` : '-';

  const winRateValue = winRate ?? 0;
  const isPositiveReturn = avgReturn !== null && avgReturn > 0;

  const colorClasses = {
    blue: {
      bg: 'bg-blue-50 dark:bg-blue-950/30',
      icon: 'bg-blue-100 text-blue-600 dark:bg-blue-900/50 dark:text-blue-400',
      progress: 'bg-blue-500',
      text: 'text-blue-600 dark:text-blue-400'
    },
    purple: {
      bg: 'bg-purple-50 dark:bg-purple-950/30',
      icon: 'bg-purple-100 text-purple-600 dark:bg-purple-900/50 dark:text-purple-400',
      progress: 'bg-purple-500',
      text: 'text-purple-600 dark:text-purple-400'
    },
    orange: {
      bg: 'bg-orange-50 dark:bg-orange-950/30',
      icon: 'bg-orange-100 text-orange-600 dark:bg-orange-900/50 dark:text-orange-400',
      progress: 'bg-orange-500',
      text: 'text-orange-600 dark:text-orange-400'
    }
  };

  const colors = colorClasses[color];

  return (
    <div className={cn("rounded-lg p-3 border", colors.bg)}>
      <div className="flex items-center gap-1.5 mb-2">
        <div className={cn("p-1 rounded", colors.icon)}>
          {icon}
        </div>
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
      </div>

      {/* Win Rate with Progress */}
      <div className="mb-2">
        <div className="flex items-baseline justify-between mb-1">
          <span className="text-xl font-bold">
            {winRate !== null ? `${winRate.toFixed(0)}%` : '-'}
          </span>
          <span className="text-xs text-muted-foreground">win rate</span>
        </div>
        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
          <div
            className={cn("h-full rounded-full transition-all duration-500", colors.progress)}
            style={{ width: `${Math.min(winRateValue, 100)}%` }}
          />
        </div>
      </div>

      {/* Average Return */}
      <div className={cn(
        "flex items-center gap-1 text-sm font-medium",
        isPositiveReturn ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
      )}>
        {isPositiveReturn ? (
          <TrendingUp className="h-3.5 w-3.5" />
        ) : avgReturn !== null ? (
          <TrendingDown className="h-3.5 w-3.5" />
        ) : null}
        <span>{formatPercent(avgReturn)} avg</span>
      </div>
    </div>
  );
}

import { CategoryPerformanceStats } from '@/lib/api';

function CategoryStats({
  stats,
  recommendations,
  onSaveAsWatchlist,
}: {
  stats: CategoryPerformanceStats;
  recommendations: RecommendationItem[];
  onSaveAsWatchlist: (symbols: string[]) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const formatPercent = (val: number | null | undefined) =>
    val !== null && val !== undefined ? `${val >= 0 ? '+' : ''}${val.toFixed(2)}%` : '-';

  const getWinRateColor = (rate: number | null) => {
    if (rate === null) return 'text-muted-foreground';
    if (rate >= 60) return 'text-green-600 dark:text-green-400';
    if (rate >= 50) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getWinRateBg = (rate: number | null) => {
    if (rate === null) return 'bg-muted';
    if (rate >= 60) return 'bg-green-100 dark:bg-green-900/30';
    if (rate >= 50) return 'bg-yellow-100 dark:bg-yellow-900/30';
    return 'bg-red-100 dark:bg-red-900/30';
  };

  const getReturnColor = (val: number | null | undefined) => {
    if (val === null || val === undefined) return 'text-muted-foreground';
    return val >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
  };

  return (
    <div className="space-y-4">
      {/* Win Rates with Visual Indicators */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: '1 Day', rate: stats.win_rate_1d, avg: stats.avg_return_1d },
          { label: '1 Week', rate: stats.win_rate_1w, avg: stats.avg_return_1w },
          { label: '1 Month', rate: stats.win_rate_1m, avg: stats.avg_return_1m },
        ].map(({ label, rate, avg }) => (
          <div
            key={label}
            className={cn(
              "rounded-lg p-2.5 border text-center",
              getWinRateBg(rate)
            )}
          >
            <p className="text-xs text-muted-foreground mb-0.5">{label}</p>
            <p className={cn("text-lg font-bold", getWinRateColor(rate))}>
              {rate !== null ? `${rate.toFixed(0)}%` : '-'}
            </p>
            {avg !== null && avg !== undefined && (
              <p className={cn("text-xs", getReturnColor(avg))}>
                {formatPercent(avg)}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Best Picks with Trophy Icons */}
      {(stats.best_pick_1d || stats.best_pick_1w || stats.best_pick_1m) && (
        <div className="bg-gradient-to-r from-amber-50/50 to-transparent dark:from-amber-950/20 rounded-lg p-3 border border-amber-100 dark:border-amber-900/30">
          <p className="text-xs font-medium text-amber-700 dark:text-amber-400 mb-2 flex items-center gap-1.5">
            <Trophy className="h-3.5 w-3.5" />
            Top Performers
          </p>
          <div className="flex flex-wrap gap-2">
            {stats.best_pick_1d && stats.best_return_1d !== null && (
              <Badge className="bg-amber-100 text-amber-800 border-amber-200 hover:bg-amber-200 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-800">
                <Zap className="h-3 w-3 mr-1" />
                1D: {stats.best_pick_1d}
                <span className="ml-1 text-green-600 dark:text-green-400 font-bold">
                  {formatPercent(stats.best_return_1d)}
                </span>
              </Badge>
            )}
            {stats.best_pick_1w && stats.best_return_1w !== null && (
              <Badge className="bg-amber-100 text-amber-800 border-amber-200 hover:bg-amber-200 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-800">
                <Timer className="h-3 w-3 mr-1" />
                1W: {stats.best_pick_1w}
                <span className="ml-1 text-green-600 dark:text-green-400 font-bold">
                  {formatPercent(stats.best_return_1w)}
                </span>
              </Badge>
            )}
            {stats.best_pick_1m && stats.best_return_1m !== null && (
              <Badge className="bg-amber-100 text-amber-800 border-amber-200 hover:bg-amber-200 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-800">
                <Flame className="h-3 w-3 mr-1" />
                1M: {stats.best_pick_1m}
                <span className="ml-1 text-green-600 dark:text-green-400 font-bold">
                  {formatPercent(stats.best_return_1m)}
                </span>
              </Badge>
            )}
          </div>
        </div>
      )}

      {/* Expandable Stock List */}
      {recommendations.length > 0 && (
        <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
          <div className="flex items-center justify-between border-t pt-3">
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="gap-2 text-xs h-8">
                {isExpanded ? (
                  <ChevronDown className="h-3.5 w-3.5" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5" />
                )}
                <Eye className="h-3.5 w-3.5" />
                View {recommendations.length} Stocks
              </Button>
            </CollapsibleTrigger>
            <Button
              variant="outline"
              size="sm"
              className="gap-2 text-xs h-8"
              onClick={() => onSaveAsWatchlist(recommendations.map(r => r.symbol))}
            >
              <Bookmark className="h-3.5 w-3.5" />
              Save as Watchlist
            </Button>
          </div>

          <CollapsibleContent className="mt-3">
            <div className="rounded-lg border overflow-hidden">
              {/* Table Header */}
              <div className="grid grid-cols-12 gap-2 px-3 py-2 bg-muted/50 text-xs font-medium text-muted-foreground border-b">
                <div className="col-span-1 text-center">#</div>
                <div className="col-span-3">Symbol</div>
                <div className="col-span-2 text-right">Score</div>
                <div className="col-span-2 text-right">1D</div>
                <div className="col-span-2 text-right">1W</div>
                <div className="col-span-2 text-right">1M</div>
              </div>

              {/* Stock Rows */}
              <div className="divide-y max-h-64 overflow-y-auto">
                {recommendations.map((rec, idx) => (
                  <div
                    key={rec.symbol}
                    className={cn(
                      "grid grid-cols-12 gap-2 px-3 py-2 text-sm items-center hover:bg-muted/30 transition-colors",
                      idx % 2 === 0 ? "bg-background" : "bg-muted/10"
                    )}
                  >
                    <div className="col-span-1 text-center text-muted-foreground text-xs">
                      {rec.rank}
                    </div>
                    <div className="col-span-3 font-medium flex items-center gap-1.5">
                      {idx < 3 && (
                        <Star className="h-3 w-3 text-amber-500 fill-amber-500" />
                      )}
                      {rec.symbol}
                    </div>
                    <div className="col-span-2 text-right">
                      <Badge variant="secondary" className="text-xs font-mono">
                        {rec.score.toFixed(0)}
                      </Badge>
                    </div>
                    <div className={cn("col-span-2 text-right font-mono text-xs", getReturnColor(rec.return_1d))}>
                      {formatPercent(rec.return_1d)}
                    </div>
                    <div className={cn("col-span-2 text-right font-mono text-xs", getReturnColor(rec.return_1w))}>
                      {formatPercent(rec.return_1w)}
                    </div>
                    <div className={cn("col-span-2 text-right font-mono text-xs", getReturnColor(rec.return_1m))}>
                      {formatPercent(rec.return_1m)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Summary Footer */}
            <div className="flex items-center justify-between mt-3 text-xs text-muted-foreground">
              <span>{recommendations.length} stocks identified</span>
              <span>Returns update daily after market close</span>
            </div>
          </CollapsibleContent>
        </Collapsible>
      )}

      {/* Fallback if no recommendations loaded */}
      {recommendations.length === 0 && (
        <div className="text-xs text-muted-foreground text-center pt-2 border-t">
          {stats.total_recommendations} recommendations in this category
        </div>
      )}
    </div>
  );
}


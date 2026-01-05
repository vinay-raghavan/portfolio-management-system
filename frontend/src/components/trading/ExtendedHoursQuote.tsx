'use client';

import { Clock, Moon, Sun, Sunrise, Sunset } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { useCurrency } from '@/hooks/useCurrency';
import { formatPercent, cn } from '@/lib/utils';
import type { StockQuote, MarketSession } from '@/types';

interface ExtendedHoursQuoteProps {
  quote: StockQuote | undefined;
  showCard?: boolean;
  className?: string;
}

const SESSION_CONFIG: Record<MarketSession, { label: string; icon: typeof Sun; color: string }> = {
  pre_market: { label: 'Pre-Market', icon: Sunrise, color: 'text-orange-500' },
  regular: { label: 'Regular', icon: Sun, color: 'text-green-500' },
  post_market: { label: 'After Hours', icon: Sunset, color: 'text-purple-500' },
  closed: { label: 'Closed', icon: Moon, color: 'text-muted-foreground' },
};

function formatTime(timestamp: string | null): string {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

export function ExtendedHoursQuote({ quote, showCard = true, className }: ExtendedHoursQuoteProps) {
  const { format: formatCurrency } = useCurrency();

  if (!quote) return null;

  const hasPreMarket = quote.pre_market_price !== null;
  const hasPostMarket = quote.post_market_price !== null;
  const hasExtendedHours = hasPreMarket || hasPostMarket;

  if (!hasExtendedHours) return null;

  const sessionConfig = quote.market_session ? SESSION_CONFIG[quote.market_session] : null;
  const SessionIcon = sessionConfig?.icon ?? Clock;

  const content = (
    <div className={cn('space-y-3', className)}>
      {/* Market Session Badge */}
      {sessionConfig && (
        <div className="flex items-center gap-2">
          <Badge variant="outline" className={cn('gap-1', sessionConfig.color)}>
            <SessionIcon className="h-3 w-3" />
            {sessionConfig.label}
          </Badge>
        </div>
      )}

      {/* Pre-Market Data */}
      {hasPreMarket && (
        <div className="flex items-center justify-between py-2 border-b border-border/50">
          <div className="flex items-center gap-2">
            <Sunrise className="h-4 w-4 text-orange-500" />
            <span className="text-sm text-muted-foreground">Pre-Market</span>
          </div>
          <div className="text-right">
            <div className="font-medium">{formatCurrency(quote.pre_market_price!)}</div>
            <Tooltip>
              <TooltipTrigger asChild>
                <div
                  className={cn(
                    'text-xs',
                    quote.pre_market_change !== null && quote.pre_market_change >= 0
                      ? 'text-profit'
                      : 'text-loss'
                  )}
                >
                  {quote.pre_market_change !== null && (
                    <>
                      {quote.pre_market_change >= 0 ? '+' : ''}
                      {formatCurrency(quote.pre_market_change)}
                      {quote.pre_market_change_pct !== null && (
                        <> ({formatPercent(quote.pre_market_change_pct)})</>
                      )}
                    </>
                  )}
                </div>
              </TooltipTrigger>
              {quote.pre_market_time && (
                <TooltipContent>
                  <p>Last update: {formatTime(quote.pre_market_time)}</p>
                </TooltipContent>
              )}
            </Tooltip>
          </div>
        </div>
      )}

      {/* Post-Market Data */}
      {hasPostMarket && (
        <div className="flex items-center justify-between py-2">
          <div className="flex items-center gap-2">
            <Sunset className="h-4 w-4 text-purple-500" />
            <span className="text-sm text-muted-foreground">After Hours</span>
          </div>
          <div className="text-right">
            <div className="font-medium">{formatCurrency(quote.post_market_price!)}</div>
            <Tooltip>
              <TooltipTrigger asChild>
                <div
                  className={cn(
                    'text-xs',
                    quote.post_market_change !== null && quote.post_market_change >= 0
                      ? 'text-profit'
                      : 'text-loss'
                  )}
                >
                  {quote.post_market_change !== null && (
                    <>
                      {quote.post_market_change >= 0 ? '+' : ''}
                      {formatCurrency(quote.post_market_change)}
                      {quote.post_market_change_pct !== null && (
                        <> ({formatPercent(quote.post_market_change_pct)})</>
                      )}
                    </>
                  )}
                </div>
              </TooltipTrigger>
              {quote.post_market_time && (
                <TooltipContent>
                  <p>Last update: {formatTime(quote.post_market_time)}</p>
                </TooltipContent>
              )}
            </Tooltip>
          </div>
        </div>
      )}
    </div>
  );

  if (!showCard) return content;

  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Clock className="h-4 w-4" />
          Extended Hours
        </CardTitle>
      </CardHeader>
      <CardContent>{content}</CardContent>
    </Card>
  );
}


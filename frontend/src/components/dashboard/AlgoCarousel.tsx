'use client';

import { useQuery } from '@tanstack/react-query';
import { Bot, Activity, Bell } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { autoTradeApi } from '@/lib/api';
import { AlgoSummaryContent } from './AlgoSummaryContent';
import { PendingAutoTradesContent } from './PendingAutoTradesContent';

/**
 * AlgoCarousel - A tabbed carousel combining Algo Trading summary and Pending Auto-Trades.
 * Displays in a single card with tabs to switch between views.
 */
export function AlgoCarousel() {
  // Fetch pending trades count for badge
  const { data: pendingData } = useQuery({
    queryKey: ['pending-auto-trades'],
    queryFn: () => autoTradeApi.getPendingTrades('PENDING').then(r => r.data),
    refetchInterval: 30000,
  });

  const pendingCount = pendingData?.pending_count || 0;

  return (
    <Card>
      <Tabs defaultValue="algo" className="w-full">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5" />
              Algo Trading
            </CardTitle>
            <TabsList className="h-8">
              <TabsTrigger value="algo" className="text-xs px-2 py-1 h-6 flex items-center gap-1">
                <Activity className="h-3 w-3" />
                Summary
              </TabsTrigger>
              <TabsTrigger value="pending" className="text-xs px-2 py-1 h-6 flex items-center gap-1">
                <Bell className="h-3 w-3" />
                Pending
                {pendingCount > 0 && (
                  <Badge variant="destructive" className="ml-1 h-4 w-4 p-0 flex items-center justify-center text-[10px]">
                    {pendingCount}
                  </Badge>
                )}
              </TabsTrigger>
            </TabsList>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <TabsContent value="algo" className="mt-0">
            <AlgoSummaryContent />
          </TabsContent>
          <TabsContent value="pending" className="mt-0">
            <PendingAutoTradesContent />
          </TabsContent>
        </CardContent>
      </Tabs>
    </Card>
  );
}


'use client';

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { OrderEntryForm, OrderConfirmationModal, OrderBook } from '@/components/trading';
import { TradeHistory } from '@/components/portfolio';
import { useQuote } from '@/hooks';
import { useTradingStore } from '@/store';
import type { OrderCreate } from '@/types';

export default function OrdersPage() {
  const [activeTab, setActiveTab] = useState('entry');
  const [pendingOrder, setPendingOrder] = useState<OrderCreate | null>(null);
  const { formState } = useTradingStore();

  const { data: quote } = useQuote(formState.symbol, {
    enabled: !!formState.symbol,
  });

  const handleConfirmOrder = (order: OrderCreate) => {
    setPendingOrder(order);
  };

  const handleOrderSuccess = () => {
    setPendingOrder(null);
    setActiveTab('open');
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Orders</h1>
        <p className="text-muted-foreground">Place orders and manage your order book</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="entry">Place Order</TabsTrigger>
          <TabsTrigger value="open">Open Orders</TabsTrigger>
          <TabsTrigger value="history">Trade History</TabsTrigger>
        </TabsList>

        <TabsContent value="entry" className="mt-4">
          <div className="grid gap-6 md:grid-cols-2">
            <OrderEntryForm onConfirm={handleConfirmOrder} />
            <OrderBook statusFilter="OPEN" pageSize={5} />
          </div>
        </TabsContent>

        <TabsContent value="open" className="mt-4">
          <OrderBook pageSize={20} />
        </TabsContent>

        <TabsContent value="history" className="mt-4">
          <TradeHistory pageSize={20} />
        </TabsContent>
      </Tabs>

      {/* Order Confirmation Modal */}
      <OrderConfirmationModal
        order={pendingOrder}
        estimatedPrice={quote?.price ?? 0}
        isOpen={!!pendingOrder}
        onClose={() => setPendingOrder(null)}
        onSuccess={handleOrderSuccess}
      />
    </div>
  );
}


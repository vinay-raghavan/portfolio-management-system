'use client';

import { useState } from 'react';
import { WatchlistList, WatchlistTable, AddSymbolDialog } from '@/components/watchlist';

export default function WatchlistPage() {
  const [selectedWatchlistId, setSelectedWatchlistId] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Watchlist</h1>
          <p className="text-muted-foreground">Track your favorite stocks</p>
        </div>
        <AddSymbolDialog watchlistId={selectedWatchlistId} />
      </div>

      <div className="grid gap-6 md:grid-cols-[280px_1fr]">
        <WatchlistList
          selectedId={selectedWatchlistId}
          onSelect={setSelectedWatchlistId}
        />
        <WatchlistTable watchlistId={selectedWatchlistId} />
      </div>
    </div>
  );
}


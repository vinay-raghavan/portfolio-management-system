'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Search, TrendingUp, ArrowRight } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { useSymbolSearch } from '@/hooks';
import { useUIStore } from '@/store';
import { cn } from '@/lib/utils';
import type { SearchResult } from '@/types';

export function GlobalSearch() {
  const router = useRouter();
  const { setSelectedSymbol } = useUIStore();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const { query, setQuery, results, isLoading, clear } = useSymbolSearch({
    minLength: 1,
    debounceMs: 300,
  });

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (result: SearchResult) => {
    setSelectedSymbol(result.symbol);
    clear();
    setIsOpen(false);
    router.push('/analysis');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && query.length > 0) {
      // If there are results, select the first one
      if (results.length > 0) {
        handleSelect(results[0]);
      } else {
        // Otherwise, just navigate with the raw query
        setSelectedSymbol(query.toUpperCase());
        clear();
        setIsOpen(false);
        router.push('/analysis');
      }
    }
    if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  return (
    <div ref={containerRef} className="relative w-80">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search stocks..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          className="pl-10 pr-4"
        />
      </div>

      {/* Dropdown Results */}
      {isOpen && query.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-popover border rounded-lg shadow-lg z-50 overflow-hidden">
          {isLoading ? (
            <div className="p-4 text-center text-muted-foreground">
              <div className="animate-spin h-5 w-5 border-2 border-primary border-t-transparent rounded-full mx-auto" />
            </div>
          ) : results.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground">
              <p className="text-sm">No results found</p>
              <p className="text-xs mt-1">Press Enter to search for &quot;{query.toUpperCase()}&quot;</p>
            </div>
          ) : (
            <div className="max-h-80 overflow-y-auto">
              {results.slice(0, 8).map((result: SearchResult) => (
                <div
                  key={result.symbol}
                  className={cn(
                    'flex items-center justify-between p-3 cursor-pointer hover:bg-muted transition-colors'
                  )}
                  onClick={() => handleSelect(result)}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-1.5 bg-primary/10 rounded">
                      <TrendingUp className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <div className="font-medium">{result.symbol}</div>
                      <div className="text-xs text-muted-foreground truncate max-w-[200px]">
                        {result.name}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">{result.exchange}</span>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


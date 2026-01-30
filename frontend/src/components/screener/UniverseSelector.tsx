'use client';

import { useQuery } from '@tanstack/react-query';
import { ChevronDown, Database, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { algoApi } from '@/lib/api';
import type { Universe } from '@/types/api';

// UniverseType now accepts any string (universe name) from the database
export type UniverseType = string;

interface UniverseSelectorProps {
  value: UniverseType;
  onChange: (universe: UniverseType) => void;
  disabled?: boolean;
}

export function UniverseSelector({ value, onChange, disabled }: UniverseSelectorProps) {
  // Fetch universes from the same API as algo trading
  const { data: universes, isLoading } = useQuery({
    queryKey: ['universes'],
    queryFn: () => algoApi.getUniverses().then((res) => res.data),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Separate system and custom universes
  const systemUniverses = universes?.filter((u) => u.is_system) ?? [];
  const customUniverses = universes?.filter((u) => !u.is_system) ?? [];

  // Find the currently selected universe
  const selectedUniverse = universes?.find((u) => u.name === value);
  const displayName = selectedUniverse?.name ?? value ?? 'Select Universe';
  const symbolCount = selectedUniverse?.symbols?.length ?? 0;

  return (
    <div className="flex items-center gap-2">
      <Database className="h-4 w-4 text-muted-foreground" />
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className="w-[220px] justify-between" disabled={disabled || isLoading}>
            {isLoading ? (
              <span className="flex items-center gap-2">
                <RefreshCw className="h-3 w-3 animate-spin" />
                Loading...
              </span>
            ) : (
              <span className="truncate">{displayName}</span>
            )}
            <ChevronDown className="h-4 w-4 opacity-50 ml-2" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[320px] max-h-[400px] overflow-y-auto">
          {/* System Universes */}
          {systemUniverses.length > 0 && (
            <>
              <DropdownMenuLabel className="text-xs text-muted-foreground">
                Index Universes
              </DropdownMenuLabel>
              {systemUniverses.map((universe) => (
                <DropdownMenuItem
                  key={universe.id}
                  onClick={() => onChange(universe.name)}
                  className={value === universe.name ? 'bg-accent' : ''}
                >
                  <div className="flex flex-col gap-1 w-full">
                    <div className="flex items-center justify-between w-full">
                      <span className="font-medium">{universe.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {universe.symbols?.length ?? 0} stocks
                      </span>
                    </div>
                    {universe.description && (
                      <span className="text-xs text-muted-foreground truncate">
                        {universe.description}
                      </span>
                    )}
                  </div>
                </DropdownMenuItem>
              ))}
            </>
          )}

          {/* Custom Universes */}
          {customUniverses.length > 0 && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuLabel className="text-xs text-muted-foreground">
                Custom Universes
              </DropdownMenuLabel>
              {customUniverses.map((universe) => (
                <DropdownMenuItem
                  key={universe.id}
                  onClick={() => onChange(universe.name)}
                  className={value === universe.name ? 'bg-accent' : ''}
                >
                  <div className="flex flex-col gap-1 w-full">
                    <div className="flex items-center justify-between w-full">
                      <span className="font-medium">{universe.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {universe.symbols?.length ?? 0} stocks
                      </span>
                    </div>
                    {universe.description && (
                      <span className="text-xs text-muted-foreground truncate">
                        {universe.description}
                      </span>
                    )}
                  </div>
                </DropdownMenuItem>
              ))}
            </>
          )}

          {/* Empty state */}
          {!isLoading && universes?.length === 0 && (
            <div className="p-4 text-center text-sm text-muted-foreground">
              No universes found. Go to Algo Trading and click the Seed Universes button.
            </div>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
      {symbolCount > 0 && (
        <span className="text-xs text-muted-foreground">({symbolCount} stocks)</span>
      )}
    </div>
  );
}


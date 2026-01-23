'use client';

import { ChevronDown, Database } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export type UniverseType = 'NIFTY50' | 'NIFTY500' | 'ALL_NSE' | 'FO_STOCKS';

interface UniverseOption {
  value: UniverseType;
  label: string;
  description: string;
  stockCount: string;
}

const UNIVERSE_OPTIONS: UniverseOption[] = [
  { value: 'NIFTY50', label: 'Nifty 50', description: 'Top 50 large-cap stocks', stockCount: '~50' },
  { value: 'NIFTY500', label: 'Nifty 500', description: 'Top 500 by market cap', stockCount: '~500' },
  { value: 'FO_STOCKS', label: 'F&O Stocks', description: 'Futures & Options eligible', stockCount: '~180' },
  { value: 'ALL_NSE', label: 'All NSE', description: 'All NSE listed stocks', stockCount: '~2000' },
];

interface UniverseSelectorProps {
  value: UniverseType;
  onChange: (universe: UniverseType) => void;
  disabled?: boolean;
}

export function UniverseSelector({ value, onChange, disabled }: UniverseSelectorProps) {
  const selectedOption = UNIVERSE_OPTIONS.find((opt) => opt.value === value) ?? UNIVERSE_OPTIONS[0];

  return (
    <div className="flex items-center gap-2">
      <Database className="h-4 w-4 text-muted-foreground" />
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className="w-[200px] justify-between" disabled={disabled}>
            <span>{selectedOption.label}</span>
            <ChevronDown className="h-4 w-4 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[280px]">
          {UNIVERSE_OPTIONS.map((option, index) => (
            <div key={option.value}>
              <DropdownMenuItem
                onClick={() => onChange(option.value)}
                className={value === option.value ? 'bg-accent' : ''}
              >
                <div className="flex flex-col gap-1">
                  <div className="flex items-center justify-between w-full">
                    <span className="font-medium">{option.label}</span>
                    <span className="text-xs text-muted-foreground">{option.stockCount} stocks</span>
                  </div>
                  <span className="text-xs text-muted-foreground">{option.description}</span>
                </div>
              </DropdownMenuItem>
              {index < UNIVERSE_OPTIONS.length - 1 && <DropdownMenuSeparator />}
            </div>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}


'use client';

import { useQuery } from '@tanstack/react-query';
import { Briefcase, Check, ChevronsUpDown, Plus, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { portfolioApi } from '@/lib/api';
import { usePortfolioStore } from '@/store';
import { useState } from 'react';
import type { PortfolioInfo } from '@/types';

interface PortfolioSelectorProps {
  onCreateClick?: () => void;
  onManageClick?: (portfolio: PortfolioInfo) => void;
}

export function PortfolioSelector({ onCreateClick, onManageClick }: PortfolioSelectorProps) {
  const [open, setOpen] = useState(false);
  const { selectedPortfolioId, setSelectedPortfolio } = usePortfolioStore();

  const { data: portfoliosData, isLoading } = useQuery({
    queryKey: ['portfolios'],
    queryFn: () => portfolioApi.listPortfolios().then((res) => res.data),
  });

  const portfolios = portfoliosData?.portfolios ?? [];
  const selectedPortfolio = portfolios.find((p) => p.id === selectedPortfolioId);

  const handleSelect = (portfolioId: string | null) => {
    setSelectedPortfolio(portfolioId);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-[220px] justify-between"
          disabled={isLoading}
        >
          <div className="flex items-center gap-2 truncate">
            <Briefcase className="h-4 w-4 shrink-0" />
            <span className="truncate">
              {selectedPortfolio ? selectedPortfolio.name : 'All Portfolios'}
            </span>
          </div>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[220px] p-0">
        <Command>
          <CommandList>
            <CommandEmpty>No portfolios found.</CommandEmpty>
            <CommandGroup>
              <CommandItem
                value="all"
                onSelect={() => handleSelect(null)}
              >
                <Check
                  className={cn(
                    'mr-2 h-4 w-4',
                    selectedPortfolioId === null ? 'opacity-100' : 'opacity-0'
                  )}
                />
                <Briefcase className="mr-2 h-4 w-4" />
                All Portfolios
              </CommandItem>
              {portfolios.map((portfolio) => (
                <CommandItem
                  key={portfolio.id}
                  value={portfolio.id}
                  onSelect={() => handleSelect(portfolio.id)}
                  className="flex items-center justify-between"
                >
                  <div className="flex items-center">
                    <Check
                      className={cn(
                        'mr-2 h-4 w-4',
                        selectedPortfolioId === portfolio.id ? 'opacity-100' : 'opacity-0'
                      )}
                    />
                    <span className="truncate">{portfolio.name}</span>
                    {portfolio.is_default && (
                      <span className="ml-2 text-xs text-muted-foreground">(Default)</span>
                    )}
                  </div>
                  {onManageClick && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 ml-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        onManageClick(portfolio);
                        setOpen(false);
                      }}
                    >
                      <Settings className="h-3 w-3" />
                    </Button>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
            {onCreateClick && (
              <>
                <CommandSeparator />
                <CommandGroup>
                  <CommandItem
                    onSelect={() => {
                      onCreateClick();
                      setOpen(false);
                    }}
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Create Portfolio
                  </CommandItem>
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}


'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { NavGroup as NavGroupType } from '@/config/navigation';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface NavGroupProps {
  group: NavGroupType;
  isExpanded: boolean;
  isOpen: boolean;
  onToggle: () => void;
}

export function NavGroup({ group, isExpanded, isOpen, onToggle }: NavGroupProps) {
  const pathname = usePathname();
  const hasActiveItem = group.items.some((item) => pathname === item.href);

  // Auto-expand group if it contains the active item
  useEffect(() => {
    if (hasActiveItem && !isOpen) {
      onToggle();
    }
    // Only run on mount or when pathname changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  if (!isExpanded) {
    // Collapsed sidebar - show only group icon with tooltip (no sub-items)
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            className={cn(
              'flex items-center justify-center w-full p-3 rounded-lg text-sm font-medium transition-colors',
              hasActiveItem
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:bg-accent'
            )}
          >
            <group.icon className="h-5 w-5 shrink-0" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="right" className="flex flex-col gap-1 p-2">
          <span className="font-medium">{group.name}</span>
          <div className="text-xs text-muted-foreground">
            {group.items.map((item) => item.name).join(', ')}
          </div>
        </TooltipContent>
      </Tooltip>
    );
  }

  // Expanded sidebar - show full group with items
  return (
    <div className="space-y-1">
      <button
        onClick={onToggle}
        className={cn(
          'flex items-center justify-between w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors',
          hasActiveItem
            ? 'bg-primary/10 text-primary'
            : 'text-muted-foreground hover:bg-accent'
        )}
      >
        <div className="flex items-center gap-3">
          <group.icon className="h-5 w-5 shrink-0" />
          <span>{group.name}</span>
        </div>
        <ChevronDown
          className={cn(
            'h-4 w-4 shrink-0 transition-transform duration-200',
            isOpen && 'rotate-180'
          )}
        />
      </button>
      {isOpen && (
        <div className="ml-4 pl-3 border-l border-border space-y-1">
          {group.items.map((item) => (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                pathname === item.href
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent'
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              <span>{item.name}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}


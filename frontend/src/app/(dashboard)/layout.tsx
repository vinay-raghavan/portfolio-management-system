'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, LogOut, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/store/auth';
import { NotificationBell } from '@/components/alerts';
import { GlobalSearch } from '@/components/search';
import { ErrorBoundary, KeyboardShortcutsHelp, type KeyboardShortcutsHelpRef, SkipLink } from '@/components/shared';
import { NavGroup } from '@/components/navigation';
import { navigationGroups, settingsNavItem } from '@/config/navigation';
import { useKeyboardShortcuts } from '@/hooks';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const [isExpanded, setIsExpanded] = useState(false);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});
  const helpModalRef = useRef<KeyboardShortcutsHelpRef>(null);
  const { registerHelpModal } = useKeyboardShortcuts(true);

  // Load persisted open groups from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem('nav-open-groups');
      if (stored) {
        setOpenGroups(JSON.parse(stored));
      }
    } catch {
      // Ignore localStorage errors
    }
  }, []);

  // Persist open groups to localStorage when they change
  useEffect(() => {
    try {
      localStorage.setItem('nav-open-groups', JSON.stringify(openGroups));
    } catch {
      // Ignore localStorage errors
    }
  }, [openGroups]);

  // Register the help modal with the keyboard shortcuts hook
  useEffect(() => {
    registerHelpModal(helpModalRef.current);
  }, [registerHelpModal]);

  // Toggle a navigation group open/closed
  const toggleGroup = useCallback((groupName: string) => {
    setOpenGroups((prev) => ({
      ...prev,
      [groupName]: !prev[groupName],
    }));
  }, []);

  return (
    <TooltipProvider delayDuration={0}>
      {/* Skip link for accessibility */}
      <SkipLink />
      <KeyboardShortcutsHelp ref={helpModalRef} />
      <div className="flex h-screen">
        {/* Sidebar */}
        <aside
          id="main-navigation"
          role="navigation"
          aria-label="Main navigation"
          className={cn(
            'border-r bg-card transition-all duration-300 ease-in-out relative flex flex-col',
            isExpanded ? 'w-64' : 'w-16'
          )}
          onMouseEnter={() => setIsExpanded(true)}
          onMouseLeave={() => setIsExpanded(false)}
        >
          <div className="flex h-16 items-center border-b overflow-hidden">
            <div className={cn(
              'flex items-center',
              isExpanded ? 'px-6' : 'px-4 justify-center w-full'
            )}>
              <LayoutDashboard className={cn('h-6 w-6 shrink-0', isExpanded && 'hidden')} aria-hidden="true" />
              <span className={cn(
                'font-bold text-xl whitespace-nowrap transition-opacity duration-300',
                isExpanded ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'
              )}>
                Portfolio
              </span>
            </div>
          </div>
          <nav className={cn('p-2 space-y-1 flex-1 overflow-y-auto', isExpanded && 'p-4 space-y-2')} role="menubar" aria-label="Primary">
            {/* Navigation Groups */}
            {navigationGroups.map((group) => (
              <NavGroup
                key={group.name}
                group={group}
                isExpanded={isExpanded}
                isOpen={openGroups[group.name] ?? false}
                onToggle={() => toggleGroup(group.name)}
              />
            ))}

            {/* Settings - standalone item */}
            <div className="pt-2 mt-2 border-t border-border">
              {isExpanded ? (
                <Link
                  href={settingsNavItem.href}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                    pathname === settingsNavItem.href
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent'
                  )}
                >
                  <Settings className="h-5 w-5 shrink-0" />
                  <span>{settingsNavItem.name}</span>
                </Link>
              ) : (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Link
                      href={settingsNavItem.href}
                      className={cn(
                        'flex items-center justify-center p-3 rounded-lg text-sm font-medium transition-colors',
                        pathname === settingsNavItem.href
                          ? 'bg-primary text-primary-foreground'
                          : 'text-muted-foreground hover:bg-accent'
                      )}
                    >
                      <Settings className="h-5 w-5 shrink-0" />
                    </Link>
                  </TooltipTrigger>
                  <TooltipContent side="right" className="flex items-center gap-2">
                    <span>{settingsNavItem.name}</span>
                    <kbd className="ml-1 inline-flex items-center gap-0.5 rounded border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                      {settingsNavItem.shortcut}
                    </kbd>
                  </TooltipContent>
                </Tooltip>
              )}
            </div>
          </nav>
          <div className={cn(
            'p-2 border-t',
            isExpanded && 'p-4'
          )}>
            <div className={cn(
              'flex items-center mb-4',
              isExpanded ? 'gap-3' : 'justify-center'
            )}>
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                {user?.email?.[0]?.toUpperCase() || 'U'}
              </div>
              <div className={cn(
                'text-sm transition-opacity duration-300',
                isExpanded ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'
              )}>
                <div className="font-medium whitespace-nowrap">{user?.full_name || 'User'}</div>
                <div className="text-muted-foreground text-xs whitespace-nowrap">{user?.email}</div>
              </div>
            </div>
            {isExpanded ? (
              <button
                onClick={logout}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
              >
                <LogOut className="h-4 w-4" />
                Logout
              </button>
            ) : (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={logout}
                    className="flex items-center justify-center w-full text-muted-foreground hover:text-foreground p-2"
                  >
                    <LogOut className="h-4 w-4" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right">
                  Logout
                </TooltipContent>
              </Tooltip>
            )}
          </div>
        </aside>

        {/* Main content */}
        <main id="main-content" className="flex-1 overflow-auto" role="main" aria-label="Main content">
          {/* Header */}
          <header className="h-16 border-b bg-card flex items-center justify-between px-8" role="banner">
            <GlobalSearch />
            <NotificationBell />
          </header>
          <div className="p-8">
            <ErrorBoundary>
              {children}
            </ErrorBoundary>
          </div>
        </main>
      </div>
    </TooltipProvider>
  );
}


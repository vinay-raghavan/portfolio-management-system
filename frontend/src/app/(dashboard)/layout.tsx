'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Briefcase,
  LineChart,
  ListOrdered,
  Star,
  Settings,
  LogOut,
  Zap,
  FlaskConical,
  Bot,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/store/auth';
import { NotificationBell } from '@/components/alerts';
import { GlobalSearch } from '@/components/search';
import { ErrorBoundary } from '@/components/shared';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Portfolio', href: '/portfolio', icon: Briefcase },
  { name: 'Analysis', href: '/analysis', icon: LineChart },
  { name: 'Signals', href: '/signals', icon: Zap },
  { name: 'Algo Trading', href: '/algo', icon: Bot },
  { name: 'Backtest', href: '/backtest', icon: FlaskConical },
  { name: 'Orders', href: '/orders', icon: ListOrdered },
  { name: 'Watchlist', href: '/watchlist', icon: Star },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <TooltipProvider delayDuration={0}>
      <div className="flex h-screen">
        {/* Sidebar */}
        <aside
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
              <LayoutDashboard className={cn('h-6 w-6 shrink-0', isExpanded && 'hidden')} />
              <span className={cn(
                'font-bold text-xl whitespace-nowrap transition-opacity duration-300',
                isExpanded ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'
              )}>
                Portfolio
              </span>
            </div>
          </div>
          <nav className={cn('p-2 space-y-1 flex-1', isExpanded && 'p-4 space-y-2')}>
            {navigation.map((item) => {
              const linkContent = (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    'flex items-center rounded-lg text-sm font-medium transition-colors',
                    isExpanded ? 'gap-3 px-3 py-2' : 'justify-center p-3',
                    pathname === item.href
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent'
                  )}
                >
                  <item.icon className="h-5 w-5 shrink-0" />
                  <span className={cn(
                    'whitespace-nowrap transition-opacity duration-300',
                    isExpanded ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'
                  )}>
                    {item.name}
                  </span>
                </Link>
              );

              if (!isExpanded) {
                return (
                  <Tooltip key={item.name}>
                    <TooltipTrigger asChild>
                      {linkContent}
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      {item.name}
                    </TooltipContent>
                  </Tooltip>
                );
              }

              return linkContent;
            })}
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
        <main className="flex-1 overflow-auto">
          {/* Header */}
          <header className="h-16 border-b bg-card flex items-center justify-between px-8">
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


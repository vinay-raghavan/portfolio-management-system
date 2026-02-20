import {
  LayoutDashboard,
  Briefcase,
  LineChart,
  ListOrdered,
  Star,
  Settings,
  Zap,
  FlaskConical,
  Bot,
  LayoutGrid,
  Search,
  TrendingUp,
  Microscope,
  FileBarChart,
  Receipt,
  TrendingDown,
  Activity,
  FileText,
  type LucideIcon,
} from 'lucide-react';

export interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
  shortcut: string;
}

export interface NavGroup {
  name: string;
  icon: LucideIcon;
  items: NavItem[];
}

// Standalone top-level items (not in groups)
export const standaloneNavItems: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, shortcut: 'G D' },
  { name: 'Portfolio', href: '/portfolio', icon: Briefcase, shortcut: 'G P' },
];

export const navigationGroups: NavGroup[] = [
  {
    name: 'Research',
    icon: Microscope,
    items: [
      { name: 'Research', href: '/research', icon: Microscope, shortcut: 'G E' },
      { name: 'Screener', href: '/screener', icon: Search, shortcut: 'G R' },
      { name: 'Analysis', href: '/analysis', icon: LineChart, shortcut: 'G A' },
      { name: 'Charts', href: '/charts', icon: LayoutGrid, shortcut: 'G C' },
      { name: 'Signals', href: '/signals', icon: Zap, shortcut: 'G S' },
    ],
  },
  {
    name: 'Trading',
    icon: TrendingUp,
    items: [
      { name: 'Orders', href: '/orders', icon: ListOrdered, shortcut: 'G O' },
      { name: 'Watchlist', href: '/watchlist', icon: Star, shortcut: 'G W' },
      { name: 'Algo Trading', href: '/algo', icon: Bot, shortcut: 'G T' },
      { name: 'Backtest', href: '/backtest', icon: FlaskConical, shortcut: 'G B' },
    ],
  },
  {
    name: 'Reports',
    icon: FileBarChart,
    items: [
      { name: 'Overview', href: '/reports', icon: FileBarChart, shortcut: 'G X' },
      { name: 'Statement', href: '/reports/statement', icon: Receipt, shortcut: 'G L' },
      { name: 'Capital Gains', href: '/reports/gains', icon: TrendingDown, shortcut: 'G G' },
      { name: 'API Logs', href: '/reports/api-logs', icon: FileText, shortcut: 'G I' },
      { name: 'Activity', href: '/reports/activity', icon: Activity, shortcut: 'G Y' },
    ],
  },
];

// Settings is standalone, not in a group
export const settingsNavItem: NavItem = {
  name: 'Settings',
  href: '/settings',
  icon: Settings,
  shortcut: 'G ,',
};

// Flat list of all navigation items for keyboard shortcuts
export const allNavItems: NavItem[] = [
  ...standaloneNavItems,
  ...navigationGroups.flatMap((group) => group.items),
  settingsNavItem,
];


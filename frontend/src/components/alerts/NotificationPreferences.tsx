'use client';

import { useState } from 'react';
import { Bell, TrendingUp, AlertTriangle, FileText, ShieldAlert } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { useNotificationStore } from '@/store';

interface NotificationSetting {
  id: string;
  label: string;
  description: string;
  icon: typeof Bell;
  enabled: boolean;
}

export function NotificationPreferences() {
  const { addNotification } = useNotificationStore();

  // In a real app, these would be fetched from and saved to the backend
  const [settings, setSettings] = useState<NotificationSetting[]>([
    {
      id: 'price_alerts',
      label: 'Price Alerts',
      description: 'Get notified when a stock reaches your target price',
      icon: TrendingUp,
      enabled: true,
    },
    {
      id: 'order_execution',
      label: 'Order Execution',
      description: 'Get notified when your orders are filled or cancelled',
      icon: FileText,
      enabled: true,
    },
    {
      id: 'daily_pnl',
      label: 'Daily P&L Summary',
      description: 'Receive a daily summary of your portfolio performance',
      icon: Bell,
      enabled: false,
    },
    {
      id: 'risk_breach',
      label: 'Risk Breach Alerts',
      description: 'Get notified when risk limits are exceeded',
      icon: ShieldAlert,
      enabled: true,
    },
    {
      id: 'market_alerts',
      label: 'Market Alerts',
      description: 'Get notified about significant market movements',
      icon: AlertTriangle,
      enabled: false,
    },
  ]);

  const handleToggle = (id: string) => {
    setSettings((prev) =>
      prev.map((setting) =>
        setting.id === id ? { ...setting, enabled: !setting.enabled } : setting
      )
    );
    addNotification({
      type: 'success',
      title: 'Preferences Updated',
      message: 'Your notification preferences have been saved',
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bell className="h-5 w-5" />
          Notification Preferences
        </CardTitle>
        <CardDescription>
          Choose which notifications you want to receive
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {settings.map((setting) => {
            const Icon = setting.icon;
            return (
              <div
                key={setting.id}
                className="flex items-center justify-between space-x-4"
              >
                <div className="flex items-start gap-4">
                  <div className="p-2 rounded-lg bg-muted">
                    <Icon className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor={setting.id} className="text-base font-medium">
                      {setting.label}
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      {setting.description}
                    </p>
                  </div>
                </div>
                <Switch
                  id={setting.id}
                  checked={setting.enabled}
                  onCheckedChange={() => handleToggle(setting.id)}
                />
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}


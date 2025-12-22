'use client';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AlertList, CreateAlertForm, NotificationPreferences } from '@/components/alerts';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage alerts and notification preferences</p>
      </div>

      <Tabs defaultValue="alerts">
        <TabsList>
          <TabsTrigger value="alerts">Price Alerts</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
        </TabsList>

        <TabsContent value="alerts" className="mt-4">
          <div className="grid gap-6 md:grid-cols-[1fr_350px]">
            <AlertList />
            <CreateAlertForm />
          </div>
        </TabsContent>

        <TabsContent value="notifications" className="mt-4">
          <div className="max-w-2xl">
            <NotificationPreferences />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}


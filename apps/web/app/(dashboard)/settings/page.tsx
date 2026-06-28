'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiGet } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { Building2, Users, Shield } from 'lucide-react';

interface Organization {
  id: string;
  name: string;
  plan: string;
  members_count: number;
  created_at: string;
}

export default function SettingsPage() {
  const [org, setOrg] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await apiGet<Organization>('/api/organization/');
        setOrg(data);
      } catch {
        setOrg(null);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-gray-500">Manage your organization settings</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading settings...</div>
      ) : (
        <div className="max-w-2xl space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-brand-100 rounded-lg">
                  <Building2 className="h-5 w-5 text-brand-600" />
                </div>
                <div>
                  <CardTitle className="text-lg">Organization</CardTitle>
                  <CardDescription>Your organization details</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">
                  Organization Name
                </label>
                <p className="text-lg font-semibold text-gray-900">
                  {org?.name || 'Not configured'}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">Plan</label>
                  <Badge variant="default">{org?.plan || 'Free'}</Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">Members</label>
                  <div className="flex items-center gap-1.5">
                    <Users className="h-4 w-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-900">
                      {org?.members_count ?? 0}
                    </span>
                  </div>
                </div>
              </div>
              {org?.created_at && (
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">
                    Created
                  </label>
                  <p className="text-sm text-gray-700">
                    {new Date(org.created_at).toLocaleDateString()}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-gray-100 rounded-lg">
                  <Shield className="h-5 w-5 text-gray-500" />
                </div>
                <div>
                  <CardTitle className="text-lg">Security</CardTitle>
                  <CardDescription>Authentication and access settings</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-500 text-center py-4">
                Security settings coming soon
              </p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

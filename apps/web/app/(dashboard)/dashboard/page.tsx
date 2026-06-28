'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { FileText, FilePlus, CheckSquare, Shield, AlertTriangle, Clock } from 'lucide-react';
import { apiGet } from '@/lib/api-client';

interface DashboardStats {
  total_contracts: number;
  pending_reviews: number;
  active_obligations: number;
  pending_signatures: number;
  overdue_obligations: number;
  compliance_score: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    async function loadStats() {
      try {
        const [contracts, obligations, documents] = await Promise.all([
          apiGet<{ total: number }>('/api/contracts/?per_page=1'),
          apiGet<{ obligations: unknown[] }>('/api/obligations/overdue'),
          apiGet<{ total: number }>('/api/documents/?per_page=1'),
        ]);
        setStats({
          total_contracts: contracts.total || 0,
          pending_reviews: 0,
          active_obligations: 0,
          pending_signatures: 0,
          overdue_obligations: obligations.obligations?.length || 0,
          compliance_score: 0,
        });
      } catch {
        // API might not be running yet
        setStats({
          total_contracts: 0,
          pending_reviews: 0,
          active_obligations: 0,
          pending_signatures: 0,
          overdue_obligations: 0,
          compliance_score: 0,
        });
      }
    }
    loadStats();
  }, []);

  const cards = [
    { title: 'Total Contracts', value: stats?.total_contracts ?? '-', icon: FileText, color: 'text-blue-600' },
    { title: 'Pending Reviews', value: stats?.pending_reviews ?? '-', icon: Clock, color: 'text-yellow-600' },
    { title: 'Active Obligations', value: stats?.active_obligations ?? '-', icon: CheckSquare, color: 'text-green-600' },
    { title: 'Pending Signatures', value: stats?.pending_signatures ?? '-', icon: FilePlus, color: 'text-purple-600' },
    { title: 'Overdue', value: stats?.overdue_obligations ?? '-', icon: AlertTriangle, color: 'text-red-600' },
    { title: 'Compliance Score', value: stats?.compliance_score ? `${Math.round(stats.compliance_score * 100)}%` : '-', icon: Shield, color: 'text-brand-600' },
  ];

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-gray-500">Overview of your contract intelligence platform</p>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((card) => (
          <Card key={card.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">
                {card.title}
              </CardTitle>
              <card.icon className={`h-5 w-5 ${card.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{card.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center text-sm text-gray-500 py-8">
              Upload your first contract to get started
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Upcoming Deadlines</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center text-sm text-gray-500 py-8">
              No upcoming deadlines
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

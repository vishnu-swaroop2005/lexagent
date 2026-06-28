'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiGet } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { CheckSquare, AlertTriangle, Clock, Filter } from 'lucide-react';

interface Obligation {
  id: string;
  title: string;
  description: string;
  due_date: string;
  status: string;
  priority: string;
  assigned_to: string;
  contract_title: string;
}

interface ObligationsResponse {
  obligations: Obligation[];
  total: number;
}

const statusVariant = (status: string) => {
  switch (status.toLowerCase()) {
    case 'completed':
      return 'success' as const;
    case 'in_progress':
      return 'default' as const;
    case 'pending':
      return 'warning' as const;
    case 'overdue':
      return 'destructive' as const;
    default:
      return 'secondary' as const;
  }
};

const priorityVariant = (priority: string) => {
  switch (priority.toLowerCase()) {
    case 'critical':
    case 'high':
      return 'destructive' as const;
    case 'medium':
      return 'warning' as const;
    case 'low':
      return 'success' as const;
    default:
      return 'secondary' as const;
  }
};

const STATUS_FILTERS = ['All', 'Pending', 'In Progress', 'Completed', 'Overdue'];

export default function ObligationsPage() {
  const [obligations, setObligations] = useState<Obligation[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('All');

  useEffect(() => {
    async function load() {
      try {
        const data = await apiGet<ObligationsResponse>('/api/obligations/');
        setObligations(data.obligations || []);
      } catch {
        setObligations([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const isOverdue = (dueDate: string, status: string) => {
    if (status.toLowerCase() === 'completed') return false;
    return new Date(dueDate) < new Date();
  };

  const filtered = obligations.filter((o) => {
    if (statusFilter === 'All') return true;
    if (statusFilter === 'Overdue') return isOverdue(o.due_date, o.status);
    return o.status.toLowerCase() === statusFilter.toLowerCase().replace(' ', '_');
  });

  const overdueCount = obligations.filter((o) => isOverdue(o.due_date, o.status)).length;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Obligations</h1>
        <p className="mt-1 text-gray-500">Track and manage contract obligations and deadlines</p>
      </div>

      {overdueCount > 0 && (
        <div className="mb-6 p-4 rounded-lg bg-red-50 border border-red-200 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-800">
              {overdueCount} overdue obligation{overdueCount > 1 ? 's' : ''} require{overdueCount === 1 ? 's' : ''} attention
            </p>
            <p className="text-xs text-red-600 mt-0.5">Review and address overdue items immediately</p>
          </div>
        </div>
      )}

      <div className="flex gap-2 mb-6 flex-wrap">
        {STATUS_FILTERS.map((filter) => (
          <Button
            key={filter}
            variant={statusFilter === filter ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter(filter)}
          >
            {filter}
            {filter === 'Overdue' && overdueCount > 0 && (
              <span className="ml-1.5 bg-white/20 rounded-full px-1.5 text-xs">
                {overdueCount}
              </span>
            )}
          </Button>
        ))}
      </div>

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <div className="text-center py-12 text-gray-500">Loading obligations...</div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-12">
              <CheckSquare className="mx-auto h-12 w-12 text-gray-300" />
              <p className="mt-4 text-gray-500">No obligations found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="pb-3 pr-4 font-medium">Title</th>
                    <th className="pb-3 pr-4 font-medium">Due Date</th>
                    <th className="pb-3 pr-4 font-medium">Status</th>
                    <th className="pb-3 pr-4 font-medium">Priority</th>
                    <th className="pb-3 pr-4 font-medium">Assigned To</th>
                    <th className="pb-3 font-medium">Contract</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((obligation) => {
                    const overdue = isOverdue(obligation.due_date, obligation.status);
                    return (
                      <tr
                        key={obligation.id}
                        className={cn(
                          'border-b last:border-0',
                          overdue ? 'bg-red-50/50 hover:bg-red-50' : 'hover:bg-gray-50'
                        )}
                      >
                        <td className="py-4 pr-4">
                          <div>
                            <p className="font-medium text-gray-900">{obligation.title}</p>
                            {obligation.description && (
                              <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                                {obligation.description}
                              </p>
                            )}
                          </div>
                        </td>
                        <td className="py-4 pr-4">
                          <div className="flex items-center gap-1.5">
                            {overdue && <AlertTriangle className="h-3.5 w-3.5 text-red-500" />}
                            <span className={cn('text-gray-600', overdue && 'text-red-600 font-medium')}>
                              {new Date(obligation.due_date).toLocaleDateString()}
                            </span>
                          </div>
                        </td>
                        <td className="py-4 pr-4">
                          <Badge variant={overdue ? 'destructive' : statusVariant(obligation.status)}>
                            {overdue ? 'Overdue' : obligation.status.replace(/_/g, ' ')}
                          </Badge>
                        </td>
                        <td className="py-4 pr-4">
                          <Badge variant={priorityVariant(obligation.priority)}>
                            {obligation.priority}
                          </Badge>
                        </td>
                        <td className="py-4 pr-4 text-gray-600">
                          {obligation.assigned_to || 'Unassigned'}
                        </td>
                        <td className="py-4 text-gray-600">
                          {obligation.contract_title || '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

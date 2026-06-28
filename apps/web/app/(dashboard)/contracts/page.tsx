'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiGet } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { Upload, Eye, FileText, Search } from 'lucide-react';

interface Contract {
  id: string;
  title: string;
  status: string;
  counterparty: string;
  created_at: string;
  updated_at: string;
}

interface ContractsResponse {
  contracts: Contract[];
  total: number;
}

const statusVariant = (status: string) => {
  switch (status.toLowerCase()) {
    case 'active':
    case 'executed':
      return 'success' as const;
    case 'pending':
    case 'in_review':
      return 'warning' as const;
    case 'expired':
    case 'terminated':
      return 'destructive' as const;
    case 'draft':
      return 'secondary' as const;
    default:
      return 'default' as const;
  }
};

export default function ContractsPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const data = await apiGet<ContractsResponse>('/api/contracts/');
        setContracts(data.contracts || []);
      } catch {
        setContracts([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filtered = contracts.filter(
    (c) =>
      c.title.toLowerCase().includes(search.toLowerCase()) ||
      c.counterparty.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Contracts</h1>
          <p className="mt-1 text-gray-500">Manage and review your contracts</p>
        </div>
        <Link href="/contracts/upload">
          <Button>
            <Upload className="mr-2 h-4 w-4" />
            Upload Contract
          </Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search contracts..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-12 text-gray-500">Loading contracts...</div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="mx-auto h-12 w-12 text-gray-300" />
              <p className="mt-4 text-gray-500">No contracts found</p>
              <Link href="/contracts/upload">
                <Button variant="outline" className="mt-4">
                  Upload your first contract
                </Button>
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="pb-3 pr-4 font-medium">Title</th>
                    <th className="pb-3 pr-4 font-medium">Status</th>
                    <th className="pb-3 pr-4 font-medium">Counterparty</th>
                    <th className="pb-3 pr-4 font-medium">Date</th>
                    <th className="pb-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((contract) => (
                    <tr key={contract.id} className="border-b last:border-0 hover:bg-gray-50">
                      <td className="py-4 pr-4">
                        <Link
                          href={`/contracts/${contract.id}`}
                          className="font-medium text-gray-900 hover:text-brand-600"
                        >
                          {contract.title}
                        </Link>
                      </td>
                      <td className="py-4 pr-4">
                        <Badge variant={statusVariant(contract.status)}>
                          {contract.status.replace(/_/g, ' ')}
                        </Badge>
                      </td>
                      <td className="py-4 pr-4 text-gray-600">{contract.counterparty}</td>
                      <td className="py-4 pr-4 text-gray-600">
                        {new Date(contract.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-4">
                        <Link href={`/contracts/${contract.id}`}>
                          <Button variant="ghost" size="sm">
                            <Eye className="h-4 w-4" />
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiGet } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { Search, BookOpen, Check, Filter } from 'lucide-react';

interface ClauseItem {
  id: string;
  title: string;
  clause_type: string;
  text: string;
  is_approved: boolean;
  risk_level: string;
  created_at: string;
}

interface ClauseLibraryResponse {
  clauses: ClauseItem[];
  total: number;
}

const CLAUSE_TYPES = [
  'All',
  'Indemnification',
  'Limitation of Liability',
  'Termination',
  'Confidentiality',
  'Non-Compete',
  'Intellectual Property',
  'Force Majeure',
  'Governing Law',
  'Dispute Resolution',
];

const riskVariant = (risk: string) => {
  switch (risk.toLowerCase()) {
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

export default function LibraryPage() {
  const [clauses, setClauses] = useState<ClauseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState('All');
  const [approvedOnly, setApprovedOnly] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await apiGet<ClauseLibraryResponse>('/api/library/clauses');
        setClauses(data.clauses || []);
      } catch {
        setClauses([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filtered = clauses.filter((clause) => {
    const matchesSearch =
      clause.title.toLowerCase().includes(search.toLowerCase()) ||
      clause.text.toLowerCase().includes(search.toLowerCase());
    const matchesType =
      selectedType === 'All' ||
      clause.clause_type.toLowerCase() === selectedType.toLowerCase();
    const matchesApproved = !approvedOnly || clause.is_approved;
    return matchesSearch && matchesType && matchesApproved;
  });

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Clause Library</h1>
        <p className="mt-1 text-gray-500">Browse and search standard contract clauses</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search clauses..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          className="px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {CLAUSE_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
        <Button
          variant={approvedOnly ? 'default' : 'outline'}
          onClick={() => setApprovedOnly(!approvedOnly)}
        >
          <Check className="mr-2 h-4 w-4" />
          Approved Only
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading clause library...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12">
          <BookOpen className="mx-auto h-12 w-12 text-gray-300" />
          <p className="mt-4 text-gray-500">No clauses found</p>
          <p className="text-sm text-gray-400">Try adjusting your search or filters</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((clause) => (
            <Card key={clause.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base leading-tight">{clause.title}</CardTitle>
                  {clause.is_approved && (
                    <div className="flex-shrink-0">
                      <Badge variant="success">
                        <Check className="mr-1 h-3 w-3" />
                        Approved
                      </Badge>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="outline" className="text-xs">
                    {clause.clause_type.replace(/_/g, ' ')}
                  </Badge>
                  <Badge variant={riskVariant(clause.risk_level)} className="text-xs">
                    {clause.risk_level} risk
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600 line-clamp-4">{clause.text}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

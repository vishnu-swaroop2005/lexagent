'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiGet, apiPost } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { ArrowLeft, Play, Check, X, AlertTriangle, FileText, Clock } from 'lucide-react';

interface ContractDetail {
  id: string;
  title: string;
  status: string;
  counterparty: string;
  created_at: string;
  updated_at: string;
  file_type: string;
  file_url: string;
  summary: string;
}

interface Clause {
  id: string;
  clause_type: string;
  text: string;
  risk_level: string;
  explanation: string;
}

interface ReviewFinding {
  id: string;
  category: string;
  severity: string;
  finding: string;
  recommendation: string;
}

interface RedlineChange {
  id: string;
  original_text: string;
  suggested_text: string;
  reason: string;
  status: string;
}

type Tab = 'overview' | 'clauses' | 'review' | 'redline';

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
    default:
      return 'secondary' as const;
  }
};

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

const severityVariant = (severity: string) => {
  switch (severity.toLowerCase()) {
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

export default function ContractDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [contract, setContract] = useState<ContractDetail | null>(null);
  const [clauses, setClauses] = useState<Clause[]>([]);
  const [findings, setFindings] = useState<ReviewFinding[]>([]);
  const [redlines, setRedlines] = useState<RedlineChange[]>([]);
  const [loading, setLoading] = useState(true);
  const [reviewing, setReviewing] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await apiGet<ContractDetail>(`/api/contracts/${id}`);
        setContract(data);
      } catch {
        // handle error
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  useEffect(() => {
    if (activeTab === 'clauses') {
      apiGet<{ clauses: Clause[] }>(`/api/contracts/${id}/clauses`)
        .then((data) => setClauses(data.clauses || []))
        .catch(() => setClauses([]));
    }
    if (activeTab === 'review') {
      apiGet<{ findings: ReviewFinding[] }>(`/api/contracts/${id}/review`)
        .then((data) => setFindings(data.findings || []))
        .catch(() => setFindings([]));
    }
    if (activeTab === 'redline') {
      apiGet<{ changes: RedlineChange[] }>(`/api/contracts/${id}/redline`)
        .then((data) => setRedlines(data.changes || []))
        .catch(() => setRedlines([]));
    }
  }, [activeTab, id]);

  const startReview = async () => {
    setReviewing(true);
    try {
      const data = await apiPost<{ findings: ReviewFinding[] }>(`/api/contracts/${id}/review`);
      setFindings(data.findings || []);
    } catch {
      // handle error
    } finally {
      setReviewing(false);
    }
  };

  const handleRedlineAction = async (changeId: string, action: 'accept' | 'reject') => {
    try {
      await apiPost(`/api/contracts/${id}/redline/${changeId}/${action}`);
      setRedlines((prev) =>
        prev.map((r) => (r.id === changeId ? { ...r, status: action === 'accept' ? 'accepted' : 'rejected' } : r))
      );
    } catch {
      // handle error
    }
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'clauses', label: 'Clauses' },
    { key: 'review', label: 'Review' },
    { key: 'redline', label: 'Redline' },
  ];

  if (loading) {
    return (
      <div className="text-center py-12 text-gray-500">Loading contract...</div>
    );
  }

  if (!contract) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Contract not found</p>
        <Link href="/contracts">
          <Button variant="outline" className="mt-4">Back to Contracts</Button>
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <Link href="/contracts" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-4">
          <ArrowLeft className="mr-1 h-4 w-4" />
          Back to Contracts
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{contract.title}</h1>
            <p className="mt-1 text-gray-500">Counterparty: {contract.counterparty}</p>
          </div>
          <Badge variant={statusVariant(contract.status)} className="text-sm">
            {contract.status.replace(/_/g, ' ')}
          </Badge>
        </div>
      </div>

      <div className="border-b mb-6">
        <nav className="flex gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                'pb-3 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab.key
                  ? 'border-brand-600 text-brand-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Contract Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Status</p>
                  <Badge variant={statusVariant(contract.status)} className="mt-1">
                    {contract.status.replace(/_/g, ' ')}
                  </Badge>
                </div>
                <div>
                  <p className="text-gray-500">File Type</p>
                  <p className="font-medium mt-1 uppercase">{contract.file_type || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-gray-500">Created</p>
                  <p className="font-medium mt-1">{new Date(contract.created_at).toLocaleDateString()}</p>
                </div>
                <div>
                  <p className="text-gray-500">Last Updated</p>
                  <p className="font-medium mt-1">{new Date(contract.updated_at).toLocaleDateString()}</p>
                </div>
                <div>
                  <p className="text-gray-500">Counterparty</p>
                  <p className="font-medium mt-1">{contract.counterparty}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Summary</CardTitle>
            </CardHeader>
            <CardContent>
              {contract.summary ? (
                <p className="text-sm text-gray-700 leading-relaxed">{contract.summary}</p>
              ) : (
                <div className="text-center py-6">
                  <FileText className="mx-auto h-8 w-8 text-gray-300" />
                  <p className="mt-2 text-sm text-gray-500">
                    Summary will appear after AI analysis completes
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'clauses' && (
        <div className="space-y-4">
          {clauses.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <FileText className="mx-auto h-8 w-8 text-gray-300" />
                <p className="mt-2 text-sm text-gray-500">
                  No clauses extracted yet. Clauses will appear after AI analysis.
                </p>
              </CardContent>
            </Card>
          ) : (
            clauses.map((clause) => (
              <Card key={clause.id}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{clause.clause_type.replace(/_/g, ' ')}</CardTitle>
                    <Badge variant={riskVariant(clause.risk_level)}>
                      {clause.risk_level} risk
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-700 mb-3">{clause.text}</p>
                  {clause.explanation && (
                    <div className="bg-gray-50 rounded-md p-3">
                      <p className="text-xs text-gray-500 font-medium mb-1">AI Explanation</p>
                      <p className="text-sm text-gray-600">{clause.explanation}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {activeTab === 'review' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">AI Review</h2>
            <Button onClick={startReview} disabled={reviewing}>
              <Play className="mr-2 h-4 w-4" />
              {reviewing ? 'Reviewing...' : 'Start AI Review'}
            </Button>
          </div>

          {findings.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <AlertTriangle className="mx-auto h-8 w-8 text-gray-300" />
                <p className="mt-2 text-sm text-gray-500">
                  No findings yet. Click &quot;Start AI Review&quot; to analyze this contract.
                </p>
              </CardContent>
            </Card>
          ) : (
            findings.map((finding) => (
              <Card key={finding.id}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{finding.category}</CardTitle>
                    <Badge variant={severityVariant(finding.severity)}>
                      {finding.severity}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <p className="text-xs text-gray-500 font-medium mb-1">Finding</p>
                    <p className="text-sm text-gray-700">{finding.finding}</p>
                  </div>
                  <div className="bg-blue-50 rounded-md p-3">
                    <p className="text-xs text-blue-600 font-medium mb-1">Recommendation</p>
                    <p className="text-sm text-blue-800">{finding.recommendation}</p>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {activeTab === 'redline' && (
        <div className="space-y-4">
          {redlines.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <FileText className="mx-auto h-8 w-8 text-gray-300" />
                <p className="mt-2 text-sm text-gray-500">
                  No redline changes available for this contract.
                </p>
              </CardContent>
            </Card>
          ) : (
            redlines.map((change) => (
              <Card key={change.id} className={cn(
                change.status === 'accepted' && 'border-green-200 bg-green-50/30',
                change.status === 'rejected' && 'border-red-200 bg-red-50/30'
              )}>
                <CardContent className="pt-6 space-y-3">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-gray-500 font-medium mb-1">Original</p>
                      <p className="text-sm text-red-700 bg-red-50 p-3 rounded-md line-through">
                        {change.original_text}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 font-medium mb-1">Suggested</p>
                      <p className="text-sm text-green-700 bg-green-50 p-3 rounded-md">
                        {change.suggested_text}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Reason:</span> {change.reason}
                  </p>
                  {change.status === 'pending' ? (
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => handleRedlineAction(change.id, 'accept')}>
                        <Check className="mr-1 h-3 w-3" />
                        Accept
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => handleRedlineAction(change.id, 'reject')}>
                        <X className="mr-1 h-3 w-3" />
                        Reject
                      </Button>
                    </div>
                  ) : (
                    <Badge variant={change.status === 'accepted' ? 'success' : 'destructive'}>
                      {change.status}
                    </Badge>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  );
}

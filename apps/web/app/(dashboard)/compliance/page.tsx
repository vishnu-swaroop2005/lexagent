'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiGet, apiPost } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { Shield, Play, AlertTriangle, Check, FileText, Search } from 'lucide-react';

interface ComplianceScore {
  framework: string;
  score: number;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  last_checked: string;
}

interface ComplianceResult {
  id: string;
  check_name: string;
  status: string;
  severity: string;
  description: string;
  recommendation: string;
}

interface Contract {
  id: string;
  title: string;
}

export default function CompliancePage() {
  const [scores, setScores] = useState<ComplianceScore[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [selectedContract, setSelectedContract] = useState('');
  const [results, setResults] = useState<ComplianceResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [scoresData, contractsData] = await Promise.all([
          apiGet<{ scores: ComplianceScore[] }>('/api/compliance/scores'),
          apiGet<{ contracts: Contract[] }>('/api/contracts/?per_page=100'),
        ]);
        setScores(scoresData.scores || []);
        setContracts(contractsData.contracts || []);
      } catch {
        setScores([]);
        setContracts([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const runCheck = async () => {
    if (!selectedContract) return;
    setChecking(true);
    try {
      const data = await apiPost<{ results: ComplianceResult[] }>('/api/compliance/check', {
        contract_id: selectedContract,
      });
      setResults(data.results || []);
    } catch {
      setResults([]);
    } finally {
      setChecking(false);
    }
  };

  const scoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const scoreBarColor = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-yellow-500';
    return 'bg-red-500';
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

  const frameworkDisplayName = (framework: string) => {
    const names: Record<string, string> = {
      gdpr: 'GDPR',
      soc2: 'SOC 2',
      hipaa: 'HIPAA',
      ccpa: 'CCPA',
    };
    return names[framework.toLowerCase()] || framework.toUpperCase();
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Compliance</h1>
        <p className="mt-1 text-gray-500">Monitor compliance scores and run checks against your contracts</p>
      </div>

      {/* Compliance Scores */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {loading ? (
          <div className="col-span-full text-center py-8 text-gray-500">
            Loading compliance data...
          </div>
        ) : scores.length > 0 ? (
          scores.map((item) => (
            <Card key={item.framework}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-gray-500">
                    {frameworkDisplayName(item.framework)}
                  </CardTitle>
                  <Shield className={cn('h-5 w-5', scoreColor(item.score))} />
                </div>
              </CardHeader>
              <CardContent>
                <div className={cn('text-3xl font-bold', scoreColor(item.score))}>
                  {Math.round(item.score)}%
                </div>
                <div className="mt-3 w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={cn('h-2 rounded-full transition-all', scoreBarColor(item.score))}
                    style={{ width: `${Math.min(100, item.score)}%` }}
                  />
                </div>
                <div className="flex justify-between mt-2 text-xs text-gray-500">
                  <span>{item.passed_checks} passed</span>
                  <span>{item.failed_checks} failed</span>
                </div>
                {item.last_checked && (
                  <p className="text-xs text-gray-400 mt-2">
                    Last checked: {new Date(item.last_checked).toLocaleDateString()}
                  </p>
                )}
              </CardContent>
            </Card>
          ))
        ) : (
          <>
            {['GDPR', 'SOC 2'].map((framework) => (
              <Card key={framework}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium text-gray-500">{framework}</CardTitle>
                    <Shield className="h-5 w-5 text-gray-300" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-gray-300">--%</div>
                  <div className="mt-3 w-full bg-gray-200 rounded-full h-2" />
                  <p className="text-xs text-gray-400 mt-2">No data yet</p>
                </CardContent>
              </Card>
            ))}
          </>
        )}
      </div>

      {/* Run Compliance Check */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="text-lg">Run Compliance Check</CardTitle>
          <CardDescription>
            Select a contract to run a compliance analysis against GDPR and SOC 2 standards
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Select Contract
              </label>
              <select
                value={selectedContract}
                onChange={(e) => setSelectedContract(e.target.value)}
                className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <option value="">Choose a contract...</option>
                {contracts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </select>
            </div>
            <Button onClick={runCheck} disabled={!selectedContract || checking}>
              <Play className="mr-2 h-4 w-4" />
              {checking ? 'Checking...' : 'Run Check'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Check Results */}
      {results.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Check Results</h2>
          {results.map((result) => (
            <Card key={result.id}>
              <CardContent className="pt-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    {result.status === 'passed' ? (
                      <Check className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    ) : (
                      <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
                    )}
                    <div>
                      <p className="font-medium text-gray-900">{result.check_name}</p>
                      <p className="text-sm text-gray-600 mt-1">{result.description}</p>
                      {result.status === 'failed' && result.recommendation && (
                        <div className="mt-3 p-3 bg-blue-50 rounded-md">
                          <p className="text-xs text-blue-600 font-medium mb-1">Recommendation</p>
                          <p className="text-sm text-blue-800">{result.recommendation}</p>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Badge variant={severityVariant(result.severity)}>
                      {result.severity}
                    </Badge>
                    <Badge variant={result.status === 'passed' ? 'success' : 'destructive'}>
                      {result.status}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

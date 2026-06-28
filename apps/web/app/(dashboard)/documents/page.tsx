'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiGet } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { Plus, Eye, FileText, Search } from 'lucide-react';

interface Document {
  id: string;
  title: string;
  doc_type: string;
  status: string;
  created_at: string;
}

interface DocumentsResponse {
  documents: Document[];
  total: number;
}

const statusVariant = (status: string) => {
  switch (status.toLowerCase()) {
    case 'completed':
    case 'signed':
      return 'success' as const;
    case 'pending_signature':
    case 'sent':
      return 'warning' as const;
    case 'expired':
    case 'rejected':
      return 'destructive' as const;
    case 'draft':
      return 'secondary' as const;
    default:
      return 'default' as const;
  }
};

const docTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    nda: 'NDA',
    mou: 'MOU',
    service_agreement: 'Service Agreement',
    employment: 'Employment',
    lease: 'Lease',
  };
  return labels[type] || type.replace(/_/g, ' ');
};

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const data = await apiGet<DocumentsResponse>('/api/documents/');
        setDocuments(data.documents || []);
      } catch {
        setDocuments([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filtered = documents.filter((d) =>
    d.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Documents</h1>
          <p className="mt-1 text-gray-500">Create and manage legal documents</p>
        </div>
        <Link href="/documents/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create Document
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
                placeholder="Search documents..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-12 text-gray-500">Loading documents...</div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="mx-auto h-12 w-12 text-gray-300" />
              <p className="mt-4 text-gray-500">No documents found</p>
              <Link href="/documents/new">
                <Button variant="outline" className="mt-4">
                  Create your first document
                </Button>
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="pb-3 pr-4 font-medium">Title</th>
                    <th className="pb-3 pr-4 font-medium">Type</th>
                    <th className="pb-3 pr-4 font-medium">Status</th>
                    <th className="pb-3 pr-4 font-medium">Date</th>
                    <th className="pb-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((doc) => (
                    <tr key={doc.id} className="border-b last:border-0 hover:bg-gray-50">
                      <td className="py-4 pr-4">
                        <Link
                          href={`/documents/${doc.id}`}
                          className="font-medium text-gray-900 hover:text-brand-600"
                        >
                          {doc.title}
                        </Link>
                      </td>
                      <td className="py-4 pr-4">
                        <Badge variant="outline">{docTypeLabel(doc.doc_type)}</Badge>
                      </td>
                      <td className="py-4 pr-4">
                        <Badge variant={statusVariant(doc.status)}>
                          {doc.status.replace(/_/g, ' ')}
                        </Badge>
                      </td>
                      <td className="py-4 pr-4 text-gray-600">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-4">
                        <Link href={`/documents/${doc.id}`}>
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

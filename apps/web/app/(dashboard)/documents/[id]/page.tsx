'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiGet, apiPost } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { ArrowLeft, Download, Send, FileText, Check, Clock, X } from 'lucide-react';

interface DocumentParty {
  id: string;
  name: string;
  email: string;
  status: string;
  signed_at: string | null;
}

interface DocumentDetail {
  id: string;
  title: string;
  doc_type: string;
  status: string;
  content: string;
  created_at: string;
  updated_at: string;
  parties: DocumentParty[];
}

const statusVariant = (status: string) => {
  switch (status.toLowerCase()) {
    case 'completed':
    case 'signed':
      return 'success' as const;
    case 'pending_signature':
    case 'pending':
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

const partyStatusIcon = (status: string) => {
  switch (status.toLowerCase()) {
    case 'signed':
      return <Check className="h-4 w-4 text-green-600" />;
    case 'pending':
      return <Clock className="h-4 w-4 text-yellow-600" />;
    case 'rejected':
      return <X className="h-4 w-4 text-red-600" />;
    default:
      return <Clock className="h-4 w-4 text-gray-400" />;
  }
};

export default function DocumentDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await apiGet<DocumentDetail>(`/api/documents/${id}`);
        setDocument(data);
      } catch {
        // handle error
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const generatePdf = async () => {
    setGenerating(true);
    try {
      const data = await apiPost<{ pdf_url: string }>(`/api/documents/${id}/pdf`);
      if (data.pdf_url) {
        window.open(data.pdf_url, '_blank');
      }
    } catch {
      // handle error
    } finally {
      setGenerating(false);
    }
  };

  const sendForSignature = async () => {
    setSending(true);
    try {
      await apiPost(`/api/documents/${id}/send`);
      const updated = await apiGet<DocumentDetail>(`/api/documents/${id}`);
      setDocument(updated);
    } catch {
      // handle error
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading document...</div>;
  }

  if (!document) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Document not found</p>
        <Link href="/documents">
          <Button variant="outline" className="mt-4">Back to Documents</Button>
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <Link href="/documents" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-4">
          <ArrowLeft className="mr-1 h-4 w-4" />
          Back to Documents
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{document.title}</h1>
            <p className="mt-1 text-gray-500">
              {document.doc_type.replace(/_/g, ' ')} &middot; Created{' '}
              {new Date(document.created_at).toLocaleDateString()}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={statusVariant(document.status)} className="text-sm">
              {document.status.replace(/_/g, ' ')}
            </Badge>
          </div>
        </div>
      </div>

      <div className="flex gap-3 mb-6">
        <Button variant="outline" onClick={generatePdf} disabled={generating}>
          <Download className="mr-2 h-4 w-4" />
          {generating ? 'Generating...' : 'Generate PDF'}
        </Button>
        <Button onClick={sendForSignature} disabled={sending}>
          <Send className="mr-2 h-4 w-4" />
          {sending ? 'Sending...' : 'Send for Signature'}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Document Content</CardTitle>
            </CardHeader>
            <CardContent>
              {document.content ? (
                <div className="prose prose-sm max-w-none whitespace-pre-wrap text-gray-700 leading-relaxed">
                  {document.content}
                </div>
              ) : (
                <div className="text-center py-8">
                  <FileText className="mx-auto h-8 w-8 text-gray-300" />
                  <p className="mt-2 text-sm text-gray-500">No content available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Parties</CardTitle>
              <CardDescription>Signatories for this document</CardDescription>
            </CardHeader>
            <CardContent>
              {document.parties && document.parties.length > 0 ? (
                <div className="space-y-3">
                  {document.parties.map((party) => (
                    <div key={party.id} className="flex items-center gap-3 p-3 border rounded-md">
                      {partyStatusIcon(party.status)}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{party.name}</p>
                        <p className="text-xs text-gray-500 truncate">{party.email}</p>
                      </div>
                      <Badge variant={statusVariant(party.status)} className="text-xs">
                        {party.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 text-center py-4">No parties added yet</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Type</span>
                <span className="font-medium">{document.doc_type.replace(/_/g, ' ')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Created</span>
                <span className="font-medium">{new Date(document.created_at).toLocaleDateString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Last Updated</span>
                <span className="font-medium">{new Date(document.updated_at).toLocaleDateString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Status</span>
                <Badge variant={statusVariant(document.status)}>
                  {document.status.replace(/_/g, ' ')}
                </Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

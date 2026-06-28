'use client';

import { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiGet, apiPost } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { SignatureCanvas } from '@/components/documents/signature-canvas';
import { Check, FileText, AlertTriangle } from 'lucide-react';

interface SigningDocument {
  id: string;
  title: string;
  doc_type: string;
  content: string;
  party_name: string;
  party_email: string;
  status: string;
}

export default function SignDocumentPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const id = params.id as string;
  const token = searchParams.get('token') || '';

  const [document, setDocument] = useState<SigningDocument | null>(null);
  const [signature, setSignature] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [signed, setSigned] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      if (!token) {
        setError('Invalid signing link. No token provided.');
        setLoading(false);
        return;
      }
      try {
        const data = await apiGet<SigningDocument>(`/api/documents/sign/${token}`);
        setDocument(data);
        if (data.status === 'signed') {
          setSigned(true);
        }
      } catch {
        setError('Unable to load document. The link may be invalid or expired.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [token]);

  const handleSubmit = async () => {
    if (!signature) {
      setError('Please draw your signature before submitting.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      await apiPost(`/api/documents/sign/${token}`, { signature });
      setSigned(true);
    } catch {
      setError('Failed to submit signature. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <p className="text-gray-500">Loading document...</p>
      </div>
    );
  }

  if (signed) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Card className="max-w-md w-full text-center">
          <CardContent className="pt-8 pb-8">
            <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
              <Check className="h-8 w-8 text-green-600" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Document Signed</h2>
            <p className="text-gray-500">
              Your signature has been recorded successfully. All parties will be notified.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error && !document) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Card className="max-w-md w-full text-center">
          <CardContent className="pt-8 pb-8">
            <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
              <AlertTriangle className="h-8 w-8 text-red-600" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Error</h2>
            <p className="text-gray-500">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!document) return null;

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6 text-center">
        <h1 className="text-3xl font-bold text-gray-900">Sign Document</h1>
        <p className="mt-1 text-gray-500">
          {document.party_name}, you have been asked to sign this document.
        </p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">{document.title}</CardTitle>
              <CardDescription>{document.doc_type.replace(/_/g, ' ')}</CardDescription>
            </div>
            <Badge variant="warning">Pending Signature</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-y-auto border rounded-md p-4 bg-gray-50">
            <div className="prose prose-sm max-w-none whitespace-pre-wrap text-gray-700">
              {document.content}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Your Signature</CardTitle>
          <CardDescription>
            Draw your signature below using your mouse or finger on a touchscreen
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <SignatureCanvas onSignature={setSignature} />

          {error && (
            <div className="p-3 rounded-md bg-red-50 text-red-700 text-sm">{error}</div>
          )}

          <div className="flex items-center gap-3">
            <Button onClick={handleSubmit} disabled={submitting || !signature}>
              {submitting ? 'Submitting...' : 'Submit Signature'}
            </Button>
            <p className="text-xs text-gray-400">
              By signing, you agree to the terms of this document.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

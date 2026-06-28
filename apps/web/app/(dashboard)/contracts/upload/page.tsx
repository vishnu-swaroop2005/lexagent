'use client';

import { useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { apiUpload } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { Upload, FileText, X, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface UploadResponse {
  id: string;
  title: string;
}

export default function UploadContractPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [counterparty, setCounterparty] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const acceptedTypes = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  ];

  const handleFile = useCallback((f: File) => {
    if (!acceptedTypes.includes(f.type)) {
      setError('Only PDF and DOCX files are supported.');
      return;
    }
    setFile(f);
    setError('');
    if (!title) {
      setTitle(f.name.replace(/\.(pdf|docx)$/i, ''));
    }
  }, [title]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) handleFile(droppedFile);
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file.');
      return;
    }
    if (!title.trim()) {
      setError('Please enter a title.');
      return;
    }

    setUploading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', title.trim());
      formData.append('counterparty', counterparty.trim());

      const result = await apiUpload<UploadResponse>('/api/contracts/upload', formData);
      router.push(`/contracts/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <div className="mb-8">
        <Link href="/contracts" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-4">
          <ArrowLeft className="mr-1 h-4 w-4" />
          Back to Contracts
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Upload Contract</h1>
        <p className="mt-1 text-gray-500">Upload a PDF or DOCX contract for AI analysis</p>
      </div>

      <Card className="max-w-2xl">
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
                dragOver
                  ? 'border-brand-500 bg-brand-50'
                  : file
                    ? 'border-green-300 bg-green-50'
                    : 'border-gray-300 hover:border-gray-400'
              )}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx"
                onChange={(e) => {
                  const selected = e.target.files?.[0];
                  if (selected) handleFile(selected);
                }}
                className="hidden"
              />
              {file ? (
                <div className="flex items-center justify-center gap-3">
                  <FileText className="h-8 w-8 text-green-600" />
                  <div className="text-left">
                    <p className="font-medium text-gray-900">{file.name}</p>
                    <p className="text-sm text-gray-500">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                    }}
                    className="ml-4 p-1 rounded-full hover:bg-gray-200"
                  >
                    <X className="h-4 w-4 text-gray-500" />
                  </button>
                </div>
              ) : (
                <>
                  <Upload className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-4 text-gray-600">
                    Drag and drop your contract here, or click to browse
                  </p>
                  <p className="mt-1 text-sm text-gray-400">Supports PDF and DOCX files</p>
                </>
              )}
            </div>

            <div>
              <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
                Contract Title
              </label>
              <input
                id="title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Service Agreement with Acme Corp"
                className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label htmlFor="counterparty" className="block text-sm font-medium text-gray-700 mb-1">
                Counterparty
              </label>
              <input
                id="counterparty"
                type="text"
                value={counterparty}
                onChange={(e) => setCounterparty(e.target.value)}
                placeholder="e.g. Acme Corporation"
                className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            {error && (
              <div className="p-3 rounded-md bg-red-50 text-red-700 text-sm">{error}</div>
            )}

            <div className="flex gap-3">
              <Button type="submit" disabled={uploading || !file}>
                {uploading ? 'Uploading...' : 'Upload & Analyze'}
              </Button>
              <Link href="/contracts">
                <Button type="button" variant="outline">
                  Cancel
                </Button>
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

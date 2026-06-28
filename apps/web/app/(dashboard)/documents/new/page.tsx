'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiPost } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import {
  ArrowLeft,
  ArrowRight,
  FileText,
  Shield,
  Handshake,
  Briefcase,
  Home,
  Users,
  Check,
  Plus,
  Trash2,
  Send,
} from 'lucide-react';

interface DocType {
  id: string;
  label: string;
  description: string;
  icon: React.ElementType;
}

interface QuestionField {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'date' | 'number' | 'select';
  required: boolean;
  options?: string[];
  placeholder?: string;
}

interface Party {
  name: string;
  email: string;
}

const DOC_TYPES: DocType[] = [
  { id: 'nda', label: 'Non-Disclosure Agreement', description: 'Protect confidential information shared between parties', icon: Shield },
  { id: 'mou', label: 'Memorandum of Understanding', description: 'Outline a mutual agreement between parties', icon: Handshake },
  { id: 'service_agreement', label: 'Service Agreement', description: 'Define terms for services to be provided', icon: Briefcase },
  { id: 'employment', label: 'Employment Contract', description: 'Establish employment terms and conditions', icon: Users },
  { id: 'lease', label: 'Lease Agreement', description: 'Set terms for property rental or lease', icon: Home },
];

export default function NewDocumentPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [selectedType, setSelectedType] = useState('');
  const [questions, setQuestions] = useState<QuestionField[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [generatedContent, setGeneratedContent] = useState('');
  const [editedContent, setEditedContent] = useState('');
  const [parties, setParties] = useState<Party[]>([{ name: '', email: '' }]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const goNext = async () => {
    setError('');

    if (step === 1) {
      if (!selectedType) {
        setError('Please select a document type.');
        return;
      }
      setLoading(true);
      try {
        const data = await apiPost<{ fields: QuestionField[] }>('/api/documents/questionnaire', {
          doc_type: selectedType,
        });
        setQuestions(data.fields || []);
        setStep(2);
      } catch {
        setError('Failed to load questionnaire. Please try again.');
      } finally {
        setLoading(false);
      }
    }

    if (step === 2) {
      const missing = questions.filter((q) => q.required && !answers[q.name]?.trim());
      if (missing.length > 0) {
        setError(`Please fill in: ${missing.map((m) => m.label).join(', ')}`);
        return;
      }
      setLoading(true);
      try {
        const data = await apiPost<{ content: string }>('/api/documents/generate', {
          doc_type: selectedType,
          answers,
        });
        setGeneratedContent(data.content || '');
        setEditedContent(data.content || '');
        setStep(3);
      } catch {
        setError('Failed to generate document. Please try again.');
      } finally {
        setLoading(false);
      }
    }

    if (step === 3) {
      setStep(4);
    }

    if (step === 4) {
      const validParties = parties.filter((p) => p.name.trim() && p.email.trim());
      if (validParties.length === 0) {
        setError('Please add at least one party.');
        return;
      }
      setLoading(true);
      try {
        const data = await apiPost<{ id: string }>('/api/documents/', {
          doc_type: selectedType,
          content: editedContent,
          parties: validParties,
          answers,
        });
        router.push(`/documents/${data.id}`);
      } catch {
        setError('Failed to create document. Please try again.');
      } finally {
        setLoading(false);
      }
    }
  };

  const goBack = () => {
    setError('');
    setStep((s) => Math.max(1, s - 1));
  };

  const addParty = () => {
    setParties((prev) => [...prev, { name: '', email: '' }]);
  };

  const removeParty = (index: number) => {
    setParties((prev) => prev.filter((_, i) => i !== index));
  };

  const updateParty = (index: number, field: keyof Party, value: string) => {
    setParties((prev) =>
      prev.map((p, i) => (i === index ? { ...p, [field]: value } : p))
    );
  };

  const stepLabels = ['Document Type', 'Details', 'Preview', 'Parties'];

  return (
    <div>
      <div className="mb-8">
        <Link href="/documents" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-4">
          <ArrowLeft className="mr-1 h-4 w-4" />
          Back to Documents
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Create Document</h1>
        <p className="mt-1 text-gray-500">Generate a legal document with AI assistance</p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-8">
        {stepLabels.map((label, i) => (
          <div key={label} className="flex items-center">
            <div
              className={cn(
                'flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium',
                step > i + 1
                  ? 'bg-green-100 text-green-700'
                  : step === i + 1
                    ? 'bg-brand-100 text-brand-700'
                    : 'bg-gray-100 text-gray-400'
              )}
            >
              {step > i + 1 ? <Check className="h-4 w-4" /> : i + 1}
            </div>
            <span
              className={cn(
                'ml-2 text-sm',
                step === i + 1 ? 'text-gray-900 font-medium' : 'text-gray-500'
              )}
            >
              {label}
            </span>
            {i < stepLabels.length - 1 && (
              <div className="w-12 h-px bg-gray-300 mx-3" />
            )}
          </div>
        ))}
      </div>

      {/* Step 1: Select Document Type */}
      {step === 1 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {DOC_TYPES.map((docType) => (
            <Card
              key={docType.id}
              className={cn(
                'cursor-pointer transition-all hover:shadow-md',
                selectedType === docType.id && 'ring-2 ring-brand-500 border-brand-500'
              )}
              onClick={() => setSelectedType(docType.id)}
            >
              <CardHeader>
                <div className="flex items-start gap-3">
                  <div
                    className={cn(
                      'p-2 rounded-lg',
                      selectedType === docType.id ? 'bg-brand-100' : 'bg-gray-100'
                    )}
                  >
                    <docType.icon
                      className={cn(
                        'h-5 w-5',
                        selectedType === docType.id ? 'text-brand-600' : 'text-gray-500'
                      )}
                    />
                  </div>
                  <div>
                    <CardTitle className="text-base">{docType.label}</CardTitle>
                    <CardDescription className="mt-1">{docType.description}</CardDescription>
                  </div>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}

      {/* Step 2: Questionnaire */}
      {step === 2 && (
        <Card className="max-w-2xl">
          <CardHeader>
            <CardTitle className="text-lg">Document Details</CardTitle>
            <CardDescription>Fill in the details for your document</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {questions.map((field) => (
              <div key={field.name}>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {field.label}
                  {field.required && <span className="text-red-500 ml-1">*</span>}
                </label>
                {field.type === 'textarea' ? (
                  <textarea
                    value={answers[field.name] || ''}
                    onChange={(e) => setAnswers((prev) => ({ ...prev, [field.name]: e.target.value }))}
                    placeholder={field.placeholder}
                    rows={4}
                    className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                ) : field.type === 'select' ? (
                  <select
                    value={answers[field.name] || ''}
                    onChange={(e) => setAnswers((prev) => ({ ...prev, [field.name]: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  >
                    <option value="">Select...</option>
                    {field.options?.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={field.type}
                    value={answers[field.name] || ''}
                    onChange={(e) => setAnswers((prev) => ({ ...prev, [field.name]: e.target.value }))}
                    placeholder={field.placeholder}
                    className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Step 3: Preview & Edit */}
      {step === 3 && (
        <Card className="max-w-3xl">
          <CardHeader>
            <CardTitle className="text-lg">Preview & Edit</CardTitle>
            <CardDescription>Review the generated document and make any edits</CardDescription>
          </CardHeader>
          <CardContent>
            <textarea
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              rows={20}
              className="w-full px-4 py-3 border rounded-md text-sm font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </CardContent>
        </Card>
      )}

      {/* Step 4: Add Parties */}
      {step === 4 && (
        <Card className="max-w-2xl">
          <CardHeader>
            <CardTitle className="text-lg">Add Parties</CardTitle>
            <CardDescription>Add signatories and send for signature</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {parties.map((party, index) => (
              <div key={index} className="flex items-start gap-3 p-4 border rounded-md">
                <div className="flex-1 space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                    <input
                      type="text"
                      value={party.name}
                      onChange={(e) => updateParty(index, 'name', e.target.value)}
                      placeholder="Full name"
                      className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                    <input
                      type="email"
                      value={party.email}
                      onChange={(e) => updateParty(index, 'email', e.target.value)}
                      placeholder="email@example.com"
                      className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                </div>
                {parties.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeParty(index)}
                    className="mt-6 p-2 rounded-md hover:bg-gray-100 text-gray-400 hover:text-red-500"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
            <Button type="button" variant="outline" onClick={addParty}>
              <Plus className="mr-2 h-4 w-4" />
              Add Another Party
            </Button>
          </CardContent>
        </Card>
      )}

      {error && (
        <div className="mt-4 p-3 rounded-md bg-red-50 text-red-700 text-sm max-w-3xl">
          {error}
        </div>
      )}

      {/* Navigation */}
      <div className="flex gap-3 mt-6">
        {step > 1 && (
          <Button variant="outline" onClick={goBack} disabled={loading}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        )}
        <Button onClick={goNext} disabled={loading}>
          {loading ? (
            'Processing...'
          ) : step === 4 ? (
            <>
              <Send className="mr-2 h-4 w-4" />
              Create & Send
            </>
          ) : (
            <>
              Next
              <ArrowRight className="ml-2 h-4 w-4" />
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

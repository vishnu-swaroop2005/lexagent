export type DocumentStatus =
  | 'draft' | 'questionnaire' | 'generating' | 'generated'
  | 'sent' | 'partially_signed' | 'fully_signed' | 'expired';

export type SignatureStatus = 'pending' | 'sent' | 'viewed' | 'signed' | 'declined' | 'expired';

export interface Document {
  id: string;
  org_id: string;
  template_id?: string;
  title: string;
  doc_type: string;
  status: DocumentStatus;
  questionnaire_answers?: Record<string, unknown>;
  generated_content?: string;
  file_path?: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
  parties?: DocumentParty[];
}

export interface DocumentTemplate {
  id: string;
  org_id?: string;
  name: string;
  doc_type: string;
  description?: string;
  questionnaire_schema?: Record<string, unknown>;
  is_system: boolean;
}

export interface DocumentParty {
  id: string;
  document_id: string;
  name: string;
  email: string;
  role: 'signer' | 'reviewer' | 'cc';
  signing_order: number;
}

export interface Signature {
  id: string;
  document_id: string;
  party_id: string;
  status: SignatureStatus;
  signed_at?: string;
}

export interface DocumentVersion {
  id: string;
  document_id: string;
  version_number: number;
  file_path: string;
  change_summary?: string;
  created_at: string;
}

export interface QuestionnaireField {
  id: string;
  label: string;
  type: 'text' | 'textarea' | 'select' | 'date' | 'number' | 'email';
  required: boolean;
  options?: string[];
  placeholder?: string;
  help_text?: string;
}

export interface QuestionnaireSchema {
  title: string;
  fields: QuestionnaireField[];
}

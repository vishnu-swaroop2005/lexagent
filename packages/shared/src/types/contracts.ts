export type ContractStatus =
  | 'uploaded' | 'parsing' | 'parsed' | 'reviewing' | 'reviewed'
  | 'redlined' | 'negotiating' | 'signed' | 'active' | 'expired';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface Contract {
  id: string;
  org_id: string;
  title: string;
  description?: string;
  file_path: string;
  file_type: 'pdf' | 'docx';
  status: ContractStatus;
  counterparty?: string;
  effective_date?: string;
  expiry_date?: string;
  raw_text?: string;
  uploaded_by?: string;
  created_at: string;
  updated_at: string;
}

export interface Clause {
  id: string;
  org_id: string;
  contract_id: string;
  clause_type?: string;
  title?: string;
  content: string;
  risk_level?: RiskLevel;
  position_start?: number;
  position_end?: number;
  created_at: string;
}

export interface ReviewFinding {
  clause_id: string;
  issue: string;
  risk_level: RiskLevel;
  suggestion: string;
  playbook_reference?: string;
}

export interface ReviewReport {
  id: string;
  contract_id: string;
  summary?: string;
  overall_risk?: RiskLevel;
  findings: ReviewFinding[];
  created_at: string;
}

export interface RedlineChange {
  clause_id: string;
  original_text: string;
  suggested_text: string;
  reason: string;
  accepted?: boolean;
}

export interface Redline {
  id: string;
  contract_id: string;
  changes: RedlineChange[];
  status: string;
  redlined_file_path?: string;
}

export interface ClauseLibraryItem {
  id: string;
  clause_type: string;
  title: string;
  content: string;
  is_approved: boolean;
  tags: string[];
  usage_count: number;
  created_at: string;
}

export interface NegotiationHistory {
  id: string;
  version: number;
  action: string;
  diff_summary?: string;
  message?: string;
  actor: string;
  created_at: string;
}

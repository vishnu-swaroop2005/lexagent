export type ComplianceFramework = 'gdpr' | 'soc2' | 'hipaa' | 'ccpa';

export interface ComplianceFinding {
  rule_id: string;
  clause_id?: string;
  status: 'pass' | 'fail' | 'warning';
  detail: string;
  recommendation?: string;
}

export interface ComplianceReport {
  id: string;
  contract_id: string;
  framework: ComplianceFramework;
  overall_score?: number;
  findings: ComplianceFinding[];
  checked_at: string;
}

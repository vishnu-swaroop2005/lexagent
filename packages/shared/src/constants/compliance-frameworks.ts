export const COMPLIANCE_FRAMEWORKS = {
  GDPR: 'gdpr',
  SOC2: 'soc2',
  HIPAA: 'hipaa',
  CCPA: 'ccpa',
} as const;

export const FRAMEWORK_LABELS: Record<string, string> = {
  gdpr: 'GDPR (General Data Protection Regulation)',
  soc2: 'SOC 2 (Trust Service Criteria)',
  hipaa: 'HIPAA (Health Insurance Portability)',
  ccpa: 'CCPA (California Consumer Privacy Act)',
};

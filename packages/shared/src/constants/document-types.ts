export const DOCUMENT_TYPES = {
  NDA: 'nda',
  MOU: 'mou',
  SERVICE_AGREEMENT: 'service_agreement',
  FOUNDER_AGREEMENT: 'founder_agreement',
  EMPLOYMENT_AGREEMENT: 'employment_agreement',
  VENDOR_AGREEMENT: 'vendor_agreement',
  CONSULTING_AGREEMENT: 'consulting_agreement',
  CUSTOM: 'custom',
} as const;

export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  nda: 'Non-Disclosure Agreement (NDA)',
  mou: 'Memorandum of Understanding (MOU)',
  service_agreement: 'Service Agreement',
  founder_agreement: 'Founder Agreement',
  employment_agreement: 'Employment Agreement',
  vendor_agreement: 'Vendor Agreement',
  consulting_agreement: 'Consulting Agreement',
  custom: 'Custom Document',
};

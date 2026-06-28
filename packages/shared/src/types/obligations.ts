export type ObligationStatus = 'pending' | 'in_progress' | 'completed' | 'overdue' | 'waived';

export interface Obligation {
  id: string;
  org_id: string;
  contract_id?: string;
  title: string;
  description?: string;
  obligated_party?: 'us' | 'counterparty';
  due_date?: string;
  recurring: boolean;
  recurrence_rule?: string;
  status: ObligationStatus;
  priority?: string;
  assigned_to?: string;
  completed_at?: string;
  created_at: string;
}

export interface Reminder {
  id: string;
  reminder_type: 'obligation_due' | 'signature_pending' | 'contract_expiry' | 'review_needed';
  reference_id: string;
  recipient_email: string;
  subject: string;
  body?: string;
  scheduled_at: string;
  is_sent: boolean;
  sent_at?: string;
}

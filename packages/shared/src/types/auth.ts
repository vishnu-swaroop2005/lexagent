export type UserRole = 'admin' | 'lawyer' | 'viewer';

export interface User {
  id: string;
  org_id: string;
  email: string;
  full_name?: string;
  role: UserRole;
  avatar_url?: string;
}

export interface Organisation {
  id: string;
  name: string;
  slug: string;
  logo_url?: string;
  settings?: Record<string, unknown>;
}

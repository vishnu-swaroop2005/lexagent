export const ROLES = {
  ADMIN: 'admin',
  LAWYER: 'lawyer',
  VIEWER: 'viewer',
} as const;

export const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrator',
  lawyer: 'Lawyer',
  viewer: 'Viewer',
};

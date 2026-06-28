-- =============================================================================
-- LexAgent — Full database bootstrap for Supabase (PostgreSQL)
-- =============================================================================
-- Copy/paste this whole file into the Supabase SQL Editor and run it once.
-- It is idempotent (safe to re-run): every object uses IF NOT EXISTS / OR REPLACE.
--
-- Creates:
--   * pgvector extension
--   * 18 tables (organisations, users + 16 app tables)
--   * updated_at triggers
--   * match_clauses() RPC (semantic search)
--   * custom_access_token_hook() (injects org_id + user_role into the JWT)
--   * handle_new_user() trigger (auto-provisions org + user on signup)
--   * HNSW vector indexes + supporting indexes
--   * Row Level Security + per-org policies
--   * 3 storage buckets (contracts, documents, signatures)
--
-- After running: Authentication > Hooks > enable "Custom Access Token"
--                and point it at public.custom_access_token_hook.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. Extensions
-- -----------------------------------------------------------------------------
create extension if not exists "vector";      -- pgvector (embeddings)
create extension if not exists "pgcrypto";     -- gen_random_uuid()

-- -----------------------------------------------------------------------------
-- 1. Generic updated_at trigger function
-- -----------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- =============================================================================
-- 2. Core multi-tenant tables
-- =============================================================================

-- Organisations (tenants) ------------------------------------------------------
create table if not exists public.organisations (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  slug        text unique,
  plan        text not null default 'free',
  settings    jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- App users (extends auth.users) ----------------------------------------------
create table if not exists public.users (
  id          uuid primary key references auth.users(id) on delete cascade,
  org_id      uuid not null references public.organisations(id) on delete cascade,
  email       text,
  full_name   text,
  role        text not null default 'viewer' check (role in ('admin','lawyer','viewer')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists idx_users_org_id on public.users(org_id);

-- =============================================================================
-- 3. Contracts domain
-- =============================================================================

create table if not exists public.contracts (
  id              uuid primary key default gen_random_uuid(),
  org_id          uuid not null references public.organisations(id) on delete cascade,
  title           text not null,
  description     text,
  file_path       text,
  file_type       text,
  status          text not null default 'uploaded',
  counterparty    text,
  raw_text        text,
  effective_date  date,
  expiry_date     date,
  uploaded_by     uuid references public.users(id) on delete set null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create index if not exists idx_contracts_org_id  on public.contracts(org_id);
create index if not exists idx_contracts_status   on public.contracts(status);

create table if not exists public.clauses (
  id              uuid primary key default gen_random_uuid(),
  org_id          uuid not null references public.organisations(id) on delete cascade,
  contract_id     uuid not null references public.contracts(id) on delete cascade,
  clause_type     text,
  title           text,
  content         text not null,
  risk_level      text,
  position_start  integer,
  position_end    integer,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create index if not exists idx_clauses_org_id      on public.clauses(org_id);
create index if not exists idx_clauses_contract_id on public.clauses(contract_id);

-- 768-dim embeddings for semantic clause search (HNSW / cosine) ----------------
create table if not exists public.clause_embeddings (
  id          uuid primary key default gen_random_uuid(),
  org_id      uuid not null references public.organisations(id) on delete cascade,
  clause_id   uuid not null references public.clauses(id) on delete cascade,
  embedding   vector(768),
  model_name  text,
  created_at  timestamptz not null default now()
);
create index if not exists idx_clause_embeddings_org_id    on public.clause_embeddings(org_id);
create index if not exists idx_clause_embeddings_clause_id on public.clause_embeddings(clause_id);
create index if not exists idx_clause_embeddings_hnsw
  on public.clause_embeddings using hnsw (embedding vector_cosine_ops);

create table if not exists public.review_reports (
  id            uuid primary key default gen_random_uuid(),
  org_id        uuid not null references public.organisations(id) on delete cascade,
  contract_id   uuid not null references public.contracts(id) on delete cascade,
  summary       text,
  overall_risk  text,
  findings      jsonb not null default '[]'::jsonb,
  created_at    timestamptz not null default now()
);
create index if not exists idx_review_reports_contract_id on public.review_reports(contract_id);
create index if not exists idx_review_reports_org_id      on public.review_reports(org_id);

create table if not exists public.redlines (
  id                  uuid primary key default gen_random_uuid(),
  org_id              uuid not null references public.organisations(id) on delete cascade,
  contract_id         uuid not null references public.contracts(id) on delete cascade,
  review_report_id    uuid references public.review_reports(id) on delete set null,
  original_file_path  text,
  redlined_file_path  text,
  changes             jsonb not null default '[]'::jsonb,
  status              text not null default 'pending',
  created_at          timestamptz not null default now()
);
create index if not exists idx_redlines_contract_id on public.redlines(contract_id);
create index if not exists idx_redlines_org_id      on public.redlines(org_id);

-- =============================================================================
-- 4. Negotiation domain
-- =============================================================================

create table if not exists public.negotiations (
  id                  uuid primary key default gen_random_uuid(),
  org_id              uuid not null references public.organisations(id) on delete cascade,
  contract_id         uuid not null references public.contracts(id) on delete cascade,
  counterparty_email  text,
  counterparty_name   text,
  status              text not null default 'active',
  current_version     integer not null default 1,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
create index if not exists idx_negotiations_contract_id on public.negotiations(contract_id);
create index if not exists idx_negotiations_org_id      on public.negotiations(org_id);

create table if not exists public.negotiation_history (
  id              uuid primary key default gen_random_uuid(),
  org_id          uuid not null references public.organisations(id) on delete cascade,
  negotiation_id  uuid not null references public.negotiations(id) on delete cascade,
  version         integer,
  action          text,
  diff_summary    text,
  message         text,
  actor           text,
  created_at      timestamptz not null default now()
);
create index if not exists idx_negotiation_history_negotiation_id on public.negotiation_history(negotiation_id);
create index if not exists idx_negotiation_history_org_id         on public.negotiation_history(org_id);

-- =============================================================================
-- 5. Clause library (org playbook)
-- =============================================================================

create table if not exists public.clause_library (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid not null references public.organisations(id) on delete cascade,
  clause_type  text,
  title        text,
  content      text not null,
  tags         text[] not null default '{}',
  embedding    vector(768),
  is_approved  boolean not null default false,
  usage_count  integer not null default 0,
  approved_by  uuid references public.users(id) on delete set null,
  approved_at  timestamptz,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index if not exists idx_clause_library_org_id      on public.clause_library(org_id);
create index if not exists idx_clause_library_clause_type on public.clause_library(clause_type);
create index if not exists idx_clause_library_hnsw
  on public.clause_library using hnsw (embedding vector_cosine_ops);

-- =============================================================================
-- 6. Obligations & compliance
-- =============================================================================

create table if not exists public.obligations (
  id               uuid primary key default gen_random_uuid(),
  org_id           uuid not null references public.organisations(id) on delete cascade,
  contract_id      uuid references public.contracts(id) on delete cascade,  -- nullable: docs have no contract
  title            text not null,
  description      text,
  obligated_party  text,
  due_date         date,
  recurring        boolean not null default false,
  recurrence_rule  text,
  status           text not null default 'pending',
  priority         text default 'medium',
  assigned_to      uuid references public.users(id) on delete set null,
  completed_at     timestamptz,
  metadata         jsonb not null default '{}'::jsonb,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);
create index if not exists idx_obligations_org_id      on public.obligations(org_id);
create index if not exists idx_obligations_contract_id on public.obligations(contract_id);
create index if not exists idx_obligations_status      on public.obligations(status);
create index if not exists idx_obligations_due_date    on public.obligations(due_date);

create table if not exists public.compliance_reports (
  id             uuid primary key default gen_random_uuid(),
  org_id         uuid not null references public.organisations(id) on delete cascade,
  contract_id    uuid not null references public.contracts(id) on delete cascade,
  framework      text not null,
  overall_score  numeric,
  findings       jsonb not null default '[]'::jsonb,
  checked_at     timestamptz not null default now(),
  created_at     timestamptz not null default now()
);
create index if not exists idx_compliance_reports_contract_id on public.compliance_reports(contract_id);
create index if not exists idx_compliance_reports_org_id      on public.compliance_reports(org_id);

-- =============================================================================
-- 7. Document generation & e-signature
-- =============================================================================

create table if not exists public.document_templates (
  id                    uuid primary key default gen_random_uuid(),
  org_id                uuid references public.organisations(id) on delete cascade,  -- null = system template
  name                  text,
  doc_type              text not null,
  questionnaire_schema  jsonb,
  is_system             boolean not null default false,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);
create index if not exists idx_document_templates_org_id   on public.document_templates(org_id);
create index if not exists idx_document_templates_doc_type on public.document_templates(doc_type);

create table if not exists public.documents (
  id                     uuid primary key default gen_random_uuid(),
  org_id                 uuid not null references public.organisations(id) on delete cascade,
  template_id            uuid references public.document_templates(id) on delete set null,
  title                  text not null,
  doc_type               text not null,
  status                 text not null default 'draft',
  questionnaire_answers  jsonb,
  generated_content      text,
  file_path              text,
  created_by             uuid references public.users(id) on delete set null,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);
create index if not exists idx_documents_org_id on public.documents(org_id);
create index if not exists idx_documents_status on public.documents(status);

create table if not exists public.document_versions (
  id              uuid primary key default gen_random_uuid(),
  org_id          uuid not null references public.organisations(id) on delete cascade,
  document_id     uuid not null references public.documents(id) on delete cascade,
  version_number  integer not null default 1,
  file_path       text,
  change_summary  text,
  created_by      uuid references public.users(id) on delete set null,
  created_at      timestamptz not null default now()
);
create index if not exists idx_document_versions_document_id on public.document_versions(document_id);
create index if not exists idx_document_versions_org_id      on public.document_versions(org_id);

create table if not exists public.document_parties (
  id             uuid primary key default gen_random_uuid(),
  org_id         uuid not null references public.organisations(id) on delete cascade,
  document_id    uuid not null references public.documents(id) on delete cascade,
  name           text not null,
  email          text not null,
  role           text not null default 'signer',
  signing_order  integer not null default 1,
  created_at     timestamptz not null default now()
);
create index if not exists idx_document_parties_document_id on public.document_parties(document_id);
create index if not exists idx_document_parties_org_id      on public.document_parties(org_id);

create table if not exists public.signatures (
  id                        uuid primary key default gen_random_uuid(),
  org_id                    uuid not null references public.organisations(id) on delete cascade,
  document_id               uuid not null references public.documents(id) on delete cascade,
  party_id                  uuid not null references public.document_parties(id) on delete cascade,
  status                    text not null default 'pending',
  verification_token        text unique,
  verification_email_sent   boolean not null default false,
  signature_image_path      text,
  signed_at                 timestamptz,
  created_at                timestamptz not null default now()
);
create index if not exists idx_signatures_document_id on public.signatures(document_id);
create index if not exists idx_signatures_org_id      on public.signatures(org_id);
create index if not exists idx_signatures_token       on public.signatures(verification_token);

-- =============================================================================
-- 8. Reminders (Celery beat)
-- =============================================================================

create table if not exists public.reminders (
  id               uuid primary key default gen_random_uuid(),
  org_id           uuid not null references public.organisations(id) on delete cascade,
  reminder_type    text,
  reference_id     uuid,
  reference_table  text,
  recipient_email  text,
  subject          text,
  body             text,
  scheduled_at     timestamptz,
  is_sent          boolean not null default false,
  sent_at          timestamptz,
  created_at       timestamptz not null default now()
);
create index if not exists idx_reminders_org_id  on public.reminders(org_id);
create index if not exists idx_reminders_pending on public.reminders(is_sent, scheduled_at);

-- =============================================================================
-- 9. updated_at triggers
-- =============================================================================
do $$
declare t text;
begin
  foreach t in array array[
    'organisations','users','contracts','clauses','review_reports',
    'negotiations','clause_library','obligations','document_templates','documents'
  ]
  loop
    execute format('drop trigger if exists trg_set_updated_at on public.%I;', t);
    execute format(
      'create trigger trg_set_updated_at before update on public.%I
       for each row execute function public.set_updated_at();', t);
  end loop;
end$$;

-- =============================================================================
-- 10. match_clauses() — semantic search RPC (used by EmbeddingService)
-- =============================================================================
create or replace function public.match_clauses(
  query_embedding  vector(768),
  match_org_id     uuid,
  match_threshold  float,
  match_count      int
)
returns table (
  clause_id    uuid,
  content      text,
  clause_type  text,
  contract_id  uuid,
  similarity   float
)
language sql
stable
as $$
  select
    c.id          as clause_id,
    c.content     as content,
    c.clause_type as clause_type,
    c.contract_id as contract_id,
    1 - (ce.embedding <=> query_embedding) as similarity
  from public.clause_embeddings ce
  join public.clauses c on c.id = ce.clause_id
  where ce.org_id = match_org_id
    and ce.embedding is not null
    and 1 - (ce.embedding <=> query_embedding) > match_threshold
  order by ce.embedding <=> query_embedding
  limit match_count;
$$;

-- =============================================================================
-- 11. Auth: custom access token hook (injects org_id + user_role into JWT)
-- =============================================================================
create or replace function public.custom_access_token_hook(event jsonb)
returns jsonb
language plpgsql
stable
as $$
declare
  claims    jsonb;
  v_org_id  uuid;
  v_role    text;
begin
  select org_id, role
    into v_org_id, v_role
  from public.users
  where id = (event->>'user_id')::uuid;

  claims := coalesce(event->'claims', '{}'::jsonb);

  if v_org_id is not null then
    claims := jsonb_set(claims, '{org_id}',    to_jsonb(v_org_id::text));
    claims := jsonb_set(claims, '{user_role}', to_jsonb(coalesce(v_role, 'viewer')));
  end if;

  event := jsonb_set(event, '{claims}', claims);
  return event;
end;
$$;

-- The Auth server (supabase_auth_admin) must be able to run the hook and read users.
grant usage on schema public to supabase_auth_admin;
grant execute on function public.custom_access_token_hook(jsonb) to supabase_auth_admin;
grant select on public.users to supabase_auth_admin;

-- =============================================================================
-- 12. Auto-provision org + user on signup
--     Reads full_name / org_name from auth signup metadata.
-- =============================================================================
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_org_id    uuid;
  v_org_name  text;
  v_slug      text;
begin
  v_org_name := coalesce(nullif(new.raw_user_meta_data->>'org_name', ''), 'My Organization');
  v_slug := lower(regexp_replace(v_org_name, '[^a-zA-Z0-9]+', '-', 'g'))
            || '-' || substr(replace(new.id::text, '-', ''), 1, 8);

  insert into public.organisations (name, slug)
  values (v_org_name, v_slug)
  returning id into v_org_id;

  insert into public.users (id, org_id, email, full_name, role)
  values (
    new.id,
    v_org_id,
    new.email,
    new.raw_user_meta_data->>'full_name',
    'admin'   -- first user of a new org is its admin
  );

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- =============================================================================
-- 13. Row Level Security
--     Backend uses the service_role key (bypasses RLS). These policies protect
--     any direct client (anon/authenticated) access and scope rows by org.
-- =============================================================================
do $$
declare t text;
begin
  foreach t in array array[
    'organisations','users','contracts','clauses','clause_embeddings',
    'review_reports','redlines','negotiations','negotiation_history',
    'clause_library','obligations','compliance_reports','document_templates',
    'documents','document_versions','document_parties','signatures','reminders'
  ]
  loop
    execute format('alter table public.%I enable row level security;', t);
  end loop;
end$$;

-- organisations: a member can see/manage only their own org
drop policy if exists org_self on public.organisations;
create policy org_self on public.organisations
  for all to authenticated
  using  (id = (auth.jwt() ->> 'org_id')::uuid)
  with check (id = (auth.jwt() ->> 'org_id')::uuid);

-- users: a member can see/manage rows within their org
drop policy if exists users_same_org on public.users;
create policy users_same_org on public.users
  for all to authenticated
  using  (org_id = (auth.jwt() ->> 'org_id')::uuid)
  with check (org_id = (auth.jwt() ->> 'org_id')::uuid);

-- All org-scoped tables: rows must match the caller's org_id claim.
-- document_templates also exposes system templates (org_id is null) read-only.
do $$
declare t text;
begin
  foreach t in array array[
    'contracts','clauses','clause_embeddings','review_reports','redlines',
    'negotiations','negotiation_history','clause_library','obligations',
    'compliance_reports','documents','document_versions','document_parties',
    'signatures','reminders'
  ]
  loop
    execute format('drop policy if exists org_isolation on public.%I;', t);
    execute format(
      'create policy org_isolation on public.%I
         for all to authenticated
         using  (org_id = (auth.jwt() ->> ''org_id'')::uuid)
         with check (org_id = (auth.jwt() ->> ''org_id'')::uuid);', t);
  end loop;
end$$;

drop policy if exists templates_read on public.document_templates;
create policy templates_read on public.document_templates
  for select to authenticated
  using (is_system = true or org_id = (auth.jwt() ->> 'org_id')::uuid);

drop policy if exists templates_write on public.document_templates;
create policy templates_write on public.document_templates
  for all to authenticated
  using  (org_id = (auth.jwt() ->> 'org_id')::uuid)
  with check (org_id = (auth.jwt() ->> 'org_id')::uuid);

-- =============================================================================
-- 14. Storage buckets (referenced by the backend services)
-- =============================================================================
insert into storage.buckets (id, name, public)
values
  ('contracts',  'contracts',  false),
  ('documents',  'documents',  false),
  ('signatures', 'signatures', false)
on conflict (id) do nothing;

-- =============================================================================
-- Done. Run the verification block in 0002 (or the query in the chat) to confirm.
-- =============================================================================

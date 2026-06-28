-- =============================================================================
-- LexAgent — post-migration verification
-- Run AFTER 0001_init_schema.sql. Every check below should report 'OK'.
-- =============================================================================

-- 1. All 18 tables present ----------------------------------------------------
with expected(name) as (
  values
    ('organisations'),('users'),('contracts'),('clauses'),('clause_embeddings'),
    ('review_reports'),('redlines'),('negotiations'),('negotiation_history'),
    ('clause_library'),('obligations'),('compliance_reports'),('document_templates'),
    ('documents'),('document_versions'),('document_parties'),('signatures'),('reminders')
)
select
  e.name as table_name,
  case when t.table_name is null then 'MISSING' else 'OK' end as status
from expected e
left join information_schema.tables t
  on t.table_schema = 'public' and t.table_name = e.name
order by status desc, e.name;

-- 2. Functions present --------------------------------------------------------
select proname as function_name, 'OK' as status
from pg_proc
where proname in ('match_clauses','custom_access_token_hook','handle_new_user','set_updated_at')
order by proname;

-- 3. Vector (HNSW) indexes present -------------------------------------------
select indexname, tablename, 'OK' as status
from pg_indexes
where schemaname = 'public' and indexname like '%hnsw%'
order by tablename;

-- 4. RLS enabled on every public table ---------------------------------------
select relname as table_name,
       case when relrowsecurity then 'RLS ON' else 'RLS OFF' end as status
from pg_class
where relnamespace = 'public'::regnamespace and relkind = 'r'
order by relname;

-- 5. Storage buckets ---------------------------------------------------------
select id, 'OK' as status from storage.buckets
where id in ('contracts','documents','signatures') order by id;

-- 6. Total table count (expect 18) -------------------------------------------
select count(*) as public_table_count
from information_schema.tables
where table_schema = 'public' and table_type = 'BASE TABLE';

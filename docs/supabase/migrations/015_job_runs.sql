create table job_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  kind text not null,
  status text not null default 'queued',
  resource_type text,
  resource_id text,
  idempotency_key text,
  progress_current integer not null default 0,
  progress_total integer,
  error_message text,
  result jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  queued_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  updated_at timestamptz,
  check (status in ('queued', 'running', 'success', 'error', 'canceled')),
  check (progress_current >= 0),
  check (progress_total is null or progress_total >= progress_current)
);

create unique index job_runs_idempotency_idx
  on job_runs (user_id, kind, idempotency_key)
  where idempotency_key is not null;

create index job_runs_user_status_idx on job_runs (user_id, status, queued_at desc);
create index job_runs_kind_status_idx on job_runs (kind, status, queued_at);
create index job_runs_resource_idx on job_runs (user_id, resource_type, resource_id);

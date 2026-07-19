create table payees (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  canonical_name text not null,
  status entity_status not null default 'active',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  unique (user_id, canonical_name)
);

create table merchant_aliases (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  payee_id uuid not null references payees(id) on delete cascade,
  alias text not null,
  normalized_alias text not null,
  source text not null default 'manual',
  status entity_status not null default 'active',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  unique (user_id, normalized_alias)
);

create index payees_user_status_idx on payees (user_id, status, canonical_name);
create index merchant_aliases_user_status_idx on merchant_aliases (user_id, status, normalized_alias);

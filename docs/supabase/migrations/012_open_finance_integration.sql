create table open_finance_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  provider text not null default 'pluggy',
  external_item_id text not null,
  connector_name text,
  institution_name text,
  status text not null default 'active',
  consent_expires_at timestamptz,
  last_sync_at timestamptz,
  last_successful_sync_at timestamptz,
  last_error text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  unique (user_id, provider, external_item_id)
);

create table open_finance_account_links (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  provider text not null default 'pluggy',
  external_account_id text not null,
  open_finance_item_id uuid references open_finance_items(id),
  account_id uuid references accounts(id),
  card_id uuid references cards(id),
  account_type text,
  subtype text,
  display_name text,
  institution_name text,
  last_digits text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  unique (user_id, provider, external_account_id),
  check (account_id is not null or card_id is not null)
);

create table open_finance_transaction_links (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  provider text not null default 'pluggy',
  external_transaction_id text not null,
  external_account_id text,
  open_finance_item_id uuid references open_finance_items(id),
  transaction_id uuid not null references transactions(id) on delete cascade,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  unique (user_id, provider, external_transaction_id)
);

create table open_finance_sync_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  provider text not null default 'pluggy',
  external_item_id text,
  status text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  duration_ms integer,
  accounts_created integer not null default 0,
  accounts_updated integer not null default 0,
  cards_created integer not null default 0,
  cards_updated integer not null default 0,
  transactions_created integer not null default 0,
  transactions_updated integer not null default 0,
  transactions_ignored integer not null default 0,
  error_message text,
  metadata jsonb not null default '{}'::jsonb
);

alter table accounts add column if not exists external_source text;
alter table cards add column if not exists external_source text;
alter table transactions add column if not exists external_source text;

create index open_finance_items_user_idx on open_finance_items (user_id, provider, status);
create index open_finance_account_links_user_idx on open_finance_account_links (user_id, provider);
create index open_finance_transaction_links_user_idx on open_finance_transaction_links (user_id, provider);
create index open_finance_sync_runs_user_idx on open_finance_sync_runs (user_id, provider, started_at desc);

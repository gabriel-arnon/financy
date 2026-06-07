create extension if not exists "pgcrypto";

create type transaction_type as enum ('expense', 'income', 'transfer', 'payment', 'refund');
create type transaction_status as enum ('pending', 'confirmed', 'reconciled', 'ignored');
create type preview_status as enum ('pending', 'selected', 'ignored', 'confirmed', 'duplicate', 'error');
create type statement_status as enum ('open', 'closed', 'paid', 'partial', 'overdue');

create table profiles (
  id uuid primary key,
  email text,
  full_name text,
  created_at timestamptz not null default now()
);

create table accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  name text not null,
  institution text,
  type text not null default 'checking',
  created_at timestamptz not null default now()
);

create table cards (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  account_id uuid references accounts(id),
  name text not null,
  brand text,
  closing_day integer,
  due_day integer,
  created_at timestamptz not null default now()
);

create table categories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  name text not null,
  created_at timestamptz not null default now()
);

create unique index categories_user_name_idx on categories (user_id, name) where user_id is not null;
create unique index categories_default_name_idx on categories (name) where user_id is null;

create table import_files (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  filename text not null,
  storage_path text not null,
  mime_type text,
  size_bytes bigint,
  created_at timestamptz not null default now()
);

create table import_batches (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  source_file_id uuid not null references import_files(id),
  status text not null default 'preview',
  created_at timestamptz not null default now()
);

create table card_statements (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  card_id uuid not null references cards(id),
  reference_month date not null,
  due_date date,
  closing_date date,
  total_amount numeric(14, 2),
  minimum_payment_amount numeric(14, 2),
  status statement_status not null default 'open',
  source_file_id uuid references import_files(id),
  created_at timestamptz not null default now()
);

create table import_preview_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  import_batch_id uuid not null references import_batches(id),
  source_file_id uuid not null references import_files(id),
  account_id uuid references accounts(id),
  card_id uuid references cards(id),
  card_statement_id uuid references card_statements(id),
  transaction_date date not null,
  description text not null,
  original_description text not null,
  amount numeric(14, 2) not null,
  type transaction_type not null default 'expense',
  category_id uuid references categories(id),
  installment_current integer,
  installment_total integer,
  raw_text text,
  raw_row jsonb,
  parser_confidence numeric(4, 3) not null default 0.75,
  needs_review boolean not null default false,
  duplicate_candidate boolean not null default false,
  status preview_status not null default 'pending',
  created_at timestamptz not null default now()
);

create table transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  account_id uuid references accounts(id),
  card_id uuid references cards(id),
  card_statement_id uuid references card_statements(id),
  transaction_date date not null,
  description text not null,
  original_description text,
  normalized_description text not null,
  amount numeric(14, 2) not null,
  type transaction_type not null,
  category_id uuid references categories(id),
  source_file_id uuid references import_files(id),
  installment_current integer,
  installment_total integer,
  status transaction_status not null default 'confirmed',
  created_at timestamptz not null default now()
);

create unique index transactions_dedupe_idx on transactions (
  user_id,
  coalesce(account_id, card_id),
  transaction_date,
  normalized_description,
  amount,
  coalesce(installment_current, 0),
  coalesce(installment_total, 0)
);

create table classification_rules (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  pattern text not null,
  category_id uuid references categories(id),
  transaction_type transaction_type,
  priority integer not null default 100,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

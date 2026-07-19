create table recurring_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  name text not null,
  kind text not null check (kind in ('installment', 'fixed_bill', 'subscription')),
  amount numeric(12,2) not null default 0,
  cadence text not null default 'monthly',
  category_id uuid references categories(id),
  account_id uuid references accounts(id),
  card_id uuid references cards(id),
  start_date date,
  end_date date,
  next_due_date date,
  status text not null default 'active' check (status in ('suggested', 'active', 'ignored', 'inactive')),
  source text not null default 'manual',
  notes text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table recurring_item_transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  recurring_item_id uuid not null references recurring_items(id) on delete cascade,
  transaction_id uuid not null references transactions(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (user_id, recurring_item_id, transaction_id)
);

create table financial_goals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  name text not null,
  target_amount numeric(12,2) not null,
  current_amount numeric(12,2) not null default 0,
  target_date date,
  status text not null default 'active' check (status in ('active', 'completed', 'paused', 'inactive')),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table budgets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  name text not null,
  amount numeric(12,2) not null,
  period_month text not null,
  category_id uuid references categories(id),
  status text not null default 'active' check (status in ('active', 'inactive')),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create index recurring_items_user_idx on recurring_items (user_id, status, kind);
create index recurring_item_transactions_user_idx on recurring_item_transactions (user_id, recurring_item_id);
create index financial_goals_user_idx on financial_goals (user_id, status, target_date);
create index budgets_user_idx on budgets (user_id, status, period_month);

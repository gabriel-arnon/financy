create type reimbursement_claim_status as enum (
  'draft',
  'sent',
  'acknowledged',
  'disputed',
  'partially_paid',
  'paid',
  'canceled'
);

create type reimbursement_item_status as enum ('active', 'canceled');
create type reimbursement_event_actor_type as enum ('owner', 'guest', 'system');

create table reimbursement_contacts (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references profiles(id),
  display_name text not null,
  email text,
  phone text,
  status entity_status not null default 'active',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index reimbursement_contacts_owner_display_name_active_idx
  on reimbursement_contacts (owner_user_id, lower(trim(display_name)))
  where status = 'active';
create index reimbursement_contacts_owner_user_id_idx on reimbursement_contacts (owner_user_id);

create table reimbursement_claims (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references profiles(id),
  contact_id uuid not null references reimbursement_contacts(id),
  title text not null,
  description text,
  due_date date,
  status reimbursement_claim_status not null default 'draft',
  total_snapshot numeric(14, 2),
  version integer not null default 1,
  sent_at timestamptz,
  canceled_at timestamptz,
  first_viewed_at timestamptz,
  last_viewed_at timestamptz,
  view_count integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index reimbursement_claims_owner_user_id_idx on reimbursement_claims (owner_user_id);
create index reimbursement_claims_owner_contact_status_due_idx on reimbursement_claims (owner_user_id, contact_id, status, due_date);
create index reimbursement_claims_contact_id_idx on reimbursement_claims (contact_id);

create table reimbursement_items (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references profiles(id),
  claim_id uuid not null references reimbursement_claims(id),
  transaction_id uuid not null references transactions(id),
  amount_requested numeric(14, 2) not null check (amount_requested > 0),
  status reimbursement_item_status not null default 'active',
  transaction_snapshot jsonb not null,
  position integer not null default 0,
  canceled_at timestamptz,
  created_at timestamptz not null default now()
);

create unique index reimbursement_items_claim_transaction_active_idx
  on reimbursement_items (claim_id, transaction_id)
  where status = 'active';
create index reimbursement_items_owner_user_id_idx on reimbursement_items (owner_user_id);
create index reimbursement_items_claim_id_idx on reimbursement_items (claim_id);
create index reimbursement_items_transaction_id_idx on reimbursement_items (transaction_id);

create table reimbursement_events (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references profiles(id),
  claim_id uuid references reimbursement_claims(id),
  contact_id uuid references reimbursement_contacts(id),
  item_id uuid references reimbursement_items(id),
  actor_type reimbursement_event_actor_type not null default 'owner',
  actor_user_id uuid,
  event_type text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index reimbursement_events_owner_created_idx on reimbursement_events (owner_user_id, created_at);
create index reimbursement_events_claim_created_idx on reimbursement_events (claim_id, created_at);

create type stored_file_status as enum ('uploaded', 'quarantined', 'available', 'rejected', 'deleted');
create type stored_file_scan_status as enum ('pending', 'clean', 'suspicious', 'failed', 'skipped');

create table stored_files (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references profiles(id),
  storage_bucket text not null,
  storage_path text not null,
  original_filename text not null,
  declared_mime_type text,
  detected_mime_type text not null,
  size_bytes bigint not null check (size_bytes > 0),
  sha256_hash text not null,
  source text not null default 'manual',
  status stored_file_status not null default 'available',
  scan_status stored_file_scan_status not null default 'skipped',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create unique index stored_files_storage_object_idx on stored_files (storage_bucket, storage_path);
create index stored_files_owner_user_id_idx on stored_files (owner_user_id);
create index stored_files_owner_hash_idx on stored_files (owner_user_id, sha256_hash);
create index stored_files_status_idx on stored_files (status);

create table transaction_attachments (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references profiles(id),
  transaction_id uuid not null references transactions(id),
  file_id uuid not null references stored_files(id),
  status entity_status not null default 'active',
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create unique index transaction_attachments_active_file_idx
  on transaction_attachments (transaction_id, file_id)
  where status = 'active';

create index transaction_attachments_owner_user_id_idx on transaction_attachments (owner_user_id);
create index transaction_attachments_transaction_id_idx on transaction_attachments (transaction_id);
create index transaction_attachments_file_id_idx on transaction_attachments (file_id);

create table stored_file_events (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references profiles(id),
  file_id uuid references stored_files(id),
  actor_type text not null default 'owner',
  actor_user_id uuid,
  event_type text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index stored_file_events_owner_file_created_idx
  on stored_file_events (owner_user_id, file_id, created_at);

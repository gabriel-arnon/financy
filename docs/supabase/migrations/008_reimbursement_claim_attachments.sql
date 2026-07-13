create table reimbursement_claim_attachments (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references profiles(id),
  claim_id uuid not null references reimbursement_claims(id),
  file_id uuid not null references stored_files(id),
  status entity_status not null default 'active',
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create unique index reimbursement_claim_attachments_active_file_idx
  on reimbursement_claim_attachments (claim_id, file_id)
  where status = 'active';
create index reimbursement_claim_attachments_owner_idx
  on reimbursement_claim_attachments (owner_user_id);
create index reimbursement_claim_attachments_claim_idx
  on reimbursement_claim_attachments (claim_id);
create index reimbursement_claim_attachments_file_idx
  on reimbursement_claim_attachments (file_id);

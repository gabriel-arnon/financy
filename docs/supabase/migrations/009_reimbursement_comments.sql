create table reimbursement_comments (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references profiles(id),
  claim_id uuid not null references reimbursement_claims(id),
  author_user_id uuid not null references profiles(id),
  author_role text not null check (author_role in ('owner', 'guest')),
  body text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  deleted_at timestamptz,
  deleted_by_user_id uuid references profiles(id),
  deleted_by_role text check (deleted_by_role in ('owner', 'guest')),
  constraint reimbursement_comments_body_not_empty check (length(btrim(body)) > 0),
  constraint reimbursement_comments_body_max_length check (length(body) <= 2000),
  constraint reimbursement_comments_delete_actor_consistent check (
    (deleted_at is null and deleted_by_user_id is null and deleted_by_role is null)
    or
    (deleted_at is not null and deleted_by_user_id is not null and deleted_by_role is not null)
  )
);

create index reimbursement_comments_claim_idx
  on reimbursement_comments (claim_id);
create index reimbursement_comments_claim_created_idx
  on reimbursement_comments (claim_id, created_at, id);
create index reimbursement_comments_claim_active_idx
  on reimbursement_comments (claim_id, created_at, id)
  where deleted_at is null;
create index reimbursement_comments_owner_claim_idx
  on reimbursement_comments (owner_user_id, claim_id, created_at);
create index reimbursement_comments_author_idx
  on reimbursement_comments (author_user_id, created_at desc);

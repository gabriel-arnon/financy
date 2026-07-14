create table reimbursement_invitation_accept_attempts (
  id uuid primary key default gen_random_uuid(),
  token_hash text not null,
  ip_hash text not null,
  auth_user_id uuid references profiles(id),
  attempted_at timestamptz not null default now(),
  success boolean not null default false,
  failure_code text,
  constraint reimbursement_invitation_attempt_token_hash_format check (length(token_hash) = 64),
  constraint reimbursement_invitation_attempt_ip_hash_format check (length(ip_hash) = 64)
);

create index reimbursement_invitation_attempts_window_idx
  on reimbursement_invitation_accept_attempts (token_hash, ip_hash, attempted_at desc);
create index reimbursement_invitation_attempts_cleanup_idx
  on reimbursement_invitation_accept_attempts (attempted_at);
create index reimbursement_invitation_attempts_user_idx
  on reimbursement_invitation_accept_attempts (auth_user_id, attempted_at desc);

create type reimbursement_invitation_status as enum ('pending', 'accepted', 'revoked', 'expired');
create type reimbursement_membership_status as enum ('active', 'revoked');

create table reimbursement_invitations (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references profiles(id),
  contact_id uuid not null references reimbursement_contacts(id),
  claim_id uuid references reimbursement_claims(id),
  email text not null,
  token_hash text not null unique,
  status reimbursement_invitation_status not null default 'pending',
  expires_at timestamptz not null,
  accepted_at timestamptz,
  accepted_by_user_id uuid references profiles(id),
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  constraint reimbursement_invitations_email_not_empty check (length(trim(email)) > 0)
);

create index reimbursement_invitations_owner_created_idx
  on reimbursement_invitations (owner_user_id, created_at desc);
create index reimbursement_invitations_contact_status_idx
  on reimbursement_invitations (owner_user_id, contact_id, status);
create index reimbursement_invitations_claim_idx
  on reimbursement_invitations (claim_id);

create table reimbursement_memberships (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references profiles(id),
  contact_id uuid not null references reimbursement_contacts(id),
  auth_user_id uuid not null references profiles(id),
  email text,
  status reimbursement_membership_status not null default 'active',
  linked_at timestamptz not null default now(),
  revoked_at timestamptz,
  created_at timestamptz not null default now()
);

create unique index reimbursement_memberships_contact_user_active_idx
  on reimbursement_memberships (owner_user_id, contact_id, auth_user_id)
  where status = 'active';
create index reimbursement_memberships_owner_status_idx
  on reimbursement_memberships (owner_user_id, status);
create index reimbursement_memberships_auth_status_idx
  on reimbursement_memberships (auth_user_id, status);
create index reimbursement_memberships_contact_idx
  on reimbursement_memberships (contact_id);

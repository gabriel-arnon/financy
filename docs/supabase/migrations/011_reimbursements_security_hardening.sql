do $$
declare
  table_name text;
  app_tables text[] := array[
    'profiles',
    'accounts',
    'cards',
    'categories',
    'import_files',
    'import_batches',
    'card_statements',
    'import_preview_items',
    'transactions',
    'classification_rules',
    'stored_files',
    'transaction_attachments',
    'stored_file_events',
    'reimbursement_contacts',
    'reimbursement_claims',
    'reimbursement_items',
    'reimbursement_events',
    'reimbursement_invitations',
    'reimbursement_memberships',
    'reimbursement_claim_attachments',
    'reimbursement_comments',
    'reimbursement_invitation_accept_attempts'
  ];
begin
  foreach table_name in array app_tables loop
    if to_regclass(format('public.%I', table_name)) is not null then
      execute format('alter table public.%I enable row level security', table_name);
      execute format('revoke all privileges on table public.%I from public', table_name);

      if exists (select 1 from pg_roles where rolname = 'anon') then
        execute format('revoke all privileges on table public.%I from anon', table_name);
      end if;

      if exists (select 1 from pg_roles where rolname = 'authenticated') then
        execute format('revoke all privileges on table public.%I from authenticated', table_name);
      end if;
    end if;
  end loop;
end $$;

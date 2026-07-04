-- Financy Phase 3 RLS draft.
-- This file is intentionally outside docs/supabase/migrations.
-- Do not apply before backend JWT auth and two-user isolation tests pass.

-- Profiles
alter table profiles enable row level security;

create policy profiles_select_own on profiles
  for select using (id = auth.uid());

create policy profiles_update_own on profiles
  for update using (id = auth.uid())
  with check (id = auth.uid());

-- User-owned tables
alter table accounts enable row level security;
alter table cards enable row level security;
alter table card_statements enable row level security;
alter table transactions enable row level security;
alter table classification_rules enable row level security;
alter table import_files enable row level security;
alter table import_batches enable row level security;
alter table import_preview_items enable row level security;

create policy accounts_user_all on accounts
  for all using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy cards_user_all on cards
  for all using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy card_statements_user_all on card_statements
  for all using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy transactions_user_all on transactions
  for all using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy classification_rules_user_all on classification_rules
  for all using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy import_files_user_all on import_files
  for all using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy import_batches_user_all on import_batches
  for all using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy import_preview_items_user_all on import_preview_items
  for all using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- Categories: system categories are readable by authenticated users, user categories are private.
alter table categories enable row level security;

create policy categories_select_system_or_own on categories
  for select using (user_id is null or user_id = auth.uid());

create policy categories_insert_own on categories
  for insert with check (user_id = auth.uid() and is_system = false);

create policy categories_update_own on categories
  for update using (user_id = auth.uid() and is_system = false)
  with check (user_id = auth.uid() and is_system = false);

create policy categories_delete_own on categories
  for delete using (user_id = auth.uid() and is_system = false);

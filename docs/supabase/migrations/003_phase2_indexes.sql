create index if not exists accounts_user_id_idx on accounts (user_id);

create index if not exists cards_user_id_idx on cards (user_id);
create index if not exists cards_account_id_idx on cards (account_id);

create index if not exists card_statements_user_id_idx on card_statements (user_id);
create index if not exists card_statements_card_id_idx on card_statements (card_id);

create index if not exists transactions_user_id_idx on transactions (user_id);
create index if not exists transactions_transaction_date_idx on transactions (transaction_date);
create index if not exists transactions_account_id_idx on transactions (account_id);
create index if not exists transactions_card_id_idx on transactions (card_id);
create index if not exists transactions_card_statement_id_idx on transactions (card_statement_id);
create index if not exists transactions_category_id_idx on transactions (category_id);

create index if not exists classification_rules_user_id_idx on classification_rules (user_id);
create index if not exists classification_rules_category_id_idx on classification_rules (category_id);

create index if not exists import_files_user_id_idx on import_files (user_id);
create index if not exists import_batches_user_id_idx on import_batches (user_id);
create index if not exists import_batches_source_file_id_idx on import_batches (source_file_id);

create index if not exists import_preview_items_user_id_idx on import_preview_items (user_id);
create index if not exists import_preview_items_import_batch_id_idx on import_preview_items (import_batch_id);
create index if not exists import_preview_items_source_file_id_idx on import_preview_items (source_file_id);

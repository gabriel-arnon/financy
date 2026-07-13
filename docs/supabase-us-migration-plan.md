# Plano Seguro de Migração Supabase US - Financy

Data da auditoria: 2026-07-13  
Escopo: análise estática do repositório local. Nenhuma migration foi executada, nenhum ambiente remoto foi acessado e nenhuma credencial foi lida ou registrada.

## 1. Resumo executivo

O repositório atual contém migrations versionadas de `001_initial_schema.sql` a `006_reimbursements_domain.sql`. Esse conjunto reproduz o schema esperado pelo backend atualmente versionado para as funcionalidades de contas, cartões, transações, importações, regras, arquivos privados, anexos de transação e ressarcimentos owner-only.

Há uma divergência importante entre documentação de produto e código versionado: `docs/reimbursements-plan.md` descreve entidades futuras de portal guest, como `reimbursement_invitations`, `reimbursement_memberships` e `reimbursement_claim_attachments`, mas essas tabelas não existem em `docs/supabase/migrations` nem nos repositories/backend deste checkout. Se o Supabase Production atual já recebeu migrations posteriores por fora do repositório, o schema novo em North Virginia não será reproduzido integralmente apenas com este repo até essas migrations serem versionadas.

Recomendação de alto nível:

1. Congelar deploy e escrita no banco antigo no momento do cutover.
2. Exportar um schema-only dump do Supabase Production atual para comparar com as migrations versionadas.
3. Corrigir qualquer migration ausente antes de tocar no projeto US.
4. Aplicar o schema no Supabase US por conexão direta/admin.
5. Migrar Auth, dados públicos e Storage de forma separada, validando contagens, FKs, hashes e isolamento por usuário.
6. Testar o backend isolado contra o projeto US antes de alterar Render/Vercel.

## 2. Migrations existentes e ordem

Ordem atual em `docs/supabase/migrations`:

1. `001_initial_schema.sql`
2. `002_default_categories.sql`
3. `003_phase2_indexes.sql`
4. `004_nullable_card_account.sql`
5. `005_private_files.sql`
6. `006_reimbursements_domain.sql`

Conclusão sobre reprodutibilidade:

- Para o backend versionado neste checkout, as migrations 001-006 cobrem as tabelas e enums usados por `backend/app/repositories/postgres.py`.
- Não há migrations para RLS final, políticas, triggers, funções de negócio, Storage bucket ou Supabase Auth.
- Não há migrations 007/008 no repositório atual. Portanto, qualquer produção que já possua portal guest, convites, memberships ou compartilhamento explícito de comprovantes tem schema não reproduzível por este checkout.

## 3. Detalhe por migration

### 001_initial_schema.sql

Tipos:

- `transaction_type`: `expense`, `income`, `transfer`, `payment`, `refund`.
- `transaction_status`: `pending`, `confirmed`, `reconciled`, `ignored`.
- `preview_status`: `pending`, `selected`, `ignored`, `confirmed`, `duplicate`, `error`.
- `statement_status`: `open`, `closed`, `paid`, `partial`, `overdue`.
- `account_type`: `checking`, `savings`, `wallet`, `investment`.
- `entity_status`: `active`, `inactive`.
- `classification_match_scope`: `description`, `original_description`, `both`.
- `category_type`: `expense`, `income`, `both`.

Extensões:

- `pgcrypto`, para `gen_random_uuid()`.

Tabelas e colunas:

- `profiles`: `id`, `email`, `full_name`, `created_at`.
- `accounts`: `id`, `user_id`, `name`, `institution`, `agency`, `account_number`, `type`, `balance`, `status`, `created_at`.
- `cards`: `id`, `user_id`, `account_id`, `name`, `institution`, `brand`, `last_digits`, `limit_amount`, `closing_day`, `due_day`, `status`, `created_at`.
- `categories`: `id`, `user_id`, `name`, `type`, `status`, `is_system`, `created_at`.
- `import_files`: `id`, `user_id`, `filename`, `storage_path`, `mime_type`, `size_bytes`, `created_at`.
- `import_batches`: `id`, `user_id`, `source_file_id`, `status`, `created_at`.
- `card_statements`: `id`, `user_id`, `card_id`, `reference_month`, `due_date`, `closing_date`, `total_amount`, `minimum_payment_amount`, `status`, `paid_at`, `source_file_id`, `created_at`.
- `import_preview_items`: campos de transação importada, dados de conta/cartão/fatura detectados, classificação, flags de revisão, status e `raw_row`.
- `transactions`: `id`, `user_id`, `account_id`, `card_id`, `card_statement_id`, `transaction_date`, `description`, `original_description`, `normalized_description`, `amount`, `type`, `category_id`, `source_file_id`, parcelas, `status`, `created_at`.
- `classification_rules`: `id`, `user_id`, `keyword`, `category_id`, `transaction_type`, `priority`, `status`, `match_scope`, `auto_created`, `created_at`.

Índices/unique constraints:

- `categories_user_name_idx`: unique parcial em `(user_id, name)` quando `user_id is not null`.
- `categories_default_name_idx`: unique parcial em `(name)` quando `user_id is null`.
- `transactions_dedupe_idx`: unique em assinatura de deduplicação por usuário, conta/cartão, data, descrição normalizada, valor e parcelas.

Foreign keys:

- Todas as entidades user-owned referenciam `profiles(id)` via `user_id`.
- `cards.account_id -> accounts(id)`.
- `import_batches.source_file_id -> import_files(id)`.
- `card_statements.card_id -> cards(id)`.
- `card_statements.source_file_id -> import_files(id)`.
- `import_preview_items` referencia import, arquivo, conta, cartão, fatura e categoria.
- `transactions` referencia conta, cartão, fatura, categoria e arquivo de importação.
- `classification_rules.category_id -> categories(id)`.

Constraints relevantes:

- PKs UUID.
- `cards.last_digits` com check de quatro dígitos.
- Numeric financeiro em geral `numeric(14, 2)`.

Funções/triggers/policies/RLS:

- Nenhuma função customizada.
- Nenhum trigger.
- Nenhuma policy/RLS.

Seeds:

- Nenhum seed nesta migration.

Operações destrutivas:

- Nenhuma `drop`, `delete` ou alteração destrutiva. Em banco já populado, não é idempotente por si só porque usa `create type` e `create table` sem `if not exists`; a idempotência depende de `schema_migrations`.

### 002_default_categories.sql

Tabelas afetadas:

- `categories`.

Seeds:

- Insere categorias sistema com `user_id = null`, `status = active`, `is_system = true`.
- Usa `on conflict do nothing`.

Observação crítica:

- O arquivo contém mojibake visível em nomes como `AlimentaÃ§Ã£o`, `SaÃºde`, `EducaÃ§Ã£o` e `ServiÃ§os`. Antes de migrar produção, validar se a produção atual tem nomes corrigidos manualmente ou se é necessário criar migration incremental de correção. Não alterar dados em produção sem confirmação.

Índices/FKs/constraints/funções/triggers/RLS:

- Nenhum objeto novo além dos inserts.

Operações destrutivas:

- Nenhuma.

### 003_phase2_indexes.sql

Índices:

- `accounts_user_id_idx`.
- `cards_user_id_idx`, `cards_account_id_idx`.
- `card_statements_user_id_idx`, `card_statements_card_id_idx`.
- `transactions_user_id_idx`, `transactions_transaction_date_idx`, `transactions_account_id_idx`, `transactions_card_id_idx`, `transactions_card_statement_id_idx`, `transactions_category_id_idx`.
- `classification_rules_user_id_idx`, `classification_rules_category_id_idx`.
- `import_files_user_id_idx`.
- `import_batches_user_id_idx`, `import_batches_source_file_id_idx`.
- `import_preview_items_user_id_idx`, `import_preview_items_import_batch_id_idx`, `import_preview_items_source_file_id_idx`.

Tabelas/colunas/FKs/constraints/funções/triggers/RLS/seeds:

- Não cria tabelas, colunas, FKs, constraints, funções, triggers, policies nem seeds.

Operações destrutivas:

- Nenhuma. Usa `create index if not exists`.

### 004_nullable_card_account.sql

Alteração:

- `alter table cards alter column account_id drop not null`.

Impacto:

- Permite cartão sem conta bancária associada, compatível com o backend atual.

Índices/FKs/constraints/funções/triggers/RLS/seeds:

- Não cria objetos novos. A FK `cards.account_id -> accounts(id)` permanece, mas nullable.

Operações destrutivas:

- Não destrói dados. É alteração permissiva.

### 005_private_files.sql

Tipos:

- `stored_file_status`: `uploaded`, `quarantined`, `available`, `rejected`, `deleted`.
- `stored_file_scan_status`: `pending`, `clean`, `suspicious`, `failed`, `skipped`.

Tabelas e colunas:

- `stored_files`: `id`, `owner_user_id`, `storage_bucket`, `storage_path`, `original_filename`, `declared_mime_type`, `detected_mime_type`, `size_bytes`, `sha256_hash`, `source`, `status`, `scan_status`, `metadata`, `created_at`, `deleted_at`.
- `transaction_attachments`: `id`, `owner_user_id`, `transaction_id`, `file_id`, `status`, `created_at`, `deleted_at`.
- `stored_file_events`: `id`, `owner_user_id`, `file_id`, `actor_type`, `actor_user_id`, `event_type`, `metadata`, `created_at`.

Índices/unique constraints:

- `stored_files_storage_object_idx`: unique em `(storage_bucket, storage_path)`.
- `stored_files_owner_user_id_idx`.
- `stored_files_owner_hash_idx`.
- `stored_files_status_idx`.
- `transaction_attachments_active_file_idx`: unique parcial em `(transaction_id, file_id)` quando `status = active`.
- `transaction_attachments_owner_user_id_idx`.
- `transaction_attachments_transaction_id_idx`.
- `transaction_attachments_file_id_idx`.
- `stored_file_events_owner_file_created_idx`.

Foreign keys:

- `stored_files.owner_user_id -> profiles(id)`.
- `transaction_attachments.owner_user_id -> profiles(id)`.
- `transaction_attachments.transaction_id -> transactions(id)`.
- `transaction_attachments.file_id -> stored_files(id)`.
- `stored_file_events.owner_user_id -> profiles(id)`.
- `stored_file_events.file_id -> stored_files(id)`.

Constraints:

- `stored_files.size_bytes > 0`.
- Status por enums.

Funções/triggers/policies/RLS/seeds:

- Nenhuma função, trigger, policy/RLS ou seed.

Operações destrutivas:

- Nenhuma.

Dependência externa:

- A migration não cria bucket no Supabase Storage. O bucket privado configurado em `PRIVATE_FILES_BUCKET`/`SUPABASE_STORAGE_BUCKET` precisa ser criado separadamente no projeto US.

### 006_reimbursements_domain.sql

Tipos:

- `reimbursement_claim_status`: `draft`, `sent`, `acknowledged`, `disputed`, `partially_paid`, `paid`, `canceled`.
- `reimbursement_item_status`: `active`, `canceled`.
- `reimbursement_event_actor_type`: `owner`, `guest`, `system`.

Tabelas e colunas:

- `reimbursement_contacts`: `id`, `owner_user_id`, `display_name`, `email`, `phone`, `status`, `metadata`, `created_at`, `updated_at`.
- `reimbursement_claims`: `id`, `owner_user_id`, `contact_id`, `title`, `description`, `due_date`, `status`, `total_snapshot`, `version`, `sent_at`, `canceled_at`, `first_viewed_at`, `last_viewed_at`, `view_count`, `created_at`, `updated_at`.
- `reimbursement_items`: `id`, `owner_user_id`, `claim_id`, `transaction_id`, `amount_requested`, `status`, `transaction_snapshot`, `position`, `canceled_at`, `created_at`.
- `reimbursement_events`: `id`, `owner_user_id`, `claim_id`, `contact_id`, `item_id`, `actor_type`, `actor_user_id`, `event_type`, `metadata`, `created_at`.

Índices/unique constraints:

- `reimbursement_contacts_owner_display_name_active_idx`: unique parcial em `(owner_user_id, lower(trim(display_name)))` para contatos ativos.
- `reimbursement_contacts_owner_user_id_idx`.
- `reimbursement_claims_owner_user_id_idx`.
- `reimbursement_claims_owner_contact_status_due_idx`.
- `reimbursement_claims_contact_id_idx`.
- `reimbursement_items_claim_transaction_active_idx`: unique parcial em `(claim_id, transaction_id)` para itens ativos.
- `reimbursement_items_owner_user_id_idx`.
- `reimbursement_items_claim_id_idx`.
- `reimbursement_items_transaction_id_idx`.
- `reimbursement_events_owner_created_idx`.
- `reimbursement_events_claim_created_idx`.

Foreign keys:

- `reimbursement_contacts.owner_user_id -> profiles(id)`.
- `reimbursement_claims.owner_user_id -> profiles(id)`.
- `reimbursement_claims.contact_id -> reimbursement_contacts(id)`.
- `reimbursement_items.owner_user_id -> profiles(id)`.
- `reimbursement_items.claim_id -> reimbursement_claims(id)`.
- `reimbursement_items.transaction_id -> transactions(id)`.
- `reimbursement_events.owner_user_id -> profiles(id)`.
- `reimbursement_events.claim_id -> reimbursement_claims(id)`.
- `reimbursement_events.contact_id -> reimbursement_contacts(id)`.
- `reimbursement_events.item_id -> reimbursement_items(id)`.

Constraints:

- `reimbursement_items.amount_requested > 0`.
- Status por enums.

Funções/triggers/policies/RLS/seeds:

- Nenhuma função, trigger, policy/RLS ou seed.

Operações destrutivas:

- Nenhuma.

## 4. RLS e policies

As migrations versionadas 001-006 não habilitam RLS e não criam policies.

Existe um draft separado em `docs/supabase/rls_phase3_draft.sql`, não aplicado pelo script de migrations, cobrindo:

- `profiles`;
- `accounts`;
- `cards`;
- `card_statements`;
- `transactions`;
- `classification_rules`;
- `import_files`;
- `import_batches`;
- `import_preview_items`;
- `categories`.

Esse draft não inclui tabelas criadas depois, como:

- `stored_files`;
- `transaction_attachments`;
- `stored_file_events`;
- `reimbursement_contacts`;
- `reimbursement_claims`;
- `reimbursement_items`;
- `reimbursement_events`.

Como o backend usa Supabase service/admin para algumas operações e valida owner no servidor, RLS final pode ser ativado depois de testes específicos. Não ativar o draft incompleto no projeto US sem política completa para todas as tabelas sensíveis.

## 5. Análise de `backend/scripts/apply_migrations.py`

Variáveis/configurações lidas:

- Argumento `--database-url`, com default `settings.database_url`.
- `settings.database_url` vem da configuração Pydantic e lê `DATABASE_URL`.
- `FINANCY_ALLOW_REMOTE_MIGRATIONS`, aceitando `1`, `true` ou `yes`.
- Não há suporte a `DATABASE_MIGRATION_URL`.

Como detecta banco remoto:

- Usa `scripts/dev_db_safety.py`.
- `parse_safe_database_url()` extrai `host`, `port`, `dbname` e `user` com `psycopg.conninfo_to_dict`.
- `assert_local_database_url()` permite apenas hosts `localhost`, `127.0.0.1`, `::1` e `postgres`.
- Bloqueia nomes de banco contendo `prod` ou `production`.
- A senha nunca é exibida; `safe.display` mascara como `***`.

Como funciona `--allow-remote`:

- Se o host não for local, o script imprime o destino mascarado.
- Sem `--allow-remote` ou `FINANCY_ALLOW_REMOTE_MIGRATIONS=true`, ele pula as migrations e encerra sem erro.
- Com `--allow-remote`, aplica migrations no remoto.
- `--reset-schema` é recusado em banco remoto mesmo com allow remoto.

Idempotência:

- Cria `schema_migrations(version text primary key, applied_at timestamptz default now())`.
- Cada arquivo SQL aplicado é registrado pelo nome do arquivo.
- Em execuções futuras, arquivos já registrados são ignorados.
- A idempotência depende da tabela `schema_migrations`; a maioria dos SQLs não é idempotente isoladamente por usar `create type`/`create table` sem `if not exists`.

Onde registra migrations:

- Tabela pública `schema_migrations`.
- Colunas: `version`, `applied_at`.

Segurança para Supabase novo:

- É seguro para um Supabase novo vazio se:
  - a URL for explicitamente do projeto US correto;
  - for usada conexão de migração/admin apropriada;
  - `--allow-remote` for passado conscientemente;
  - `--reset-schema` não for usado remoto;
  - as migrations ausentes forem resolvidas antes, caso produção tenha schema além de 001-006.
- Não cria bucket Storage, não migra Auth, não aplica RLS e não migra dados.

## 6. Comparação backend x migrations

Tabelas esperadas pelo `PostgresRepository` e cobertas:

- `profiles`: coberta por 001.
- `categories`: coberta por 001/002.
- `classification_rules`: coberta por 001/003.
- `accounts`: coberta por 001/003.
- `cards`: coberta por 001/003/004.
- `import_files`: coberta por 001/003.
- `import_batches`: coberta por 001/003.
- `import_preview_items`: coberta por 001/003.
- `transactions`: coberta por 001/003.
- `card_statements`: coberta por 001/003.
- `stored_files`: coberta por 005.
- `transaction_attachments`: coberta por 005.
- `stored_file_events`: coberta por 005.
- `reimbursement_contacts`: coberta por 006.
- `reimbursement_claims`: coberta por 006.
- `reimbursement_items`: coberta por 006.
- `reimbursement_events`: coberta por 006.

Diferenças ou riscos encontrados:

- `docs/reimbursements-plan.md` menciona tabelas futuras não presentes no backend/migrations: `reimbursement_invitations`, `reimbursement_memberships`, `reimbursement_claim_attachments`, comentários e pagamentos.
- `ReimbursementClaimStatus` inclui `acknowledged`, `disputed`, `partially_paid` e `paid`, mas o backend versionado não implementa portal guest nem pagamentos. O enum está preparado, não é incompatibilidade.
- `import_files.storage_path` guarda caminho de arquivo de importação, mas a infraestrutura persistente de import files não é a mesma de `stored_files`; validar se arquivos históricos de importação precisam ser migrados do filesystem/Storage antigo.
- `002_default_categories.sql` tem mojibake nos nomes seedados; isso pode divergir do dado real de produção se houve correção manual.
- O schema não tem `updated_at` em várias tabelas que o backend não exige; sem divergência operacional, mas relevante para auditoria.
- Não há triggers para atualizar `updated_at`; o backend atualiza explicitamente onde precisa.

## 7. Tabelas que precisam ter dados migrados

Dados públicos/financeiros:

- `profiles`.
- `accounts`.
- `cards`.
- `categories`.
- `classification_rules`.
- `import_files`.
- `import_batches`.
- `import_preview_items`, se previews históricos devem ser preservados.
- `card_statements`.
- `transactions`.
- `stored_files`.
- `transaction_attachments`.
- `stored_file_events`, se auditoria de arquivos deve ser preservada.
- `reimbursement_contacts`.
- `reimbursement_claims`.
- `reimbursement_items`.
- `reimbursement_events`.

Metadados de migration:

- `schema_migrations` pode ser recriada pela execução das migrations no projeto US. Não deve ser importada antes de aplicar o schema, a menos que a estratégia seja restaurar dump integral.

Seeds:

- Categorias sistema (`categories.user_id is null`) precisam existir. Preferir aplicar migration 002 e depois comparar/corrigir nomes, em vez de importar duplicado.

Supabase Auth:

- Usuários em `auth.users` não são criados pelas migrations públicas. Eles precisam ser migrados por fluxo próprio de Auth/export ou recriados de forma controlada mantendo UUIDs.

Storage:

- Objetos do bucket privado, vinculados por `stored_files.storage_bucket` e `stored_files.storage_path`.
- Possíveis arquivos antigos de importação vinculados por `import_files.storage_path`, dependendo de onde estão armazenados no ambiente atual.

## 8. Relação Supabase Auth x tabelas públicas

Identidade:

- O backend lê o JWT Supabase em `backend/app/core/auth.py`.
- `sub` do JWT vira `CurrentUser.id`.
- `email` e `user_metadata.full_name` entram em `CurrentUser`.
- `backend/app/api/deps.py` chama `ensure_profile(user.id, email, full_name)` em cada request autenticado, criando/atualizando `profiles`.

Colunas de owner:

- Domínio core usa `user_id`: `accounts`, `cards`, `categories` user-owned, `classification_rules`, `import_files`, `import_batches`, `import_preview_items`, `card_statements`, `transactions`.
- Arquivos privados e ressarcimentos usam `owner_user_id`: `stored_files`, `transaction_attachments`, `stored_file_events`, `reimbursement_contacts`, `reimbursement_claims`, `reimbursement_items`, `reimbursement_events`.

Memberships:

- O repositório atual não possui `reimbursement_memberships`.
- O plano de produto prevê memberships para guest, mas não há migration/código versionado nesta árvore.
- Se produção atual já tiver memberships, é necessário exportar o schema real e versionar migration incremental antes da migração.

Requisito crítico para migrar Auth:

- Os UUIDs de `auth.users.id` no projeto US precisam continuar iguais aos IDs referenciados em `profiles.id`, `user_id` e `owner_user_id`.
- Se UUIDs mudarem, será necessário remapear todos os FKs/owners, o que aumenta muito o risco e deve ser evitado.

## 9. Dependências de Storage

Configuração:

- Backend lê `PRIVATE_FILES_BACKEND` ou `FILE_STORAGE_PROVIDER`.
- Para Supabase Storage, requer `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` e `PRIVATE_FILES_BUCKET` ou `SUPABASE_STORAGE_BUCKET`.
- Exemplo de produção aponta bucket `financy-private`.

Buckets:

- Bucket privado esperado: valor de `PRIVATE_FILES_BUCKET`, default `financy-private`.
- A migration 005 não cria bucket. O bucket precisa ser criado no Supabase US antes de habilitar uploads/signed URLs.
- Não usar bucket público.

Object keys:

- Arquivos privados novos usam padrão: `user/{owner_user_id}/files/{file_id}{extension}`.
- `stored_files.storage_path` é fonte de verdade para signed URLs.
- `stored_files.storage_bucket` precisa bater com o bucket migrado.

Tabelas relacionadas:

- `stored_files`: metadata, hash, status, scan status, caminho e bucket.
- `transaction_attachments`: vínculo ativo/inativo entre transação e arquivo.
- `stored_file_events`: auditoria de upload/delete/signed URL.
- `import_files`: tem `storage_path` próprio para arquivos de importação; precisa ser avaliado separadamente do bucket privado.

Signed URLs:

- Geradas em `FileService.signed_url()`.
- Para Supabase, chama `/storage/v1/object/sign/{bucket}/{path}` com service role.
- TTL vem de `PRIVATE_FILES_SIGNED_URL_TTL_SECONDS` ou `SIGNED_URL_TTL_SECONDS`, default atual 300 segundos.
- O backend bloqueia signed URL se `stored_files.status != available` ou `scan_status` não for `clean`/`skipped`.

Cuidados:

- Não expor `SUPABASE_SERVICE_ROLE_KEY` no frontend.
- Não logar URLs assinadas.
- Após migrar Storage, validar amostras com arquivos JPEG/PNG/WebP/PDF e anexos reais.

## 10. Plano em etapas

### Etapa 0 - Congelamento e baseline

1. Definir janela de migração.
2. Pausar deploys e jobs de escrita.
3. Coletar versão de commit em produção.
4. Gerar schema-only dump do Supabase antigo para comparação offline.
5. Confirmar se produção tem tabelas além de 001-006.
6. Confirmar bucket(s), região antiga e nova, e volume de Storage.

### Etapa 1 - Preparar projeto Supabase US

1. Criar projeto North Virginia.
2. Configurar Auth providers e URLs sem apontar produção ainda.
3. Criar bucket privado `financy-private` ou nome configurado.
4. Registrar credenciais apenas em cofre/Render/Vercel, nunca no repositório.
5. Usar conexão direta/admin para migrations, não transaction pooler.

### Etapa 2 - Aplicar schema

1. Validar que a URL é do projeto US novo.
2. Aplicar migrations 001-006 com `--allow-remote`.
3. Verificar `schema_migrations`.
4. Verificar tabelas, enums, índices e FKs.
5. Se houver migrations ausentes em produção antiga, parar e versionar antes de importar dados.

### Etapa 3 - Migrar Auth

1. Exportar usuários do Supabase Auth antigo por método oficial/seguro.
2. Importar para o projeto US preservando UUIDs.
3. Validar que `auth.users.id` corresponde a `profiles.id`.
4. Validar emails, status de confirmação e providers.
5. Forçar reset/reauth se senhas/provider identities não forem migráveis de forma segura.

### Etapa 4 - Migrar dados públicos

1. Exportar dados por tabela em ordem compatível com FKs.
2. Importar no projeto US em transação ou lotes controlados.
3. Preservar UUIDs e timestamps.
4. Desabilitar escritas no banco antigo durante export final.
5. Reaplicar/analisar sequences se houver, embora o schema use UUID.

Ordem sugerida:

1. `profiles`
2. `categories`
3. `accounts`
4. `cards`
5. `import_files`
6. `import_batches`
7. `card_statements`
8. `classification_rules`
9. `transactions`
10. `import_preview_items`
11. `stored_files`
12. `transaction_attachments`
13. `stored_file_events`
14. `reimbursement_contacts`
15. `reimbursement_claims`
16. `reimbursement_items`
17. `reimbursement_events`

### Etapa 5 - Migrar Storage

1. Copiar objetos do bucket antigo para o bucket privado US preservando `storage_path`.
2. Validar contagem de objetos contra `stored_files`.
3. Validar amostras por `sha256_hash`.
4. Confirmar que o bucket US é privado.
5. Gerar signed URLs apenas em smoke test controlado.
6. Verificar `import_files.storage_path` e migrar objetos de importação se eles estiverem em Storage.

### Etapa 6 - Validação

Consultas mínimas:

- Contagem por tabela.
- FKs sem órfãos.
- `profiles` sem usuário Auth correspondente.
- `auth.users` sem profile, se relevante.
- `stored_files` sem objeto no bucket.
- Objetos sem metadata em `stored_files`.
- Hash por amostra de arquivos.
- Contagens de transações por usuário.
- Contagens de claims/items por owner.
- Dedupe index sem conflito.

### Etapa 7 - Backend isolado

1. Criar ambiente Render staging apontando para Supabase US.
2. Configurar `STORAGE_BACKEND=postgres`, `PRIVATE_FILES_BACKEND=supabase`, Auth US e CORS de staging.
3. Rodar smoke tests manuais e automatizados.
4. Validar login, dashboard, transações, importação, anexos e ressarcimentos owner-only.
5. Validar logs sem secrets.

### Etapa 8 - Cutover

1. Ativar modo manutenção ou congelar escrita.
2. Fazer export incremental final.
3. Reimportar delta.
4. Migrar delta de Storage.
5. Atualizar Render para Supabase US.
6. Atualizar Vercel frontend para Supabase US Auth.
7. Fazer smoke test de produção.
8. Monitorar erros, latência e CORS.

### Etapa 9 - Rollback

1. Manter projeto antigo em read-only por período definido.
2. Se falhar antes de novas escritas no US, voltar Render/Vercel para variáveis antigas.
3. Se houver escritas no US após cutover, rollback exige plano de reconciliação de delta.
4. Não deletar projeto antigo até concluir validação de dados e backups.

## 11. Comandos PowerShell propostos

Não executar automaticamente. Substituir placeholders localmente sem registrar secrets.

### 11.1. Validar arquivos versionados

```powershell
git status --short
Get-ChildItem -File docs\supabase\migrations | Sort-Object Name | Select-Object Name, Length, LastWriteTime
```

### 11.2. Aplicar schema no Supabase US novo

Use conexão direta/admin do projeto US. Não usar production antigo. Não colar a senha em logs compartilhados.

```powershell
cd backend
$env:DATABASE_URL = "postgresql://postgres:REDACTED@db.NEW_US_PROJECT_REF.supabase.co:5432/postgres"
.\.venv\Scripts\python.exe scripts\apply_migrations.py --allow-remote
Remove-Item Env:\DATABASE_URL
```

Alternativa com argumento explícito:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\apply_migrations.py --database-url "postgresql://postgres:REDACTED@db.NEW_US_PROJECT_REF.supabase.co:5432/postgres" --allow-remote
```

### 11.3. Verificar migrations aplicadas

```powershell
psql "postgresql://postgres:REDACTED@db.NEW_US_PROJECT_REF.supabase.co:5432/postgres" -c "select version, applied_at from schema_migrations order by version;"
```

### 11.4. Contagens por tabela no banco antigo e novo

Executar separadamente contra origem e destino, salvando saídas sem credenciais.

```powershell
$tables = @(
  "profiles",
  "categories",
  "accounts",
  "cards",
  "import_files",
  "import_batches",
  "card_statements",
  "classification_rules",
  "transactions",
  "import_preview_items",
  "stored_files",
  "transaction_attachments",
  "stored_file_events",
  "reimbursement_contacts",
  "reimbursement_claims",
  "reimbursement_items",
  "reimbursement_events"
)

foreach ($table in $tables) {
  psql "postgresql://postgres:REDACTED@HOST:5432/postgres" -c "select '$table' as table_name, count(*) from public.$table;"
}
```

### 11.5. Verificar órfãos de FKs críticas

```powershell
psql "postgresql://postgres:REDACTED@db.NEW_US_PROJECT_REF.supabase.co:5432/postgres" -c "
select 'accounts without profile' check_name, count(*) from accounts a left join profiles p on p.id = a.user_id where p.id is null
union all
select 'transactions without profile', count(*) from transactions t left join profiles p on p.id = t.user_id where p.id is null
union all
select 'stored_files without profile', count(*) from stored_files sf left join profiles p on p.id = sf.owner_user_id where p.id is null
union all
select 'claims without profile', count(*) from reimbursement_claims rc left join profiles p on p.id = rc.owner_user_id where p.id is null
union all
select 'items without claim', count(*) from reimbursement_items ri left join reimbursement_claims rc on rc.id = ri.claim_id where rc.id is null;
"
```

### 11.6. Export/import público via dump customizado

Preferir validar primeiro em staging. Exemplo conceitual:

```powershell
pg_dump "postgresql://postgres:REDACTED@db.OLD_PROJECT_REF.supabase.co:5432/postgres" `
  --format=custom `
  --data-only `
  --schema=public `
  --exclude-table=public.schema_migrations `
  --file ".\backups\financy-public-data.dump"

pg_restore "postgresql://postgres:REDACTED@db.NEW_US_PROJECT_REF.supabase.co:5432/postgres" `
  --data-only `
  --schema=public `
  --disable-triggers `
  ".\backups\financy-public-data.dump"
```

### 11.7. Export schema-only para comparação

```powershell
pg_dump "postgresql://postgres:REDACTED@db.OLD_PROJECT_REF.supabase.co:5432/postgres" `
  --schema-only `
  --schema=public `
  --file ".\backups\old-public-schema.sql"

pg_dump "postgresql://postgres:REDACTED@db.NEW_US_PROJECT_REF.supabase.co:5432/postgres" `
  --schema-only `
  --schema=public `
  --file ".\backups\new-public-schema.sql"
```

### 11.8. Smoke do backend isolado

```powershell
cd backend
$env:STORAGE_BACKEND = "postgres"
$env:DATABASE_URL = "postgresql://postgres:REDACTED@db.NEW_US_PROJECT_REF.supabase.co:5432/postgres"
$env:AUTH_REQUIRED = "true"
$env:AUTH_DEV_BYPASS = "false"
$env:SUPABASE_URL = "https://NEW_US_PROJECT_REF.supabase.co"
$env:SUPABASE_JWT_ISSUER = "https://NEW_US_PROJECT_REF.supabase.co/auth/v1"
$env:SUPABASE_JWKS_URL = "https://NEW_US_PROJECT_REF.supabase.co/auth/v1/.well-known/jwks.json"
$env:SUPABASE_AUDIENCE = "authenticated"
$env:PRIVATE_FILES_BACKEND = "supabase"
$env:PRIVATE_FILES_BUCKET = "financy-private"
$env:SUPABASE_SERVICE_ROLE_KEY = "REDACTED"
.\.venv\Scripts\python.exe -m pytest
```

### 11.9. Smoke de Storage Supabase dev/staging

Usar apenas projeto US não produção ou staging antes do cutover.

```powershell
.\scripts\smoke_supabase_storage.ps1 `
  -DatabaseUrl "postgresql://postgres:REDACTED@db.NEW_US_PROJECT_REF.supabase.co:5432/postgres"
```

## 12. Validações recomendadas

Schema:

- `schema_migrations` contém exatamente 001-006, ou também migrations adicionais versionadas antes do cutover.
- `pg_type` contém todos os enums esperados.
- `information_schema.tables` contém todas as tabelas públicas esperadas.
- Índices unique existem, especialmente `transactions_dedupe_idx` e partial uniques de ressarcimentos/anexos.

Dados:

- Contagens iguais por tabela entre origem e destino.
- `sum(amount)` por usuário em `transactions` igual.
- Número de `stored_files` por status igual.
- Número de anexos ativos por usuário igual.
- Número de claims/items/eventos por owner igual.

Auth:

- Todo `profiles.id` existe em `auth.users.id`, exceto usuários de sistema/dev que não devam ir para produção.
- JWT do novo projeto autentica no backend isolado.
- `SUPABASE_JWT_ISSUER`, `SUPABASE_JWKS_URL` e `SUPABASE_AUDIENCE` apontam para o projeto US.

Storage:

- Bucket privado existe.
- Nenhum objeto esperado falta.
- Amostras de arquivos batem com `sha256_hash`.
- Signed URL curta funciona e não revela `storage_path` em resposta pública além do necessário no backend.

Segurança:

- Backend não aceita `user_id`/`owner_user_id` do cliente para entidades user-owned.
- Service role fica somente no backend.
- RLS incompleta não é ativada silenciosamente.
- Logs não contêm secrets, tokens ou signed URLs.

## 13. Riscos e bloqueios

Riscos críticos:

- Schema real de produção pode conter migrations não versionadas neste checkout.
- Supabase Auth pode não preservar senhas/providers se migrado de forma inadequada.
- Storage pode ter objetos fora de `stored_files` ou `import_files`.
- `002_default_categories.sql` possui texto corrompido em seeds.
- Sem RLS aplicada nas migrations, a segurança depende do backend e do uso correto da service role.
- Usar transaction pooler para migrations pode causar falhas ou comportamento inesperado em DDL; usar conexão direta/admin.

Bloqueios antes de migrar:

- Obter dump schema-only do Supabase Production atual.
- Confirmar se existem tabelas/migrations 007+ em produção.
- Definir procedimento oficial para migrar Auth preservando UUIDs.
- Confirmar bucket(s) e paths reais usados por `import_files.storage_path`.

## 14. Checklist de cutover

Antes:

- Backup do banco antigo.
- Export de Auth validado.
- Export de Storage validado.
- Schema US comparado com produção.
- Backend staging contra US aprovado.
- Variáveis Render/Vercel preparadas, sem aplicar.
- Plano de rollback com janela máxima definida.

Durante:

- Congelar escrita.
- Exportar delta final.
- Importar delta.
- Sincronizar Storage final.
- Atualizar Render.
- Atualizar Vercel/Supabase client env.
- Smoke test login, transações, importação, anexos e ressarcimentos.

Depois:

- Monitorar 401/403/500, CORS, latência e falhas de Storage.
- Comparar contagens finais.
- Manter projeto antigo sem escrita até fim da janela de rollback.
- Documentar hora de cutover e commit usado.

## 15. Conclusão

Não há alteração executada nesta auditoria. O repositório atual está preparado para reconstruir o schema versionado 001-006 em um Supabase novo, mas não prova equivalência com o Supabase Production atual sem um schema dump da produção antiga. O maior risco é migrar para North Virginia assumindo que as migrations versionadas representam produção se houve alterações manuais ou migrations não commitadas.

Próximo passo seguro: gerar e comparar o schema-only dump do Supabase Production antigo contra o schema produzido por 001-006 em um banco descartável/local ou projeto US staging, sem migrar dados reais ainda.

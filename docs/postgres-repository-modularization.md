# Modularizacao do PostgresRepository

## Objetivo

Reduzir o tamanho de `backend/app/repositories/postgres.py` em lotes pequenos, preservando `create_repository(settings)` e o contrato usado por APIs, servicos e testes.

## Fachada atual

`PostgresRepository` continua sendo a fachada publica. Dominios extraidos devem entrar como mixins ou componentes internos sem exigir alteracao nos consumidores.

## Mapa por dominio

- Base/infra: conexao, `_fetch_all`, `_fetch_one`, `_execute`, `_insert`, `_update`, profiles.
- Categorias e regras: categorias, seeds, `classification_rules`, matching deterministico.
- Contas e cartoes: accounts, cards e vinculacao basica.
- Planejamento: recorrentes, metas e orcamentos.
- Open Finance: items, account links, transaction links e sync runs.
- Importacao e preview: arquivos importados, batches, preview items e status.
- Transacoes e faturas: transactions, signatures, card statements.
- Arquivos privados: stored files, attachments, eventos e limpeza.
- Ressarcimentos owner: contacts, claims, items, allocation atomica e eventos.
- Ressarcimentos guest: comments, invitations, rate limits, memberships, guest claims e attachments compartilhados.

## Lote 1 concluido

Extraido `PostgresCategoriesRulesMixin` para `backend/app/repositories/postgres_categories_rules.py`.

Metodos movidos:

- `categories`
- `_all_categories`
- `get_category`
- `find_category_by_name`
- `create_category`
- `update_category`
- `delete_category`
- `_ensure_classification_seeds`
- `list_classification_rules`
- `_all_classification_rules`
- `get_classification_rule`
- `create_classification_rule`
- `update_classification_rule`
- `delete_classification_rule`
- `category_exists`
- `category_name`
- `match_classification_rule`

## Lotes adicionais em andamento

- `PostgresPayeesMixin` concentra `payees` e `merchant_aliases`, preservando a fachada `PostgresRepository`.
- `PostgresJobsMixin` concentra `job_runs` e a idempotencia de jobs por `user_id`, `kind` e `idempotency_key`.
- `PostgresAccountsCardsMixin` concentra CRUDs de `accounts` e `cards`, mantendo as mesmas queries owner-scoped e soft delete.

## Proximos lotes sugeridos

1. Planejamento, porque ja e um dominio novo e coeso.
2. Open Finance persistence, agora que provider e jobs ja estao separados.
3. Importacao/preview e transacoes/faturas, com cuidado maior por causa de dedupe.
4. Arquivos privados.
5. Ressarcimentos, por ultimo, pois concentra concorrencia, guest access e historico sensivel.

Cada lote deve rodar a suite backend completa quando tocar contratos usados por servicos.

# Open Finance via Meu Pluggy/Pluggy

## Escopo

A integracao Open Finance do Financy e owner-only e somente leitura. Ela busca dados da Pluggy e alimenta as tabelas atuais de `accounts`, `cards` e `transactions`, permitindo que dashboard, transacoes, contas, cartoes, regras e insights usem os mesmos dados ja existentes no produto.

Nao ha pagamentos, Pix, transferencias ou confirmacao automatica de acoes sensiveis.

## Variaveis

Backend:

```env
OPEN_FINANCE_ENABLED=true
OPEN_FINANCE_OWNER_USER_ID=<uuid-do-owner>
PLUGGY_BASE_URL=https://api.pluggy.ai
PLUGGY_CLIENT_ID=<client-id>
PLUGGY_CLIENT_SECRET=<client-secret>
PLUGGY_WEBHOOK_SECRET=<secret-opcional>
PLUGGY_SYNC_LOOKBACK_DAYS=370
PLUGGY_API_TIMEOUT_SECONDS=30
```

Frontend:

```env
NEXT_PUBLIC_OPEN_FINANCE_ENABLED=true
NEXT_PUBLIC_OPEN_FINANCE_OWNER_USER_ID=<uuid-do-owner>
```

As variaveis `NEXT_PUBLIC_*` apenas controlam visibilidade da aba. O backend sempre valida o usuario autenticado contra `OPEN_FINANCE_OWNER_USER_ID`.

## Setup inicial

1. Acesse `https://meu.pluggy.ai`.
2. Conecte as instituicoes pessoais desejadas.
3. Acesse o Pluggy Dashboard e conecte os items do Meu Pluggy na aplicacao usada pelo Financy.
4. Configure `PLUGGY_CLIENT_ID` e `PLUGGY_CLIENT_SECRET` somente no backend.
5. Configure o UUID do owner no backend e frontend.
6. Aplique a migration `012_open_finance_integration.sql`.
7. Abra a aba `Open Finance`, cadastre o `Item ID Pluggy` e rode `Sincronizar`.

## Persistencia

Tabelas novas:

- `open_finance_items`: conexoes/items Pluggy.
- `open_finance_account_links`: vinculo entre contas/cartoes Pluggy e entidades locais.
- `open_finance_transaction_links`: vinculo entre transacoes Pluggy e transacoes locais.
- `open_finance_sync_runs`: historico sanitizado de sincronizacoes.

Colunas novas:

- `accounts.external_source`
- `cards.external_source`
- `transactions.external_source`

O dedupe principal usa `provider + external_transaction_id`. O dedupe secundario usa a assinatura local de transacao.

## Endpoints

- `GET /open-finance/status`
- `GET /open-finance/items`
- `POST /open-finance/items`
- `POST /open-finance/items/{external_item_id}/sync`
- `POST /open-finance/sync`
- `GET /open-finance/sync-runs`
- `POST /open-finance/webhook/pluggy`

## Validacao local

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

PostgreSQL local:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_dev_db.ps1 -ResetSchema
cd backend
$env:TEST_DATABASE_URL='postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev_test'
.\.venv\Scripts\python.exe -m pytest tests_postgres -m postgres -q
```

Frontend:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
npx.cmd playwright test tests/e2e/open-finance.spec.ts --project=chromium --reporter=line
```

## Runbook rapido

- `open_finance_not_configured`: faltam `OPEN_FINANCE_OWNER_USER_ID`, `PLUGGY_CLIENT_ID` ou `PLUGGY_CLIENT_SECRET`.
- `open_finance_not_found`: usuario autenticado nao e o owner configurado.
- `open_finance_sync_failed`: falha ao chamar ou normalizar dados Pluggy; veja `open_finance_sync_runs.error_message`.
- HTTP 401/403 da Pluggy: credenciais invalidas, expiradas ou sem acesso ao item.
- HTTP 429 da Pluggy: aguarde janela de rate limit antes de sincronizar novamente.
- Item sem transacoes: confirme o consentimento no Meu Pluggy e o periodo configurado em `PLUGGY_SYNC_LOOKBACK_DAYS`.

## Pendencia operacional

A validacao real contra `meu.pluggy.ai` depende das credenciais Pluggy, item IDs e conexoes pessoais do owner. Nao coloque esses valores no repositorio.

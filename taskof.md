# Financy - Tasks Open Finance

## Objetivo

Integrar Open Finance via Meu Pluggy/Pluggy para uso inicial exclusivo do usuario owner, alimentando as tabelas atuais de contas, cartoes e transacoes para que o dashboard principal passe a considerar os dados sincronizados automaticamente.

## Regras obrigatorias

- Integracao inicial e somente leitura: nao iniciar pagamentos, Pix, transferencias ou qualquer acao financeira sensivel.
- A feature deve funcionar apenas para o owner configurado no servidor.
- Nao aceitar `user_id` do frontend em nenhum endpoint Open Finance.
- Derivar o usuario autenticado pelo token atual e comparar com `OPEN_FINANCE_OWNER_USER_ID`.
- Guardar `PLUGGY_CLIENT_SECRET`, API key temporaria e webhook secret somente no backend/ambiente.
- Nao imprimir segredos, tokens, URLs assinadas completas, CPF, CNPJ ou payload financeiro sensivel em logs.
- Manter isolamento por usuario mesmo sendo uma feature owner-only.
- Usar upsert idempotente para evitar duplicidade em sync repetido.
- Preservar regras financeiras atuais; a sync deve alimentar dados, nao mudar sem necessidade a semantica de dashboard, contas, cartoes ou transacoes.

## Variaveis previstas

Backend:

```env
OPEN_FINANCE_ENABLED=false
OPEN_FINANCE_OWNER_USER_ID=
PLUGGY_BASE_URL=https://api.pluggy.ai
PLUGGY_CLIENT_ID=
PLUGGY_CLIENT_SECRET=
PLUGGY_WEBHOOK_SECRET=
PLUGGY_SYNC_LOOKBACK_DAYS=370
PLUGGY_API_TIMEOUT_SECONDS=30
```

Frontend:

```env
NEXT_PUBLIC_OPEN_FINANCE_ENABLED=false
NEXT_PUBLIC_OPEN_FINANCE_OWNER_USER_ID=
```

Observacao: as variaveis publicas do frontend servem apenas para esconder/mostrar UI. A autorizacao real deve ficar no backend.

## OF0 - Preparacao Meu Pluggy e credenciais

Status: [/] Em andamento

Objetivo:

- Deixar a conta Meu Pluggy e o acesso API prontos sem colocar segredo no repositorio.

Checklist:

- [ ] Criar/acessar conta em `https://meu.pluggy.ai`.
- [ ] Conectar instituicoes pessoais desejadas no Meu Pluggy.
- [ ] Acessar Pluggy Dashboard e conectar os items do Meu Pluggy na aplicacao/demo conforme guia da Pluggy.
- [ ] Obter `clientId` e `clientSecret` da aplicacao Pluggy.
- [ ] Identificar item IDs iniciais que serao sincronizados.
- [ ] Definir o UUID do usuario owner no Financy.
- [x] Configurar env vars em local/dev sem versionar segredos.
- [ ] Confirmar se a conta/plano habilita os produtos necessarios: accounts, transactions, credit cards, investments quando aplicavel.

Validacao:

- [ ] Chamada manual segura ao `/auth` da Pluggy retorna API key temporaria.
- [ ] Chamada manual a `/accounts?itemId=...` retorna dados esperados.
- [x] Nenhum segredo aparece em `git diff`, logs ou arquivos versionados.

## OF1 - Modelo de dados e migrations

Status: [x] Concluida

Objetivo:

- Criar rastreabilidade da origem Open Finance sem quebrar as tabelas financeiras atuais.

Checklist:

- [x] Criar migration `012_open_finance_integration.sql`.
- [x] Criar tabela `open_finance_items` com `user_id`, `provider`, `pluggy_item_id`, instituicao, status, consentimento e timestamps de sync.
- [x] Criar tabela `open_finance_account_links` ligando `pluggy_account_id` a `accounts.id` ou `cards.id`.
- [x] Criar tabela `open_finance_transaction_links` ligando `pluggy_transaction_id` a `transactions.id`.
- [x] Criar tabela `open_finance_sync_runs` com status, contadores, erro sanitizado e duracao.
- [x] Avaliar coluna opcional `source` ou `external_source` em `accounts`, `cards` e `transactions` para filtros futuros.
- [x] Garantir indices unicos por `user_id + provider + external_id`.
- [x] Garantir FKs para `profiles`, `accounts`, `cards` e `transactions`.
- [x] Atualizar repositories JSON e PostgreSQL com os novos metodos.
- [x] Adicionar testes de repository para upsert idempotente.

Validacao:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Se houver migration PostgreSQL real:

```powershell
cd backend
$env:TEST_DATABASE_URL='postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev_test'
.\.venv\Scripts\python.exe -m pytest tests_postgres -m postgres -q
```

## OF2 - Cliente Pluggy backend

Status: [x] Concluida

Objetivo:

- Criar uma camada isolada para autenticar e buscar dados da Pluggy.

Checklist:

- [x] Adicionar configs Pluggy em `backend/app/core/config.py`.
- [x] Criar `backend/app/services/pluggy_client.py`.
- [x] Implementar autenticacao `POST /auth` com cache de API key ate expiracao.
- [x] Implementar timeout e erros tipados sem vazar payload sensivel.
- [x] Implementar chamadas para items, accounts, transactions e credit cards/bills se disponiveis.
- [x] Implementar paginacao conforme API Pluggy.
- [x] Implementar retries apenas para leituras seguras e erros transientes.
- [x] Sanitizar logs e mensagens de erro.
- [x] Criar testes mockados para sucesso, 401, 403, 429, timeout e item inexistente.

Validacao:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_open_finance_pluggy_client.py
```

## OF3 - Servico de sincronizacao e normalizacao

Status: [/] Em andamento

Objetivo:

- Transformar dados Pluggy em entidades atuais do Financy.

Checklist:

- [x] Criar `OpenFinanceService` com dependencia do repository e `PluggyClient`.
- [x] Bloquear execucao quando `OPEN_FINANCE_ENABLED=false`.
- [x] Bloquear execucao quando usuario autenticado nao for `OPEN_FINANCE_OWNER_USER_ID`.
- [x] Sincronizar item metadata para `open_finance_items`.
- [x] Criar/atualizar contas bancarias em `accounts`.
- [x] Criar/atualizar cartoes em `cards` quando a Pluggy retornar dados de cartao.
- [ ] Criar/atualizar faturas em `card_statements` quando houver bill/statement confiavel.
- [x] Inserir transacoes em `transactions` usando `open_finance_transaction_links` como dedupe principal.
- [x] Usar dedupe existente como protecao secundaria quando faltar external id confiavel.
- [x] Mapear tipos Pluggy para `expense`, `income`, `transfer`, `payment` e `refund` sem mudar regras atuais.
- [x] Preservar `original_description` vindo da instituicao.
- [x] Gerar `normalized_description` usando a regra local existente.
- [x] Aplicar regras de classificacao deterministicas ja existentes apos inserir transacoes novas.
- [x] Marcar transacoes ambiguas como `confirmed` no MVP; revisao manual fica para filtros/regras.
- [x] Registrar contadores por sync: novas, atualizadas, ignoradas, duplicadas, erros.
- [x] Criar testes de sync idempotente com duas execucoes seguidas.
- [x] Criar testes para transacoes de conta, cartao, pagamento, estorno e transferencia.

Validacao:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_open_finance_service.py
```

## OF4 - API Open Finance owner-only

Status: [/] Em andamento

Objetivo:

- Expor endpoints seguros para a aba Open Finance.

Endpoints previstos:

- `GET /open-finance/status`
- `GET /open-finance/items`
- `POST /open-finance/items`
- `POST /open-finance/items/{item_id}/sync`
- `POST /open-finance/sync`
- `GET /open-finance/sync-runs`
- `POST /open-finance/webhook/pluggy`

Checklist:

- [x] Criar router `backend/app/api/open_finance.py`.
- [x] Registrar router em `backend/app/main.py`.
- [x] Criar dependency `require_open_finance_owner`.
- [x] Retornar `404` ou `403` para nao-owner sem revelar detalhes da integracao.
- [x] Nao aceitar `user_id` em payload.
- [x] Criar schemas Pydantic especificos.
- [x] Proteger sync manual contra execucao concorrente por item.
- [x] Garantir resposta resumida e sanitizada para a UI.
- [/] Implementar webhook somente apos confirmar assinatura/segredo na doc Pluggy.
- [x] Criar testes de owner autorizado, nao-owner bloqueado, feature desligada e sync concorrente.

Validacao:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_open_finance_api.py
```

## OF5 - Aba Open Finance owner-only no frontend

Status: [x] Concluida

Objetivo:

- Criar uma aba exclusiva para o owner gerenciar a sync.

Checklist:

- [x] Adicionar item `Open Finance` na sidebar apenas quando a sessao atual for do owner e a feature estiver habilitada.
- [x] Criar rota `frontend/src/app/open-finance/page.tsx`.
- [x] Criar componente `OpenFinanceContent`.
- [x] Exibir estado de feature desligada, sem credenciais, sem items, sincronizando e erro.
- [x] Exibir cards compactos: conexoes, ultima sync, novas transacoes, erros recentes.
- [x] Exibir tabela de items/conexoes com instituicao, status, ultima sync e acao `Sincronizar`.
- [x] Exibir historico de sync runs com erro sanitizado.
- [x] Usar toast para sync iniciada, concluida e falha.
- [x] Bloquear botoes durante sync para evitar duplo clique.
- [x] Garantir responsividade desktop/mobile.
- [x] Adicionar tipos em `frontend/src/lib/types.ts` e funcoes em `frontend/src/lib/api.ts`.
- [x] Criar E2E com mock para owner vendo a aba e nao-owner sem aba.

Validacao:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
npx.cmd playwright test tests/e2e/open-finance.spec.ts --project=chromium --reporter=line
```

## OF6 - Dashboard principal alimentado por Open Finance

Status: [/] Em andamento

Objetivo:

- Fazer os dados sincronizados aparecerem naturalmente no dashboard atual.

Checklist:

- [x] Confirmar que dashboard atual usa `GET /transactions`, `GET /accounts` e demais APIs existentes.
- [x] Garantir que transacoes Open Finance entram nas mesmas tabelas e aparecem nos cards, graficos e insights.
- [x] Garantir que contas/cartoes sincronizados aparecem em Contas e Cartoes.
- [x] Adicionar indicador discreto de origem `Open Finance` onde ajudar auditoria sem poluir a UI.
- [x] Avaliar filtro opcional por origem no dashboard ou na tela de transacoes.
- [x] Garantir que IA financeira usa dados sincronizados sem enviar dados extras desnecessarios a provider externo.
- [x] Validar que classificacoes/regras continuam funcionando para transacoes sincronizadas.
- [x] Criar teste backend para overview/insights incluindo transacoes Open Finance.
- [x] Criar E2E ou teste de componente com dashboard exibindo transacoes sincronizadas.

Validacao:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
cd ..\frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

## OF7 - Automacao de sync e webhooks

Status: [/] Em andamento

Objetivo:

- Reduzir dependencia de sync manual depois do MVP estar validado.

Checklist:

- [ ] Confirmar formato e seguranca dos webhooks Pluggy.
- [x] Implementar verificacao de assinatura/secret antes de aceitar webhook.
- [x] Registrar eventos recebidos sem payload sensivel.
- [x] Disparar sync por item quando evento indicar dados novos.
- [ ] Adicionar job/scheduler externo ou endpoint protegido para sync diaria.
- [x] Evitar sync concorrente do mesmo item.
- [ ] Definir politica para consentimento expirado e reconexao manual.
- [ ] Adicionar alerta visual quando item precisar de renovacao de consentimento.

Validacao:

- [x] Teste unitario de webhook valido/invalido.
- [ ] Teste de sync diaria mockada.
- [ ] Smoke manual com webhook em ambiente dev/preview quando disponivel.

## OF8 - Observabilidade, seguranca e documentacao

Status: [/] Em andamento

Objetivo:

- Fechar a integracao com seguranca operacional suficiente para uso privado.

Checklist:

- [x] Documentar setup em `docs/open-finance.md`.
- [x] Atualizar `.env.example` e `.env.production.example` sem segredos reais.
- [x] Atualizar `README.md` com comandos locais de validacao.
- [x] Adicionar runbook de problemas comuns: 401 Pluggy, consentimento expirado, rate limit, item sem transacoes.
- [x] Revisar logs para garantir ausencia de segredos e dados sensiveis.
- [x] Revisar `git diff` antes de qualquer commit.
- [x] Atualizar `output.md` quando uma fase for concluida.
- [ ] Manter `taskof.md` apenas com pendencias ativas durante a execucao.

Validacao obrigatoria final:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
cd ..\frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
npm.cmd run e2e
```

## Ordem sugerida de implementacao

1. OF0 - Preparacao Meu Pluggy e credenciais.
2. OF1 - Modelo de dados e migrations.
3. OF2 - Cliente Pluggy backend.
4. OF3 - Servico de sincronizacao e normalizacao.
5. OF4 - API Open Finance owner-only.
6. OF5 - Aba Open Finance owner-only.
7. OF6 - Dashboard principal alimentado por Open Finance.
8. OF7 - Automacao de sync e webhooks.
9. OF8 - Observabilidade, seguranca e documentacao.

## Definicao de pronto do MVP

- Owner ve a aba `Open Finance`.
- Nao-owner nao ve a aba e recebe bloqueio no backend.
- Sync manual busca dados do Meu Pluggy/Pluggy.
- Contas, cartoes e transacoes aparecem nas telas atuais.
- Dashboard principal considera as transacoes sincronizadas.
- Reexecutar sync nao duplica transacoes.
- Segredos ficam somente em variaveis de ambiente.
- Testes backend e frontend obrigatorios passam.

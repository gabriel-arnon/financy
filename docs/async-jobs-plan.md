# Jobs assincronos

## Decisao inicial

Usar uma fila simples em PostgreSQL como primeira etapa.

Motivos:

- Ja existe PostgreSQL/Supabase como dependencia operacional do Financy.
- Render/Supabase comportam bem uma tabela de `job_runs` antes de introduzir Redis.
- O contrato fica facil de auditar, consultar no frontend e migrar para Redis/Celery depois se volume justificar.
- Mantem o MVP self-hosted com menos servicos obrigatorios.

## Contrato `job_runs`

A migration proposta esta em `docs/supabase/migrations/015_job_runs.sql`.

Campos principais:

- `id`: identificador do job.
- `user_id`: owner do job; nao deve ser aceito do cliente.
- `kind`: tipo do job, como `open_finance_sync_item`, `open_finance_sync_all`, `import_confirm_large` ou `ai_finance_overview`.
- `status`: `queued`, `running`, `success`, `error` ou `canceled`.
- `resource_type` e `resource_id`: alvo opcional, por exemplo `open_finance_item` + external item id.
- `idempotency_key`: chave opcional para evitar jobs duplicados por owner/kind.
- `progress_current` e `progress_total`: progresso para UI.
- `error_message`: mensagem segura, sem segredo ou payload bruto.
- `result`: resumo final seguro.
- `metadata`: detalhes operacionais seguros para suporte.
- `queued_at`, `started_at`, `finished_at`, `updated_at`: trilha temporal.

## Candidatos

### Open Finance sync

Primeiro candidato.

Novo fluxo sugerido:

1. `POST /open-finance/items/{external_item_id}/sync-jobs` cria ou reutiliza um `job_runs` idempotente.
2. Worker busca jobs `queued` de kind `open_finance_sync_item`.
3. Worker marca `running`, chama `OpenFinanceService.sync_item` e salva resultado.
4. Frontend consulta `GET /jobs/{job_id}` ou lista jobs recentes.
5. Endpoint sincrono atual permanece durante transicao para suporte/manual.

Idempotencia:

- Usar `idempotency_key = provider_name + ":" + external_item_id + ":" + yyyy-mm-dd`.
- Manter lock atual de `OpenFinanceService.sync_item` como protecao de segunda camada.

Estado implementado:

- `JobService.create_open_finance_sync_item_job` cria jobs `open_finance_sync_item` com `resource_type = open_finance_item`.
- `LocalJsonRepository` e `PostgresRepository` persistem `job_runs` sem aceitar `user_id` do cliente.
- `PostgresRepository` usa o indice unico parcial de `docs/supabase/migrations/015_job_runs.sql` para reutilizar o mesmo job por owner/kind/idempotency key.
- API exposta: `POST /open-finance/items/{external_item_id}/sync-jobs`, `GET /jobs` e `GET /jobs/{job_id}`.
- UI exposta em `/open-finance`: botao `Fila` por item, banner de jobs ativos, lista de jobs recentes e atualizacao manual de status.
- Worker exposto em `python -m app.workers.job_worker`; use `--once` para processar um job e sair.

### Importacoes grandes

Segundo candidato.

- Upload continua sincrono ate salvar arquivo e batch.
- Parsing e preview podem virar job quando tamanho/timeout justificar.
- Confirmacao em lote pode virar job se quantidade de preview items passar de um limite configurado.

### IA financeira pesada

Terceiro candidato.

- Overview atual pode continuar sincrono enquanto usa heuristicas locais.
- Chamadas futuras a provider externo para resumo, perguntas ou regras devem entrar como job quando demoradas.
- Payload enviado ao provider deve continuar minimo e agregado quando possivel.

## Frontend

UI esperada:

- Botao dispara job e libera navegacao.
- Tela mostra status recente por tipo de job.
- Toast informa criacao, sucesso ou falha.
- Erro mostra mensagem segura e `request_id` quando houver.
- Retry manual deve criar novo job com idempotencia controlada.

Estado implementado:

- `/open-finance` carrega `GET /jobs` junto com items e historico de sync.
- Cada item Open Finance tem acao `Fila`, que chama `POST /open-finance/items/{external_item_id}/sync-jobs`.
- O usuario pode atualizar a lista de jobs sem bloquear a navegacao.

## Operacao

- Worker pode iniciar como processo Python separado no Render.
- Comando sugerido para worker continuo:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.workers.job_worker
```

- Comando sugerido para smoke test/local one-shot:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.workers.job_worker --once
```

- Sem worker ativo, endpoints `sync-jobs` apenas enfileiram e retornam status `queued`; UI deve deixar claro que a execucao operacional ainda depende do worker.
- Jobs antigos devem ter limpeza/retencao configurada depois que houver volume real.
- Antes de producao publica, definir alerta para muitos jobs `error` ou `running` por tempo anormal.

Fluxo atual do worker:

1. `claim_next_job_run` seleciona o job `queued` mais antigo dos kinds suportados e marca `running`.
2. Para `open_finance_sync_item`, o worker chama `OpenFinanceService.sync_item`.
3. Em sucesso, grava `status=success`, progresso `1/1`, `finished_at` e um `result` resumido.
4. Em erro, grava `status=error`, `finished_at` e mensagem segura truncada.

# Correlacao de `Failed to fetch`

## Objetivo

Transformar uma falha generica do navegador em uma investigacao rastreavel usando `request_id`.

## Onde encontrar o `request_id`

- Toasts de erro do frontend mostram `Request ID: ...` quando a API respondeu com erro.
- Falhas de rede antes de resposta HTTP tambem incluem `Request ID: ...` na mensagem.
- Console do navegador registra `Financy API request failed` com `path`, `method`, `attempt`, `status` e `request_id`.
- Toda resposta backend inclui `X-Request-Id`; erros JSON incluem `error.request_id`.

## Como correlacionar

1. Copiar o `request_id` exibido no toast ou no console do navegador.
2. Registrar horario local da falha, path e metodo.
3. Buscar o mesmo `request_id` nos logs da API no Render.
4. Se houver log da API, comparar `status`, `duration_ms`, `user_id_hash`, path e horario.
5. Se nao houver log da API, investigar rede antes da aplicacao: CORS, DNS, cold start, deploy/restart ou bloqueio do navegador.
6. Se houver log da API com erro de banco/storage/auth, buscar no Supabase pela mesma janela de tempo, filtrando por horario e rota/operacao correlata.
7. Classificar a causa raiz como uma destas categorias:
   - `api_error`: API respondeu com 4xx/5xx e `request_id`.
   - `api_timeout`: API recebeu a chamada, mas duracao excedeu limite esperado.
   - `cold_start_or_restart`: chamada caiu durante start/restart sem log completo da aplicacao.
   - `cors_or_network`: navegador nao recebeu resposta valida e a API nao registrou request.
   - `auth_expired`: API respondeu 401 ou frontend encerrou sessao.
   - `supabase_dependency`: API registrou erro relacionado a banco/storage/auth Supabase.

## Evidencia minima para fechar incidente

Use este formato em `output.md` ou no ticket:

```text
request_id:
horario navegador:
path/metodo:
erro exibido:
log Render encontrado: sim/nao
status/duracao Render:
log Supabase relacionado: sim/nao
categoria:
causa raiz ou proximo passo:
```

## Proximo passo quando a falha reaparecer

- Se o `request_id` aparecer no Render, corrigir a rota/servico que gerou status ou latencia anormal.
- Se o `request_id` nao aparecer no Render, validar CORS, URL publica da API, cold start/restart e conectividade entre Vercel/navegador e Render.
- Se Render apontar erro Supabase, correlacionar com logs Supabase na mesma janela e decidir entre migration, policy, limite, credencial ou indisponibilidade externa.

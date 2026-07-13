# Ambientes Financy

Data da revisao: 2026-07-13

Este documento descreve a separacao operacional entre Production e Dev. Nunca registrar valores de secrets aqui.

## Producao

| Camada | Ambiente |
|---|---|
| Branch | `main` |
| Frontend | Vercel Production |
| Backend | Render Production |
| Banco/Auth/Storage | Supabase Production US |
| Bucket privado | `private-files` |

### Estrategia de migrations

- Migrations versionadas em `docs/supabase/migrations`.
- Production US deve conter `001` a `008`.
- Aplicacao remota exige acao explicita com `--allow-remote`.
- Nao usar `--reset-schema` em remoto.
- Nao aplicar migrations automaticamente em startup remoto sem revisao; o script atual faz skip seguro em banco remoto quando `--allow-remote` nao e informado.
- Para DDL/migrations, preferir conexao direta/admin do Supabase, nao Transaction Pooler.

### Variaveis obrigatorias do Backend Production

- `APP_ENV`
- `AUTH_PROVIDER`
- `AUTH_REQUIRED`
- `AUTH_DEV_BYPASS`
- `STORAGE_BACKEND`
- `DATABASE_URL`
- `CORS_ORIGINS`
- `SUPABASE_URL`
- `SUPABASE_JWT_ISSUER`
- `SUPABASE_JWKS_URL`
- `SUPABASE_AUDIENCE`
- `JWT_SECRET`
- `SUPABASE_SERVICE_ROLE_KEY`
- `PRIVATE_FILES_ENABLED`
- `PRIVATE_FILES_BACKEND`
- `PRIVATE_FILES_BUCKET`
- `SUPABASE_STORAGE_BUCKET`
- `PRIVATE_FILES_SIGNED_URL_TTL_SECONDS`
- `PRIVATE_FILES_ALLOWED_MIME_TYPES`
- `PRIVATE_FILES_SCAN_PROVIDER`
- `PRIVATE_FILES_ORPHAN_RETENTION_HOURS`

### Variaveis obrigatorias do Frontend Production

- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Desenvolvimento

| Camada | Ambiente |
|---|---|
| Branch | `dev` |
| Frontend | Vercel Preview/dev |
| Backend | Render Dev |
| Banco/Auth/Storage | Supabase Dev |
| Bucket privado | `private-files` |

### Estrategia de migrations

- Dev deve receber as mesmas migrations versionadas antes de testar funcionalidades novas.
- Usar banco Supabase Dev ou PostgreSQL local descartavel.
- Scripts locais podem usar `localhost`, `127.0.0.1`, `::1` ou `postgres`.
- Nao apontar Dev para Supabase Production.
- Nao usar service role de Production em Render Dev, Vercel Preview ou ambiente local.

### Variaveis obrigatorias do Backend Dev

- `APP_ENV`
- `AUTH_PROVIDER`
- `AUTH_REQUIRED`
- `AUTH_DEV_BYPASS`
- `STORAGE_BACKEND`
- `DATABASE_URL`
- `CORS_ORIGINS`
- `SUPABASE_URL`
- `SUPABASE_JWT_ISSUER`
- `SUPABASE_JWKS_URL`
- `SUPABASE_AUDIENCE`
- `JWT_SECRET`
- `SUPABASE_SERVICE_ROLE_KEY`
- `PRIVATE_FILES_ENABLED`
- `PRIVATE_FILES_BACKEND`
- `PRIVATE_FILES_BUCKET`
- `SUPABASE_STORAGE_BUCKET`
- `PRIVATE_FILES_SIGNED_URL_TTL_SECONDS`
- `PRIVATE_FILES_ALLOWED_MIME_TYPES`
- `PRIVATE_FILES_SCAN_PROVIDER`
- `PRIVATE_FILES_ORPHAN_RETENTION_HOURS`

### Variaveis obrigatorias do Frontend Dev/Preview

- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Prevencao contra cruzamento de ambientes

| Regra | Motivo |
|---|---|
| Frontend Production nunca deve apontar para backend Dev. | Evita usuario real escrevendo em ambiente incorreto. |
| Backend Production nunca deve usar Supabase Dev. | Evita perda de dados e mistura de Auth/JWT. |
| Frontend Preview nunca deve usar Supabase Production. | Evita testes gravando dados reais. |
| Backend Dev nunca deve usar service role de Production. | Service role ignora RLS e tem poder administrativo. |
| Service role nunca deve ficar no frontend. | Variaveis `NEXT_PUBLIC_*` sao publicas no bundle. |
| `localhost` nunca deve aparecer em build remoto. | Em Vercel/Render remoto, localhost aponta para o proprio container/build, nao para o servico correto. |
| `127.0.0.1:8000` nunca deve ser usado em Vercel Production ou Preview. | Indica falta de `NEXT_PUBLIC_API_URL`. |
| Production deve usar Supabase US. | Mantem baixa latencia com Render Production em Virginia. |
| Dev deve usar Supabase Dev. | Mantem testes isolados. |
| Bucket `private-files` deve existir em cada Supabase. | Uploads e signed URLs dependem de bucket privado. |
| JWT issuer/JWKS devem pertencer ao mesmo Supabase usado pelo frontend. | Evita 401 por tokens emitidos por projeto diferente. |
| CORS do backend deve conter somente frontend do ambiente correspondente. | Evita acesso cruzado e falhas de browser. |
| Backend persistente nao deve depender de Transaction Pooler `6543` se houver incompatibilidade com conexoes longas/prepared statements. | Render FastAPI e `psycopg_pool` funcionam melhor com direct/session pooler conforme estrategia definida. |

## Auditoria rapida antes de deploy

1. Conferir branch: `main` para Production, `dev` para Dev.
2. Conferir `NEXT_PUBLIC_API_URL`.
3. Conferir `NEXT_PUBLIC_SUPABASE_URL`.
4. Conferir `DATABASE_URL`.
5. Conferir `SUPABASE_JWT_ISSUER` e `SUPABASE_JWKS_URL`.
6. Conferir `CORS_ORIGINS`.
7. Conferir `PRIVATE_FILES_BUCKET`/`SUPABASE_STORAGE_BUCKET`.
8. Confirmar que nenhum valor real foi versionado.

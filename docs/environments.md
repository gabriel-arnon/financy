# Ambientes Financy

Este documento lista apenas nomes de variaveis e regras operacionais. Nunca
registre valores reais, service role, JWT, senhas ou URLs assinadas.

## Backend

Variaveis obrigatorias ou relevantes:

- `APP_ENV` ou `ENVIRONMENT`
- `AUTH_PROVIDER`
- `AUTH_REQUIRED`
- `AUTH_DEV_BYPASS`
- `DEV_USER_ID`
- `SUPABASE_URL`
- `SUPABASE_JWT_ISSUER`
- `SUPABASE_JWKS_URL`
- `SUPABASE_AUDIENCE`
- `JWT_SECRET`
- `STORAGE_BACKEND`
- `DATABASE_URL`
- `TEST_DATABASE_URL`
- `CORS_ORIGINS`
- `PRIVATE_FILES_ENABLED`
- `PRIVATE_FILES_BACKEND`
- `PRIVATE_FILES_BUCKET`
- `PRIVATE_FILES_MAX_SIZE_BYTES`
- `PRIVATE_FILES_SIGNED_URL_TTL_SECONDS`
- `PRIVATE_FILES_ALLOWED_MIME_TYPES`
- `PRIVATE_FILES_SCAN_PROVIDER`
- `PRIVATE_FILES_ORPHAN_RETENTION_HOURS`
- `SUPABASE_SERVICE_ROLE_KEY`
- `INVITATION_ACCEPT_RATE_LIMIT_ENABLED`
- `INVITATION_ACCEPT_RATE_LIMIT_MAX_ATTEMPTS`
- `INVITATION_ACCEPT_RATE_LIMIT_WINDOW_SECONDS`

## Frontend

Variaveis obrigatorias ou relevantes:

- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

`NEXT_PUBLIC_API_URL` e obrigatoria em Vercel Preview e Production. Builds
remotos nao podem usar `localhost`, `127.0.0.1` ou `http` sem TLS. O fallback
local para `http://127.0.0.1:8000` e permitido apenas em desenvolvimento local.

## Prevencao de cruzamento

| Regra | Motivo |
| --- | --- |
| Frontend production nunca aponta para backend dev. | Evita misturar usuarios e dados reais com staging. |
| Backend production nunca usa Supabase Dev. | Preserva dados reais e Auth correto. |
| Frontend preview/dev nunca usa Supabase Production. | Evita testes contra dados reais. |
| `SUPABASE_SERVICE_ROLE_KEY` nunca fica no frontend. | A service role ignora RLS e deve ser exclusiva do backend. |
| Build remoto nao deve usar `localhost` ou `127.0.0.1`. | Em Vercel/Render, localhost aponta para o container do proprio servico. |
| Migrations remotas exigem confirmacao explicita. | Evita aplicar schema no banco errado. |

## Ressarcimentos

Comentarios de ressarcimentos usam autorizacao no backend. O guest precisa de
membership ativa para acessar claims compartilhadas. Convites usam `token_hash`
e rate limiting persistente por token hash e origem derivada.

## RLS e Data API

Operacoes funcionais de dados financeiros passam pelo FastAPI. A migration
`011_reimbursements_security_hardening.sql` habilita RLS e revoga privilegios
diretos de `PUBLIC`, `anon` e `authenticated` nas tabelas financeiras,
arquivos privados, imports e ressarcimentos. Nao ha policy permissiva para
acesso direto pela Data API nesta fundacao.

O backend usa a conexao configurada em `DATABASE_URL` e a service role apenas
para operacoes administrativas de Storage. A service role nunca deve ser
exposta no frontend.

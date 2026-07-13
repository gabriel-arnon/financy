# Plano e Registro da Migracao Supabase US - Financy

Data da migracao: 2026-07-13
Status: cutover concluido e validado manualmente
Escopo deste documento: registrar o estado final da migracao de infraestrutura do Financy para Supabase Production US e manter o runbook de aplicacao/validacao de schema.

Nenhuma credencial deve ser registrada neste documento. Listar apenas nomes de variaveis e identificadores logicos de ambiente.

## 1. Estado confirmado

- A branch `main` recebeu merge da `dev`.
- A Fundacao 3 de Ressarcimentos esta integrada.
- As migrations `001` a `008` estao versionadas no `HEAD`.
- As migrations `001` a `008` foram aplicadas no Supabase Production US.
- O Supabase Production foi recriado nos EUA, proximo ao Render Production em Virginia.
- O Supabase Dev permanece separado e funcional.
- Render Production aponta para Supabase Production US.
- Render Dev aponta para Supabase Dev.
- Vercel Production usa Supabase Production US e backend Production.
- Vercel Preview/dev usa Supabase Dev e backend Dev.
- Auth, banco, Storage e JWT estao alinhados por ambiente.
- O bucket privado `private-files` foi criado no Production US.
- Login, dashboard, transacoes, contas, cartoes, importacoes e ressarcimentos foram testados manualmente.
- O desempenho da producao melhorou muito apos aproximar Render e Supabase.
- O antigo Supabase Production Brasil nao deve ser excluido ainda; manter intacto como rollback temporario ou pausar apos validacao final.

## 2. Arquitetura anterior

- Frontend Production: Vercel Production.
- Backend Production: Render Production em Virginia.
- Banco/Auth/Storage Production: Supabase em `sa-east-1`.
- Efeito observado: cada request do backend para o banco fazia multiplas viagens internacionais entre Virginia e Sao Paulo.
- Sintoma principal: latencia alta em telas com varias chamadas ou consultas ao PostgreSQL.

## 3. Arquitetura atual

Producao:

- Branch: `main`.
- Frontend: Vercel Production.
- Backend: Render Production em Virginia.
- Banco/Auth/Storage: Supabase Production US, em North Virginia.
- Storage privado: bucket `private-files`.
- Migrations: `001` a `008` aplicadas no projeto Production US.

Desenvolvimento:

- Branch: `dev`.
- Frontend: Vercel Preview/dev.
- Backend: Render Dev.
- Banco/Auth/Storage: Supabase Dev.
- Storage privado: bucket `private-files`.
- Migrations: mesmo conjunto versionado, aplicado de forma separada no ambiente Dev.

## 4. Motivo da migracao

A principal causa de lentidao identificada foi a distancia entre:

- Render Production em Virginia;
- Supabase Production em `sa-east-1`;
- multiplas viagens internacionais entre backend e banco durante carregamento de dashboard, transacoes, contas, cartoes, imports e ressarcimentos.

A migracao para Supabase US aproxima backend, banco, Auth e Storage, reduzindo latencia e variabilidade de TTFB.

## 5. Problemas encontrados e correcoes realizadas

Problemas:

- Latencia de producao muito superior a dev.
- Supabase Production antigo em regiao distante do backend.
- Uso anterior de URL remota no deploy exigia protecao para migrations automaticas.
- Necessidade de separar claramente Production e Dev em Vercel, Render, Supabase, Auth, JWT e Storage.
- Necessidade de confirmar migrations 001-008 versionadas apos merge da `dev`.

Correcoes:

- Production migrada para Supabase US.
- Render Production configurado para Supabase Production US.
- Render Dev mantido em Supabase Dev.
- Vercel Production configurada para Supabase Production US e backend Production.
- Vercel Preview/dev configurada para Supabase Dev e backend Dev.
- Bucket privado `private-files` criado no Supabase Production US.
- Migrations 001-008 versionadas e aplicadas.
- `backend/scripts/apply_migrations.py` mantem skip seguro em banco remoto quando `--allow-remote` nao e informado.
- `backend/.env.production.example` documenta bucket `private-files`.

## 6. Migrations aplicadas

1. `001_initial_schema.sql`
2. `002_default_categories.sql`
3. `003_phase2_indexes.sql`
4. `004_nullable_card_account.sql`
5. `005_private_files.sql`
6. `006_reimbursements_domain.sql`
7. `007_reimbursement_guest_access.sql`
8. `008_reimbursement_claim_attachments.sql`

Essas migrations cobrem:

- core financeiro;
- imports e previews;
- contas, cartoes, faturas e transacoes;
- categorias e regras;
- arquivos privados e anexos de transacao;
- contatos, cobrancas, itens, snapshots e eventos de ressarcimento;
- convites, memberships e portal guest;
- compartilhamento explicito de comprovantes em cobrancas.

## 7. Variaveis substituidas por ambiente

Listar apenas nomes. Valores reais devem permanecer nos paineis dos provedores.

Backend Render Production e Dev:

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
- `SIGNED_URL_TTL_SECONDS`
- `PRIVATE_FILES_SCAN_PROVIDER`
- `FILE_SCAN_PROVIDER`
- `PRIVATE_FILES_ORPHAN_RETENTION_HOURS`
- `AI_IMPORT_ENABLED`
- `AI_IMPORT_PROVIDER`
- `AI_IMPORT_BASE_URL`
- `AI_IMPORT_API_KEY`
- `AI_IMPORT_MODEL`
- `AI_IMPORT_TIMEOUT_SECONDS`

Frontend Vercel Production e Preview/dev:

- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## 8. Validacao executada

Validacao manual confirmada apos cutover:

- login;
- dashboard;
- transacoes;
- contas;
- cartoes;
- importacoes;
- ressarcimentos;
- Auth/JWT por ambiente;
- banco por ambiente;
- Storage privado por ambiente;
- frontend Production apontando para backend Production;
- frontend Preview/dev apontando para backend Dev.

Resultado:

- Production funcional.
- Dev funcional e separado.
- Performance percebida melhorou muito apos aproximar Render e Supabase.
- Nenhum cruzamento conhecido entre Production e Dev apos configuracao final.

## 9. Desempenho

Valores historicos observados antes da migracao:

| Ambiente | Rota | Tempo observado |
|---|---:|---:|
| Dev | `/overview` | aproximadamente 144 ms |
| Dev | `/transactions` | aproximadamente 176 ms |
| Dev | `/accounts` | aproximadamente 137 ms |
| Dev | `/cards` | aproximadamente 139 ms |
| Production antes | `/overview` | aproximadamente 2,30 s |
| Production antes | `/transactions` | aproximadamente 1,05 s |
| Production antes | `/accounts` | aproximadamente 828 ms |
| Production antes | `/cards` | aproximadamente 943 ms |

Causa principal identificada:

- Render Production em Virginia;
- Supabase Production em `sa-east-1`;
- multiplas viagens internacionais entre backend e banco.

Campos para medicoes atuais apos migracao:

| Ambiente | Rota | TTFB atual | Data | Observacao |
|---|---:|---:|---|---|
| Production US | `/overview` | A medir |  |  |
| Production US | `/transactions` | A medir |  |  |
| Production US | `/accounts` | A medir |  |  |
| Production US | `/cards` | A medir |  |  |

## 10. Rollback

Enquanto a validacao final nao terminar:

1. Manter o Supabase Production Brasil intacto ou pausado, sem exclusao definitiva.
2. Nao destruir banco, Auth, Storage ou backups antigos.
3. Manter registro das variaveis antigas em cofre seguro, nunca no repositorio.
4. Em caso de rollback antes de novas escritas relevantes no US:
   - restaurar variaveis do Render Production para Supabase Brasil;
   - restaurar variaveis da Vercel Production para Supabase Brasil;
   - validar login, dashboard, transacoes, imports e ressarcimentos;
   - monitorar logs por 401, 403 e 500.
5. Em caso de rollback apos novas escritas no US:
   - nao trocar de volta sem reconciliar delta de Auth, banco e Storage;
   - exportar diferencas por janela de tempo;
   - validar integridade antes de apontar usuarios novamente para o Brasil.

Condicao para exclusao definitiva do Supabase Brasil:

- Janela de validacao final concluida;
- backups verificados;
- contagens e integridade conferidas no Supabase US;
- Auth e Storage validados;
- nenhum erro recorrente em logs;
- nenhuma necessidade de rollback aberta;
- decisao humana explicita de exclusao.

## 11. Comando historico para aplicar schema 001-008

Nao executar novamente sem necessidade. Exemplo seguro para novo ambiente US vazio:

```powershell
cd C:\Users\Gabriel\Documents\Financy\backend

$expectedProjectRef = "NEW_US_PROJECT_REF"
$env:DATABASE_URL = "postgresql://postgres:REDACTED_PASSWORD@db.NEW_US_PROJECT_REF.supabase.co:5432/postgres"

$uri = [System.Uri]$env:DATABASE_URL
$expectedHost = "db.$expectedProjectRef.supabase.co"
if ($uri.Host -ne $expectedHost) {
  Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
  throw "DATABASE_URL host '$($uri.Host)' nao corresponde ao projeto US esperado '$expectedHost'."
}
if ($env:DATABASE_URL -match "sa-east-1|OLD_PROJECT_REF|prod-antigo|production-old") {
  Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
  throw "DATABASE_URL parece apontar para ambiente antigo/proibido."
}

Write-Host "Destino validado: postgresql://postgres:***@$($uri.Host):$($uri.Port)$($uri.AbsolutePath)"
.\.venv\Scripts\python.exe scripts\apply_migrations.py --allow-remote

Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
```

## 12. Validacoes SQL pos-migration

```powershell
psql $env:DATABASE_URL -c "select version, applied_at from public.schema_migrations order by version;"
```

```powershell
psql $env:DATABASE_URL -c "
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_type = 'BASE TABLE'
order by table_name;
"
```

```powershell
psql $env:DATABASE_URL -c "
select tablename, indexname, indexdef
from pg_indexes
where schemaname = 'public'
  and (
    indexname in (
      'transactions_dedupe_idx',
      'transaction_attachments_active_file_idx',
      'reimbursement_items_claim_transaction_active_idx',
      'reimbursement_invitations_token_hash_key',
      'reimbursement_memberships_contact_user_active_idx',
      'reimbursement_claim_attachments_active_file_idx'
    )
    or tablename like 'reimbursement_%'
    or tablename in ('stored_files', 'transaction_attachments')
  )
order by tablename, indexname;
"
```

```powershell
psql $env:DATABASE_URL -c "
select
  conrelid::regclass as table_name,
  conname,
  contype,
  pg_get_constraintdef(oid) as definition
from pg_constraint
where connamespace = 'public'::regnamespace
order by table_name::text, conname;
"
```

## 13. Riscos residuais

- RLS final ainda nao deve ser ativada sem politica completa para todas as tabelas sensiveis.
- O antigo Supabase Brasil deve permanecer disponivel como rollback temporario ate decisao explicita.
- `frontend/src/lib/api.ts` e `frontend/src/lib/server-api.ts` possuem fallback local para `http://127.0.0.1:8000` se `NEXT_PUBLIC_API_URL` estiver ausente; checklist de deploy deve impedir build remoto sem essa variavel.
- `output.md` contem historico antigo mencionando `sa-east-1`; nao e configuracao ativa, mas pode confundir se usado como fonte operacional.
- Arquivos de exemplo usam placeholders de Supabase; confirmar valores reais somente nos paineis dos provedores.

## 14. Auditoria de referencias de ambiente

Achados relevantes da busca local:

| Arquivo | Linha aproximada | Tipo de risco | Acao |
|---|---:|---|---|
| `frontend/src/lib/api.ts` | 40 | Fallback local para `127.0.0.1:8000` se `NEXT_PUBLIC_API_URL` faltar em build remoto. | Documentado no checklist; nao alterado por ser logica funcional. |
| `frontend/src/lib/server-api.ts` | 13 | Mesmo fallback local em chamadas server-side. | Documentado no checklist; nao alterado por ser logica funcional. |
| `output.md` | 1053-1068 | Historico cita Supabase antigo em `sa-east-1`. | Mantido como historico, nao usar como runbook operacional. |
| `backend/.env` | 12-13 | Arquivo local ignorado contem valores reais de Supabase. | Nao versionar, nao imprimir; considerar rotacao se esse arquivo tiver sido compartilhado fora da maquina. |
| `.uploads/` e `backend/.uploads/` | varias | Logs locais citam `127.0.0.1`; alguns arquivos de cache/log podem conter historico local. | Nao versionar; limpar antes de empacotar artefatos. |
| `docker-compose.yml` | 25-46 | URLs e hosts locais de desenvolvimento. | Esperado para ambiente local. |
| `backend/.env.example` | 5-7 | URLs locais de exemplo. | Esperado para ambiente local. |
| `backend/.env.production.example` | 11-19 | Placeholders `YOUR_PROJECT_REF`. | Esperado; valores reais ficam nos provedores. |
| `frontend/.env.production.example` | 2-3 | URL publica do backend e placeholder Supabase. | Esperado; conferir valores reais na Vercel. |

Nao foram encontradas referencias versionadas ativas a `sa-east-1` fora de historico/documentacao. Nao foi encontrada porta `6543` em configuracao versionada ativa; ocorrencias com `6543` em dados/cache locais nao representam Transaction Pooler.

## 15. Confirmacoes deste fechamento

- Nenhum servico externo foi alterado por esta documentacao.
- Nenhum secret foi registrado.
- Nenhuma migration foi editada.
- Nenhuma logica funcional da aplicacao foi alterada.

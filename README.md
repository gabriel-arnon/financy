# Financy

Base fullstack para gerenciamento financeiro com importacao de faturas/extratos, preview editavel e confirmacao de transacoes.

## Estrutura

```text
Financy/
  backend/   API FastAPI, parsers e servicos de importacao
  frontend/  Next.js + TypeScript + Tailwind
  docs/      arquitetura e migrations Supabase/PostgreSQL
```

## Backend


```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

A API sobe em `http://127.0.0.1:8000`.

Atalho opcional para desenvolvimento local:

```powershell
.\backend\scripts\run_dev.ps1
```

Esse script evita depender de `Start-Process`. Em alguns shells PowerShell, o processo pode conter `Path` e `PATH` ao mesmo tempo; isso quebra comandos que mesclam variáveis de ambiente em um dicionário case-insensitive, mas não indica problema no FastAPI.

### Variaveis de ambiente

Veja `backend/.env.example`.

- `APP_ENV`: ambiente atual (`local`, `development`, `staging` ou `production`).
- `DEV_USER_ID`: usuario local para desenvolvimento sem login.
- `UPLOAD_STORAGE_PATH`: pasta local para arquivos enviados e banco JSON local.
- `CORS_ORIGINS`: origens permitidas separadas por virgula.
- `JWT_SECRET`: segredo reservado para autenticacao futura. Nao use o valor de exemplo em producao.
- `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY`: reservadas para integracao Supabase.
- `DATABASE_URL`: conexao PostgreSQL/Supabase para evolucao do repositorio persistente.

Por padrao, sem Supabase configurado, o backend usa persistencia local em JSON dentro de `UPLOAD_STORAGE_PATH`, apenas para desenvolvimento. O backend ainda aceita `ENVIRONMENT` e `UPLOAD_DIR` como aliases legados durante a transicao.

## Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

O app sobe em `http://localhost:3000`.

### Variaveis de ambiente

Veja `frontend/.env.example`.

- `NEXT_PUBLIC_API_URL`: URL da API FastAPI. Localmente pode apontar para `http://127.0.0.1:8000`; em Preview/Production deve ser uma URL `https` real e nao pode ficar ausente.
- `NEXT_PUBLIC_SUPABASE_URL`: preparado para Supabase Auth futuro.
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: preparado para Supabase Auth futuro.

O build remoto valida `NEXT_PUBLIC_API_URL` antes do Next.js compilar. Isso
impede que Preview/Production caiam silenciosamente no fallback local.

## Docker Compose local

Para subir frontend e backend com Docker:

```powershell
docker-compose config
docker-compose up --build
```

Servicos:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Healthcheck: `http://localhost:8000/health`

O Compose usa `UPLOAD_STORAGE_PATH=/app/.uploads` no container do backend e um volume nomeado para persistir uploads/dados locais.

## PostgreSQL local

A Fase 2 adiciona PostgreSQL como persistencia definitiva, mantendo JSON como fallback local.

O ambiente local usa um PostgreSQL descartavel no Docker Compose:

- host: `localhost`
- porta: `${POSTGRES_PORT:-5432}`
- database: `financy_dev`
- user: `financy_dev`
- senha: `financy_dev_local`

Esses valores sao apenas locais e estao documentados para reproduzibilidade. Nao use essa senha fora da maquina de desenvolvimento.

Suba o banco e aplique migrations em ordem segura:

```powershell
.\scripts\setup_dev_db.ps1 -ResetSchema
```

Se ja existir um volume Docker antigo com credenciais diferentes, recrie apenas o banco local descartavel:

```powershell
.\scripts\setup_dev_db.ps1 -ResetVolume -ResetSchema
```

O script:

1. verifica Docker;
2. sobe o servico `postgres`;
3. aguarda healthcheck;
4. valida que a URL e local;
5. aplica as migrations de `docs/supabase/migrations`;
6. inspeciona tabelas e indices esperados.

Para aplicar migrations manualmente no banco local:

```powershell
cd backend
$env:DATABASE_URL='postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev'
.\.venv\Scripts\python.exe scripts\apply_migrations.py --reset-schema
```

Prepare um banco de teste isolado:

```powershell
cd backend
$env:TEST_DATABASE_URL='postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev_test'
.\.venv\Scripts\python.exe scripts\prepare_test_database.py
```

Para rodar o backend usando PostgreSQL:

```powershell
cd backend
$env:STORAGE_BACKEND='postgres'
$env:DATABASE_URL='postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Para voltar ao fallback JSON, use `STORAGE_BACKEND=json` ou remova a variavel.

Protecoes:

- scripts de dev recusam hosts fora de `localhost`, `127.0.0.1`, `::1` ou `postgres`;
- URLs remotas de Supabase/producao nao sao migradas automaticamente por esses scripts;
- o identificador exibido mascara senha;
- nunca rode `--reset-schema` contra banco remoto.
- Em deploy, `python scripts/apply_migrations.py` faz skip seguro em host remoto sem `--allow-remote` ou `FINANCY_ALLOW_REMOTE_MIGRATIONS=true`, retornando sucesso para nao impedir o start da API.

### Migracao JSON -> PostgreSQL

Sempre rode dry-run antes do apply:

```powershell
cd backend
$env:DATABASE_URL='postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev'
.\.venv\Scripts\python.exe scripts\migrate_json_to_postgres.py --dry-run
.\.venv\Scripts\python.exe scripts\migrate_json_to_postgres.py --apply
```

O `--apply` cria backup local automaticamente em `UPLOAD_STORAGE_PATH/backups`, aplica migrations pendentes e insere os dados em transacao SQL. O script preserva IDs validos e informa reparos de integridade aplicados em memoria antes de gravar no PostgreSQL.

## Seed local

O script oficial de seed garante categorias do sistema e regras iniciais.

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\seed_local.py
```

Para criar tambem uma conta e um cartao de exemplo:

```powershell
.\.venv\Scripts\python.exe scripts\seed_local.py --with-demo-data
```

O seed nao apaga dados existentes.

## Backup local

O script oficial de backup copia o `local_dev_db.json` e uploads locais para uma pasta com timestamp.

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\backup_local.py
```

Por padrao, os backups sao criados em `UPLOAD_STORAGE_PATH/backups`.

Para restaurar manualmente, pare o backend, copie o `local_dev_db.json` do backup para `UPLOAD_STORAGE_PATH` e recoloque os arquivos de upload conforme necessario.

## Deploy privado

Use [deploy-checklist.md](./deploy-checklist.md) antes de publicar ou atualizar um ambiente privado.

Riscos remanescentes da Fase 1:

- O JSON local ainda nao e banco definitivo.
- Nao ha autenticacao real nesta fase.
- `DEV_USER_ID` ainda representa usuario local unico.
- Backups sao locais e manuais.

## Supabase

1. Crie um projeto no Supabase separado para desenvolvimento/staging.
2. Abra o SQL Editor.
3. Execute as migrations em `docs/supabase/migrations` na ordem numerica.
4. Configure as variaveis do backend com `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` e, quando o repositorio PostgreSQL for ativado, `DATABASE_URL`.
5. Nunca envie `SUPABASE_SERVICE_ROLE_KEY` ao frontend e nunca commite secrets.

### Supabase Storage dev

Para validar storage privado real em um projeto Supabase de desenvolvimento:

1. crie um bucket privado, por exemplo `financy-private-dev`;
2. configure somente o backend local com `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY`;
3. configure `FILE_STORAGE_PROVIDER=supabase`, `SUPABASE_STORAGE_BUCKET=<bucket>`, `PRIVATE_FILES_ENABLED=true`, `SIGNED_URL_TTL_SECONDS=300` e `FILE_SCAN_PROVIDER=mock` para smoke local;
4. mantenha `DATABASE_URL` apontando para PostgreSQL local;
5. execute:

```powershell
.\scripts\smoke_supabase_storage.ps1
```

O smoke test recusa `APP_ENV=production`, recusa bucket publico, nao imprime signed URLs, cria metadata temporaria em `stored_files`, gera URL assinada e remove o objeto de teste ao final.

### RLS e service role

As tabelas que precisam de RLS antes de exposicao publica incluem `stored_files`, `transaction_attachments`, `stored_file_events`, `reimbursement_contacts`, `reimbursement_claims`, `reimbursement_items` e `reimbursement_events`, alem das tabelas financeiras ja existentes por owner. Enquanto o backend usa service role, o isolamento por owner continua sendo validado no backend e em testes. A service role ignora RLS e por isso deve permanecer exclusivamente no backend.

## Fluxo MVP

1. Usuario envia PDF, OFX, CSV ou XLSX em `/imports`.
2. Backend detecta tipo pelo `ParserFactory`, extrai transacoes e cria itens de preview.
3. Frontend lista itens extraidos, permite selecionar e editar campos principais.
4. Usuario confirma itens selecionados.
5. Backend evita duplicidades e grava transacoes.

## Testes

```powershell
cd backend
pytest
```

Para validar o backend contra PostgreSQL:

```powershell
cd backend
$env:TEST_DATABASE_URL='postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev_test'
.\.venv\Scripts\python.exe -m pytest tests_postgres -m postgres
```

## Debug de PDF

O fluxo de importacao PDF esta documentado em `docs/importacao-pdf.md`. Para testar um PDF real privado sem gravar nada:

```powershell
python backend/scripts/debug_pdf_parser.py "C:\Users\Gabriel\Downloads\Comprovante_07-06-2026_185907.pdf"
```

## Proximos passos

- Trocar o contexto `DEV_USER_ID` por Supabase Auth.
- Implementar repositorio PostgreSQL/Supabase direto na API.
- Adicionar RLS no Supabase conforme o modelo de autenticacao.
- Evoluir `merchant aliases` para normalizar nomes comerciais.
- Adicionar classificacao inteligente em uma camada propria sem acoplar aos parsers.

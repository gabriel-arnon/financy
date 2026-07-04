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

- `NEXT_PUBLIC_API_URL`: URL da API FastAPI.
- `NEXT_PUBLIC_SUPABASE_URL`: preparado para Supabase Auth futuro.
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: preparado para Supabase Auth futuro.

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

Suba o banco:

```powershell
docker-compose up --build -d postgres
```

Aplique as migrations no banco da aplicacao:

```powershell
cd backend
$env:DATABASE_URL='postgresql://financy:financy@localhost:5432/financy'
.\.venv\Scripts\python.exe scripts\apply_migrations.py --reset-schema
```

Prepare um banco de teste isolado:

```powershell
cd backend
$env:TEST_DATABASE_URL='postgresql://financy:financy@localhost:5432/financy_test'
.\.venv\Scripts\python.exe scripts\prepare_test_database.py
```

Para rodar o backend usando PostgreSQL:

```powershell
cd backend
$env:STORAGE_BACKEND='postgres'
$env:DATABASE_URL='postgresql://financy:financy@localhost:5432/financy'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Para voltar ao fallback JSON, use `STORAGE_BACKEND=json` ou remova a variavel.

### Migracao JSON -> PostgreSQL

Sempre rode dry-run antes do apply:

```powershell
cd backend
$env:DATABASE_URL='postgresql://financy:financy@localhost:5432/financy'
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

1. Crie um projeto no Supabase.
2. Abra o SQL Editor.
3. Execute as migrations em `docs/supabase/migrations` na ordem numerica.
4. Configure as variaveis do backend com `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` e, quando o repositorio PostgreSQL for ativado, `DATABASE_URL`.

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
$env:STORAGE_BACKEND='postgres'
$env:DATABASE_URL='postgresql://financy:financy@localhost:5432/financy_test'
.\.venv\Scripts\python.exe -m pytest
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

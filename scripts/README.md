# Scripts de desenvolvimento

## PostgreSQL local descartavel

Inicie o banco local e aplique migrations:

```powershell
.\scripts\setup_dev_db.ps1 -ResetSchema
```

Se o volume local ja existir com credenciais antigas, recrie somente o ambiente dev descartavel:

```powershell
.\scripts\setup_dev_db.ps1 -ResetVolume -ResetSchema
```

URL padrao usada pelo script:

```text
postgresql://financy_dev:***@localhost:5432/financy_dev
```

O script recusa hosts que nao sejam `localhost`, `127.0.0.1`, `::1` ou `postgres`.
Ele nao deve ser usado contra producao ou Supabase remoto.

## Testes PostgreSQL reais

Prepare o banco de teste isolado:

```powershell
cd backend
$env:TEST_DATABASE_URL='postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev_test'
.\.venv\Scripts\python.exe scripts\prepare_test_database.py
```

Execute os testes de integracao PostgreSQL:

```powershell
cd backend
$env:TEST_DATABASE_URL='postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev_test'
.\.venv\Scripts\python.exe -m pytest tests_postgres -m postgres
```

## Supabase Storage dev

Depois de configurar um projeto Supabase separado de desenvolvimento e um bucket privado:

```powershell
$env:APP_ENV='development'
$env:PRIVATE_FILES_ENABLED='true'
$env:FILE_STORAGE_PROVIDER='supabase'
$env:SUPABASE_STORAGE_BUCKET='financy-private-dev'
$env:FILE_SCAN_PROVIDER='mock'
$env:SUPABASE_URL='https://PROJECT_REF.supabase.co'
$env:SUPABASE_SERVICE_ROLE_KEY='local-dev-service-role'
$env:DATABASE_URL='postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev'
.\scripts\smoke_supabase_storage.ps1
```

Resolucao da URL de metadata:

1. parametro `-DatabaseUrl`;
2. variavel da sessao `$env:DATABASE_URL`;
3. fallback seguro para `DATABASE_URL` em `backend/.env`.

O parser do `.env` ignora comentarios e linhas vazias, aceita valores entre aspas, nao carrega outras chaves e nao sobrescreve variaveis ja definidas na sessao. O script imprime apenas a URL mascarada, por exemplo `postgresql://financy_dev:***@localhost:5432/financy_dev`.

Nao envie `SUPABASE_SERVICE_ROLE_KEY` ao frontend e nao commite secrets.

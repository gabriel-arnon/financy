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
uvicorn app.main:app --reload
```

A API sobe em `http://127.0.0.1:8000`.

### Variaveis de ambiente

Veja `backend/.env.example`.

- `DEV_USER_ID`: usuario local para desenvolvimento sem login.
- `UPLOAD_DIR`: pasta local para arquivos enviados.
- `CORS_ORIGINS`: origens permitidas separadas por virgula.
- `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY`: reservadas para integracao Supabase.
- `DATABASE_URL`: conexao PostgreSQL/Supabase para evolucao do repositorio persistente.

Por padrao, sem Supabase configurado, o backend usa persistencia local em JSON dentro de `UPLOAD_DIR`, apenas para desenvolvimento.

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

## Proximos passos

- Trocar o contexto `DEV_USER_ID` por Supabase Auth.
- Implementar repositorio PostgreSQL/Supabase direto na API.
- Adicionar RLS no Supabase conforme o modelo de autenticacao.
- Evoluir `merchant aliases` para normalizar nomes comerciais.
- Adicionar classificacao inteligente em uma camada propria sem acoplar aos parsers.

# Financy - Checklist de Deploy Privado

## Objetivo

Checklist operacional para publicar ou atualizar o Financy em ambiente privado controlado com Supabase Auth, PostgreSQL e backend/frontend separados.

## 1. Seguranca das credenciais

- [ ] Rotacionar qualquer `SUPABASE_SERVICE_ROLE_KEY`, `JWT_SECRET`, database password ou secret colado em chat/ferramentas.
- [ ] Garantir que segredos reais estao apenas nos paineis do provedor, nunca em arquivos versionados.
- [ ] Usar `backend/.env.production.example` e `frontend/.env.production.example` apenas como modelo.
- [ ] Confirmar que `.env` reais continuam ignorados pelo Git.

## 2. Infraestrutura obrigatoria

- [x] Projeto Supabase criado.
- [x] PostgreSQL de producao disponivel via Supabase.
- [x] Frontend publicado na Vercel: `https://financy-flame.vercel.app`.
- [x] Backend publicado no Render: `https://financy-api-mpt0.onrender.com`.
- [x] HTTPS configurado para frontend pela Vercel.
- [x] HTTPS configurado para backend pelo Render.
- [ ] Estrategia de uploads definida: volume persistente, Supabase Storage ou Cloudflare R2.
- [ ] Backups automaticos do banco habilitados.
- [ ] Backup dos uploads definido.

## 3. Variaveis obrigatorias

### Backend

- [x] `APP_NAME`
- [x] `APP_ENV=production`
- [x] `AUTH_PROVIDER=supabase`
- [x] `AUTH_REQUIRED=true`
- [x] `AUTH_DEV_BYPASS=false`
- [x] `DATABASE_URL`
- [x] `STORAGE_BACKEND=postgres`
- [x] `JWT_SECRET`
- [x] `SUPABASE_URL`
- [x] `SUPABASE_JWT_ISSUER`
- [x] `SUPABASE_JWKS_URL`
- [x] `SUPABASE_AUDIENCE`
- [x] `CORS_ORIGINS`
- [x] `UPLOAD_STORAGE_PATH` configurado como `.uploads` no Render.
- [ ] `SUPABASE_SERVICE_ROLE_KEY` somente para scripts/migracoes/admin.

### Frontend

- [x] `NEXT_PUBLIC_API_URL`
- [x] `NEXT_PUBLIC_SUPABASE_URL`
- [x] `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## 4. Pontos ainda pendentes das credenciais atuais

- [x] Configurar `DATABASE_URL` com a senha real do PostgreSQL no painel do provedor. A senha foi fornecida, mas nao deve ser versionada.
- [x] Configurar `JWT_SECRET` real do Supabase no painel do provedor. O valor foi fornecido, mas nao deve ser versionado.
- [x] Substituir `NEXT_PUBLIC_API_URL` local pela URL publica do backend: `https://financy-api-mpt0.onrender.com`.
- [x] Substituir `CORS_ORIGINS` local pelo dominio publico do frontend: `https://financy-flame.vercel.app`.
- [x] Backend valida token Supabase via HS256/JWKS conforme token recebido.

## 5. Validacao local antes do deploy

### Backend

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

- [x] Testes backend passaram: `45 passed, 1 warning`.
- [x] `/health` responde `{"status":"ok"}`.
- [x] Rotas financeiras retornam `401` sem token quando auth obrigatoria esta ativa.
- [x] `UPLOAD_STORAGE_PATH` aponta para `.uploads` no Render. Pendente trocar para storage persistente.

### Frontend

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

- [x] Typecheck passou.
- [x] Lint passou.
- [x] Build passou.
- [x] `NEXT_PUBLIC_API_URL` aponta para `https://financy-api-mpt0.onrender.com`.
- [x] Login/logout Supabase funcionam em ambiente configurado.

### Docker/local

```powershell
docker compose config
docker compose up --build
```

- [ ] Compose e valido.
- [ ] Backend sobe na porta esperada.
- [ ] Frontend sobe na porta esperada.
- [ ] Frontend acessa backend.

## 6. Banco e migracoes

- [x] Aplicar migrations no PostgreSQL de producao.
- [ ] Se houver dados locais, executar backup antes da migracao.
- [ ] Migrar JSON para PostgreSQL, se aplicavel.
- [ ] Reassociar dados de `DEV_USER_ID` para o usuario real com `backend/scripts/reassign_user_data.py`.
- [ ] Conferir contagens antes/depois.
- [ ] Guardar registro do backup e do usuario destino.
- [x] Backend pode manter `python scripts/apply_migrations.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT` no start command; por seguranca, o script nao aplica migrations em banco remoto sem `--allow-remote` ou `FINANCY_ALLOW_REMOTE_MIGRATIONS=true`, e faz skip com sucesso para nao derrubar deploy.

## 7. Smoke test funcional pos-deploy

- [x] Abrir frontend publicado: `https://financy-flame.vercel.app`.
- [x] Fazer login com usuario real.
- [x] Confirmar carregamento do dashboard.
- [x] Abrir transacoes.
- [x] Editar descricao/categoria de uma transacao.
- [ ] Criar uma regra a partir de transacao categorizada.
- [x] Abrir contas.
- [x] Criar ou editar uma conta.
- [x] Abrir cartoes.
- [x] Criar ou editar um cartao.
- [x] Abrir importacao.
- [x] Importar arquivo pequeno de teste.
- [x] Importar PDF com multiplas transacoes.
- [x] Confirmar que a API responde `/health`: `https://financy-api-mpt0.onrender.com/health`.
- [ ] Fazer logout.
- [ ] Confirmar que rotas protegidas exigem login.

## 7.1 Performance pos-deploy

- [x] Deploy do commit de performance aplicado: `e7e86bd Add Postgres pooling and faster import duplicate checks`.
- [x] Connection pool Postgres habilitado no backend com `psycopg-pool`.
- [x] Checagem de duplicidade da importacao otimizada para evitar listar transacoes a cada item.
- [x] Parser CSV aceita valores com virgula e ponto decimal.
- [x] Parser PDF otimizado para evitar extracao de tabelas quando texto normal ja existe.
- [x] Inserts de `import_preview_items` otimizados em lote.
- [x] Confirmacao de importacao otimizada com criacao de transacoes em lote.
- [x] Atualizacao de status de preview otimizada em lote.
- [x] Cache de referencias/faturas aplicado na confirmacao de importacao.
- [x] Logs temporarios de diagnostico de importacao removidos.
- [x] Benchmark local criado em `backend/scripts/benchmark_import_confirm.py`.
- [x] Benchmark local: 500 itens em 0.0655s e 1000 itens em 0.1199s.
- [/] Performance melhorou parcialmente, mas ainda ha latencia perceptivel de 3-5 segundos em algumas telas.
- [/] Importacao PDF funciona, mas ainda pode demorar minutos em PDFs com muitas transacoes.
- [ ] Avaliar upgrade do Render Free para instancia sempre ligada/mais CPU.
- [ ] Revalidar tempo real de upload/confirmacao apos deploy do commit de lote.

## 8. Smoke test de isolamento

- [ ] Criar ou usar usuario A.
- [ ] Criar ou usar usuario B.
- [ ] Confirmar que usuario B nao ve contas, cartoes, transacoes, regras e imports do usuario A.
- [ ] Confirmar que referencias cruzadas entre usuarios retornam erro/404.
- [ ] Confirmar que categorias de sistema aparecem para ambos.

## 9. Backup depois do deploy

- [ ] Criar backup pos-deploy do banco.
- [ ] Criar ou confirmar backup dos uploads.
- [ ] Registrar timestamp.
- [ ] Confirmar que o backup esta fora de diretorio temporario do host.
- [ ] Testar restauracao em ambiente descartavel quando possivel.

## 10. Riscos conhecidos

- [ ] RLS existe como draft em `docs/supabase/rls_phase3_draft.sql`, mas ainda nao deve ser aplicado sem validacao final.
- [ ] Storage local em host sem volume persistente pode perder uploads.
- [ ] Backups locais/manuais nao bastam para producao.
- [ ] Render Free possui cold start, CPU limitada e latencia perceptivel. Performance ideal provavelmente exige upgrade de instancia ou outro provedor.
- [ ] Deploy privado ainda exige configuracao manual dos provedores.
- [ ] Producao publica/SaaS exige LGPD, termos, exportacao/exclusao de dados, rate limiting e suporte.
- [x] Runbook pos-deploy criado em `docs/production-readiness-runbook.md`.

## 11. Criterio de pronto

O deploy privado esta pronto para uso controlado quando:

- [ ] Credenciais sensiveis foram rotacionadas e configuradas nos provedores.
- [ ] Variaveis obrigatorias estao configuradas.
- [ ] Build/testes passaram.
- [x] Migrations foram aplicadas.
- [ ] Dados foram migrados/reassociados, se aplicavel.
- [ ] Smoke test funcional passou.
- [ ] Smoke test de isolamento passou.
- [ ] Backup pos-deploy foi criado.

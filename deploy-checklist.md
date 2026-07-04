# Financy - Checklist de Deploy Privado

## Objetivo

Checklist operacional para publicar ou atualizar o Financy em ambiente privado controlado com Supabase Auth, PostgreSQL e backend/frontend separados.

## 1. Seguranca das credenciais

- [ ] Rotacionar qualquer `SUPABASE_SERVICE_ROLE_KEY`, `JWT_SECRET`, database password ou secret colado em chat/ferramentas.
- [ ] Garantir que segredos reais estao apenas nos paineis do provedor, nunca em arquivos versionados.
- [ ] Usar `backend/.env.production.example` e `frontend/.env.production.example` apenas como modelo.
- [ ] Confirmar que `.env` reais continuam ignorados pelo Git.

## 2. Infraestrutura obrigatoria

- [ ] Projeto Supabase criado.
- [ ] PostgreSQL de producao disponivel.
- [ ] Frontend publicado, por exemplo Vercel.
- [ ] Backend publicado, por exemplo Railway/Render/Fly.io.
- [ ] Dominio/HTTPS configurado para frontend.
- [ ] Dominio/HTTPS configurado para backend.
- [ ] Estrategia de uploads definida: volume persistente, Supabase Storage ou Cloudflare R2.
- [ ] Backups automaticos do banco habilitados.
- [ ] Backup dos uploads definido.

## 3. Variaveis obrigatorias

### Backend

- [ ] `APP_NAME`
- [ ] `APP_ENV=production`
- [ ] `AUTH_PROVIDER=supabase`
- [ ] `AUTH_REQUIRED=true`
- [ ] `AUTH_DEV_BYPASS=false`
- [ ] `DATABASE_URL`
- [ ] `STORAGE_BACKEND=postgres`
- [ ] `JWT_SECRET`
- [ ] `SUPABASE_URL`
- [ ] `SUPABASE_JWT_ISSUER`
- [ ] `SUPABASE_JWKS_URL`
- [ ] `SUPABASE_AUDIENCE`
- [ ] `CORS_ORIGINS`
- [ ] `UPLOAD_STORAGE_PATH` ou configuracao equivalente do storage escolhido.
- [ ] `SUPABASE_SERVICE_ROLE_KEY` somente para scripts/migracoes/admin.

### Frontend

- [ ] `NEXT_PUBLIC_API_URL`
- [ ] `NEXT_PUBLIC_SUPABASE_URL`
- [ ] `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## 4. Pontos ainda pendentes das credenciais atuais

- [ ] Configurar `DATABASE_URL` com a senha real do PostgreSQL no painel do provedor. A senha foi fornecida, mas nao deve ser versionada.
- [ ] Configurar `JWT_SECRET` real do Supabase no painel do provedor. O valor foi fornecido, mas nao deve ser versionado.
- [ ] Substituir `NEXT_PUBLIC_API_URL` local pela URL publica do backend.
- [ ] Substituir `CORS_ORIGINS` local pelo dominio publico do frontend.
- [ ] Confirmar que o token Supabase recebido usa HS256 com o `JWT_SECRET` configurado; se o projeto usar tokens assimetricos/JWKS, implementar validacao JWKS antes do deploy.

## 5. Validacao local antes do deploy

### Backend

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

- [ ] Testes backend passaram.
- [ ] `/health` responde `{"status":"ok"}`.
- [ ] Rotas financeiras retornam `401` sem token quando auth obrigatoria esta ativa.
- [ ] `UPLOAD_STORAGE_PATH` aponta para diretorio persistente ou storage escolhido.

### Frontend

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

- [ ] Typecheck passou.
- [ ] Lint passou.
- [ ] Build passou.
- [ ] `NEXT_PUBLIC_API_URL` aponta para a API correta.
- [ ] Login/logout Supabase funcionam em ambiente configurado.

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

- [ ] Aplicar migrations no PostgreSQL de producao.
- [ ] Se houver dados locais, executar backup antes da migracao.
- [ ] Migrar JSON para PostgreSQL, se aplicavel.
- [ ] Reassociar dados de `DEV_USER_ID` para o usuario real com `backend/scripts/reassign_user_data.py`.
- [ ] Conferir contagens antes/depois.
- [ ] Guardar registro do backup e do usuario destino.

## 7. Smoke test funcional pos-deploy

- [ ] Abrir frontend publicado.
- [ ] Fazer login com usuario real.
- [ ] Confirmar carregamento do dashboard.
- [ ] Abrir transacoes.
- [ ] Editar descricao/categoria de uma transacao.
- [ ] Criar uma regra a partir de transacao categorizada.
- [ ] Abrir contas.
- [ ] Criar ou editar uma conta.
- [ ] Abrir cartoes.
- [ ] Criar ou editar um cartao.
- [ ] Abrir importacao.
- [ ] Importar arquivo pequeno de teste.
- [ ] Confirmar que a API responde `/health`.
- [ ] Fazer logout.
- [ ] Confirmar que rotas protegidas exigem login.

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
- [ ] Deploy privado ainda exige configuracao manual dos provedores.
- [ ] Producao publica/SaaS exige LGPD, termos, exportacao/exclusao de dados, rate limiting e suporte.

## 11. Criterio de pronto

O deploy privado esta pronto para uso controlado quando:

- [ ] Credenciais sensiveis foram rotacionadas e configuradas nos provedores.
- [ ] Variaveis obrigatorias estao configuradas.
- [ ] Build/testes passaram.
- [ ] Migrations foram aplicadas.
- [ ] Dados foram migrados/reassociados, se aplicavel.
- [ ] Smoke test funcional passou.
- [ ] Smoke test de isolamento passou.
- [ ] Backup pos-deploy foi criado.

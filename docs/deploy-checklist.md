# Checklist de Deploy - Financy

Data da revisao: 2026-07-13

Use este checklist para Production e Dev. Nao registrar secrets no repositorio, em logs compartilhados ou em tickets.

## Antes do deploy

### Codigo e branch

- [ ] Branch correta selecionada: `main` para Production, `dev` para Dev.
- [ ] `git status` sem alteracoes inesperadas.
- [ ] Merge esperado concluido.
- [ ] Migrations esperadas presentes em `docs/supabase/migrations`.
- [ ] Migrations de ressarcimentos atuais presentes quando aplicavel: `009_reimbursement_comments.sql`, `010_invitation_accept_rate_limits.sql` e `011_reimbursements_security_hardening.sql`.
- [ ] Nenhuma migration aplicada em producao foi editada retroativamente.

### Validacoes locais

- [ ] Backend: `cd backend; .\.venv\Scripts\python.exe -m pytest`.
- [ ] Frontend typecheck, se aplicavel: `cd frontend; npm.cmd run typecheck`.
- [ ] Frontend lint, se aplicavel: `cd frontend; npm.cmd run lint`.
- [ ] Frontend build: `cd frontend; npm.cmd run build`.
- [ ] E2E, quando seguro: `cd frontend; npm.cmd run e2e`.

### Migrations

- [ ] Confirmar se existem migrations pendentes.
- [ ] Confirmar `schema_migrations` no ambiente alvo.
- [ ] Para Production, aplicar migrations remotas apenas com acao explicita e revisada.
- [ ] Nunca usar `--reset-schema` em remoto.
- [ ] Para DDL, preferir direct/admin connection; evitar Transaction Pooler `6543` para migrations.

### Variaveis e ambientes

- [ ] Variaveis pertencem ao ambiente correto.
- [ ] `DATABASE_URL` nao aponta para `localhost`, `127.0.0.1`, Supabase Dev quando alvo e Production, nem Supabase Production quando alvo e Dev.
- [ ] `DATABASE_URL` nao usa host antigo do Supabase Brasil quando alvo e Production US.
- [ ] `DATABASE_URL` nao usa Transaction Pooler `6543` no backend persistente sem decisao tecnica explicita.
- [ ] `NEXT_PUBLIC_API_URL` nao aponta para `localhost` ou `127.0.0.1` em build remoto.
- [ ] `NEXT_PUBLIC_API_URL` usa `https` em Vercel Preview/Production.
- [ ] `NEXT_PUBLIC_API_URL` do Frontend Production aponta para Backend Production.
- [ ] `NEXT_PUBLIC_API_URL` do Frontend Preview aponta para Backend Dev.
- [ ] `NEXT_PUBLIC_SUPABASE_URL` corresponde ao Supabase do ambiente.
- [ ] `NEXT_PUBLIC_SUPABASE_ANON_KEY` corresponde ao Supabase do ambiente.
- [ ] `SUPABASE_URL` corresponde ao Supabase do ambiente.
- [ ] `SUPABASE_JWT_ISSUER` corresponde ao projeto correto.
- [ ] `SUPABASE_JWKS_URL` corresponde ao projeto correto.
- [ ] `SUPABASE_AUDIENCE` configurado.
- [ ] `JWT_SECRET` corresponde ao projeto correto, quando usado.
- [ ] `CORS_ORIGINS` contem somente frontend do ambiente correto.
- [ ] `SUPABASE_SERVICE_ROLE_KEY` existe somente no backend/admin, nunca no frontend.
- [ ] Nenhuma credencial real esta versionada.
- [ ] Variaveis de rate limit de convites configuradas:
  - `INVITATION_ACCEPT_RATE_LIMIT_ENABLED`
  - `INVITATION_ACCEPT_RATE_LIMIT_MAX_ATTEMPTS`
  - `INVITATION_ACCEPT_RATE_LIMIT_WINDOW_SECONDS`

### Storage

- [ ] Bucket privado `private-files` existe no Supabase do ambiente.
- [ ] Bucket nao e publico.
- [ ] `PRIVATE_FILES_ENABLED=true`.
- [ ] `PRIVATE_FILES_BACKEND=supabase` em ambientes remotos.
- [ ] `PRIVATE_FILES_BUCKET` ou `SUPABASE_STORAGE_BUCKET` aponta para `private-files`.
- [ ] TTL de signed URL configurado.
- [ ] Scan provider configurado conforme ambiente.

## Depois do deploy

### Smoke tecnico

- [ ] `GET /health` retorna sucesso no backend do ambiente.
- [ ] Logs do backend sem falhas de startup.
- [ ] Logs sem secrets ou signed URLs.
- [ ] Logs analisados por `401`, `403` e `500`.
- [ ] DevTools/network sem chamadas para ambiente incorreto.
- [ ] Nenhuma chamada para `localhost` ou `127.0.0.1` em ambiente remoto.
- [ ] Medir TTFB nas rotas principais e registrar no plano de migracao.

### Smoke funcional

- [ ] Login.
- [ ] Logout.
- [ ] Dashboard.
- [ ] Transacoes.
- [ ] Contas.
- [ ] Cartoes.
- [ ] Importacoes.
- [ ] Ressarcimentos.
- [ ] Invitations.
- [ ] Memberships.
- [ ] Claim attachments.
- [ ] Signed URLs de arquivos privados.
- [ ] Upload e visualizacao de comprovante, quando seguro.
- [ ] Comentarios de ressarcimento funcionam para owner e guest autorizado.
- [ ] Exclusao de comentarios usa dialogo, respeita permissoes e nao usa confirmacao nativa do navegador.
- [ ] Comentarios sao exibidos como texto puro e nao renderizam HTML arbitrario.
- [ ] Aceite de convite retorna `429` apos excesso de tentativas configurado.
- [ ] Data API nao permite leitura/escrita direta das tabelas financeiras com roles `anon` ou `authenticated`.
- [ ] Bundles publicos do frontend nao contem `localhost`, `127.0.0.1` ou URLs de ambiente incorreto.

### Smoke de isolamento

- [ ] Usuario A nao ve dados do usuario B.
- [ ] Frontend Production usa backend Production.
- [ ] Backend Production usa Supabase Production US.
- [ ] Frontend Preview usa backend Dev.
- [ ] Backend Dev usa Supabase Dev.
- [ ] Guest acessa somente cobrancas autorizadas.
- [ ] Membership revogado bloqueia novo acesso.

## Performance

Valores historicos antes da migracao para Supabase US:

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

Causa identificada:

- Render Production em Virginia;
- Supabase Production em `sa-east-1`;
- multiplas viagens internacionais entre backend e banco.

Registrar medicoes atuais:

| Ambiente | Rota | TTFB atual | Data | Observacao |
|---|---:|---:|---|---|
| Production US | `/overview` | A medir |  |  |
| Production US | `/transactions` | A medir |  |  |
| Production US | `/accounts` | A medir |  |  |
| Production US | `/cards` | A medir |  |  |

## Rollback

- [ ] Manter Supabase Production Brasil intacto ou pausado durante a janela de validacao.
- [ ] Nao excluir o projeto Brasil ate decisao humana explicita.
- [ ] Antes de rollback, avaliar se houve novas escritas no Supabase US.
- [ ] Se houve novas escritas, reconciliar delta antes de voltar.
- [ ] Se rollback for necessario antes de delta relevante, restaurar variaveis antigas em Render/Vercel a partir de cofre seguro.
- [ ] Validar Auth, banco, Storage e JWT apos rollback.

## Criterio de pronto

- [ ] Deploy concluiu.
- [ ] Smoke tecnico passou.
- [ ] Smoke funcional passou.
- [ ] Smoke de isolamento passou.
- [ ] Logs limpos.
- [ ] TTFB medido.
- [ ] Sem cruzamento entre ambientes.
- [ ] Rollback ainda disponivel ate fim da janela definida.

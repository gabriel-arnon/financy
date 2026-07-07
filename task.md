# Financy - Tasks da Fase 3: Autenticacao e Isolamento de Usuarios

## Legenda

- `[x]` Concluida
- `[ ]` Nao iniciada
- `[/]` Em andamento
- `[-]` Pausada/cancelada

## Objetivo da fase

Implementar autenticacao real e isolamento estrito por usuario, substituindo o uso operacional de `DEV_USER_ID` por identidade autenticada via Supabase Auth.

## P0 - Planejamento e auditoria

### [x] P0.1 - Inspecionar uso atual de usuario

Feito:

- `get_user_id()` fica em `backend/app/api/deps.py`.
- Hoje retorna `settings.dev_user_id`.
- Todas as rotas financeiras dependem desse contexto direta ou indiretamente.

### [x] P0.2 - Mapear entidades com `user_id`

Feito:

- Entidades user-owned: accounts, cards, card_statements, transactions, classification_rules, import_files, import_batches, import_preview_items.
- Categorias sao mistas: sistema com `user_id = null`; categorias de usuario com `user_id`.
- `profiles` representa usuarios da aplicacao.

### [x] P0.3 - Mapear endpoints protegidos

Feito:

- Devem ser protegidos: transactions, imports, statements, categories, accounts, cards e classification-rules.
- Deve permanecer publico: `GET /health`.

### [x] P0.4 - Escolher estrategia de auth

Feito:

- Recomendacao: Supabase Auth com JWT Bearer.
- Motivo: schema ja usa `profiles`, reduz auth propria e prepara RLS futuro.

### [x] P0.5 - Criar plano detalhado

Feito:

- Criado `docs/auth-user-isolation-plan.md`.

## P1 - Backend Auth Foundation

### [x] P1.1 - Adicionar settings de auth

- `AUTH_PROVIDER`.
- `AUTH_REQUIRED`.
- `AUTH_DEV_BYPASS`.
- `SUPABASE_JWT_ISSUER`.
- `SUPABASE_JWKS_URL`.
- `SUPABASE_AUDIENCE`, se necessario.

Resultado esperado:

- Configuracao clara para auth real, local e teste.

Feito:

- Adicionados settings em `backend/app/core/config.py`.
- Atualizado `backend/.env.example` com flags de auth.
- `DEV_USER_ID` ficou restrito ao bypass local/teste por `AUTH_DEV_BYPASS`.

### [x] P1.2 - Criar modelo/contexto de usuario atual

- Criar `CurrentUser`.
- Incluir `id` e `email` quando disponivel.

Resultado esperado:

- Rotas podem depender de um usuario autenticado padronizado.

Feito:

- Criado `CurrentUser` em `backend/app/core/auth.py`.
- Incluidos `id`, `email`, `full_name` e `auth_source`.

### [x] P1.3 - Implementar validacao JWT Supabase

- Ler Bearer token.
- Validar assinatura.
- Validar expiracao, issuer e subject.
- Extrair `sub` como `user_id`.

Resultado esperado:

- Token valido resolve usuario; token invalido retorna `401`.

Feito:

- Implementada leitura de Bearer token.
- Implementada validacao JWT HS256 com biblioteca padrao.
- Valida assinatura, expiracao, `issuer`, `audience` e `sub`.
- Token invalido retorna `401` via `AppError`.

### [x] P1.4 - Implementar bypass local/teste

- Usar `DEV_USER_ID` apenas com `AUTH_DEV_BYPASS=true`.
- Bloquear bypass em producao.

Resultado esperado:

- Desenvolvimento local continua possivel sem fallback inseguro.

Feito:

- `get_current_user` usa bypass somente quando `AUTH_DEV_BYPASS=true` e ambiente e `local`, `development` ou `test`.
- Bypass e bloqueado em `production`.
- Rotas usam `get_request_user_id`; helper direto `get_user_id()` continua disponivel para testes/scripts locais.

### [x] P1.5 - Criar/upsert profile autenticado

- Garantir `profiles.id = current_user.id`.
- Espelhar email/full_name quando disponivel.

Resultado esperado:

- Usuario autenticado sempre possui profile.

Feito:

- `PostgresRepository.ensure_profile` agora faz upsert de profile.
- `deps.py` chama `ensure_profile` quando o repository suporta esse metodo.
- JSON segue sem profile fisico, preservando fallback local.

## P2 - Protecao de endpoints

### [x] P2.1 - Proteger transactions

- `GET /transactions`.
- `POST /transactions`.
- `PUT /transactions/{transaction_id}`.
- `DELETE /transactions/{transaction_id}`.

Resultado esperado:

- Apenas usuario autenticado acessa transacoes proprias.

Feito:

- Rotas usam `get_request_user_id`.
- Sem token retorna `401` quando `AUTH_REQUIRED=true` e `AUTH_DEV_BYPASS=false`.

### [x] P2.2 - Proteger imports

- `POST /imports/upload`.
- `GET /imports/{import_id}/preview`.
- `POST /imports/{import_id}/confirm`.

Resultado esperado:

- Preview e confirmacao sao isolados por usuario.

Feito:

- Rotas de import usam usuario autenticado.
- Uploads novos sao salvos em subpasta por usuario.

### [x] P2.3 - Proteger statements

- `GET /statements`.
- `GET /statements/{statement_id}`.
- `DELETE /statements/{statement_id}`.
- `PATCH /statements/{statement_id}/status`.

Resultado esperado:

- Faturas e agregacoes pertencem ao usuario autenticado.

Feito:

- Rotas de faturas usam usuario autenticado e repository filtrado por `user_id`.

### [x] P2.4 - Proteger accounts/cards

- Todas as rotas de `/accounts`.
- Todas as rotas de `/cards`.

Resultado esperado:

- Contas e cartoes ficam isolados por usuario.

Feito:

- Rotas de contas/cartoes usam usuario autenticado.
- Teste multiusuario garante que usuario B nao ve conta de usuario A.

### [x] P2.5 - Proteger categories/rules

- Todas as rotas de `/categories`.
- Todas as rotas de `/classification-rules`.

Resultado esperado:

- Usuario acessa categorias de sistema e proprias; regras sao proprias.

Feito:

- Rotas usam usuario autenticado.
- Regras validam categoria no escopo do usuario atual.

### [x] P2.6 - Manter `/health` publico

Resultado esperado:

- Healthcheck continua sem auth.

Feito:

- Teste confirma `/health` publico com auth obrigatoria.

## P3 - Hardening de isolamento

### [x] P3.1 - Validar referencias em cards

- `account_id` deve pertencer ao usuario atual.

Resultado esperado:

- Usuario nao cria/edita cartao com conta de outro usuario.

Feito:

- Validacao existente de `account_id` permanece escopada por usuario.

### [x] P3.2 - Validar referencias em transactions

- `account_id`, `card_id`, `card_statement_id`, `category_id`, `source_file_id`.

Resultado esperado:

- Transacao nao referencia recurso de outro usuario.

Feito:

- `TransactionService` valida conta, cartao, fatura, categoria e source file no escopo do usuario.
- Teste cobre tentativa de usuario B criar transacao com conta do usuario A.

### [x] P3.3 - Validar referencias em classification rules

- `category_id` deve ser categoria de sistema ou do usuario atual.

Resultado esperado:

- Regra nao aponta para categoria privada de outro usuario.

Feito:

- `classification_rules` valida `category_id` com `user_id`.

### [x] P3.4 - Endurecer categorias de sistema

- Bloquear update/delete comum em categoria `is_system=true`.

Resultado esperado:

- Categorias globais nao sao alteradas por usuarios comuns.

Feito:

- Update/delete de categoria `is_system` retorna erro de protecao.

### [x] P3.5 - Isolar import confirm

- Confirmacao deve validar batch, preview items e destino por usuario.

Resultado esperado:

- Usuario nao confirma import de outro usuario.

Feito:

- Import batch e preview items seguem filtrados por usuario.
- Confirmacao agora valida referencias antes de criar transacao.

### [x] P3.6 - Particionar novos uploads por usuario

- Salvar novos arquivos em path com `user_id`.

Resultado esperado:

- Uploads novos possuem isolamento fisico basico.

Feito:

- Novos uploads sao gravados em `UPLOAD_STORAGE_PATH/{user_id}`.

## P4 - Frontend Auth Shell

### [x] P4.1 - Instalar/configurar Supabase client

- Usar `NEXT_PUBLIC_SUPABASE_URL`.
- Usar `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

Resultado esperado:

- Frontend consegue iniciar client Supabase.

Feito:

- Instalado `@supabase/supabase-js`.
- Criado `frontend/src/lib/supabase.ts`.

### [x] P4.2 - Criar login

- Tela/form de login.
- Fluxo email/senha ou magic link.

Resultado esperado:

- Usuario consegue autenticar.

Feito:

- Criada rota `/login` com email/senha via Supabase Auth.

### [x] P4.3 - Criar logout

Resultado esperado:

- Usuario encerra sessao e perde acesso a rotas protegidas.

Feito:

- `AuthStatus` adiciona acao de sair.

### [x] P4.4 - Criar provider de sessao

- Restaurar sessao.
- Expor usuario atual.
- Estado de loading.

Resultado esperado:

- App conhece estado autenticado.

Feito:

- Criado `AuthProvider`.
- Sessao Supabase e sincronizada e access token e salvo em cookie para Server Components.

### [x] P4.5 - Proteger rotas frontend

Resultado esperado:

- Usuario anonimo e enviado ao login.

Feito:

- `AuthProvider` redireciona anonimo para `/login` quando Supabase esta configurado.
- Sem env Supabase, app permanece em modo local/bypass.

### [x] P4.6 - Enviar Bearer token no API client

- Atualizar `frontend/src/lib/api.ts`.
- Tratar `401`.

Resultado esperado:

- Chamadas protegidas chegam autenticadas ao backend.

Feito:

- `frontend/src/lib/api.ts` envia `Authorization: Bearer <access_token>`.
- `frontend/src/lib/server-api.ts` envia Bearer token a partir do cookie.

## P5 - Migracao de propriedade

### [x] P5.1 - Criar checklist/script de reassociacao

- Reassociar `DEV_USER_ID` para usuario real.
- Cobrir todas as tabelas user-owned.

Resultado esperado:

- Existe caminho seguro para dados atuais.

Feito:

- Criado `backend/scripts/reassign_user_data.py`.

### [x] P5.2 - Exigir backup antes do apply

Resultado esperado:

- Migracao de ownership nao roda sem backup/confirmacao.

Feito:

- `--apply` exige `--backup-confirmation`.

### [x] P5.3 - Validar contagens antes/depois

Resultado esperado:

- Reassociacao pode ser auditada.

Feito:

- Dry-run imprime contagens por tabela para origem e destino.
- Apply imprime contagens antes/depois.

### [x] P5.4 - Documentar rollback

Resultado esperado:

- E possivel voltar ao estado anterior em ambiente local/teste.

Feito:

- Script preserva dry-run e exige confirmacao de backup.
- Rollback esperado: restaurar backup ou aplicar reassociacao inversa validada por contagens.

## P6 - Preparacao de RLS

### [x] P6.1 - Criar draft de policies RLS

- Profiles.
- Accounts.
- Cards.
- Statements.
- Transactions.
- Categories.
- Rules.
- Imports.

Resultado esperado:

- Politicas planejadas sem ativacao prematura.

Feito:

- Criado `docs/supabase/rls_phase3_draft.sql` fora da pasta de migrations numeradas.

### [x] P6.2 - Testar RLS em banco descartavel

Resultado esperado:

- Policies sao verificadas antes de uso real.

Feito:

- Draft aplicado em `financy_test` com mock de `auth.uid()`.
- Banco de teste foi resetado depois.

### [x] P6.3 - Definir service role para scripts

Resultado esperado:

- Migrations/scripts nao quebram quando RLS existir.

Feito:

- Draft registra que RLS nao deve ser aplicado antes de definir service role/fluxo de scripts.
- Scripts operacionais continuam usando conexao direta fora de RLS nesta fase.

## P7 - Testes e QA

### [x] P7.1 - Testes de auth backend

- Sem token -> `401`.
- Token invalido -> `401`.
- Token valido -> user atual.
- Bypass local/teste.

Resultado esperado:

- Fundacao de auth coberta.

Feito:

- Criado `backend/tests/test_auth.py`.
- Cobertos token valido, assinatura invalida, token ausente com bypass, token ausente sem bypass e bloqueio de bypass em producao.
- Backend JSON/local: 40 passed, 1 warning.
- Backend PostgreSQL: 40 passed, 1 warning.

### [x] P7.2 - Testes de isolamento com dois usuarios

- Usuario A nao ve/acessa recursos do usuario B.
- Usuario A nao referencia recursos do usuario B.

Resultado esperado:

- Isolamento validado por testes.

Feito:

- Criado `backend/tests/test_auth_endpoints.py`.
- Cobre rota anonima, `/health`, listagem isolada e referencia cross-user bloqueada.

### [x] P7.3 - Testes frontend de auth

- Login.
- Logout.
- Rotas protegidas.
- Header Authorization.
- Tratamento de `401`.

Resultado esperado:

- UX minima de auth validada.

Feito:

- Validado por `typecheck`, `lint` e `build`.
- Nao foi criado suite e2e novo nesta rodada.

### [x] P7.4 - Smoke test multiusuario

Resultado esperado:

- Fluxo ponta a ponta validado com usuario A e usuario B.

Feito:

- Smoke multiusuario coberto por testes backend com tokens distintos.

## Validacao final da Fase 3

### [x] VF1 - Backend JSON/local

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Resultado:

- 44 passed, 1 warning.

### [x] VF2 - Backend PostgreSQL

```powershell
cd backend
$env:STORAGE_BACKEND='postgres'
$env:DATABASE_URL='postgresql://financy:financy@localhost:5432/financy_test'
.\.venv\Scripts\python.exe -m pytest
```

Resultado:

- 44 passed, 1 warning.

### [x] VF3 - Frontend

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

Resultado:

- `typecheck`, `lint` e `build` passaram.

### [x] VF4 - Auth smoke

- `/health` publico.
- Rotas financeiras retornam `401` sem token.
- Login funciona.
- Logout funciona.
- Bearer token chega ao backend.

Resultado:

- `/health` publico validado por teste.
- Rotas financeiras sem token retornam `401` quando auth obrigatoria esta ativa.
- Login/logout implementados no frontend.
- Bearer token implementado no client API e server API.

### [x] VF5 - User isolation smoke

- Usuario A cria dados.
- Usuario B nao ve dados de A.
- Usuario B nao acessa IDs de A.
- Categorias de sistema seguem visiveis para ambos.

Resultado:

- Isolamento A/B validado por testes backend.
- Acesso direto a summary de conta de outro usuario retorna `404`.

## Definicao de pronto

- [x] Supabase Auth implementado.
- [x] Backend valida JWT.
- [x] Frontend possui login/logout.
- [x] Rotas financeiras protegidas.
- [x] User isolation testado.
- [x] `DEV_USER_ID` restrito a bypass local/teste.
- [x] Migracao de ownership documentada/scriptada.
- [x] RLS preparado como draft nao aplicado automaticamente.
- [x] Validacoes obrigatorias passam.

## Pendencias pos-deploy - Producao privada

Esta secao registra o que ainda ficou fora da Fase 3 funcional, mas e necessario para estabilizar o uso privado em producao.

### [/] PD1 - Performance em producao

Feito:

- Deploy privado publicado em Render/Vercel.
- Connection pool Postgres aplicado no backend.
- Checagem de duplicidade da importacao otimizada para evitar listar transacoes a cada item.
- Parser CSV aceita valores com virgula e ponto decimal.
- Parser PDF otimizado para evitar extrair tabelas quando texto normal ja existe.
- Inserts de `import_preview_items` otimizados em lote.
- Logs temporarios de diagnostico de importacao removidos.

Pendente:

- Avaliar upgrade do Render Free para instancia sempre ligada/mais CPU.
- Validar ganho real apos novo deploy em producao.

### [/] PD2 - Storage persistente de uploads

Feito:

- Criado runbook operacional em `docs/production-readiness-runbook.md`.
- Recomendacao registrada: Supabase Storage como primeira opcao, mantendo paths por usuario.

Pendente externo:

- Escolher estrategia definitiva: Supabase Storage, Cloudflare R2 ou disco persistente.
- Migrar uploads de `.uploads` local do Render para storage persistente.
- Garantir que imports antigos continuem acessiveis quando necessario.

### [/] PD3 - Backups de producao

Feito:

- Criado checklist de backup e restore em `docs/production-readiness-runbook.md`.

Pendente externo:

- Confirmar backup automatico do PostgreSQL/Supabase.
- Definir backup dos uploads.
- Executar pelo menos um teste de restauracao em ambiente descartavel.

### [/] PD4 - Rotacao de segredos

Feito:

- Criado checklist de rotacao em `docs/production-readiness-runbook.md`.
- Lista de segredos a rotacionar documentada sem expor valores.

Pendente externo:

- Rotacionar senha do banco, JWT secret e service role key compartilhados durante o deploy.
- Atualizar variaveis no Render/Vercel/Supabase.
- Confirmar que nenhum segredo real esta versionado.

### [/] PD5 - Smoke test multiusuario em producao

Feito:

- Criado roteiro de smoke multiusuario em `docs/production-readiness-runbook.md`.

Pendente externo:

- Criar/usar usuario A e usuario B reais no Supabase.
- Confirmar que usuario B nao ve contas, cartoes, transacoes, regras, faturas e imports do usuario A.
- Confirmar que referencias cruzadas retornam erro/404.

### [/] PD6 - RLS Supabase

Feito:

- Draft de RLS ja existe em `docs/supabase/rls_phase3_draft.sql`.
- Ordem segura de ativacao registrada em `docs/production-readiness-runbook.md`.

Pendente externo:

- Revisar `docs/supabase/rls_phase3_draft.sql`.
- Decidir se RLS sera ativado ainda na producao privada ou apenas antes de multiusuario publico.
- Testar policies em staging antes de aplicar no banco real.

### [/] PD7 - Checklist de producao publica

Feito:

- Checklist de producao publica criado em `docs/production-readiness-runbook.md`.

Pendente externo:

- LGPD: termos, politica de privacidade, exportacao e exclusao de dados.
- Rate limiting.
- Monitoramento/logs de erro.
- Suporte/feedback.
- Plano de rollback operacional.

# Fundacao 3.5 - Comunicacao Segura em Ressarcimentos

Data: 2026-07-13

Status: plano aprovado tecnicamente para revisao humana antes da implementacao.

Atualizacao da Etapa B: migrations e backend devem ser implementados em
`docs/supabase/migrations`, que e o diretorio real usado pelo runner
`backend/scripts/apply_migrations.py` nesta branch. O caminho
`backend/migrations` citado em conversas anteriores nao existe no repositorio.

Branch alvo: `dev`.

## 1. Escopo

A Fundacao 3.5 fecha lacunas de comunicacao e seguranca antes de avancar para Telegram, OCR, audio, inbox, filas e pagamentos.

Escopo desta fundacao:

- comentarios em `reimbursement_claims` para owner e guest autorizado;
- exclusao logica e auditavel de comentarios;
- rate limiting no aceite de convites;
- revisao final de autorizacao/RLS para o dominio de ressarcimentos;
- melhoria de erros esperados em reimbursements;
- analise e correcao isolada do fallback silencioso de API URL no frontend, se o impacto permanecer pequeno;
- documentacao e testes de contrato, isolamento e regressao.

## 2. Fora de Escopo

Ficam explicitamente fora desta fundacao:

- pagamentos;
- Pix, gateway, conciliacao ou baixa automatica;
- Telegram;
- OCR;
- audio;
- inbox financeira;
- filas e workers;
- automacoes;
- alteracoes em Render, Vercel, Supabase ou servicos externos;
- alteracao da branch `main`;
- edicao de migrations ja versionadas de `001` a `008`;
- comentario em tempo real via WebSocket/SSE;
- anexos especificos em comentarios;
- mencoes, notificacoes push ou e-mail de comentario.

## 3. Estado Atual Observado

O repositorio esta na branch `dev`, sincronizado com `origin/dev`.

Migrations existentes:

- `001_initial_schema.sql`;
- `002_default_categories.sql`;
- `003_phase2_indexes.sql`;
- `004_nullable_card_account.sql`;
- `005_private_files.sql`;
- `006_reimbursements_domain.sql`;
- `007_reimbursement_guest_access.sql`;
- `008_reimbursement_claim_attachments.sql`.

O dominio atual de ressarcimentos ja possui:

- contatos;
- claims;
- items;
- events;
- invitations;
- memberships;
- claim attachments explicitos;
- portal guest;
- acknowledge;
- dispute;
- revoke;
- signed URLs autorizadas;
- snapshots sanitizados para guest.

Nao ha endpoints, schemas, repository methods ou UI para comentarios.

O aceite de convite usa `token_hash` SHA-256 e fluxo atomico no repository PostgreSQL, mas ainda nao possui rate limiting persistente.

## 4. Decisoes de Produto

Comentarios entram na Fundacao 3.5, antes de pagamentos, porque contestacao sem canal de comunicacao fica incompleta.

Comentarios serao texto puro, sem HTML arbitrario.

Comentarios serao imutaveis apos criacao nesta fundacao. Nao havera edicao (`PATCH`) no primeiro corte.

Exclusao sera logica:

- autor pode excluir o proprio comentario;
- owner pode moderar/excluir comentarios em claims proprios;
- guest nao pode excluir comentarios de outras pessoas;
- comentarios excluidos nao aparecem por padrao;
- linha e evento de auditoria permanecem.

A ordenacao padrao sera cronologica crescente.

A paginacao inicial sera simples, com `limit` e cursor estavel por `created_at` + `id`.

## 5. Modelo de Dados

Criar migration nova, sem alterar migrations antigas.

Proposta:

- `009_reimbursement_comments.sql`;
- `010_reimbursement_invitation_rate_limits.sql`;
- eventual `011_reimbursements_rls_policies.sql` somente se a auditoria RLS exigir policies versionadas nesta fundacao.

Decisao da Etapa B: `009` e `010` serao criadas agora. A migration `011` nao
sera criada nesta etapa porque a Fundacao 3.5 ainda nao esta aplicando policies
RLS finais; a auditoria RLS permanece para a Etapa D, sem policy vazia.

### 5.1. `reimbursement_comments`

Campos recomendados:

- `id uuid primary key default gen_random_uuid()`;
- `owner_user_id uuid not null references profiles(id)`;
- `claim_id uuid not null references reimbursement_claims(id)`;
- `author_user_id uuid not null references profiles(id)`;
- `author_role text not null check (author_role in ('owner', 'guest'))`;
- `body text not null`;
- `created_at timestamptz not null default now()`;
- `updated_at timestamptz null`;
- `deleted_at timestamptz null`;
- `deleted_by_user_id uuid null references profiles(id)`;
- `deleted_by_role text null check (deleted_by_role in ('owner', 'guest'))`.

Constraints recomendadas:

- `length(btrim(body)) > 0`;
- `length(body) <= 2000`;
- `deleted_by_user_id is null` quando `deleted_at is null`;
- `owner_user_id` deve ser o owner da claim, validado no service e reforcado por FK/consulta transacional quando possivel.

Indices recomendados:

- `idx_reimbursement_comments_claim_created` em `(claim_id, created_at, id)`;
- `idx_reimbursement_comments_claim_active` em `(claim_id, created_at, id) where deleted_at is null`;
- `idx_reimbursement_comments_owner_claim` em `(owner_user_id, claim_id, created_at)`;
- `idx_reimbursement_comments_author` em `(author_user_id, created_at desc)`.

### 5.2. `reimbursement_invitation_accept_attempts`

Recomendacao: usar PostgreSQL, nao memoria, para suportar multiplas instancias Render, restart de processo e auditoria minima.

Campos recomendados:

- `id uuid primary key default gen_random_uuid()`;
- `token_hash text not null`;
- `ip_hash text not null`;
- `auth_user_id uuid null references profiles(id)`;
- `attempted_at timestamptz not null default now()`;
- `success boolean not null default false`;
- `failure_code text null`.

Indices recomendados:

- `idx_reimbursement_invitation_attempts_window` em `(token_hash, ip_hash, attempted_at desc)`;
- `idx_reimbursement_invitation_attempts_cleanup` em `(attempted_at)`;
- `idx_reimbursement_invitation_attempts_user` em `(auth_user_id, attempted_at desc)`.

Regras:

- nunca persistir token bruto;
- `token_hash` continua SHA-256 do token bruto;
- `ip_hash` deve ser hash/HMAC do IP, nunca IP puro em logs publicos;
- tentativas invalidas, expiradas, revogadas e com e-mail divergente contam para o limite;
- respostas publicas continuam neutras para evitar enumeracao;
- limpeza pode ser manual ou job futuro por janela de retencao.

Variaveis novas:

- `INVITATION_ACCEPT_RATE_LIMIT_ENABLED`;
- `INVITATION_ACCEPT_RATE_LIMIT_MAX_ATTEMPTS`;
- `INVITATION_ACCEPT_RATE_LIMIT_WINDOW_SECONDS`.

Se for necessario salt/HMAC especifico, adicionar `RATE_LIMIT_HASH_SECRET` somente no backend. Alternativa inicial: usar segredo backend ja existente, sem expor no frontend.

## 6. Contratos de API

Os endpoints devem seguir o padrao atual de FastAPI, schemas Pydantic, `AppError` e autorizacao no service.

### 6.1. Owner comments

`GET /reimbursements/claims/{claim_id}/comments`

- Auth: owner JWT.
- Query: `limit`, `cursor`.
- Retorno: lista paginada de comentarios sanitizados.
- Autorizacao: claim deve pertencer ao owner.
- Erros: `401`, `404`, `422`.

`POST /reimbursements/claims/{claim_id}/comments`

- Auth: owner JWT.
- Payload: `{ "body": "texto" }`.
- Retorno: comentario criado.
- Autorizacao: claim deve pertencer ao owner.
- Regras: body texto puro, nao vazio, ate limite configurado/schema.
- Eventos: `comment_created`, sem gravar o corpo no evento.
- Erros: `400`, `401`, `404`, `422`.

`DELETE /reimbursements/claims/{claim_id}/comments/{comment_id}`

- Auth: owner JWT.
- Retorno: comentario marcado como excluido ou resposta de sucesso idempotente.
- Autorizacao: owner pode moderar qualquer comentario do proprio claim.
- Eventos: `comment_deleted`, sem corpo do comentario.
- Erros: `401`, `404`, `409`, `422`.

### 6.2. Guest comments

`GET /reimbursements/guest/claims/{claim_id}/comments`

- Auth: guest autenticado via Supabase Auth.
- Retorno: comentarios do claim compartilhado.
- Autorizacao: membership ativa, contato vinculado a claim e status compartilhavel.
- Erros: `401`, `404`, `422`.

`POST /reimbursements/guest/claims/{claim_id}/comments`

- Auth: guest.
- Payload: `{ "body": "texto" }`.
- Retorno: comentario criado.
- Autorizacao: membership ativa.
- Eventos: `comment_created`.
- Erros: `400`, `401`, `404`, `422`.

`DELETE /reimbursements/guest/claims/{claim_id}/comments/{comment_id}`

- Auth: guest.
- Retorno: comentario excluido logicamente.
- Autorizacao: guest so exclui comentario proprio.
- Eventos: `comment_deleted`.
- Erros: `401`, `404`, `409`, `422`.

### 6.3. Schema de resposta

O guest e o owner recebem somente:

- `id`;
- `claim_id`;
- `author_role`;
- `author_label`;
- `is_mine`;
- `body`;
- `created_at`;
- `updated_at`, se existir no futuro;
- `deleted_at` somente se a UI decidir exibir marcador de exclusao; padrao: nao listar excluidos.

Nao retornar:

- `owner_user_id`;
- e-mail;
- token;
- `token_hash`;
- `auth_user_id` de terceiros;
- `storage_path`;
- dados bancarios;
- payload completo da transacao;
- metadados internos de eventos.

## 7. Regras de Autorizacao

Owner:

- pode listar comentarios de qualquer claim proprio;
- pode comentar em claim proprio em qualquer status;
- pode excluir logicamente comentarios proprios e de guests no proprio claim;
- nao pode acessar claims de outro owner.

Guest:

- precisa ter membership ativa;
- so acessa claims vinculadas ao contato da membership;
- nao acessa draft nao compartilhado;
- perde acesso imediatamente apos revogacao;
- pode comentar apenas claims compartilhadas com ele;
- pode excluir apenas comentario proprio;
- nao acessa dados internos do owner.

Status de claim:

- guest pode comentar em claims compartilhadas como `sent`, `acknowledged`, `disputed`, `canceled` e futuros status compartilhaveis;
- guest nao comenta em `draft`;
- claim cancelada preserva historico e pode aceitar comentario somente se o produto quiser permitir comunicacao pos-cancelamento. Recomendacao inicial: permitir leitura e comentario enquanto membership estiver ativa, pois contestacoes podem exigir fechamento.

Arquivos:

- comentarios nao alteram a politica de anexos;
- anexos continuam compartilhados apenas por `reimbursement_claim_attachments`;
- signed URL continua exigindo membership ativa ou owner;
- revogacao bloqueia novas signed URLs.

## 8. Rate Limiting de Convites

Endpoint prioritario: aceite de convite.

Fluxo recomendado:

1. receber token bruto no endpoint;
2. calcular `token_hash`;
3. calcular `ip_hash`;
4. consultar tentativas dentro da janela;
5. se excedeu limite, registrar tentativa bloqueada e retornar `429`;
6. executar aceite atomico atual;
7. registrar sucesso ou falha sem token bruto;
8. retornar mensagem publica neutra em falhas de token, expiracao, revogacao ou e-mail.

Configuracao inicial recomendada:

- habilitado em dev/prod por env;
- max attempts configuravel;
- window seconds configuravel;
- testes com valores pequenos e determinismo por injecao de relogio ou janela curta.

Trade-off:

- PostgreSQL adiciona uma tabela simples e evita inconsistencia entre instancias;
- Redis nao e necessario neste estagio;
- in-memory e aceitavel apenas para testes unitarios/local, mas nao como protecao principal em producao.

## 9. Revisao RLS e Autorizacao

O frontend usa o backend FastAPI como camada de acesso. Ainda assim, como Supabase expõe Data API quando a chave anon e conhecida, a revisao RLS precisa cobrir risco de acesso direto.

Tabelas a auditar:

- `reimbursement_claims`;
- `reimbursement_items`;
- `reimbursement_events`;
- `reimbursement_invitations`;
- `reimbursement_memberships`;
- `reimbursement_claim_attachments`;
- `reimbursement_comments`;
- `stored_files`;
- `transaction_attachments`;
- `transactions`;
- tabelas auxiliares de rate limit.

Classificacao esperada:

- backend com service role pode acessar e validar regras no service;
- frontend nunca recebe service role;
- Data API publica deve ser bloqueada por RLS ou policies restritivas;
- guests so podem ver claims, items, attachments e comments explicitamente autorizados via membership ativa;
- rate limit attempts nao devem ser expostos pela Data API.

Entrega da auditoria:

- documentar policies necessarias;
- se for preciso, criar migration versionada com RLS/policies;
- validar em PostgreSQL local;
- nao aplicar policies em Supabase remoto sem aprovacao explicita.

## 10. Tratamento de Erros

Mapear erros esperados para `AppError`, evitando `UNEXPECTED_APP_ERROR`.

Casos obrigatorios:

- claim inexistente ou inacessivel: `404` neutro;
- guest sem membership ativa: `404` neutro ou `403` quando a existencia ja for conhecida pelo proprio fluxo;
- comentario vazio: `400`;
- comentario acima do limite: `400` ou `422`;
- comentario excluido: sucesso idempotente ou `409`, conforme implementacao;
- token invalido/expirado/revogado/e-mail diferente: erro publico neutro;
- rate limit: `429`;
- erro de infraestrutura: `503` ou `500` com log redigido.

Logs nunca devem conter:

- token bruto;
- JWT;
- service role;
- senha;
- URL assinada completa;
- corpo completo de comentario se contiver dado financeiro sensivel;
- payload financeiro bruto.

## 11. Protecao Contra API URL Ausente

Arquivos a revisar:

- `frontend/src/lib/api.ts`;
- `frontend/src/lib/server-api.ts`.

Comportamento desejado:

- desenvolvimento local pode usar `http://127.0.0.1:8000`;
- Vercel Preview e Production devem falhar claramente se `NEXT_PUBLIC_API_URL` estiver ausente;
- builds remotos nao devem cair silenciosamente em localhost;
- erro deve explicar a variavel obrigatoria;
- documentar em `docs/environments.md` e `docs/deploy-checklist.md`.

Implementacao proposta na Etapa D:

- centralizar resolucao da URL em helper pequeno;
- permitir fallback local somente quando `NODE_ENV=development` e nao houver indicio de ambiente remoto;
- adicionar teste simples ou validacao de build/script para garantir erro claro em ambiente remoto simulado.

Se o impacto for maior que o previsto, registrar como tarefa separada e nao misturar com comments/rate limit.

## 12. Interface

Owner:

- adicionar secao "Comentarios" no detalhe de uma cobranca;
- listar comentarios em ordem cronologica;
- textarea com contador;
- botao de envio com loading;
- estado vazio;
- tratamento de erro inline/toast;
- exclusao com dialogo shadcn, sem `window.confirm`;
- atualizacao da lista sem recarregar a pagina inteira.

Guest:

- adicionar secao equivalente no portal `/guest/reimbursements`;
- usar o shell guest existente;
- nao expor rotas owner-only;
- labels seguros:
  - "Voce" para comentario do usuario atual;
  - "Titular" para owner no portal guest;
  - nome do contato ou "Responsavel" no owner view para comentario guest.

Acessibilidade:

- foco gerenciado em dialogos;
- suporte a teclado;
- `aria-label` em acoes;
- mensagens de erro associadas ao textarea;
- contador de caracteres legivel.

## 13. Estrategia de Migrations

Regras:

- nao editar `001` a `008`;
- criar migrations incrementais;
- nao executar migrations automaticamente em ambiente remoto;
- validar primeiro em PostgreSQL local;
- aplicar em Supabase Dev apenas apos aprovacao;
- aplicar em Production somente no ciclo de release.

Ordem proposta:

1. `009_reimbursement_comments.sql`;
2. `010_reimbursement_invitation_accept_rate_limits.sql`;
3. `011_reimbursements_rls_policies.sql`, somente se a auditoria RLS demandar policies nesta fundacao.

Rollback:

- migrations aditivas podem permanecer sem uso se o codigo for revertido;
- rate limit pode ser desligado por env;
- comments podem ser escondidos por UI/API se necessario;
- se RLS causar impacto, usar migration de rollback explicita para ajustar policies, nao alterar manualmente em producao.

## 14. Estrategia de Testes

Backend:

- owner cria comentario;
- guest autorizado cria comentario;
- guest sem membership;
- guest revogado;
- claim de outro owner;
- claim nao compartilhado;
- comentario vazio;
- comentario acima do limite;
- listagem cronologica;
- paginacao;
- exclusao pelo autor;
- exclusao pelo owner;
- exclusao por usuario nao autorizado;
- comentario excluido nao aparece;
- eventos de auditoria sem body sensivel;
- rate limit de convite;
- limite desativado;
- janela expirada;
- token invalido;
- token expirado;
- token revogado;
- ausencia de token bruto em respostas/logs testaveis;
- signed URLs continuam protegidas;
- attachments compartilhados e nao compartilhados continuam corretos.

PostgreSQL real:

- comments persistidos com constraints e indices;
- guest/owner isolation;
- accept invitation rate limit usando conexoes reais;
- concorrencia de aceite continua atomica;
- policies/RLS, se criadas, bloqueiam acesso direto indevido.

Frontend/E2E:

- owner envia comentario;
- guest envia comentario;
- lista atualiza sem refresh completo;
- estado vazio;
- erro de envio;
- exclusao com dialogo;
- guest sem acesso;
- guest revogado perde comentarios;
- convite com rate limit;
- login/logout segue funcionando;
- dashboard e modulos existentes sem regressao;
- build remoto sem API URL falha claramente, se a protecao for implementada nesta fundacao.

Comandos de validacao:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest
```

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -m postgres
```

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
npm.cmd run e2e
```

## 15. Rollout

Sequencia recomendada:

1. implementar e validar localmente;
2. aplicar migrations em PostgreSQL local;
3. rodar testes unitarios e PostgreSQL;
4. validar UI owner/guest local;
5. aplicar migrations em Supabase Dev apos aprovacao;
6. deploy Render Dev e Vercel Preview;
7. smoke test manual em Dev:
   - owner comenta;
   - guest comenta;
   - guest revogado perde acesso;
   - convite com tentativas repetidas retorna `429`;
   - signed URLs seguem protegidas;
8. preparar release para Production com checklist.

## 16. Riscos e Mitigacoes

Risco: guest acessar comentario de claim nao compartilhado.

- Mitigacao: autorizacao no service, testes owner A/B, membership ativa obrigatoria e RLS quando aplicavel.

Risco: comentarios vazarem dados internos.

- Mitigacao: response schema sanitizado e eventos sem body.

Risco: token bruto vazar em logs.

- Mitigacao: nunca logar payload de aceite, persistir somente hash, testes de contrato.

Risco: rate limit in-memory falhar em multiplas instancias.

- Mitigacao: usar PostgreSQL como fonte do limite.

Risco: RLS incompleta quebrar fluxo legitimo.

- Mitigacao: validar local/dev, service role no backend, rollout separado e rollback por migration.

Risco: fallback de API URL quebrar desenvolvimento local.

- Mitigacao: permitir fallback apenas em desenvolvimento local e documentar variavel obrigatoria para remoto.

Risco: comentario virar canal de HTML/script.

- Mitigacao: texto puro, render sem `dangerouslySetInnerHTML`, validacao de tamanho e conteudo.

## 17. Criterios de Aceite

A Fundacao 3.5 estara concluida quando:

- comentarios funcionarem para owner;
- comentarios funcionarem para guest autorizado;
- guest sem acesso ou revogado nao listar, criar ou excluir comentarios;
- exclusao logica estiver auditavel;
- owner puder moderar comentarios do proprio claim;
- rate limiting de aceite estiver ativo e testado;
- token bruto nunca for persistido ou logado;
- erros de dominio retornarem status HTTP corretos;
- RLS/autorizacao estiverem revisados e documentados;
- signed URLs continuarem protegidas;
- migrations forem incrementais e reproduziveis;
- documentacao estiver atualizada;
- todos os testes obrigatorios passarem;
- nenhum secret for adicionado ao Git;
- pagamentos, Telegram, OCR, audio, inbox, filas e Fundacao 4 nao tiverem sido iniciados.

## 18. Rollback

Rollback de codigo:

- reverter rotas, services, UI e client API da Fundacao 3.5;
- manter migrations aditivas sem uso, se ja aplicadas;
- desabilitar rate limit por `INVITATION_ACCEPT_RATE_LIMIT_ENABLED=false` se houver falso positivo critico.

Rollback de banco:

- preferir migrations reversiveis apenas em ambiente de desenvolvimento;
- em producao, evitar drop imediato de tabelas com dados de comunicacao;
- se RLS causar impacto, aplicar migration corretiva de policy em vez de alteracao manual.

Rollback operacional:

- manter acesso guest anterior funcionando sem comentarios;
- validar acknowledge/dispute/invitations/attachments apos rollback;
- revisar logs por `401`, `403`, `429` e `500`.

## 19. Plano de Execucao por Etapas

### Etapa A - Plano

- confirmar branch `dev`;
- sincronizar com `origin/dev`;
- analisar codigo atual;
- registrar este plano;
- parar antes de implementar.

### Etapa B - Backend

- criar migrations novas;
- adicionar schemas;
- adicionar repository methods local e PostgreSQL;
- implementar service de comments;
- implementar rate limit;
- mapear erros;
- adicionar testes backend e PostgreSQL.

### Etapa C - Frontend

- criar componente compartilhado de comentarios;
- integrar owner claim detail;
- integrar guest portal;
- adicionar dialogo de exclusao;
- adicionar client API/types;
- adicionar E2E.

Status em 2026-07-13:

- componente compartilhado `ReimbursementComments` criado para owner e guest;
- owner claim detail exibe, cria e exclui comentarios sem refresh completo;
- portal guest exibe, cria e exclui apenas comentarios proprios;
- confirmacao de exclusao usa dialog proprio, sem `window.confirm`;
- comentarios sao texto puro, com trim, limite de 2000 caracteres e contador;
- erros esperados `401`, `403`, `404`, `409`, `422` e `429` sao mapeados para mensagens amigaveis no frontend;
- client API tipado consome `GET`, `POST` e `DELETE /reimbursements/claims/{claim_id}/comments`;
- E2E cobre fluxo owner, fluxo guest, exclusao, rate limit visual e ausencia de HTML renderizado;
- nenhum backend, migration ou policy RLS foi alterado nesta etapa.

### Etapa D - Auditoria e Fechamento

- revisar RLS/policies;
- revisar signed URLs e attachments;
- revisar API URL fallback;
- atualizar `.env.example`, `.env.production.example`, `docs/environments.md`, `docs/deploy-checklist.md`, `task.md`, `plan.md` e `output.md`;
- rodar validacoes completas;
- documentar pendencias.

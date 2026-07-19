# Financy - Plano de Workspaces

## Objetivo

Planejar a separacao entre identidade (`user_id`) e escopo financeiro (`workspace_id`) antes de abrir o Financy para multiusuario publico, familia, negocio pequeno, contador ou operacao self-hosted com mais de um contexto financeiro.

Este documento e planejamento. Ele nao cria migrations, nao altera APIs e nao muda regras financeiras atuais.

## Decisao recomendada

Manter Supabase Auth como fonte de identidade e introduzir `workspace_id` como tenant financeiro.

- `user_id`: usuario autenticado, ator de auditoria e dono de acoes.
- `workspace_id`: escopo onde dados financeiros vivem e sao compartilhados.
- `profiles.id`: continua espelhando o usuario Supabase.
- Toda entidade financeira nova deve pertencer a exatamente um workspace.
- Toda acao sensivel deve derivar `user_id` da sessao e `workspace_id` do contexto validado no backend.

O usuario atual ganha um workspace pessoal padrao. Isso preserva a experiencia single-user e permite migrar sem exigir que o produto exponha gestao de workspaces de imediato.

## Por que nao fazer agora diretamente

O Financy ja esta protegido por `user_id` e ainda tem pendencias operacionais de producao, storage, RLS e performance. Adicionar `workspace_id` mexe em quase todos os dominios. A implementacao deve vir depois de:

- auth e isolamento por usuario estarem validados em producao;
- RLS atual estar revisado;
- repository Postgres estar menos concentrado;
- smoke multiusuario real estar documentado;
- estrategia de migracao estar testada em banco descartavel.

## Modelo inicial

### `workspaces`

Campos recomendados:

- `id uuid primary key`
- `name text not null`
- `kind text not null default 'personal'`
- `created_by_user_id uuid references profiles(id)`
- `default_currency text default 'BRL'`
- `locale text`
- `status text default 'active'`
- `created_at timestamptz`
- `updated_at timestamptz`

`kind` inicial:

- `personal`
- `family`
- `small_business`
- `accountant`

Comecar usando apenas `personal` na UI.

### `workspace_members`

Campos recomendados:

- `id uuid primary key`
- `workspace_id uuid not null references workspaces(id)`
- `user_id uuid not null references profiles(id)`
- `role text not null`
- `invited_by_user_id uuid references profiles(id)`
- `status text not null default 'active'`
- `joined_at timestamptz`

Constraint recomendada:

- unico ativo por `(workspace_id, user_id)`.

## Papeis iniciais

`owner`:

- gerencia workspace, membros, configuracoes, dados financeiros e integracoes.
- pode excluir/inativar dados conforme regras de dominio.

`editor`:

- cria e edita dados financeiros do workspace.
- nao gerencia membros, secrets, integracoes globais ou ownership.

`viewer`:

- leitura de dados financeiros.
- nao cria transacoes, regras, importacoes, sync, comentarios de owner ou acoes sensiveis.

Regras:

- Backend deve validar papel por endpoint.
- Frontend pode esconder controles, mas autorizacao real fica no backend.
- A resposta para workspace inexistente ou sem acesso deve preferir `404` para reduzir enumeracao.

## Resolucao do workspace atual

Ordem recomendada:

1. Header `X-Workspace-Id`, quando a UI ja tiver seletor.
2. Workspace pessoal padrao do usuario autenticado.
3. Erro `404` se nao existir workspace acessivel.

O backend deve retornar um objeto de contexto:

- `user_id`
- `workspace_id`
- `role`
- `can_write`
- `is_owner`

Endpoints de escrita usam contexto write-gated. Endpoints administrativos usam owner-gated.

## Entidades impactadas

Adicionar `workspace_id` e escopo por workspace:

- `accounts`
- `cards`
- `card_statements`
- `transactions`
- `classification_rules`
- `import_files`
- `import_batches`
- `import_preview_items`
- `stored_files`
- `transaction_attachments`
- `recurring_items`
- `recurring_item_transactions`
- `financial_goals`
- `budgets`
- `open_finance_items`
- `open_finance_account_links`
- `open_finance_transaction_links`
- `open_finance_sync_runs`
- `reimbursement_contacts`
- `reimbursement_claims`
- `reimbursement_items`
- `reimbursement_events`
- `reimbursement_comments`
- `reimbursement_invitations`
- `reimbursement_memberships`
- futuras entidades de payees/merchant aliases

Categorias precisam de modelo misto:

- categorias de sistema continuam globais (`workspace_id is null`, `user_id is null`, `is_system = true`);
- categorias customizadas passam a pertencer a um workspace;
- se for necessario historico de autoria, manter `created_by_user_id`.

## `user_id` depois do workspace

`user_id` nao desaparece. Ele muda de papel:

- em entidades financeiras, pode virar `created_by_user_id` ou `updated_by_user_id`;
- em tabelas de auditoria, continua sendo ator;
- em convites/memberships, representa pessoa autenticada;
- em integracoes owner-only, ajuda a identificar quem configurou ou disparou sync.

Tenant principal deve ser `workspace_id`, nao `user_id`.

## Migracao de dados existentes

Fase segura:

1. Fazer backup do banco.
2. Criar tabela `workspaces`.
3. Criar tabela `workspace_members`.
4. Para cada `profiles.id` com dados, criar workspace pessoal.
5. Criar membership `owner` para o proprio usuario.
6. Adicionar `workspace_id` nullable nas tabelas impactadas.
7. Popular `workspace_id` usando o workspace pessoal do `user_id` atual.
8. Validar contagens antes/depois por tabela.
9. Adicionar `not null` nas tabelas onde todos os registros foram migrados.
10. Adicionar indexes por `workspace_id`.
11. Atualizar backend para filtrar por workspace.
12. So depois remover dependencia de `user_id` como tenant.

Rollback:

- manter `user_id` durante a primeira fase;
- nao apagar colunas antigas no mesmo lote;
- feature flag para esconder seletor de workspace;
- scripts de migracao devem ser idempotentes e recusarem banco remoto sem autorizacao explicita.

## Impacto em RLS Supabase

RLS atual por `user_id = auth.uid()` precisara evoluir para membership.

Direcao recomendada:

- `profiles`: usuario acessa proprio perfil.
- `workspaces`: usuario acessa workspaces onde possui membership ativo.
- `workspace_members`: membro acessa linhas do proprio workspace; apenas owner gerencia.
- entidades financeiras: acesso se `exists workspace_members where workspace_id = row.workspace_id and user_id = auth.uid() and status = 'active'`.
- escrita exige papel `owner` ou `editor`.
- leitura aceita `owner`, `editor` ou `viewer`.
- categorias de sistema continuam legiveis por usuarios autenticados.

Como o backend usa service role em alguns fluxos, RLS deve ser defesa adicional e nao substituir autorizacao no FastAPI.

## Impacto em ressarcimentos

O dominio atual usa `owner_user_id` para separar titular e guest. Com workspaces:

- cobrancas devem pertencer ao workspace do owner;
- `owner_user_id` deve continuar como ator/responsavel pelo envio;
- guest continua acessando por membership de ressarcimento, nao por membership geral do workspace;
- payload guest nao deve ganhar acesso ao workspace financeiro;
- revogacao de membership de ressarcimento deve continuar bloqueando guest mesmo se ele for membro de outro workspace;
- se uma cobranca for criada a partir de transacao, a transacao e a cobranca devem ter o mesmo `workspace_id`.

Recomendacao: nao migrar ressarcimentos para workspace antes de congelar a regra de guest. Primeiro adicionar `workspace_id` mantendo `owner_user_id`; depois avaliar simplificacao.

## Impacto em Open Finance

Open Finance deve ser configurado por workspace.

- `open_finance_items.workspace_id` define quem ve a conexao.
- Apenas `owner` pode criar/revogar conexao.
- `editor` pode disparar sync somente se produto permitir explicitamente.
- `viewer` nunca dispara sync.
- Secrets continuam somente no backend.
- Sync runs registram `triggered_by_user_id`.

Enquanto o produto permanecer owner-only, manter a flag atual e tratar workspace como preparacao interna.

## Impacto no frontend

Fase 1:

- sem seletor visivel;
- backend resolve workspace pessoal padrao;
- API client nao envia `X-Workspace-Id`.

Fase 2:

- carregar lista de workspaces no shell autenticado;
- salvar workspace selecionado no estado local;
- enviar `X-Workspace-Id` em todas as chamadas protegidas;
- esconder acoes por papel;
- tratar `403` como papel insuficiente e `404` como workspace indisponivel.

## Testes obrigatorios

Backend:

- usuario recebe workspace pessoal no bootstrap/migracao;
- usuario A nao acessa workspace B;
- viewer nao escreve;
- editor escreve transacao, mas nao gerencia membros;
- owner gerencia membros;
- categoria de sistema segue legivel;
- categoria customizada e isolada por workspace;
- importacao confirma transacoes no workspace correto;
- Open Finance sync grava no workspace correto;
- ressarcimento nao compartilha dados fora do workspace;
- RLS reproduz as mesmas regras em banco descartavel.

Frontend:

- usuario sem workspace mostra estado seguro;
- troca de workspace recarrega dados;
- acoes somem para viewer;
- erro `403` tem feedback claro;
- chamadas incluem `X-Workspace-Id` quando houver workspace selecionado.

## Ordem de implementacao recomendada

1. Criar migrations de `workspaces` e `workspace_members`.
2. Criar servico de contexto de workspace no backend.
3. Criar script de migracao local/staging para workspace pessoal.
4. Adicionar `workspace_id` em categorias customizadas e regras.
5. Adicionar `workspace_id` em contas/cartoes/transacoes/faturas.
6. Adicionar `workspace_id` em imports e arquivos.
7. Adicionar `workspace_id` em planejamento.
8. Adicionar `workspace_id` em Open Finance.
9. Adicionar `workspace_id` em ressarcimentos mantendo `owner_user_id`.
10. Atualizar RLS para membership.
11. Criar UI minima de seletor/gestao, atras de feature flag.

## Riscos

- Misturar `user_id` e `workspace_id` pode criar vazamento se uma query filtrar pelo campo errado.
- Migrar tudo em um unico lote aumenta risco de perda de dados.
- RLS por membership e mais complexa e precisa de testes reais.
- Portal guest de ressarcimentos tem autorizacao propria e nao deve herdar acesso financeiro sem querer.
- Open Finance por workspace precisa de cuidado com secrets e consentimentos.
- Relatorios podem duplicar dados se uma transacao compartilhada aparecer em mais de um contexto.

## Criterio de pronto para iniciar implementacao

- Este plano revisado.
- `PostgresRepository` menos concentrado ou com fachada clara por dominio.
- Backup e restore testados.
- Smoke multiusuario por `user_id` atual passando.
- RLS atual revisada.
- Ambiente descartavel para migration com dados representativos.

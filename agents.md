# Financy - Agents da Fase 3

## Objetivo

Dividir a Fase 3, autenticacao e isolamento de usuarios, em frentes pequenas e verificaveis.

## Regras gerais

- Nao mudar regras financeiras sem necessidade.
- Nao aceitar `user_id` do cliente para entidades user-owned.
- Manter `/health` publico.
- Proteger rotas financeiras.
- Usar Supabase Auth como estrategia recomendada.
- Manter `DEV_USER_ID` apenas como bypass local/teste explicito.
- Preferir `404` para tentativa de acessar recurso de outro usuario.
- Adiar RLS ate backend auth e testes multiusuario passarem.
- Rodar validacoes da area alterada.

## Agent 1 - Auditoria de Auth Atual

Missao:

Mapear o uso atual de `DEV_USER_ID`, `get_user_id` e `user_id`.

Responsabilidades:

- Revisar `backend/app/api/deps.py`.
- Mapear rotas que usam `Depends(get_user_id)`.
- Mapear entidades user-owned.
- Mapear frontend API client.
- Identificar pontos que aceitam IDs relacionados.

Entregas:

- mapa de rotas protegidas;
- mapa de entidades por ownership;
- riscos de acesso cruzado.

Validacao:

- plano documentado em `docs/auth-user-isolation-plan.md`.

## Agent 2 - Backend Auth Foundation

Missao:

Implementar a base de autenticacao no backend.

Responsabilidades:

- Adicionar settings de auth.
- Criar modelo/contexto `CurrentUser`.
- Criar dependencia `get_current_user`.
- Validar JWT Supabase.
- Manter bypass local/teste explicito.
- Atualizar `get_user_id` para derivar do usuario atual.

Entregas:

- dependencia de auth;
- testes de token ausente/invalido/valido;
- testes de bypass.

Validacao:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

## Agent 3 - Endpoint Protection

Missao:

Garantir que todas as rotas financeiras exigem usuario autenticado.

Responsabilidades:

- Proteger transactions, imports, statements, categories, accounts, cards e classification-rules.
- Manter `/health` publico.
- Padronizar `401`, `403` e `404`.
- Atualizar OpenAPI com bearer auth quando cabivel.

Entregas:

- rotas protegidas;
- testes de endpoint sem token;
- testes de endpoint com usuario autenticado.

Validacao:

- request anonimo falha nas rotas financeiras;
- `/health` continua respondendo.

## Agent 4 - User Isolation Hardening

Missao:

Impedir acesso cruzado entre usuarios.

Responsabilidades:

- Validar ownership em create/update com IDs relacionados.
- Garantir que summaries agregam apenas dados do usuario atual.
- Bloquear mutacao comum de categorias de sistema.
- Garantir import preview/confirm por usuario.
- Particionar novos uploads por usuario.

Entregas:

- validacoes de ownership;
- testes com usuario A e usuario B;
- regras claras para categoria de sistema.

Validacao:

- usuario A nao acessa nem referencia recursos do usuario B.

## Agent 5 - Frontend Auth Shell

Missao:

Adicionar experiencia minima de autenticacao no frontend.

Responsabilidades:

- Configurar Supabase client.
- Criar login.
- Criar logout.
- Criar provider/contexto de sessao.
- Proteger rotas da aplicacao.
- Adicionar Bearer token ao API client.
- Tratar `401`.

Entregas:

- login/logout funcionais;
- API client autenticado;
- telas protegidas.

Validacao:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

## Agent 6 - Data Ownership Migration

Missao:

Preparar migracao dos dados atuais do `DEV_USER_ID` para usuario real.

Responsabilidades:

- Criar checklist/script de reassociacao.
- Exigir backup.
- Atualizar tabelas user-owned em ordem segura.
- Preservar categorias de sistema.
- Validar contagens.
- Documentar rollback.

Entregas:

- script ou checklist operacional;
- relatorio de riscos;
- rollback documentado.

Validacao:

- dry-run mostra contagens;
- apply em ambiente local/teste preserva dados.

## Agent 7 - RLS Preparation

Missao:

Preparar Row Level Security sem ativar antes da hora.

Responsabilidades:

- Criar draft de policies.
- Testar policies em banco descartavel.
- Definir comportamento de service role para scripts.
- Documentar ordem de ativacao.

Entregas:

- migration draft de RLS;
- checklist de ativacao;
- riscos documentados.

Validacao:

- policies passam em smoke test com dois usuarios antes de ativacao real.

## Agent 8 - QA e Release Auth

Missao:

Validar a Fase 3 ponta a ponta.

Responsabilidades:

- Rodar testes backend.
- Rodar testes backend PostgreSQL.
- Rodar validações frontend.
- Executar smoke test com dois usuarios.
- Registrar pendencias e riscos.

Entregas:

- resultado de validacoes;
- checklist final;
- lista de riscos remanescentes.

Validacao:

- todas as validacoes obrigatorias passam ou possuem justificativa.

## Sequencia recomendada

1. Agent 1 - Auditoria de Auth Atual.
2. Agent 2 - Backend Auth Foundation.
3. Agent 3 - Endpoint Protection.
4. Agent 4 - User Isolation Hardening.
5. Agent 5 - Frontend Auth Shell.
6. Agent 6 - Data Ownership Migration.
7. Agent 7 - RLS Preparation.
8. Agent 8 - QA e Release Auth.

## Handoff esperado

Cada agent deve entregar:

- arquivos alterados;
- decisoes tomadas;
- comandos executados;
- resultados;
- riscos ou pendencias.

## Definicao de pronto geral

A Fase 3 esta pronta quando:

- auth real esta implementada;
- frontend tem login/logout;
- backend deriva `user_id` de token valido;
- rotas financeiras exigem auth;
- isolamento entre usuarios esta testado;
- `DEV_USER_ID` nao e fallback silencioso;
- migracao de propriedade esta documentada;
- RLS esta preparado para fase posterior;
- validacoes obrigatorias passam.

# Financy - Especificacao da Fase 3: Autenticacao e Isolamento de Usuarios

## Contexto

O Financy usa atualmente `DEV_USER_ID` como usuario unico local. A Fase 2 consolidou PostgreSQL e manteve `profiles` como tabela de identidade da aplicacao. A Fase 3 deve introduzir autenticacao real, login no frontend e isolamento de dados por usuario.

## Objetivo da especificacao

Definir requisitos tecnicos, criterios de aceite e limites para implementar autenticacao e isolamento sem alterar o comportamento financeiro validado.

## Requisitos funcionais

### RF01 - Provedor de autenticacao

O projeto deve usar Supabase Auth como provedor recomendado.

Requisitos:

- frontend autentica via Supabase;
- backend valida JWT Supabase;
- `profiles.id` representa o ID do usuario autenticado;
- `user_id` usado nas entidades vem do `sub` do token.

### RF02 - Usuario atual no backend

O backend deve substituir o retorno fixo de `settings.dev_user_id` por contexto autenticado.

Requisitos:

- criar dependencia `get_current_user`;
- criar modelo/contexto de usuario atual;
- manter helper de `user_id` para reduzir churn nas rotas;
- validar token Bearer;
- retornar `401` para token ausente/invalido.

### RF03 - Bypass local/teste

O uso de `DEV_USER_ID` deve continuar apenas como bypass controlado.

Requisitos:

- env explicita, por exemplo `AUTH_DEV_BYPASS=true`;
- permitido apenas em ambiente `local` ou `test`;
- proibido como fallback silencioso em producao;
- coberto por testes.

### RF04 - Rotas protegidas

Todas as rotas financeiras devem exigir autenticacao.

Rotas protegidas:

- `/transactions`
- `/imports`
- `/statements`
- `/categories`
- `/accounts`
- `/cards`
- `/classification-rules`

Rota publica:

- `/health`

### RF05 - Isolamento de entidades

Entidades user-owned:

- `accounts`
- `cards`
- `card_statements`
- `transactions`
- `classification_rules`
- `import_files`
- `import_batches`
- `import_preview_items`

Requisitos:

- listagens retornam apenas dados do usuario autenticado;
- get/update/delete nao expõem recursos de outro usuario;
- create/update nao aceitam `user_id` vindo do cliente;
- referencias relacionadas devem pertencer ao mesmo usuario.

### RF06 - Categorias

Categorias possuem comportamento misto.

Requisitos:

- categorias de sistema usam `user_id = null`;
- categorias de usuario usam `user_id = current_user.id`;
- todos podem listar categorias de sistema;
- usuario pode criar/editar/excluir apenas categorias proprias;
- usuario comum nao pode editar/excluir categoria de sistema.

### RF07 - Frontend autenticado

O frontend deve possuir auth shell.

Requisitos:

- Supabase client configurado;
- tela de login;
- logout;
- provider/contexto de sessao;
- protecao de rotas da aplicacao;
- chamadas API com `Authorization: Bearer <access_token>`;
- tratamento de `401`.

### RF08 - Perfil do usuario

`profiles` deve ser mantida como tabela de perfil da aplicacao.

Requisitos:

- criar profile no primeiro request autenticado ou via trigger Supabase;
- `profiles.id` deve ser igual ao ID Supabase Auth;
- `email` e `full_name` podem ser espelhados dos metadados de auth.

### RF09 - Migracao de propriedade

Dados atuais ligados ao `DEV_USER_ID` precisam de estrategia de reassociacao.

Requisitos:

- backup antes de reassociar;
- script/checklist para trocar `user_id` em tabelas user-owned;
- preservar categorias de sistema com `user_id = null`;
- validar contagens antes/depois;
- rollback documentado.

### RF10 - Preparacao para RLS

RLS deve ser planejado como camada posterior.

Requisitos:

- criar draft de policies;
- testar em banco descartavel;
- nao ativar RLS antes de backend auth e testes multiusuario passarem.

## Requisitos nao funcionais

### RNF01 - Compatibilidade

Payloads financeiros atuais devem ser preservados sempre que possivel.

### RNF02 - Seguranca

JWT deve ser validado corretamente:

- assinatura;
- expiracao;
- issuer;
- audience quando aplicavel;
- subject obrigatorio.

### RNF03 - Privacidade

Recursos de outro usuario nao devem vazar por listagem, detalhe, update, delete ou mensagens de erro.

### RNF04 - Testabilidade

Testes devem conseguir rodar com bypass local/teste e com tokens simulados/validos conforme a camada implementada.

### RNF05 - Operacao local

Desenvolvimento local deve continuar possivel sem depender de usuario real quando `AUTH_DEV_BYPASS=true`.

## Criterios de aceite

### CA01 - Backend auth

- request sem token recebe `401` nas rotas financeiras;
- token invalido recebe `401`;
- token valido define `current_user.id`;
- `/health` continua publico;
- bypass local/teste funciona apenas quando explicitamente habilitado.

### CA02 - User isolation

- usuario A nao ve dados do usuario B;
- usuario A nao acessa recurso do usuario B por ID;
- usuario A nao cria recurso vinculado a conta/cartao/fatura do usuario B;
- usuario comum nao altera categoria de sistema.

### CA03 - Frontend auth

- usuario nao autenticado e enviado para login;
- usuario autenticado acessa app;
- logout remove acesso;
- chamadas API enviam Bearer token;
- `401` limpa sessao ou redireciona.

### CA04 - Migracao de propriedade

- existe procedimento para reassociar dados do `DEV_USER_ID`;
- procedimento exige backup;
- contagens sao validadas;
- rollback e claro.

### CA05 - Validacoes

- backend pytest passa;
- backend PostgreSQL pytest passa;
- frontend typecheck/lint/build passam;
- smoke test com dois usuarios passa.

## Nao objetivos

- Nao construir auth propria.
- Nao armazenar senhas no backend.
- Nao ativar RLS antes de testar auth no backend.
- Nao criar painel admin completo.
- Nao mudar regras financeiras.
- Nao alterar parser/importacao por motivo de auth, exceto ownership.

## Referencia detalhada

Plano tecnico detalhado:

- `docs/auth-user-isolation-plan.md`

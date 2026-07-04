# Financy - Plano da Fase 3: Autenticacao e Isolamento de Usuarios

## Objetivo

Implementar autenticacao real e isolamento estrito por usuario, substituindo o uso operacional de `DEV_USER_ID` por identidade autenticada.

A Fase 3 deve manter os contratos financeiros atuais, preservar o backend PostgreSQL validado na Fase 2 e preparar a base para uso privado com usuarios reais.

## Resultado esperado

Ao final da Fase 3, o projeto deve ter:

- autenticacao real baseada em Supabase Auth;
- backend validando JWT e derivando `user_id` do token;
- frontend com login/logout e sessao autenticada;
- chamadas API enviando `Authorization: Bearer <token>`;
- rotas financeiras protegidas;
- isolamento entre usuarios testado;
- plano de migracao do `DEV_USER_ID` para usuario real;
- categorias de sistema protegidas contra mutacao comum;
- preparacao documentada para RLS;
- `DEV_USER_ID` restrito a bypass local/teste explicito.

## Escopo

### Incluido

- Configuracao de autenticacao.
- Dependencia backend para usuario autenticado.
- Validacao de JWT Supabase no backend.
- Bypass local/teste controlado por env.
- Protecao de endpoints financeiros.
- Frontend auth shell: login, logout, sessao e rotas protegidas.
- Envio de Bearer token nas chamadas API.
- Testes de autenticacao e isolamento entre usuarios.
- Plano/script de reassociacao de dados do `DEV_USER_ID`.
- Hardening de referencias cruzadas por usuario.
- Documentacao operacional da Fase 3.

### Fora do escopo

- Reescrever regras financeiras.
- Alterar payloads financeiros sem necessidade.
- Criar painel admin completo.
- Ativar RLS antes de validar auth no backend.
- Criar auth propria com senha/token customizados.
- Trocar PostgreSQL por outro storage.
- Mudancas grandes de UX fora de login/sessao.

## Estado atual observado

### Backend

- `backend/app/api/deps.py` centraliza o usuario atual em `get_user_id()`.
- Hoje `get_user_id()` retorna `settings.dev_user_id`.
- Todas as rotas financeiras usam `Depends(get_user_id)` direta ou indiretamente.
- Repositories ja recebem `user_id` na maioria dos metodos.
- PostgreSQL ja possui tabela `profiles`.
- Dados existentes estao associados ao `DEV_USER_ID`.

### Frontend

- `frontend/src/lib/api.ts` centraliza chamadas para a API.
- O client usa `NEXT_PUBLIC_API_URL`.
- Nao envia header `Authorization`.
- Nao existe tela de login/logout.
- Nao existe provider de sessao.

### Banco

- Entidades de usuario possuem `user_id`.
- Categorias de sistema usam `user_id = null`.
- RLS ainda nao esta ativo.
- Uploads possuem `import_files.user_id`, mas caminho fisico ainda nao e particionado por usuario.

## Estrategia recomendada

Usar Supabase Auth como provedor de identidade.

Arquitetura alvo:

1. Frontend autentica com Supabase Auth.
2. Frontend obtem `access_token`.
3. Frontend envia `Authorization: Bearer <access_token>` para FastAPI.
4. Backend valida JWT Supabase.
5. Backend extrai `sub` do token e usa como `user_id`.
6. Backend cria/atualiza `profiles` quando necessario.
7. Repositories continuam recebendo `user_id` de contexto autenticado.
8. RLS entra depois, como camada adicional.

Justificativa:

- O schema ja usa `profiles`, alinhado a Supabase.
- Evita implementar armazenamento de senha, reset, refresh token e recuperacao de conta.
- Reduz superficie de seguranca propria.
- Mantem FastAPI como camada de regras de negocio.
- Facilita RLS nas proximas etapas.

## Marcos de execucao

### Marco 1 - Fundacao de auth no backend

Objetivo: substituir o retorno fixo de `DEV_USER_ID` por dependencia autenticada.

Entregas:

- settings de auth;
- modelo de usuario atual;
- dependencia `get_current_user`;
- `get_user_id` derivado do usuario autenticado;
- bypass local/teste explicito;
- testes de token ausente/invalido/bypass.

### Marco 2 - Protecao de endpoints

Objetivo: exigir autenticacao nas rotas financeiras.

Entregas:

- todas as rotas financeiras protegidas;
- `/health` permanece publico;
- respostas `401`, `403` e `404` padronizadas;
- OpenAPI com bearer auth.

### Marco 3 - Frontend auth shell

Objetivo: permitir login real e enviar token para a API.

Entregas:

- Supabase client;
- tela de login;
- logout;
- provider de sessao;
- protecao de rotas;
- API client com Bearer token;
- tratamento de `401`.

### Marco 4 - Isolamento e hardening

Objetivo: impedir vazamento/acesso cruzado entre usuarios.

Entregas:

- validacao de referencias cruzadas;
- bloqueio de mutacao comum em categorias de sistema;
- upload path particionado para novos uploads;
- testes com dois usuarios.

### Marco 5 - Migracao de propriedade

Objetivo: mover dados do `DEV_USER_ID` para um usuario real quando necessario.

Entregas:

- checklist/script de reassociacao;
- backup obrigatorio;
- validacao de contagens;
- rollback documentado.

### Marco 6 - Preparacao de RLS

Objetivo: desenhar e testar politicas RLS sem ativar prematuramente.

Entregas:

- migration draft de RLS;
- testes em banco descartavel;
- decisao de service role para scripts;
- checklist de ativacao.

## Ordem recomendada

1. Criar settings de auth.
2. Criar dependencia backend de usuario autenticado.
3. Adicionar testes de auth basica.
4. Proteger endpoints mantendo payloads atuais.
5. Adicionar frontend Supabase client e login.
6. Enviar Bearer token nas chamadas API.
7. Adicionar testes de isolamento com dois usuarios.
8. Endurecer validacoes de referencias cruzadas.
9. Bloquear mutacao comum de categorias de sistema.
10. Particionar uploads novos por usuario.
11. Criar migracao de propriedade do `DEV_USER_ID`.
12. Preparar RLS em migration separada.
13. Validar smoke test multiusuario.
14. Atualizar documentacao final.

## Validacoes obrigatorias

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Backend PostgreSQL:

```powershell
cd backend
$env:STORAGE_BACKEND='postgres'
$env:DATABASE_URL='postgresql://financy:financy@localhost:5432/financy_test'
.\.venv\Scripts\python.exe -m pytest
```

Frontend:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

Smoke test:

- usuario anonimo recebe `401` nas rotas financeiras;
- `/health` continua publico;
- usuario A cria conta/cartao/transacao;
- usuario B nao ve dados do usuario A;
- usuario B nao acessa IDs do usuario A por URL/API direta;
- categorias de sistema aparecem para ambos;
- categorias de sistema nao sao alteradas por usuario comum;
- login/logout funcionam;
- importacao continua funcionando para usuario autenticado.

## Riscos

- Validacao incorreta de JWT Supabase.
- Dados atuais presos ao `DEV_USER_ID`.
- Frontend perder sessao sem UX clara.
- Scripts locais quebrarem se auth obrigatoria nao tiver bypass controlado.
- RLS ativado antes de o backend estar pronto.
- Referencias cruzadas permitirem vincular recurso de outro usuario.
- Uploads fisicos ainda sem particionamento.
- Categorias de sistema mutaveis por usuarios comuns.

## Mitigacoes

- Validar issuer, assinatura, expiracao e subject do JWT.
- Manter bypass apenas em `local/test` e com env explicita.
- Adicionar testes de dois usuarios antes de considerar pronto.
- Reassociar dados com backup e validacao de contagens.
- Adiar RLS para depois da autenticacao backend.
- Validar ownership em todo create/update que recebe IDs relacionados.
- Particionar novos uploads por usuario.

## Criterio de pronto da Fase 3

A Fase 3 esta pronta quando:

- rotas financeiras exigem autenticacao;
- `user_id` vem do token em ambiente real;
- `DEV_USER_ID` nao e fallback silencioso em producao;
- frontend possui login/logout e envia Bearer token;
- isolamento entre dois usuarios foi testado;
- categorias de sistema estao protegidas;
- migracao do `DEV_USER_ID` esta documentada/testada;
- RLS esta planejado ou preparado sem bloquear a aplicacao;
- validacoes backend/frontend passam.

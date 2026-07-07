# Financy - Runbook de Prontidao de Producao

## Objetivo

Concentrar as tarefas pos-deploy que dependem de decisao operacional ou configuracao em provedores externos.

## PD2 - Storage persistente de uploads

Estado atual:

- O backend usa `UPLOAD_STORAGE_PATH`.
- Em producao, o caminho atual no Render e `.uploads`.
- Esse caminho funciona para uso privado, mas nao e uma garantia forte de persistencia.

Recomendacao:

1. Usar Supabase Storage como primeira opcao, por ja existir Supabase no projeto.
2. Manter o particionamento por usuario: `{user_id}/{file_id}.{ext}`.
3. Salvar no banco apenas o identificador/caminho do objeto.
4. Migrar arquivos antigos antes de trocar a leitura para storage remoto.

Alternativas:

- Cloudflare R2: bom custo e compatibilidade S3.
- Disco persistente Render: simples, mas acopla arquivo ao provedor.

Checklist:

- [ ] Escolher storage definitivo.
- [ ] Criar bucket privado.
- [ ] Definir variaveis do provedor.
- [ ] Implementar adapter de storage.
- [ ] Migrar arquivos existentes.
- [ ] Testar upload, preview e confirmacao de import.
- [ ] Testar rollback para storage anterior.

## PD3 - Backups de producao

Banco:

- Habilitar backup automatico no Supabase.
- Registrar frequencia e retencao.
- Executar um restore em ambiente descartavel antes de considerar pronto.

Uploads:

- Se usar Supabase Storage ou R2, habilitar estrategia de backup/versionamento quando disponivel.
- Se usar disco persistente, criar rotina externa de copia.

Checklist:

- [ ] Confirmar backup automatico do banco.
- [ ] Registrar retencao.
- [ ] Criar backup manual pos-deploy.
- [ ] Testar restore em banco descartavel.
- [ ] Confirmar backup de uploads.
- [ ] Registrar timestamp do ultimo teste de restore.

## PD4 - Rotacao de segredos

Segredos que precisam ser rotacionados porque passaram pelo fluxo de deploy/manual:

- Senha do PostgreSQL.
- `JWT_SECRET`.
- `SUPABASE_SERVICE_ROLE_KEY`.
- Qualquer secret administrativo Supabase.

Ordem recomendada:

1. Criar novos valores no provedor.
2. Atualizar Render.
3. Atualizar Vercel quando aplicavel.
4. Fazer redeploy.
5. Validar login, API e importacao.
6. Revogar valores antigos.

Checklist:

- [ ] Rotacionar senha do PostgreSQL.
- [ ] Atualizar `DATABASE_URL` no Render.
- [ ] Rotacionar `JWT_SECRET`/JWT secret legado conforme configuracao Supabase usada.
- [ ] Rotacionar `SUPABASE_SERVICE_ROLE_KEY`.
- [ ] Confirmar que nenhum segredo real esta versionado.
- [ ] Confirmar login e rotas financeiras apos redeploy.

## PD5 - Smoke test multiusuario em producao

Preparacao:

- Usar dois usuarios reais do Supabase: usuario A e usuario B.
- Fazer o teste em producao privada, com dados pequenos e identificaveis.

Roteiro:

1. Login com usuario A.
2. Criar conta, cartao, categoria, regra e transacao com nomes contendo `SMOKE_A`.
3. Fazer logout.
4. Login com usuario B.
5. Confirmar que `SMOKE_A` nao aparece em contas, cartoes, transacoes, regras, faturas e imports.
6. Criar dados `SMOKE_B`.
7. Confirmar que usuario A nao ve `SMOKE_B`.
8. Testar uma chamada direta com ID do outro usuario quando possivel; resultado esperado: `404` ou erro de autorizacao.

Checklist:

- [ ] Usuario B nao ve contas do usuario A.
- [ ] Usuario B nao ve cartoes do usuario A.
- [ ] Usuario B nao ve transacoes do usuario A.
- [ ] Usuario B nao ve regras do usuario A.
- [ ] Usuario B nao ve imports do usuario A.
- [ ] Referencia cruzada falha.
- [ ] Categorias de sistema continuam visiveis para ambos.

## PD6 - RLS Supabase

Estado atual:

- Existe draft em `docs/supabase/rls_phase3_draft.sql`.
- Nao aplicar diretamente em producao antes de smoke em staging.

Ordem recomendada:

1. Criar banco descartavel/staging com schema atualizado.
2. Aplicar `docs/supabase/rls_phase3_draft.sql`.
3. Testar dois usuarios via Supabase Auth.
4. Confirmar que scripts administrativos usam service role ou conexao apropriada.
5. Planejar janela curta de ativacao em producao privada.
6. Aplicar em producao.
7. Rodar smoke multiusuario.

Checklist:

- [ ] Draft revisado.
- [ ] Teste em banco descartavel passou.
- [ ] Service role de scripts definido.
- [ ] Plano de rollback documentado.
- [ ] Aplicacao em producao executada.
- [ ] Smoke multiusuario pos-RLS passou.

## PD7 - Checklist de producao publica

Antes de abrir para usuarios externos:

- [ ] Termos de uso.
- [ ] Politica de privacidade.
- [ ] Fluxo de exclusao de conta/dados.
- [ ] Exportacao de dados do usuario.
- [ ] Rate limiting.
- [ ] Monitoramento de erros.
- [ ] Alertas para falhas de API.
- [ ] Plano de suporte/feedback.
- [ ] Plano de rollback operacional.
- [ ] Rotacao de segredos concluida.
- [ ] Backups testados.
- [ ] RLS aplicado e testado.
- [ ] Instancia de backend dimensionada acima do Render Free, se performance continuar insuficiente.

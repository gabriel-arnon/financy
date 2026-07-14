# Financy - Relatório de Entregas Realizadas

## Objetivo

Registrar o que já foi concluído para análise, deixando `task.md`, `plan.md`, `spec.md` e `agents.md` focados apenas no trabalho ativo.

## Fase 3 - Autenticação e Isolamento de Usuários

Status: concluída.

Entregas:

- Supabase Auth definido como estratégia principal.
- Backend passou a validar JWT e derivar `user_id` do usuário autenticado.
- `DEV_USER_ID` ficou restrito a bypass local/teste explícito.
- Rotas financeiras protegidas.
- `/health` mantido público.
- Frontend recebeu login, logout, provider de sessão e proteção de rotas.
- API client passou a enviar Bearer token.
- Profiles são garantidos/upsertados no backend quando suportado pelo repository.
- Entidades user-owned ficaram isoladas por usuário.
- Categorias de sistema foram protegidas contra mutação comum.
- Uploads novos foram particionados por usuário.
- Criado script/checklist de reassociação de dados do `DEV_USER_ID`.
- Criado draft de RLS em `docs/supabase/rls_phase3_draft.sql`.

Validações registradas:

- Backend JSON/local passou.
- Backend PostgreSQL passou durante a fase.
- Frontend `typecheck`, `lint` e `build` passaram.
- Testes multiusuário cobriram isolamento A/B.

Arquivos/documentos relevantes:

- `docs/auth-user-isolation-plan.md`
- `docs/supabase/rls_phase3_draft.sql`
- `backend/scripts/reassign_user_data.py`

## Produção Privada e Estabilização

Status: parcialmente concluída, com pendências externas mantidas em `task.md`.

Entregas:

- Deploy privado configurado com backend no Render e frontend na Vercel.
- Migrações foram aplicadas no start do Render.
- Configurações de CORS e URLs de produção foram ajustadas.
- Retry automático adicionado para leituras GET/HEAD client-side e server-side.
- Mensagens de erro melhoradas para diferenciar falha de conexão e resposta HTTP.
- Escritas não receberam retry automático para evitar duplicidade.
- Connection pool PostgreSQL aplicado.
- Importação e confirmação em lote otimizadas.
- Benchmark local de confirmação criado.
- Logs temporários de diagnóstico removidos.
- Runbook de produção criado.

Arquivos/documentos relevantes:

- `docs/production-readiness-runbook.md`
- `backend/scripts/benchmark_import_confirm.py`
- `deploy-checklist.md`

Pendências mantidas:

- investigar causa raiz final de `Failed to fetch` residual;
- validar performance real pós-deploy;
- decidir storage persistente;
- confirmar backup/restore;
- rotacionar segredos;
- smoke multiusuário em produção;
- decidir ativação futura de RLS.

## Transações e UX Principal

Status: concluído nas frentes anteriores; novos ajustes finos estão em `task.md`.

Entregas:

- Dashboard de transações redesenhado com cards de resumo, filtros em card dedicado e lista simplificada.
- Edição inline removida da tabela.
- Drawer de detalhe/edição de transação criado.
- Drawer melhorado com largura desktop maior, layout de ações e campos read-only/editáveis.
- Botões de editar/excluir mantidos na linha, com popup de confirmação para exclusão.
- Paginação `Carregar mais` criada com 25 transações iniciais e incrementos de 25.
- Cards de resumo continuam usando todas as transações filtradas.
- Drawer passou a editar data, descrição, tipo, categoria, origem, valor e pendência.
- Criação de transação ganhou `Salvar e criar nova`.
- Status virou checkbox `Pendente`.
- Origem foi unificada em contas e cartões.
- Valor ganhou máscara/formatador BRL.
- Aviso de transações sem categoria passou a aparecer apenas quando há pendências.

Validações:

- Frontend `typecheck`, `lint` e `build` passaram nas rodadas correspondentes.

## Toasts e Feedback Global

Status: concluído.

Entregas:

- Criado `ToastProvider` global.
- Toasts posicionados no canto superior direito.
- Suporte a sucesso, erro e informação.
- Aplicado em transações, categorias, regras, contas, cartões, importação e faturas.
- Toasts de erro foram padronizados para mensagens em Português.
- Delete usa feedback visual apropriado.

## Categorias e Regras

Status: concluído.

Entregas:

- Categorias passaram a tratar criação duplicada/inativa com comportamento amigável.
- Categoria inativa com mesmo nome pode ser reativada.
- Regras passaram a editar inline como categorias.
- UX de regras foi padronizada com categorias:
  - botão `Adicionar regra`;
  - criação escondida por padrão;
  - grupos por Receita, Despesa e Ambos;
  - contadores por grupo;
  - remoção de recarregamento manual;
  - modal de inativação.

Validações:

- Backend pytest passou quando houve alteração de API/categorias.
- Frontend typecheck/lint/build passou quando houve alteração de UI.

## Cartões, Faturas e Contas

Status: base concluída; novos ajustes visuais estão em `task.md`.

Entregas:

- Transações manuais de cartão passaram a encontrar/criar fatura aberta automaticamente quando necessário.
- Dashboard do cartão passou a considerar transações manuais vinculadas a cartão.
- Faturas abertas e histórico foram integrados ao fluxo de cartões.
- Detalhes de cartão receberam ajustes de layout:
  - barra de uso de limite;
  - remoção de card duplicado de percentual;
  - cards de limite total, utilizado e disponível;
  - card de conta vinculada revisado;
  - correções de largura em histórico de faturas e últimas transações.
- BRL auditado em várias áreas principais.

Validações:

- Backend pytest passou.
- Frontend typecheck/lint/build passou.

## Importação e Parsers

Status: concluído nas entregas principais; novos ajustes de UX estão em `task.md`.

Entregas:

- Parser CSV passou a aceitar valores com vírgula e ponto decimal.
- Parser PDF otimizado para evitar extração cara quando texto normal já existe.
- Suporte dedicado adicionado para faturas Cartões CAIXA.
- Suporte dedicado adicionado para faturas Inter.
- Suporte dedicado adicionado para faturas Mercado Pago.
- Importação passou a vincular automaticamente cartão por últimos dígitos quando cadastrado.
- Compras parceladas são normalizadas quando detectadas.
- Pagamentos, boletos, totais, encargos e textos informativos são ignorados para evitar transações indevidas.
- Preview e confirmação foram otimizados em lote.

Validações:

- Testes de parser adicionados/atualizados.
- Backend pytest passou.

## IA na Importação

Status: concluído para importação; expansão de IA financeira está em `task.md`.

Entregas:

- Criado serviço opcional `AiImportAnalyzer`.
- IA desligada por padrão via env.
- Variáveis adicionadas:
  - `AI_IMPORT_ENABLED`
  - `AI_IMPORT_PROVIDER`
  - `AI_IMPORT_BASE_URL`
  - `AI_IMPORT_API_KEY`
  - `AI_IMPORT_MODEL`
  - `AI_IMPORT_TIMEOUT_SECONDS`
- IA pode gerar preview para PDF desconhecido quando parser retorna zero itens.
- Endpoint manual `POST /imports/{import_id}/analyze-ai`.
- Itens gerados por IA entram com `needs_review=true`.
- Metadados técnicos salvos em `raw_row`, sem prompt completo.
- Frontend mostra botão `Analisar com IA` quando preview está vazio.
- Criado enriquecimento de preview por IA:
  - sugestão de categoria;
  - descrição normalizada;
  - explicações;
  - duplicidade;
  - parcelas;
  - resumo de consistência.
- Enriquecimento é opcional e não bloqueia confirmação manual.
- Documentação criada/atualizada em `docs/ai-import.md`.

Validações:

- Backend pytest: `59 passed, 1 warning`.
- Frontend typecheck passou.
- Frontend lint passou.
- Frontend build passou.

Commit relevante:

- `7a0f5ab Add AI import review enrichment`

## Branding

Status: parcialmente concluído.

Entregas:

- Logo/logotipo do Financy adicionados ao projeto em rodada anterior.
- Imagens transparentes foram recebidas para substituir assets.

Pendência:

- Confirmar se todas as imagens finais transparentes foram aplicadas aos pontos necessários.

## Estado Atual dos Arquivos de Planejamento

- `task.md`: tasks ativas de produção, produto, IA e polish visual.
- `plan.md`: plano ativo consolidado.
- `spec.md`: especificação ativa.
- `agents.md`: agentes ativos para próximas frentes.
- `output.md`: este relatório histórico.
## Insights e Assistente Financeiro Global

Status: implementado com validacoes principais concluidas.

Entregas:

- Card de Insights ficou mais enxuto: resumo textual redundante, chat embutido e grafico inferior deixaram de ser renderizados.
- `Regras sugeridas` ganhou acao `Adicionar regra`, com dialogo reutilizavel de criacao e valores iniciais vindos da sugestao.
- Apos criar regra sugerida, a sugestao sai da lista local e os insights sao recarregados.
- `Descricoes para limpar` ganhou CTA para `/transactions?cleanup=rename&transaction_ids=...`.
- Tela de transacoes passou a aceitar filtros iniciais por query params: busca, tipo, categoria, status, data inicial/final e IDs focados para limpeza.
- Assistente financeiro global criado no shell autenticado com launcher flutuante, painel de conversa, historico em sessao, fechamento por botao, clique fora e Escape.
- API do assistente passou a retornar campos estruturados compativeis: `message`, `kind`, `summary` e `cta`.
- Campos antigos (`answer`, `matched_count`, `total_amount`, `filters`) foram preservados.

Decisoes de arquitetura:

- O contrato do backend foi expandido sem quebrar consumidores existentes.
- O assistente global usa a mesma rota `/ai-finance/ask` e prefere `message`, com fallback para `answer`.
- A navegacao para transacoes reutiliza a tela atual por query params, sem criar nova pagina.
- A criacao de regra sugerida reutiliza o payload/API de regras e concentra o fluxo em um componente reutilizavel.

Validacoes:

- Frontend typecheck: passou.
- Frontend lint: passou.
- Frontend build: passou.
- Backend pytest no `.venv`: `61 passed, 1 warning`.
- Teste backend novo cobre resposta estruturada do assistente e fallback textual.
- Playwright e2e: executou contra API local com CORS para `127.0.0.1:3100`; 6 passaram e 7 falharam por expectativas pre-existentes/desalinhadas na tela de transacoes e navegacao responsiva (`Status` no drawer, campos readonly, contador de selecao, confirmacao de exclusao e link mobile `Cartoes de Credito`).

Como validar manualmente:

- Abrir Dashboard e confirmar que Insights nao mostra resumo redundante, chat embutido nem grafico inferior.
- Clicar em `Adicionar regra`, revisar campos preenchidos e salvar.
- Clicar em `Ver transacoes` em descricoes para limpar e confirmar filtro aplicado.
- Abrir o launcher no canto inferior direito, perguntar sobre gastos do mes e usar o CTA de transacoes.

## Estabilizacao E2E de Insights, Assistente e Transacoes

Status: concluido; suite E2E completamente verde.

Falhas originais investigadas:

| Teste / area | Esperado | Observado | Causa raiz | Classificacao | Correcao |
| --- | --- | --- | --- | --- | --- |
| Drawer de transacao - campo `Status` | Validar campos atuais do drawer | Teste esperava `Status`, mas produto usa checkbox `Pendente` | Contrato do drawer evoluiu; `Status` nao faz mais parte do formulario | Teste desatualizado | Teste atualizado para `Origem` e `Pendente` |
| Drawer de transacao - campos readonly | Confirmar editabilidade correta | Teste esperava `readonly` em data/tipo/origem/valor/status | Produto atual permite editar esses campos no drawer | Teste desatualizado | Teste passou a validar campos editaveis e habilitados |
| Confirmacao de exclusao | Abrir dialogo antes de excluir | Seletor global por nome era ambiguo em tabela grande | Clique nao estava ancorado na linha/drawer certo | Seletor fragil | Teste passou a clicar no botao da linha e no botao dentro do drawer |
| Contador de selecao | Feedback ao selecionar transacoes | Produto so mostrava acoes com mais de 1 item selecionado | Selecionar 1 item nao dava feedback nem acesso a limpar selecao | Regressao real de UX | Produto agora exibe barra de selecao a partir de 1 item |
| Link mobile `Cartoes de Credito` em 375px | Validar item de menu mobile | Teste procurava link sem abrir menu mobile | Nav desktop esta corretamente oculto no mobile | Problema de viewport/responsividade no teste | Teste abre `Abrir menu` antes de buscar o link |
| Link mobile `Cartoes de Credito` em 430px | Validar item de menu mobile | Mesmo comportamento do viewport 375px | Mesmo motivo: menu fechado por padrao | Problema de viewport/responsividade no teste | Teste abre `Abrir menu` antes de buscar o link |
| Fixtures de transacoes | Suite independente de dados locais | Testes dependiam da base local e usavam `skip` quando vazia | Dados mutaveis causavam falsos negativos e skips | Problema de fixture/dados | Spec de transacoes usa mocks deterministas, sem `skip` |

Cobertura E2E adicionada/ajustada:

- `/transactions` sem query params inicia filtros vazios.
- `/transactions` com `q`, `type`, `category_id`, `start_date` e `end_date` hidrata filtros e lista filtrada.
- `Ver transacoes` em Insights navega para `/transactions?cleanup=rename&transaction_ids=...` e filtra a lista.
- `Adicionar regra` em Insights abre dialogo, preenche valores iniciais, salva pela API mockada, mostra toast e remove sugestao.
- Assistente global nao aparece em `/login`.
- Assistente global abre pelo launcher, fecha por botao, Escape e clique fora.
- Assistente global envia pergunta, renderiza resposta estruturada, mostra CTA e navega para transacoes filtradas.

Arquivos alterados nesta etapa:

- `frontend/tests/e2e/transactions.spec.ts`
- `frontend/tests/e2e/responsive-buttons.spec.ts`
- `frontend/tests/e2e/finance-assistant-insights.spec.ts`
- `frontend/src/components/transactions-table.tsx`
- `frontend/src/components/dashboard-content.tsx`
- `output.md`

Comandos executados:

- `npx.cmd playwright test tests/e2e/transactions.spec.ts --project=chromium --reporter=line`
- `npx.cmd playwright test tests/e2e/responsive-buttons.spec.ts --project=chromium --reporter=line`
- `npx.cmd playwright test tests/e2e/finance-assistant-insights.spec.ts --project=chromium --reporter=line`
- `npm.cmd run e2e`
- `npm.cmd run typecheck`
- `npm.cmd run lint`
- `npm.cmd run build`
- `.venv\Scripts\python.exe -m pytest`

Resultado final:

- Frontend typecheck: passou.
- Frontend lint: passou.
- Frontend build: passou.
- Frontend E2E: `19 passed`.
- Backend pytest: `61 passed, 1 warning`.
- Nenhum teste foi desabilitado, marcado com `skip`, `only` ou enfraquecido artificialmente.

Risco residual:

- O Playwright ainda emite aviso do Next sobre `script` renderizado no client durante alguns testes; nao bloqueia a suite, mas vale investigar em uma frente separada de higiene do layout/theme init.

## Dashboard: Acoes Rapidas, Grafico Pizza e Insights Enxutos

Status: concluido no codigo; pendencias operacionais de producao do `task.md` seguem dependentes de ambiente real.

Entregas:

- Dashboard ganhou botoes de acao rapida ao lado de `Importar arquivo`: `Receita` em verde e `Despesa` em vermelho.
- Os botoes navegam para `/transactions?create=income` e `/transactions?create=expense`.
- Tela de transacoes passou a aceitar o query param `create` para abrir o drawer de criacao manual ja preenchido com o tipo correto.
- Grafico de `Gastos por categoria` foi trocado de barras para pizza, reutilizando os mesmos dados agregados por categoria.
- Card de `Insights` deixou de renderizar os textos pedidos: maior categoria, maior despesa, resultado positivo/negativo, resultado do periodo e relacao gastos/entradas.
- Codigo morto do chat antigo e do grafico inferior dentro do card de Insights foi removido de verdade.
- Mantidos os blocos acionaveis de Insights: regras sugeridas, classificacao automatica, recorrencias provaveis e descricoes para limpar.

Decisoes de arquitetura:

- A criacao rapida reutiliza a tela e o drawer existentes de transacoes, sem criar CRUD paralelo.
- O deep link `create=income|expense` fica restrito a tipos suportados pelo dashboard; valores desconhecidos sao ignorados.
- O backend nao foi alterado, pois os dados removidos do card apenas deixaram de ser renderizados no frontend.
- As pendencias de `task.md` ligadas a Render, Supabase, backups, rotacao de segredos e validacao real de producao nao foram marcadas como concluidas porque exigem acesso/observacao do ambiente real.

Arquivos alterados nesta etapa:

- `frontend/src/components/dashboard-content.tsx`
- `frontend/src/app/transactions/page.tsx`
- `frontend/src/components/page-loaders.tsx`
- `frontend/src/components/transactions-table.tsx`
- `frontend/tests/e2e/transactions.spec.ts`
- `frontend/tests/e2e/finance-assistant-insights.spec.ts`
- `output.md`

Cobertura adicionada/ajustada:

- E2E valida `/transactions?create=income` e `/transactions?create=expense` abrindo o drawer manual com tipo correto.
- E2E valida os botoes `Receita` e `Despesa` do dashboard navegando para transacoes e abrindo o drawer pre-preenchido.
- E2E de regra sugerida foi escopado ao dialogo correto para evitar colisao com o `aria-label` do novo grafico.

Comandos executados:

- `npm.cmd run typecheck`
- `npm.cmd run lint`
- `npm.cmd run build`
- `npm.cmd run e2e`
- `.venv\Scripts\python.exe -m pytest`

Resultado final:

- Frontend typecheck: passou.
- Frontend lint: passou.
- Frontend build: passou.
- Frontend E2E: `21 passed`.
- Backend pytest: `61 passed, 1 warning`.
- Nenhum teste foi desabilitado, marcado com `skip`, `only`, `todo` ou enfraquecido artificialmente.

Risco residual:

- O aviso recorrente do Next sobre `script` renderizado em componente client ainda aparece durante alguns E2E e permanece como divida tecnica separada.
- Validacoes operacionais reais de producao listadas no `task.md` continuam pendentes por dependerem de logs, credenciais, backups, rotacao de segredos e observacao do ambiente publicado.

## Ressarcimentos: Fundacao 0 - Storage Privado e Arquivos

Status: implementado no codigo; migration criada, mas nao executada.

Entregas:

- Criado plano tecnico revisado em `docs/reimbursements-plan.md`, consolidando escopo do MVP, Supabase Auth para convidados, Fundacao 0, pagamentos informados versus confirmados e status simplificados.
- Adicionada migration `docs/supabase/migrations/005_private_files.sql` para `stored_files`, `transaction_attachments` e `stored_file_events`.
- Backend ganhou configuracao de storage privado local/Supabase, limites de arquivo e TTL de URL assinada.
- Criado service de arquivos com validacao de extensao, MIME declarado, magic bytes, limite de tamanho, hash SHA-256, upload privado, soft delete e URL assinada.
- Criados endpoints de arquivos e anexos de transacao:
  - `POST /files/upload`
  - `GET /files/{file_id}/signed-url`
  - `GET /files/{file_id}/download`
  - `DELETE /files/{file_id}`
  - `POST /transactions/{transaction_id}/attachments`
  - `GET /transactions/{transaction_id}/attachments`
  - `DELETE /transactions/{transaction_id}/attachments/{attachment_id}`
- Repositories JSON local e PostgreSQL passaram a persistir metadados de arquivos, anexos de transacao e eventos de arquivo.
- Drawer de transacoes ganhou bloco de comprovantes com upload, listagem, abertura por URL assinada e remocao do vinculo.
- `.env.example` e `.env.production.example` documentam as novas variaveis de storage privado.

Decisoes de arquitetura:

- A fundacao de arquivos e reutilizavel, nao especifica de ressarcimentos.
- Em desenvolvimento local, arquivos privados ficam em `UPLOAD_STORAGE_PATH/private_files`.
- Em producao, `PRIVATE_FILES_BACKEND=supabase` prepara uso de Supabase Storage privado sem adicionar dependencia Python.
- Signed URLs no modo local sao URLs temporarias do proprio backend com token HMAC.
- O guest portal, cobrancas, Telegram, OCR e audio continuam fora desta entrega.

Validacoes:

- Backend pytest: `64 passed, 1 warning`.
- Frontend typecheck: passou.
- Frontend lint: passou.
- Frontend build: passou.
- Playwright E2E via `npx.cmd playwright test --reporter=line`: `21 passed`.

Observacoes:

- `npm.cmd run e2e` teve uma execucao que encerrou com codigo 1 sem detalhar falha no stdout; a mesma suite executada em seguida via Playwright com reporter em linha passou completamente.
- O aviso conhecido do Next sobre `script` em componente client continua aparecendo nos E2E e permanece como divida tecnica separada.

## Auditoria e Fechamento da Fundacao 0

Status: concluido.

Causa do codigo 1 no E2E:

- A falha original de `npm.cmd run e2e` nao era diferenca real entre npm e Playwright direto. O script em `package.json` e apenas `playwright test`, usando o mesmo `playwright.config.ts`.
- A causa foi uma regressao no drawer de transacoes: o mock generico `**/transactions/**` dos testes E2E interceptava o novo endpoint `/transactions/{id}/attachments` e devolvia uma transacao em vez de uma lista de anexos.
- A UI tentou renderizar essa resposta como anexos e quebrou. O frontend foi endurecido para tratar resposta inesperada como lista vazia, e o mock E2E foi corrigido para deixar `/attachments` cair na rota especifica.

Correcoes e auditoria:

- `npm.cmd run e2e` passou de forma reproduzivel com `22 passed`.
- Migration `005_private_files.sql` revisada sem execucao: cria tipos, tabelas, FKs, indices e uniques para `stored_files`, `transaction_attachments` e `stored_file_events`, sem alteracao destrutiva em transacoes existentes e sem dependencia de bucket publico.
- Contrato publico de arquivo foi endurecido: `storage_path` e `storage_bucket` nao aparecem mais nas respostas para o frontend.
- Configuracoes adicionadas:
  - `PRIVATE_FILES_ENABLED`
  - `PRIVATE_FILES_ALLOWED_MIME_TYPES`
  - `PRIVATE_FILES_SCAN_PROVIDER`
  - `PRIVATE_FILES_ORPHAN_RETENTION_HOURS`
- Startup valida provider, variaveis obrigatorias do Supabase quando `PRIVATE_FILES_BACKEND=supabase`, limites e TTL.
- Provider local e Supabase ficam encapsulados no adapter `PrivateFileStorage`; endpoints nao possuem logica especifica de Supabase.
- Scan/quarentena:
  - local/desenvolvimento/teste com `PRIVATE_FILES_SCAN_PROVIDER=mock` libera como `available/skipped`;
  - producao com mock nao libera automaticamente, mantendo `quarantined/pending`;
  - signed URL e negada para arquivos em quarentena, suspeitos, rejeitados, deletados ou sem scan liberado.
- Orfaos:
  - arquivos sem vinculo ativo e mais antigos que `PRIVATE_FILES_ORPHAN_RETENTION_HOURS` podem ser identificados via repository/service;
  - scheduler de purge fisico ficou para etapa futura.
- Hash:
  - SHA-256 e calculado no backend;
  - owners diferentes podem enviar conteudo identico, mas continuam isolados por `owner_user_id`;
  - hash nao substitui autorizacao.
- Compensacao banco/storage:
  - se upload no storage falha, metadata nao e criada;
  - se insert no banco falha apos upload, o objeto local e removido de forma compensatoria;
  - soft delete impede novas signed URLs mesmo que exclusao fisica futura falhe;
  - falha de associacao deixa arquivo sem vinculo e elegivel para limpeza de orfaos.

Testes adicionados/reforcados:

- JPEG, PNG, WebP e PDF validos.
- Arquivo vazio, MIME falso, extensao falsa, magic bytes invalidos e arquivo acima do limite.
- Hash calculado e isolamento de hash entre owners.
- Owner nao acessa arquivo de outro owner.
- Associacao cruzada owner/file/transaction bloqueada.
- Arquivo deletado, em quarentena e suspeito nao gera signed URL.
- Producao com scan mock mantem arquivo em quarentena.
- Orfaos identificados por janela configuravel.
- Falha de storage e falha de banco com compensacao.
- E2E do drawer cobre anexar, listar, abrir via signed URL e remover comprovante.

Comandos executados:

- Backend: `.venv\Scripts\python.exe -m pytest` -> `73 passed, 1 warning`.
- Frontend: `npm.cmd run typecheck` -> passou.
- Frontend: `npm.cmd run lint` -> passou.
- Frontend: `npm.cmd run build` -> passou.
- Frontend: `npm.cmd run e2e` -> `22 passed`.

Risco residual:

- Nao ha antivirus comercial integrado; a arquitetura deixa scanner real como configuracao futura.
- Purge fisico de orfaos ainda nao possui scheduler.
- Uma signed URL ja emitida pode permanecer valida ate expirar conforme comportamento do provider; mitigacao atual e TTL curto configuravel.
- Aviso conhecido do Next sobre `script` em componente client segue como divida tecnica independente.

## Fundacao 1 - Dominio owner-only de ressarcimentos

Status: concluido.

Escopo entregue:

- Migration `006_reimbursements_domain.sql` criada e revisada, mas nao executada.
- Enums de ressarcimentos adicionados no backend.
- Schemas Pydantic adicionados para contatos, cobrancas, itens e eventos.
- Repositories local JSON e PostgreSQL preparados para:
  - `reimbursement_contacts`;
  - `reimbursement_claims`;
  - `reimbursement_items`;
  - `reimbursement_events`.
- Service `ReimbursementService` criado com regras de dominio owner-only.
- Router FastAPI `/reimbursements` criado e registrado.
- Testes backend adicionados para contatos, cobrancas, itens, snapshots, envio, cancelamento, isolamento por owner e travas de status.

APIs adicionadas nesta fundacao:

- `GET /reimbursements/contacts`
- `POST /reimbursements/contacts`
- `PATCH /reimbursements/contacts/{contact_id}`
- `DELETE /reimbursements/contacts/{contact_id}`
- `GET /reimbursements/claims`
- `POST /reimbursements/claims`
- `GET /reimbursements/claims/{claim_id}`
- `PATCH /reimbursements/claims/{claim_id}`
- `POST /reimbursements/claims/{claim_id}/send`
- `POST /reimbursements/claims/{claim_id}/cancel`
- `POST /reimbursements/claims/{claim_id}/items`
- `PATCH /reimbursements/claims/{claim_id}/items/{item_id}`
- `DELETE /reimbursements/claims/{claim_id}/items/{item_id}`

Decisoes implementadas:

- Ressarcimentos ficam como modulo dentro do backend atual, seguindo o padrao `api -> service -> repository`.
- `owner_user_id` nunca e aceito do cliente; ele vem da dependencia de usuario autenticado.
- Contato pode existir sem login e e escopado por owner.
- Cobranca nasce como `draft`; status nao pode ser alterado livremente por payload.
- Apenas despesas (`type=expense`) podem ser adicionadas como item ressarcivel no MVP.
- Ressarcimento parcial e suportado por `amount_requested`.
- A soma de itens ativos para a mesma transacao, no mesmo owner, nao pode exceder o valor absoluto da transacao.
- Itens cancelados deixam de consumir alocacao.
- `send` exige ao menos um item ativo, muda status para `sent`, registra `sent_at` e congela `total_snapshot`.
- Depois de enviada, a cobranca nao pode receber edicao de metadados nem alteracao/adicao/remocao de itens.
- Cada item guarda `transaction_snapshot` com dados essenciais da transacao, incluindo descricao, data, valor, valor solicitado, categoria, conta, cartao, fatura e versao do snapshot.
- Eventos de dominio registram criacao/atualizacao de contato, criacao/atualizacao/envio/cancelamento de cobranca e adicao/alteracao/remocao de item.

Fora de escopo mantido:

- Nenhuma UI de Ressarcimentos foi criada.
- Nenhum portal guest foi iniciado.
- Nenhum convite real, membership, comentario ou pagamento foi implementado.
- Nenhuma integracao Telegram, OCR, audio ou fila assincrona foi implementada.

Validacoes executadas:

- Backend especifico: `backend/.venv/Scripts/python.exe -m pytest tests/test_reimbursements_api.py -q` -> `9 passed`.
- Backend completo: `backend/.venv/Scripts/python.exe -m pytest` -> `82 passed, 1 warning`.
- Frontend typecheck: `npm.cmd run typecheck` -> passou.
- Frontend lint: `npm.cmd run lint` -> passou.
- Frontend build: `npm.cmd run build` -> passou.
- Frontend E2E: `npm.cmd run e2e` -> `22 passed`.

Risco residual:

- A migration `006_reimbursements_domain.sql` ainda nao foi executada em Supabase.
- As regras de soma de alocacao sao validadas no service; em producao com concorrencia alta, a etapa futura deve adicionar protecao transacional/lock ou constraint complementar.
- Ainda nao ha RLS final para as novas tabelas; a autorizacao atual esta no backend.
- Portal guest, convites, comentarios e pagamentos continuam como Fundacoes/Fases futuras.

## Fundacao 2 - Interface owner-only de ressarcimentos

Status: concluido.

Fechamento critico da Fundacao 1:

- Concorrencia de alocacao:
  - PostgreSQL agora usa operacoes atomicas no repository com transacao e `select ... for update` na transacao financeira antes de calcular saldo e inserir/atualizar item.
  - Repository local usa `RLock` para simular a mesma serializacao nos testes e ambiente local.
  - Criacao e atualizacao concorrentes de `amount_requested` nao conseguem exceder o valor ressarcivel da despesa.
  - Itens em claim `draft` ou `sent` reservam saldo enquanto estiverem ativos.
  - Claim `canceled` deixa de reservar saldo; ao cancelar, os itens ativos sao marcados como `canceled`, preservando historico e snapshots.
- Snapshots:
  - Ao adicionar item em draft, o backend cria snapshot preliminar.
  - Em draft, o owner pode atualizar snapshots da claim via endpoint dedicado.
  - No `send`, o backend rele a transacao, valida owner/tipo/valor/alocacao e finaliza o snapshot com assinatura da fonte e `finalized_at`.
  - Depois de `sent`, o snapshot nao e alterado silenciosamente; se a transacao original mudar, a UI indica que o snapshot ficou diferente da fonte atual.

Interface criada:

- Nova rota owner-only `/reimbursements`.
- Item `Ressarcimentos` adicionado na sidebar desktop, sidebar recolhida e menu mobile.
- Tela com tabs:
  - `Visao geral`;
  - `Cobrancas`;
  - `Pessoas`.
- Visao geral com total em cobrancas enviadas, quantidade de rascunhos, quantidade finalizada, cobrancas recentes e rascunhos pendentes.
- Pessoas:
  - listar;
  - buscar;
  - criar;
  - editar;
  - inativar sem hard delete;
  - exibir quantidade de cobrancas associadas;
  - indicar que acesso compartilhado ainda nao esta configurado.
- Cobrancas:
  - listar com filtros por busca, pessoa e status;
  - criar draft;
  - editar draft;
  - adicionar transacoes elegiveis;
  - definir valor integral/parcial;
  - editar/remover item em draft;
  - atualizar snapshots em draft;
  - finalizar cobranca;
  - cancelar cobranca;
  - visualizar timeline owner-only;
  - abrir comprovante da transacao quando houver anexo.
- Transacoes:
  - acao individual `Solicitar ressarcimento`;
  - acao em lote `Solicitar ressarcimento`;
  - selecao mista mostra itens inelegiveis e permite prosseguir apenas com despesas elegiveis;
  - fluxo sempre exige revisao antes de incluir itens.

Endpoints reutilizados/adicionados:

- Reutilizados da Fundacao 1:
  - contatos, cobrancas, itens, envio e cancelamento sob `/reimbursements`.
- Adicionados para UI:
  - `GET /reimbursements/overview`;
  - `GET /reimbursements/eligible-transactions`;
  - `POST /reimbursements/claims/{claim_id}/refresh-snapshots`;
  - `GET /reimbursements/claims/{claim_id}/events`.
- Reutilizados da Fundacao 0:
  - `GET /transactions/{transaction_id}/attachments`;
  - `GET /files/{file_id}/signed-url`.

Arquivos principais alterados/criados:

- Backend:
  - `backend/app/api/reimbursements.py`;
  - `backend/app/schemas/reimbursements.py`;
  - `backend/app/services/reimbursement_service.py`;
  - `backend/app/repositories/postgres.py`;
  - `backend/app/repositories/local_json.py`;
  - `backend/tests/test_reimbursements_api.py`.
- Frontend:
  - `frontend/src/app/reimbursements/page.tsx`;
  - `frontend/src/components/reimbursements-content.tsx`;
  - `frontend/src/components/app-shell.tsx`;
  - `frontend/src/components/page-loaders.tsx`;
  - `frontend/src/components/transactions-table.tsx`;
  - `frontend/src/lib/api.ts`;
  - `frontend/src/lib/types.ts`;
  - `frontend/tests/e2e/reimbursements.spec.ts`.

Migrations:

- Nenhuma migration foi executada.
- Nenhuma migration nova foi necessaria para a Fundacao 2; as mudancas de concorrencia e snapshot foram resolvidas por codigo usando as tabelas da `006_reimbursements_domain.sql`.
- `005_private_files.sql` e `006_reimbursements_domain.sql` continuam criadas e nao executadas.

Validacoes executadas:

- Backend especifico: `backend/.venv/Scripts/python.exe -m pytest tests/test_reimbursements_api.py -q` -> `15 passed`.
- Backend completo: `backend/.venv/Scripts/python.exe -m pytest` -> `88 passed, 1 warning`.
- Frontend typecheck: `npm.cmd run typecheck` -> passou.
- Frontend lint: `npm.cmd run lint` -> passou.
- Frontend build: `npm.cmd run build` -> passou.
- Frontend E2E especifico: `npx.cmd playwright test tests/e2e/reimbursements.spec.ts --reporter=line` -> `4 passed`.
- Frontend E2E completo: `npm.cmd run e2e` -> `26 passed`.

Warning restante:

- Backend: warning deprecado do `reportlab` em `.venv/Lib/site-packages/reportlab/lib/rl_safe_eval.py`, uso de `ast.NameConstant` que sera removido no Python 3.14.
- Frontend E2E: aviso existente do navegador sobre `script` renderizado dentro de componente React client; ficou como divida tecnica da Fundacao 2 e foi corrigido na Fundacao 2.5.

Fora de escopo mantido:

- Fundacao 3 nao foi iniciada.
- Portal guest nao foi iniciado.
- Convites reais, memberships, comentarios e pagamentos nao foram implementados.
- Telegram, OCR, audio, inbox e filas nao foram implementados.

Risco residual:

- RLS final das novas tabelas ainda precisa ser criada antes de producao publica.
- A protecao concorrente real depende da migration 006 aplicada no PostgreSQL; no local JSON ela e apenas simulada para desenvolvimento/testes.
- A UI de Ressarcimentos ainda usava `window.confirm` para finalizacao/cancelamento na Fundacao 2; isso foi substituido por dialog visual dedicado na Fundacao 2.5.

## Fundacao 2.5 - Validacao PostgreSQL e polimento owner-only

Status: parcialmente concluido; polimento e validacoes automatizadas locais concluidos, validacao real em PostgreSQL/Supabase bloqueada por seguranca de ambiente.

Seguranca de ambiente:

- Ambiente local inspecionado: `backend/.env` declara `ENVIRONMENT=local`.
- `DATABASE_URL`, `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` estao vazios no ambiente local inspecionado.
- `docker-compose.yml` contem um PostgreSQL local descartavel em `postgres:16-alpine`, mas o Docker daemon nao estava disponivel nesta sessao.
- `docker ps` falhou com acesso negado ao `C:\Users\Gabriel\.docker\config.json` e ausencia do named pipe do Docker.
- `psql` e `supabase` CLI nao estavam disponiveis no PATH.
- Como nao foi possivel confirmar um alvo PostgreSQL/Supabase de desenvolvimento com backup/descartabilidade e credenciais nao produtivas, nenhuma migration foi aplicada.

Migrations revisadas:

- `docs/supabase/migrations/005_private_files.sql`:
  - cria enums de arquivo, scanner e eventos;
  - cria `stored_files`, `transaction_attachments` e `stored_file_events`;
  - usa `owner_user_id`, timestamps, soft delete, status de arquivo, status de scan, SHA-256, chaves estrangeiras e indices;
  - nao depende de bucket publico;
  - nao altera destrutivamente transacoes existentes.
- `docs/supabase/migrations/006_reimbursements_domain.sql`:
  - cria enums de contatos, claims, itens e eventos;
  - cria `reimbursement_contacts`, `reimbursement_claims`, `reimbursement_items` e `reimbursement_events`;
  - usa `owner_user_id`, `numeric(14,2)`, timestamps, soft/inactive status, snapshots `jsonb`, FKs e indices por owner/status/transacao;
  - preserva historico por status/cancelamento e nao altera destrutivamente dados existentes.
- Ordem validada estaticamente: aplicar `005_private_files.sql` antes de `006_reimbursements_domain.sql`.
- Nenhuma migration foi editada nesta etapa e nenhuma migration nova foi criada.

Aplicacao em desenvolvimento:

- `005_private_files.sql`: nao aplicada.
- `006_reimbursements_domain.sql`: nao aplicada.
- Motivo: ausencia de ambiente PostgreSQL/Supabase de desenvolvimento confirmavel nesta sessao.
- Consultas de sanidade, verificacao de tabelas/indices e smoke real com fixtures nao foram executados por esse bloqueio.

Repository PostgreSQL e concorrencia real:

- A validacao real com repository PostgreSQL nao foi executada porque nao havia `DATABASE_URL` seguro/disponivel nem servidor PostgreSQL acessivel.
- A protecao concorrente continua implementada no repository PostgreSQL por transacao e lock em registro estavel da transacao financeira antes de calcular saldo e inserir/atualizar item.
- A prova automatizada local continua cobrindo a regra de dominio com repository local serializado, mas isso nao substitui o teste concorrente real em PostgreSQL.
- Divida tecnica obrigatoria antes de producao publica: rodar teste de integracao PostgreSQL com duas alocacoes simultaneas de R$ 70 em uma despesa de R$ 100 e confirmar que no maximo uma e aceita.

Supabase Storage real:

- Nao validado nesta sessao porque `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` e bucket real nao estavam configurados no ambiente local.
- A Fundacao 0 permanece validada por testes com providers locais/mocks, mas falta smoke real em bucket privado Supabase.
- Divida tecnica obrigatoria antes de producao publica: validar bucket privado, upload JPEG/PNG/WebP/PDF, metadata, signed URL, expiracao, soft delete, bloqueio pos-delete, owner diferente e compensacao banco/storage em Supabase dev/staging.

Polimento de dialogos:

- Substituidos os `window.confirm` dos fluxos owner-only de Ressarcimentos por dialogo visual consistente:
  - finalizar cobranca;
  - cancelar cobranca;
  - inativar pessoa;
  - remover item.
- O dialogo mostra detalhes seguros da acao, tem estado de loading, botao de retorno focavel, fechamento por Escape quando nao ha acao em andamento e bloqueia duplo envio.
- `window.confirm` ainda existe em areas fora do escopo desta fase (`Contas`, `Cartoes` e `Faturas`), sem alteracao nesta entrega.

Warnings:

- Backend: permanece 1 warning de dependencia em `reportlab==4.2.5`: `ast.NameConstant is deprecated and will be removed in Python 3.14`.
- Origem: `.venv/Lib/site-packages/reportlab/lib/rl_safe_eval.py`.
- Impacto atual: baixo em Python 3.12; nao quebra testes nem execucao atual.
- Existe versao mais nova do ReportLab, mas upgrade foi adiado para evitar mudanca indireta no fluxo de PDF/importacao sem tarefa especifica.
- Frontend: warning de `<script>` em componente React client foi corrigido removendo o script inline do layout e adicionando `ThemeInitializer` client-side sem renderizar tag `<script>`.
- Frontend: warning de key duplicada em toast foi corrigido trocando IDs baseados em tempo por contador monotono em memoria.

Arquivos alterados nesta Fundacao 2.5:

- `frontend/src/app/layout.tsx`;
- `frontend/src/components/theme-initializer.tsx`;
- `frontend/src/components/reimbursements-content.tsx`;
- `frontend/src/components/toast-provider.tsx`;
- `frontend/tests/e2e/reimbursements.spec.ts`;
- `output.md`.

Validacoes executadas:

- Backend completo: `backend/.venv/Scripts/python.exe -m pytest` -> `88 passed, 1 warning in 18.59s`.
- Frontend typecheck: `npm.cmd run typecheck` -> passou.
- Frontend lint: `npm.cmd run lint` -> passou.
- Frontend build: `npm.cmd run build` -> passou.
- Frontend E2E especifico responsivo: `npx.cmd playwright test tests/e2e/responsive-buttons.spec.ts --reporter=line` -> `2 passed`.
- Frontend E2E completo: `npm.cmd run e2e` -> `26 passed (48.6s)`.

Smoke tests:

- Smoke automatizado owner-only passou via E2E:
  - navegacao Ressarcimentos desktop/mobile;
  - criar/editar/inativar pessoa;
  - criar claim;
  - adicionar item com erro acima do saldo e valor parcial valido;
  - finalizar com dialogo;
  - bloquear edicao apos sent;
  - cancelar com dialogo;
  - timeline;
  - iniciar fluxo a partir de Transacoes com selecao mista.
- Smoke manual real em PostgreSQL/Supabase nao foi executado por falta de ambiente seguro confirmado.

Fora de escopo preservado:

- Fundacao 3 nao foi iniciada.
- Portal guest, invitations, memberships, comentarios, pagamentos, Telegram, OCR, audio, inbox e filas nao foram implementados.

## Fundacao 3 - Convites e Portal Guest Limitado

Escopo implementado:

- Criada a migration incremental `docs/supabase/migrations/007_reimbursement_guest_access.sql`, nao executada automaticamente.
- Adicionados convites de ressarcimento com token bruto retornado apenas na criacao e `token_hash` persistido no banco.
- Adicionados memberships para vincular um contato de ressarcimento a um usuario autenticado.
- O aceite de convite exige usuario autenticado e e-mail igual ao e-mail convidado.
- Owner pode listar/criar/revogar convites e listar/revogar acessos.
- Guest pode listar apenas cobrancas compartilhadas por membership ativo e status compartilhavel.
- Guest pode reconhecer ou contestar uma cobranca; a contestacao registra nota curta em evento de dominio.
- Portal guest criado em `/guest/reimbursements`, sem sidebar financeira, dashboard, contas, cartoes, transacoes gerais, importacoes ou regras.
- Rota de aceite criada em `/guest/reimbursements/accept?token=...`.
- UI owner-only ganhou criacao de convite em cobranca finalizada e visualizacao/revogacao de convites e acessos em Pessoas.

Endpoints adicionados:

- `GET /reimbursements/invitations`
- `POST /reimbursements/invitations`
- `POST /reimbursements/invitations/{invitation_id}/revoke`
- `GET /reimbursements/memberships`
- `POST /reimbursements/memberships/{membership_id}/revoke`
- `POST /reimbursements/guest/invitations/accept`
- `GET /reimbursements/guest/claims`
- `GET /reimbursements/guest/claims/{claim_id}`
- `POST /reimbursements/guest/claims/{claim_id}/acknowledge`
- `POST /reimbursements/guest/claims/{claim_id}/dispute`

Seguranca e isolamento:

- `owner_user_id` continua derivado do backend/JWT; o frontend nao envia owner.
- Convite nao vira autorizacao permanente; somente membership ativo libera acesso.
- Revogar membership remove imediatamente a listagem guest de cobrancas daquele contato.
- Guest nao acessa cobrancas draft nem claims fora de memberships ativos.
- Tokens sao armazenados como SHA-256; o token bruto so aparece na resposta de criacao para montar o link.
- Eventos de aceite, visualizacao, reconhecimento, contestacao e revogacao sao registrados no dominio.

Validacoes:

- Backend focado: `backend/.venv/Scripts/python.exe -m pytest tests/test_reimbursements_api.py -q` -> `18 passed in 4.35s`.
- Backend completo: `backend/.venv/Scripts/python.exe -m pytest` -> `91 passed, 1 warning in 15.70s`.
- Frontend typecheck: `npm.cmd run typecheck` -> passou.
- Frontend lint: `npm.cmd run lint` -> passou.
- Frontend build: `npm.cmd run build` -> passou.
- E2E ressarcimentos isolado: `npx.cmd playwright test tests/e2e/reimbursements.spec.ts --reporter=line` -> `4 passed (9.0s)`.
- E2E completo final: `npm.cmd run e2e` -> `26 passed (48.9s)`.
- PostgreSQL marcado nesta sessao: `backend/.venv/Scripts/python.exe -m pytest tests_postgres -m postgres -q` -> bloqueado por ambiente: `TEST_DATABASE_URL is required for PostgreSQL integration tests.`

Observacao de E2E:

- Uma execucao intermediaria de `npm.cmd run e2e` falhou em cascata apos o webServer do Playwright ficar indisponivel (`ERR_CONNECTION_REFUSED`).
- Antes da cascata, os mocks de `reimbursements.spec.ts` ainda nao cobriam `/reimbursements/invitations` e `/reimbursements/memberships`; isso foi corrigido.
- Reexecucoes posteriores passaram: spec isolado `4 passed` e suite completa `26 passed`.

Warning restante:

- Permanece o warning conhecido de `reportlab==4.2.5` usando `ast.NameConstant`, deprecado para Python 3.14.

Fora de escopo preservado:

- Fundacao 4 nao foi iniciada.
- Comentarios, pagamentos, Telegram, OCR, audio, inbox, filas, gateway, Pix e portal corporativo nao foram implementados.

## Fechamento da Fundacao 3 - Validacao PostgreSQL, Payload Guest e Comprovantes

Ambiente e migrations:

- Ambiente usado: PostgreSQL local Docker em `localhost:5432`, banco `financy_dev`, validado pelo script seguro anti-remoto.
- Comando executado: `powershell.exe -ExecutionPolicy Bypass -File .\scripts\setup_dev_db.ps1 -ResetSchema`.
- Resultado: migrations `001` a `007` aplicadas com sucesso no PostgreSQL local.
- Criada migration incremental `docs/supabase/migrations/008_reimbursement_claim_attachments.sql`.
- Comando incremental executado: `backend/.venv/Scripts/python.exe scripts/apply_migrations.py --database-url postgresql://financy_dev:***@localhost:5432/financy_dev`.
- Resultado incremental: somente `008_reimbursement_claim_attachments.sql` aplicada.
- Reexecucao do aplicador sem reset: `Migrations applied: none`, validando idempotencia operacional via `schema_migrations`.
- Inspecao de schema: `21 public tables`.
- Nenhuma migration foi executada em Supabase remoto ou producao.

Schema criado no fechamento:

- `reimbursement_invitations` pela migration 007:
  - `token_hash` unico;
  - `owner_user_id`, `contact_id`, `claim_id`, `email`, `status`, `expires_at`, `accepted_at`, `accepted_by_user_id`, `revoked_at`, `created_at`;
  - indices por owner/contact/status/claim.
- `reimbursement_memberships` pela migration 007:
  - `owner_user_id`, `contact_id`, `auth_user_id`, `email`, `status`, `linked_at`, `revoked_at`, `created_at`;
  - unique parcial para membership ativo por owner/contact/auth user.
- `reimbursement_claim_attachments` pela migration 008:
  - vinculo explicito entre claim e stored file;
  - unique parcial por `claim_id` + `file_id` quando ativo;
  - indices por owner, claim e file.

Token e seguranca:

- Token bruto e retornado somente na criacao do convite, para montagem do link.
- Listagens de convites nao retornam token bruto.
- Banco persiste somente SHA-256 em `token_hash`.
- Aceite PostgreSQL usa `select ... for update` no convite e `on conflict` no membership ativo.
- Aceite duplicado pelo mesmo usuario retorna o mesmo membership ativo.
- E-mail e normalizado com `casefold`.
- Convites expirados, revogados, com e-mail diferente ou de outro usuario retornam erro generico de convite invalido/expirado.
- Divida tecnica registrada: rate limiting especifico para aceite de convite ainda nao foi implementado.

Contrato guest:

- Endpoints guest passaram a usar schema proprio limitado.
- Guest recebe: id publico da claim, titulo, descricao, status, vencimento, total, datas compartilhaveis, quantidade de comprovantes e itens sanitizados.
- Guest nao recebe: `owner_user_id`, `contact_id`, `transaction_id`, `account_id`, `card_id`, `storage_path`, payload bruto da transacao, `source_signature` ou metadados internos.

Comprovantes:

- Anexos de transacao nao sao compartilhados automaticamente.
- Owner precisa compartilhar arquivo explicitamente com uma cobranca.
- Guest lista somente comprovantes vinculados a `reimbursement_claim_attachments` ativos.
- Signed URL guest exige membership ativo, claim autorizada, attachment ativo e arquivo liberado pelo FileService.
- Arquivo deleted/quarantined/rejected/suspicious continua bloqueado pela Fundacao 0/FileService.
- Revogacao de membership bloqueia novas listas e novas signed URLs.
- `storage_path` nunca e retornado ao guest.

Reconhecimento, contestacao e revogacao:

- `acknowledge` e idempotente.
- `dispute` exige motivo.
- Guest nao envia status livremente.
- Contestacao nao altera itens, valores ou snapshots.
- Owner ve eventos de dominio.
- Revogar membership bloqueia lista, detalhe, acknowledge, dispute, comprovantes e novas signed URLs; historico permanece.

Comentarios:

- Decisao formal: comentarios ficam para **Fundacao 3.5**, antes de pagamentos.
- Justificativa: contestacao sem conversa estruturada fica incompleta, mas deve ser implementada em tarefa separada para nao misturar com auditoria/seguranca.

Validacoes executadas:

- Backend completo: `backend/.venv/Scripts/python.exe -m pytest` -> `92 passed, 1 warning in 16.19s`.
- PostgreSQL real: `TEST_DATABASE_URL=postgresql://financy_dev:***@localhost:5432/financy_dev_test; backend/.venv/Scripts/python.exe -m pytest tests_postgres -m postgres -q` -> `9 passed in 11.45s`.
- Frontend typecheck: `npm.cmd run typecheck` -> passou.
- Frontend lint: `npm.cmd run lint` -> passou.
- Frontend build: `npm.cmd run build` -> passou.
- E2E ressarcimentos: `npx.cmd playwright test tests/e2e/reimbursements.spec.ts --reporter=line` -> `5 passed (13.9s)`.
- E2E completo: `npm.cmd run e2e` -> `27 passed (52.0s)`.

Warning restante:

- Permanece o warning conhecido de `reportlab==4.2.5` usando `ast.NameConstant`, deprecado para Python 3.14.

Fora de escopo preservado:

- Pagamentos e Fundacao 4 nao foram iniciados.
- Telegram, OCR, audio, inbox, filas, gateway e Pix nao foram implementados.

## Ajuste do smoke Supabase Storage - DATABASE_URL fallback

Status: concluido.

Alteracao:

- `scripts/smoke_supabase_storage.ps1` agora resolve a URL de metadata nesta ordem:
  1. parametro explicito `-DatabaseUrl`;
  2. variavel da sessao `$env:DATABASE_URL`;
  3. `DATABASE_URL` em `backend/.env`.
- O parser de `backend/.env`:
  - ignora comentarios;
  - ignora linhas vazias;
  - aceita linhas `KEY=VALUE`;
  - aceita valor entre aspas simples ou duplas;
  - le somente `DATABASE_URL`;
  - nao sobrescreve variavel de sessao;
  - nao carrega nem imprime outros secrets.
- O script imprime apenas a URL mascarada, por exemplo `postgresql://user:***@localhost:5432/db`.
- A protecao contra ambiente de producao permanece no smoke Python (`backend/scripts/smoke_supabase_storage.py`).

Documentacao:

- `scripts/README.md` atualizado com a ordem de resolucao e comportamento do parser.

Testes executados:

- Parametro explicito tem prioridade sobre variavel de sessao e `.env`: passou.
- Variavel `$env:DATABASE_URL` e usada quando nao ha parametro: passou.
- Fallback para `backend/.env` quando nao ha parametro nem variavel de sessao: passou.
- Ausencia total de URL retorna erro claro `DATABASE_URL is required`: passou.
- Valor com aspas em `backend/.env` e aceito: passou.

Observacao:

- Os testes esperaram falha do smoke real porque Supabase dev ainda nao esta configurado, mas validaram a resolucao da URL e a mascara sem imprimir senha.

## Fundacao 2.5 - Rodada final de validacao

Status: concluido para avanco tecnico; nao foi iniciada a Fundacao 3.

PostgreSQL local:

- Container `financy-postgres-1` confirmado como `healthy`.
- Ambiente: `postgresql://financy_dev:***@localhost:5432/financy_dev`.
- Migrations idempotentes:
  - `backend/.venv/Scripts/python.exe scripts/apply_migrations.py` -> `Migrations applied: none`.
- Schema inspecionado:
  - `18` tabelas publicas;
  - `25` indices das fundacoes de arquivos/ressarcimentos;
  - `0` transacoes no banco dev descartavel.

Backend:

- Suite local/unitaria: `backend/.venv/Scripts/python.exe -m pytest` -> `88 passed, 1 warning in 15.92s`.
- Suite PostgreSQL real: `backend/.venv/Scripts/python.exe -m pytest tests_postgres -m postgres` -> `5 passed in 6.22s`.
- Concorrencia real permanece validada com conexoes independentes e `SELECT ... FOR UPDATE`.

Frontend:

- `npm.cmd run typecheck` -> passou.
- `npm.cmd run lint` -> passou.
- `npm.cmd run build` -> passou.
- `npm.cmd run e2e` -> `26 passed (49.3s)`.

Supabase Storage dev:

- Ambiente lido sem imprimir secrets:
  - `ENVIRONMENT=development`;
  - `PRIVATE_FILES_BACKEND=supabase`;
  - `FILE_STORAGE_PROVIDER=supabase`;
  - bucket configurado: `private-files`;
  - Supabase URL identificada apenas pelo host.
- Smoke real executado:
  - `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke_supabase_storage.ps1`;
  - resultado: `Supabase Storage smoke passed with metadata database postgresql://financy_dev:***@localhost:5432/financy_dev`;
  - signed URL foi gerada/validada sem ser impressa.
- Testes do fallback de `DATABASE_URL` do wrapper:
  - parametro explicito: passou;
  - variavel da sessao: passou;
  - fallback para `backend/.env`: passou;
  - variavel ausente: passou;
  - valor com aspas: passou.

Warning restante:

- Permanece apenas o warning de dependencia do `reportlab==4.2.5` sobre `ast.NameConstant` deprecado para Python 3.14.
- Decisao mantida: nao fazer upgrade nessa etapa para nao arriscar fluxo de PDF/importacao.

Conclusao:

- Fundacao 2.5 esta finalizada do ponto de vista de infraestrutura/testes locais e smoke Supabase dev.
- Pendencia antes de Fundacao 3 nao e bloqueio de teste, e sim decisao/implementacao de produto-seguranca: RLS final e desenho do acesso guest/convites.
- Fundacao 3, portal guest, invitations, memberships, comentarios, pagamentos, Telegram, OCR, audio, inbox e filas nao foram iniciados.

## Correcao de deploy Render - migrations remotas seguras

Status: concluido.

Causa:

- O start command do Render executa `python scripts/apply_migrations.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- A protecao adicionada para Fundacao 2.5 fazia `apply_migrations.py` recusar qualquer host nao local.
- Em deploy, `DATABASE_URL` aponta para o pooler Supabase remoto (`aws-1-sa-east-1.pooler.supabase.com`), entao o script encerrava com status `1` antes de subir o `uvicorn`.

Correcao:

- `backend/scripts/apply_migrations.py` agora diferencia:
  - banco local: aplica migrations normalmente;
  - banco remoto sem autorizacao explicita: faz skip seguro, imprime URL mascarada e retorna sucesso;
  - banco remoto com `--allow-remote` ou `FINANCY_ALLOW_REMOTE_MIGRATIONS=true`: aplica migrations intencionalmente;
  - `--reset-schema` em remoto: continua bloqueado.
- Nenhuma migration remota foi executada nesta correcao.
- Nenhum secret foi impresso.

Testes executados:

- URL remota falsa igual ao host do erro do Render:
  - comando: `DATABASE_URL=postgresql://postgres:secret@aws-1-sa-east-1.pooler.supabase.com:5432/postgres python scripts/apply_migrations.py`;
  - resultado: `Remote database detected; skipping migrations by default.` com exit `0`.
- URL local dev:
  - comando: `DATABASE_URL=postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev python scripts/apply_migrations.py`;
  - resultado: `Migrations applied: none`.
- Reset destrutivo remoto:
  - comando: `python scripts/apply_migrations.py --reset-schema` com URL remota falsa;
  - resultado: bloqueado com exit `1`.

Documentacao:

- `README.md` atualizado para explicar o skip seguro em deploy remoto.
- `deploy-checklist.md` atualizado para refletir que migrations remotas nao sao aplicadas automaticamente sem opt-in.

## Ambiente dev reproduzivel - fechamento das pendencias da Fundacao 2.5

Status: concluido para PostgreSQL local; Supabase Storage real preparado e pendente de credenciais/projeto dev.

Seguranca de ambiente:

- Nenhuma URL remota foi usada para migrations.
- Nenhum projeto Supabase de producao foi acessado.
- Nenhum secret real foi impresso ou adicionado ao repositorio.
- Scripts de dev recusam hosts fora de `localhost`, `127.0.0.1`, `::1` ou `postgres`.
- Identificadores de banco sao exibidos com senha mascarada.

PostgreSQL local reproduzivel:

- `docker-compose.yml` agora usa PostgreSQL `postgres:16-alpine` com:
  - database: `financy_dev`;
  - user: `financy_dev`;
  - senha local: `financy_dev_local`;
  - volume nomeado `postgres_data`;
  - healthcheck;
  - porta configuravel por `POSTGRES_PORT`.
- Criado `scripts/setup_dev_db.ps1`.
- O script valida Docker, sobe `postgres`, aguarda healthcheck, valida URL local, aplica migrations e inspeciona schema.
- `-ResetSchema` recria o schema public.
- `-ResetVolume` recria apenas o volume local do PostgreSQL no script corrigido.
- Observacao: uma primeira tentativa usou `docker compose down -v` para remover o volume antigo com credenciais anteriores; o script foi corrigido em seguida para preservar demais volumes/servicos.

Migrations aplicadas localmente:

- Ambiente: PostgreSQL local descartavel `postgresql://financy_dev:***@localhost:5432/financy_dev`.
- Comando: `.\scripts\setup_dev_db.ps1 -ResetVolume -ResetSchema`, depois `.\scripts\setup_dev_db.ps1 -ResetSchema`.
- Resultado aplicado:
  - `001_initial_schema.sql`;
  - `002_default_categories.sql`;
  - `003_phase2_indexes.sql`;
  - `004_nullable_card_account.sql`;
  - `005_private_files.sql`;
  - `006_reimbursements_domain.sql`.
- Schema inspecionado:
  - `18` tabelas publicas;
  - `25` indices das fundacoes de arquivos/ressarcimentos;
  - `0` transacoes existentes no banco descartavel.
- Idempotencia validada sem reset:
  - `backend/.venv/Scripts/python.exe scripts/apply_migrations.py` -> `Migrations applied: none`.
- Container confirmado:
  - `financy-postgres-1`;
  - imagem `postgres:16-alpine`;
  - status `healthy`;
  - porta `5432`.

Repository PostgreSQL real:

- Criado `backend/tests_postgres/test_reimbursements_postgres.py` com marker `postgres`.
- Criado `backend/pytest.ini` para manter a suite padrao em `backend/tests` e separar testes com infraestrutura.
- Comando:
  - `cd backend`;
  - `$env:TEST_DATABASE_URL='postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev_test'`;
  - `.\.venv\Scripts\python.exe -m pytest tests_postgres -m postgres`.
- Resultado: `5 passed in 6.85s`.
- Fluxos cobertos em PostgreSQL real:
  - criar/editar/inativar contato;
  - criar claim draft;
  - adicionar item;
  - atualizar valor parcial;
  - atualizar snapshot;
  - finalizar claim;
  - bloquear edicao apos `sent`;
  - cancelar;
  - liberar saldo;
  - listar timeline.

Concorrencia real:

- Testes usam conexoes/pools independentes contra PostgreSQL real.
- Cenario principal validado:
  - transacao expense de R$ 100;
  - duas claims diferentes tentam alocar R$ 70 simultaneamente;
  - exatamente uma operacao conclui;
  - a outra retorna `reimbursement_amount_exceeds_transaction`;
  - total persistido permanece `<= R$ 100`.
- Cenarios adicionais cobertos:
  - atualizacao simultanea de dois itens;
  - cancelamento concorrente com inclusao;
  - retry/duplicidade na mesma claim;
  - item draft reservando saldo;
  - claim canceled liberando saldo.
- A protecao exercitada e a do repository PostgreSQL com `SELECT ... FOR UPDATE` na transacao financeira.

Supabase Storage dev:

- Criado `backend/scripts/smoke_supabase_storage.py`.
- Criado wrapper `scripts/smoke_supabase_storage.ps1`.
- Configuracao preparada com aliases:
  - `FILE_STORAGE_PROVIDER`;
  - `SUPABASE_STORAGE_BUCKET`;
  - `SIGNED_URL_TTL_SECONDS`;
  - `FILE_SCAN_PROVIDER`.
- Smoke test preparado para:
  - recusar `APP_ENV=production`;
  - exigir provider `supabase`;
  - verificar bucket privado;
  - fazer upload de PNG de teste;
  - confirmar metadata em `stored_files`;
  - gerar signed URL sem imprimi-la;
  - soft delete;
  - confirmar bloqueio de nova URL;
  - remover objeto e metadata de teste.
- Smoke real nao foi executado porque `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` e bucket dev nao estao configurados.
- Comando executado sem credenciais/provider:
  - `backend/.venv/Scripts/python.exe scripts/smoke_supabase_storage.py --database-url <local>`;
  - resultado esperado: `PRIVATE_FILES_BACKEND must be 'supabase' for this smoke test.`

Documentacao atualizada:

- `README.md`:
  - como iniciar PostgreSQL;
  - como aplicar migrations;
  - como resetar schema/volume dev;
  - como rodar testes PostgreSQL;
  - checklist Supabase Storage dev;
  - nota de RLS/service role.
- `scripts/README.md`:
  - comandos curtos para setup DB, testes PostgreSQL e smoke Supabase.
- `docs/postgres-migration-checklist.md`:
  - URLs e comandos atualizados para `financy_dev`.

Validacoes finais:

- Backend unitario/local: `backend/.venv/Scripts/python.exe -m pytest` -> `88 passed, 1 warning in 17.27s`.
- Backend PostgreSQL: `backend/.venv/Scripts/python.exe -m pytest tests_postgres -m postgres` -> `5 passed in 6.85s`.
- Frontend typecheck: `npm.cmd run typecheck` -> passou.
- Frontend lint: `npm.cmd run lint` -> passou.
- Frontend build: `npm.cmd run build` -> passou.
- Frontend E2E: `npm.cmd run e2e` -> `26 passed (52.0s)`.

Warning restante:

- Permanece o warning de dependencia `reportlab==4.2.5` usando `ast.NameConstant`, deprecado para Python 3.14.
- Nao foi feito upgrade nesta etapa para evitar risco indireto no fluxo de PDF/importacao.

Dvidas tecnicas restantes:

- Configurar um projeto Supabase development/staging real e bucket privado para executar o smoke de storage.
- Avaliar upgrade controlado do ReportLab em tarefa isolada.
- Implementar RLS final antes de qualquer exposicao publica ampla, especialmente para `stored_files`, `transaction_attachments`, `stored_file_events`, `reimbursement_contacts`, `reimbursement_claims`, `reimbursement_items` e `reimbursement_events`.

Fora de escopo preservado:

- Fundacao 3 nao foi iniciada.
- Portal guest, invitations, memberships, comentarios, pagamentos, Telegram, OCR, audio, inbox e filas nao foram implementados.

## Fundacao 3.5 - Etapa B backend

Data: 2026-07-13.

Escopo executado:

- Migrations backend/PostgreSQL para comentarios e rate limit de convites.
- Backend de comentarios em ressarcimentos.
- Rate limiting persistente no aceite de convites.
- Testes unitarios e PostgreSQL reais.
- Documentacao operacional de variaveis e checklist.

Arquivos criados:

- `docs/foundation-3.5-plan.md`;
- `docs/environments.md`;
- `docs/deploy-checklist.md`;
- `docs/supabase/migrations/009_reimbursement_comments.sql`;
- `docs/supabase/migrations/010_invitation_accept_rate_limits.sql`.

Arquivos alterados:

- `backend/.env.example`;
- `backend/.env.production.example`;
- `backend/app/api/reimbursements.py`;
- `backend/app/core/config.py`;
- `backend/app/models/enums.py`;
- `backend/app/repositories/local_json.py`;
- `backend/app/repositories/postgres.py`;
- `backend/app/schemas/reimbursements.py`;
- `backend/app/services/reimbursement_service.py`;
- `backend/tests/test_reimbursements_api.py`;
- `backend/tests_postgres/test_reimbursements_postgres.py`;
- `output.md`;
- `plan.md`;
- `task.md`.

Modelo final:

- `reimbursement_comments` guarda comentarios por claim com `owner_user_id`, `claim_id`, `author_user_id`, `author_role`, `body`, timestamps e soft delete.
- Comentarios sao imutaveis nesta versao; exclusao e logica.
- `reimbursement_invitation_accept_attempts` guarda somente `token_hash`, `ip_hash`, usuario autenticado opcional, timestamp e resultado.
- Token bruto e IP bruto nao sao persistidos.

Endpoints implementados:

- `GET /reimbursements/claims/{claim_id}/comments`;
- `POST /reimbursements/claims/{claim_id}/comments`;
- `DELETE /reimbursements/claims/{claim_id}/comments/{comment_id}`.

Regras de autorizacao:

- Owner pode listar/comentar/moderar comentarios de claims proprios.
- Guest precisa de membership ativa e claim compartilhada.
- Guest pode excluir somente comentario proprio.
- Guest revogado ou sem acesso recebe bloqueio sem acessar comentarios.
- `author_user_id`, `author_role`, `deleted_at` e dados internos nao sao aceitos do cliente.

Rate limiting:

- Configurado por:
  - `INVITATION_ACCEPT_RATE_LIMIT_ENABLED`;
  - `INVITATION_ACCEPT_RATE_LIMIT_MAX_ATTEMPTS`;
  - `INVITATION_ACCEPT_RATE_LIMIT_WINDOW_SECONDS`.
- Implementacao principal usa PostgreSQL com lock transacional via advisory lock por `token_hash` + `ip_hash`.
- Repository local simula a mesma regra com lock para testes deterministicos.
- Excesso retorna `429` com `reimbursement_invitation_rate_limited`.

RLS:

- Nao foi criada migration `011`.
- Decisao: RLS final permanece para a Etapa D, porque esta etapa nao aplica policies remotas e nao deve criar migration vazia.
- Autorizacao backend foi reforcada e testada; service role permanece exclusiva do backend.

Validacoes:

- `cd backend; .venv\Scripts\python.exe -m pytest tests\test_reimbursements_api.py -q` -> `26 passed in 5.97s`.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_dev_db.ps1 -ResetSchema` -> migrations `001` a `010` aplicadas no PostgreSQL local `localhost`.
- `cd backend; $env:TEST_DATABASE_URL='postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev_test'; .venv\Scripts\python.exe -m pytest tests_postgres -m postgres -q` -> `14 passed in 18.33s`.
- `cd backend; .venv\Scripts\python.exe -m pytest` -> `99 passed, 1 warning in 17.43s`.

Warning restante:

- Permanece o warning conhecido do ReportLab em `reportlab/lib/rl_safe_eval.py` sobre `ast.NameConstant` deprecado para Python 3.14.

Pendencias:

- Etapa C: frontend owner e portal guest para comentarios.
- Etapa D: auditoria RLS final, hardening de fallback de API URL, documentacao final e validacoes completas.
- Frontend nao foi implementado nesta etapa.
- Pagamentos, Telegram, OCR, audio, inbox, filas e Fundacao 4 nao foram iniciados.

## Fundacao 3.5 - Etapa C frontend

Data: 2026-07-13.

Escopo executado:

- UI owner para comentarios no detalhe de cobranca de ressarcimento.
- UI guest para comentarios no portal `/guest/reimbursements`.
- Integracao frontend com endpoints de comentarios ja existentes.
- Testes E2E para owner e guest.
- Documentacao da etapa e pendencias para Etapa D.

Arquivos criados:

- `frontend/src/components/reimbursement-comments.tsx`.

Arquivos alterados:

- `frontend/src/components/reimbursements-content.tsx`;
- `frontend/src/components/guest-reimbursements-content.tsx`;
- `frontend/src/lib/api.ts`;
- `frontend/src/lib/types.ts`;
- `frontend/tests/e2e/reimbursements.spec.ts`;
- `docs/foundation-3.5-plan.md`;
- `docs/deploy-checklist.md`;
- `output.md`;
- `plan.md`;
- `task.md`.

Comportamento implementado:

- Owner e guest autorizados listam comentarios em ordem cronologica.
- Comentarios usam texto puro, trim obrigatorio e limite de 2000 caracteres.
- O envio atualiza a lista sem reload completo.
- Exclusao logica e acionada por dialog proprio, sem `window.confirm`.
- Owner pode acionar moderacao quando o backend autoriza; guest ve apenas exclusao de comentarios proprios.
- HTML digitado no comentario e exibido como texto, sem parser Markdown e sem `dangerouslySetInnerHTML`.
- Erros `401`, `403`, `404`, `409`, `422` e `429` sao convertidos em mensagens amigaveis.

Endpoints consumidos:

- `GET /reimbursements/claims/{claim_id}/comments`;
- `POST /reimbursements/claims/{claim_id}/comments`;
- `DELETE /reimbursements/claims/{claim_id}/comments/{comment_id}`.

Validacoes:

- `cd frontend; npm.cmd run typecheck` -> passou.
- `cd frontend; npm.cmd run lint` -> passou.
- `cd frontend; npm.cmd run build` -> passou.
- `cd frontend; npx.cmd playwright test -g comments --reporter=line` -> `2 passed`.
- `cd frontend; npm.cmd run e2e` -> `29 passed (49.5s)`.
- `cd backend; .venv\Scripts\python.exe -m pytest` -> `99 passed, 1 warning in 17.12s`.

Warning restante:

- Permanece o warning conhecido do ReportLab em `reportlab/lib/rl_safe_eval.py` sobre `ast.NameConstant` deprecado para Python 3.14.

Pendencias:

- Etapa D: auditoria RLS final, revisao de signed URLs/attachments, hardening do fallback de API URL e validacao final.
- Testes unitarios dedicados de componente frontend nao foram adicionados porque o projeto segue cobrindo estes fluxos por Playwright E2E; a cobertura nova foi adicionada na suite E2E existente.
- Pagamentos, Telegram, OCR, audio, inbox, filas e Fundacao 4 nao foram iniciados.

## Fundacao 3.5 - Etapa D fechamento

Data: 2026-07-13.

Escopo executado:

- Auditoria final de RLS/Data API.
- Hardening de acesso direto a tabelas financeiras.
- Revisao de signed URLs e anexos.
- Protecao contra fallback remoto silencioso de API URL.
- Observabilidade segura para eventos sensiveis.
- Testes PostgreSQL, backend, frontend e E2E.

Migration criada:

- `docs/supabase/migrations/011_reimbursements_security_hardening.sql`.

Decisao RLS:

- O FastAPI permanece como unica camada funcional de acesso aos dados.
- A migration `011` habilita RLS e revoga privilegios diretos de `PUBLIC`, `anon` e `authenticated` em tabelas financeiras, imports, arquivos privados e ressarcimentos.
- Nao foram criadas policies permissivas para Data API nesta fundacao.
- Service role continua exclusiva do backend/Storage e nao deve ser exposta ao frontend.

Auditoria de signed URLs e anexos:

- Anexos de transacao nao sao compartilhados automaticamente.
- Guest acessa somente `reimbursement_claim_attachments` explicitamente compartilhados.
- Membership revogada bloqueia novas signed URLs por meio da autorizacao em `_guest_claim`.
- Arquivos `deleted`, em quarentena ou sem scan liberado nao geram novas URLs.
- Respostas publicas nao expõem `storage_path`, bucket interno ou service role.
- Uma URL ja emitida pode continuar valida ate expirar, mitigada por TTL curto.

Protecao de API URL:

- Criado helper `frontend/src/lib/api-url.ts`.
- `frontend/src/lib/api.ts` e `frontend/src/lib/server-api.ts` usam resolucao centralizada.
- Fallback local para `http://127.0.0.1:8000` fica restrito a desenvolvimento local.
- Preview/Production falham explicitamente se `NEXT_PUBLIC_API_URL` estiver ausente, malformada, sem `https`, com credenciais ou apontando para localhost.
- Criados scripts `check-api-url-config.mjs` e `test-api-url-config.mjs`.

Observabilidade segura:

- Logs adicionados para comentario criado/removido, convite bloqueado por rate limit, acesso negado a attachment e falha de signed URL.
- Logs nao registram body do comentario, token, token hash, IP bruto, JWT, service role, senha, URL assinada completa ou conteudo financeiro.

Validacoes:

- `cd frontend; npm.cmd run test:api-url` -> passou.
- `cd frontend; npm.cmd run typecheck` -> passou.
- `cd backend; .venv\Scripts\python.exe -m pytest tests_postgres -m postgres -q` sem `TEST_DATABASE_URL` -> falhou como esperado com mensagem clara.
- `cd backend; $env:TEST_DATABASE_URL='postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev_test'; .venv\Scripts\python.exe -m pytest tests_postgres -m postgres -q` -> `14 passed in 20.96s`.

Pendencias residuais:

- Aplicar migrations `009`, `010` e `011` em Supabase Dev/Production somente com autorizacao explicita por ambiente.
- Validar smoke remoto apos deploy Dev/Preview.
- Revisar upgrade do ReportLab em tarefa separada.
- Pagamentos, Telegram, OCR, audio, inbox, filas e Fundacao 4 nao foram iniciados.

## Fundacao 3.5 - Implantacao Dev

Data: 2026-07-14.

Estado inicial:

- Branch `dev`.
- Commit versionado em `dev`/`origin/dev`: `20d3c09 feat: fecha fundacao 3.5 com hardening de seguranca`.
- Worktree limpo antes da implantacao remota.
- Migrations versionadas: `001` a `011`.

Validacoes locais executadas antes de qualquer operacao remota:

- `git branch --show-current` -> `dev`.
- `git status --short` -> limpo.
- `git diff --stat` -> vazio.
- `git diff --check` -> passou.
- Backend: `.venv\Scripts\python.exe -m pytest` -> `99 passed, 1 warning`.
- PostgreSQL real local: `TEST_DATABASE_URL` local + `pytest tests_postgres -m postgres -q` -> `14 passed`.
- Frontend `npm.cmd run test:api-url` -> passou.
- Frontend `npm.cmd run typecheck` -> passou.
- Frontend `npm.cmd run lint` -> passou.
- Frontend `npm.cmd run build` -> passou.
- Frontend `npm.cmd run e2e` -> `29 passed`.

Auditoria local:

- Arquivos locais `.env` e `.uploads` existem apenas no workspace local e nao estavam staged.
- Nenhum secret foi identificado como staged.
- Nao houve chamada para Production durante as validacoes locais.

Migrations Dev:

- Aplicacao remota feita pelo operador no terminal local com `DATABASE_URL` do Supabase Dev e `--allow-remote`.
- `--reset-schema` nao foi usado.
- Migrations pendentes aplicadas: `009_reimbursement_comments.sql`, `010_invitation_accept_rate_limits.sql`, `011_reimbursements_security_hardening.sql`.
- Idempotencia confirmada com nova execucao: `Migrations applied: - none`.

Validacao Supabase Dev:

- `schema_migrations` contem `001` a `011`.
- `has_001_to_011=True`.
- RLS habilitado para `reimbursement_claim_attachments`, `reimbursement_claims`, `reimbursement_comments`, `reimbursement_invitation_accept_attempts`, `reimbursement_memberships`, `stored_files`, `transaction_attachments` e `transactions`.
- `public_grants_count=0` para as tabelas criticas validadas.
- Indices confirmados: `reimbursement_claim_attachments_active_file_idx`, `reimbursement_comments_claim_active_idx`, `reimbursement_invitation_attempts_window_idx`.
- Tabelas novas confirmadas: `reimbursement_comments`, `reimbursement_invitation_accept_attempts`.

Smoke remoto Dev sem credenciais:

- Backend Dev `https://financy-svme.onrender.com/health` -> `200`, body `{"status":"ok"}`.
- Frontend Preview `https://financy-git-dev-gabriel-arnon1.vercel.app/` -> `200`.
- Rotas publicas/estaticas `/login`, `/reimbursements` e `/guest/reimbursements` -> `200`.
- Endpoint autenticado `/reimbursements/claims` sem token -> `401 unauthenticated`, comportamento esperado.
- HTML inicial e 65 assets JS publicos verificados: sem `localhost`, `127.0.0.1`, backend production antigo ou frontend production.

Nao validado automaticamente:

- Fluxos autenticados reais de login/logout, comentarios owner/guest, exclusao, invitations, memberships, attachments, signed URLs, revogacao e rate limit em Dev dependem de sessao autenticada e smoke manual.
- Render/Vercel env vars nao foram lidas por CLI nesta maquina porque `render` e `vercel` nao estavam disponiveis.

Riscos residuais:

- Executar smoke manual autenticado em Dev/Preview antes de preparar merge para `main`.
- Aplicar migrations em Production somente em janela propria e com aprovacao explicita.
- Manter o warning conhecido do ReportLab em backlog.

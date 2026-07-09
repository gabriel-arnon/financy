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

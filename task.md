# Financy - Tasks Ativas

## Legenda

- `[x]` Concluída
- `[ ]` Não iniciada
- `[/]` Em andamento
- `[-]` Pausada/cancelada

## Objetivo

Centralizar todas as tasks ativas em um único arquivo: pendências operacionais de produção, inteligência financeira com IA e polish visual/UX.

## PD0 - Confiabilidade em Produção

### [/] PD0.1 - Investigar `Failed to fetch` intermitente

Contexto:

- Em produção, algumas chamadas falham com `Failed to fetch` e depois funcionam ao tentar novamente.
- Retry automático para leituras já foi implementado.
- Escritas não receberam retry automático para evitar duplicidade.

Checklist:

- [ ] Coletar Network real no navegador quando a falha ocorrer.
- [ ] Comparar horário da falha com logs do Render.
- [ ] Confirmar se a API recebeu a requisição.
- [ ] Confirmar se a falha é timeout, cold start, CORS, token ou conexão antes de resposta HTTP.
- [ ] Definir se será necessário idempotency key para escritas.

Resultado esperado:

- Falhas intermitentes ficam explicadas e tratadas sem criar duplicidade de dados.

## PD1 - Performance em Produção

### [/] PD1.1 - Validar performance real após otimizações

Feito:

- Pool de conexões PostgreSQL.
- Otimização de importação e confirmação em lote.
- Benchmark local de confirmação em lote.
- Remoção de logs temporários.

Pendente:

- [ ] Validar ganho real após deploy.
- [ ] Avaliar upgrade do Render Free para instância sempre ligada/mais CPU.
- [ ] Validar suite PostgreSQL quando banco local `financy_test` estiver disponível.

Resultado esperado:

- App responde de forma aceitável em produção, especialmente ao trocar abas e confirmar importações.

## PD2 - Storage Persistente

### [/] PD2.1 - Migrar uploads para storage persistente

Feito:

- Runbook criado em `docs/production-readiness-runbook.md`.
- Recomendação registrada: Supabase Storage como primeira opção.

Pendente:

- [ ] Escolher estratégia definitiva: Supabase Storage, Cloudflare R2 ou disco persistente.
- [ ] Migrar uploads de `.uploads` local do Render.
- [ ] Garantir compatibilidade com imports antigos quando necessário.

Resultado esperado:

- Uploads não dependem do filesystem efêmero do Render.

## PD3 - Backups

### [/] PD3.1 - Confirmar backup e restore

Feito:

- Checklist de backup e restore criado em `docs/production-readiness-runbook.md`.

Pendente:

- [ ] Confirmar backup automático do PostgreSQL/Supabase.
- [ ] Definir backup dos uploads.
- [ ] Executar teste de restauração em ambiente descartável.

Resultado esperado:

- Existe processo validado para recuperar dados em caso de falha.

## PD4 - Segredos

### [/] PD4.1 - Rotacionar segredos compartilhados

Feito:

- Checklist de rotação criado em `docs/production-readiness-runbook.md`.

Pendente:

- [ ] Rotacionar senha do banco.
- [ ] Rotacionar JWT secret.
- [ ] Rotacionar service role key.
- [ ] Atualizar variáveis no Render, Vercel e Supabase.
- [ ] Confirmar que nenhum segredo real está versionado.

Resultado esperado:

- Produção não depende de segredos compartilhados em conversa ou ambiente inseguro.

## PD5 - Smoke Multiusuário em Produção

### [/] PD5.1 - Validar isolamento com usuários reais

Feito:

- Roteiro criado em `docs/production-readiness-runbook.md`.
- Testes backend cobrem isolamento A/B.

Pendente:

- [ ] Criar/usar usuário A e usuário B reais no Supabase.
- [ ] Confirmar que usuário B não vê dados de usuário A.
- [ ] Confirmar que referências cruzadas retornam erro/404.

Resultado esperado:

- Isolamento está validado no ambiente real, não só em teste automatizado.

## PD6 - RLS Supabase

### [/] PD6.1 - Revisar e decidir ativação de RLS

Feito:

- Draft de RLS existe em `docs/supabase/rls_phase3_draft.sql`.
- Ordem segura de ativação registrada no runbook.

Pendente:

- [ ] Revisar policies.
- [ ] Decidir se RLS entra ainda na produção privada ou antes de multiusuário público.
- [ ] Testar em staging antes de aplicar no banco real.

Resultado esperado:

- RLS entra como camada adicional sem quebrar scripts ou backend.

## PD7 - Produção Pública

### [/] PD7.1 - Preparar checklist público

Feito:

- Checklist criado em `docs/production-readiness-runbook.md`.

Pendente:

- [ ] Termos de uso.
- [ ] Política de privacidade.
- [ ] Exportação/exclusão de dados.
- [ ] Rate limiting.
- [ ] Monitoramento/logs de erro.
- [ ] Plano de rollback operacional.

Resultado esperado:

- App fica preparado para sair de uso privado e caminhar para produção pública.

## P6 - Inteligência Financeira com IA

### [/] P6.1 - Classificação automática contínua

Objetivo:

- Sugerir categorias para transações novas ou sem categoria com base no histórico do usuário, sem sobrescrever regras determinísticas de maior prioridade.

Feito:

- Criado endpoint `/ai-finance/overview` com sugestões de categoria para transações sem categoria a partir do histórico do usuário.
- Sugestões aparecem no dashboard e não alteram transações automaticamente.

Checklist:

- [x] Mapear transações categorizadas do usuário como contexto de aprendizado.
- [x] Criar schema de sugestão de categoria com categoria existente e justificativa.
- [x] Gerar sugestão apenas para transações sem categoria no MVP.
- [x] Preservar regras determinísticas existentes como prioridade.
- [x] Exibir sugestão ao usuário antes de alterar a transação.
- [ ] Adicionar confiança numérica às sugestões.
- [ ] Permitir aplicar sugestão em lote para transações selecionadas.
- [ ] Criar testes com resposta mockada da IA.

### [/] P6.2 - Criação inteligente de regras

Objetivo:

- Sugerir regras de classificação a partir de comerciantes recorrentes, descrições parecidas e categorias aplicadas pelo usuário.

Feito:

- Detecta descrições recorrentes com mesma categoria.
- Evita sugerir keywords já cobertas por regras ativas.
- Exibe sugestões no dashboard com keyword, categoria, tipo e ocorrências.

Checklist:

- [x] Identificar grupos de transações similares com mesma categoria.
- [x] Detectar se já existe regra equivalente ou sobreposta por keyword ativa.
- [x] Gerar sugestão com keyword, categoria, tipo, ocorrências e justificativa.
- [x] Exibir sugestões no painel de IA do dashboard.
- [ ] Permitir criar regra individualmente.
- [ ] Permitir descartar sugestão.
- [x] Evitar regras duplicadas por keyword já existente.
- [ ] Criar testes para sugestão, duplicidade e descarte.

### [/] P6.3 - Resumo financeiro mensal

Objetivo:

- Gerar resumo mensal em linguagem natural com entradas, saídas, resultado, categorias em alta, maiores gastos e pontos de atenção.

Feito:

- Criado resumo financeiro em `/ai-finance/overview`.
- Dashboard exibe resumo, insights, loading e erro.

Checklist:

- [x] Definir agregados usados pelo resumo sem alterar transações.
- [x] Criar endpoint de resumo financeiro inicial.
- [ ] Incluir comparação com período anterior quando houver dados.
- [x] Destacar maior categoria de gastos do período analisado.
- [x] Destacar relação entre entradas e saídas.
- [x] Mostrar resumo no dashboard.
- [x] Criar estado de loading e erro.
- [ ] Criar testes com resposta mockada da IA.

### [x] P6.8 - Insights: criacao assistida de categorias

Objetivo:

- Permitir criar categorias diretamente no card de Insights do dashboard, para casos em que a IA identifica corretamente o padrao da transacao, mas ainda nao existe uma categoria pertinente e a classificacao acaba caindo em uma alternativa ruim.

Feito:

- Card de Insights recebeu bloco de Categorias com acao `Adicionar categoria`.
- Criacao usa a API existente de categorias, preservando isolamento por usuario e sem aceitar `user_id` do cliente.
- Categoria criada atualiza a lista local do dashboard e passa a aparecer imediatamente no dialogo de criacao de regras sugeridas.
- Insights sao recarregados apos a criacao, permitindo que sugestoes futuras considerem a nova taxonomia.

Checklist:

- [x] Mapear lacuna entre classificacao automatica e ausencia de categoria pertinente.
- [x] Adicionar CTA de categoria dentro de Insights.
- [x] Reutilizar contrato existente de categoria com nome, tipo e status.
- [x] Exibir confirmacao por toast e erro por toast.
- [x] Atualizar opcoes de categoria usadas por regras sugeridas sem reload da pagina.
- [x] Cobrir fluxo em E2E mockado.

### [/] P6.4 - Busca em linguagem natural

Objetivo:

- Permitir buscas como `quanto gastei com mercado em junho?` ou `mostre gastos do cartão Inter acima de R$ 100`.

Feito:

- Criado endpoint `/ai-finance/ask`.
- Dashboard permite perguntas simples por tipo, categoria e mês.
- Backend calcula filtros em código e não executa SQL livre.

Checklist:

- [x] Definir intents MVP: somar por tipo, categoria e mês.
- [x] Criar schema estruturado de pergunta/resposta sem SQL livre.
- [x] Validar filtros no backend antes de executar.
- [x] Reutilizar repository existente.
- [x] Exibir resultado como resumo com total e quantidade.
- [ ] Listar transações encontradas conforme intent.
- [ ] Suportar filtros por origem/cartão e valor mínimo.
- [ ] Tratar perguntas fora do escopo com mensagem clara.
- [ ] Criar testes contra prompt injection e filtros inválidos.

### [/] P6.5 - Perguntas sobre finanças

Objetivo:

- Criar um assistente de perguntas financeiras baseado em dados agregados e transações do usuário.

Feito:

- Criada UI de pergunta/resposta no dashboard.
- Respostas usam dados do usuário autenticado e mostram total/quantidade analisada.

Checklist:

- [x] Definir escopo permitido inicial de perguntas.
- [x] Criar camada de contexto com dados agregados, categorias e transações relevantes.
- [x] Evitar envio a provider externo neste MVP.
- [x] Responder com base nos dados disponíveis.
- [ ] Adicionar aviso de resposta informativa, sem aconselhamento financeiro profissional.
- [x] Criar UI de painel de pergunta/resposta.
- [ ] Criar testes com mock de IA e controle de escopo.

### [/] P6.6 - Detecção de recorrências

Objetivo:

- Detectar transações recorrentes e sugerir agrupamentos como assinatura, renda fixa, conta mensal ou compra parcelada recorrente.

Feito:

- Detecta recorrências prováveis por descrição normalizada, valor e ocorrência em meses diferentes.
- Exibe recorrências prováveis no dashboard.

Checklist:

- [x] Criar heurística inicial por descrição normalizada, valor e ocorrência mensal.
- [ ] Usar IA/provider externo para nomear/explicar recorrências ambíguas.
- [x] Mostrar recorrências com frequência/ocorrências, valor e cadência provável.
- [ ] Permitir marcar como recorrência confirmada ou ignorar.
- [ ] Usar recorrências confirmadas em resumos e previsões futuras.
- [ ] Criar testes para recorrência mensal, quinzenal e falso positivo.

### [/] P6.7 - Renomear descrições bagunçadas automaticamente

Objetivo:

- Sugerir nomes limpos para transações importadas, mantendo `original_description` salvo.

Feito:

- Gera sugestões de descrição limpa para textos com ruído/caixa alta.
- Mantém `original_description` inalterado e exibe contagem no dashboard.

Checklist:

- [x] Criar schema de normalização com descrição sugerida e justificativa.
- [ ] Adicionar confiança numérica.
- [ ] Aplicar sugestão automaticamente apenas quando confiança for alta e regra do produto permitir.
- [x] Para baixa confiança, mostrar sugestão para aceite manual no dashboard.
- [x] Manter `original_description` inalterado.
- [ ] Permitir aplicar sugestões em lote.
- [ ] Evitar alterar descrições editadas manualmente pelo usuário sem confirmação.
- [ ] Criar testes para descrições com adquirente, Pix, marketplace e assinatura.

## P7 - Polish Visual e UX Operacional

### [x] P7.1 - Sidebar: corrigir acentuação dos labels

Feito:

- Sidebar revisada com labels acentuados para Transações, Contas Bancárias, Cartões de Crédito, Importação e Configurações.

Checklist:

- [x] Revisar todos os itens da sidebar.
- [x] Corrigir `Transacoes` para `Transações`.
- [x] Corrigir `Contas Bancarias` para `Contas Bancárias`.
- [x] Corrigir outros textos sem acento.
- [x] Garantir que labels cabem no layout desktop/mobile.

### [x] P7.2 - Dashboard: cards, gráficos, insights e filtros

Feito:

- Removido card de transações pendentes de revisão.
- Adicionados filtros rápidos, período personalizado, cards recalculados, gráfico de gastos por categoria, barras diárias e insights.
- Dashboard recebeu painel inicial de inteligência financeira.

Checklist:

- [x] Remover card `Transações pendentes de revisão`.
- [x] Adicionar gráficos de gastos por categoria, período ou origem.
- [x] Adicionar área de insights financeiros.
- [x] Adicionar filtros rápidos: esse mês, mês passado, essa semana, semana passada.
- [x] Adicionar período personalizado.
- [x] Garantir que filtros alteram cards, gráficos e insights de forma consistente.
- [ ] Validar responsividade dos gráficos em browser real com screenshots.

### [x] P7.3 - Transações: polish do drawer, status e fluxo de salvar

Feito:

- Removido texto `confirmed` abaixo da data.
- Rodapé do drawer ajustado para evitar linha visual quebrada.
- Campo Origem ganhou truncamento para caber melhor.
- Criação e salvamento fecham o drawer automaticamente.

Checklist:

- [x] Retirar texto `confirmed` abaixo da data da transação.
- [x] Corrigir linha branca bugada no layout do drawer.
- [x] Ajustar tamanho de `Origem` para caber em uma linha quando possível.
- [x] Fechar drawer automaticamente ao criar transação com sucesso.
- [x] Fechar drawer automaticamente ao salvar alterações com sucesso.
- [x] Garantir toasts de sucesso/erro existentes.
- [ ] Validar comportamento mobile em browser real.

### [x] P7.4 - Conta bancária: loading, filtros e layout dos detalhes

Feito:

- Botão `Detalhes` usa loading de navegação.
- Adicionado filtro local por nome, instituição e tipo.
- Cards de cartões vinculados e faturas abertas foram compactados.
- Tabela de últimas transações relacionadas recebeu largura consistente.

Checklist:

- [x] Adicionar loading ao clicar em detalhes.
- [x] Investigar filtro que não funciona ou está lento.
- [x] Corrigir performance/estado do filtro com busca local.
- [x] Ajustar altura dos cards em `Cartões vinculados`.
- [x] Compactar cards de `Faturas abertas`.
- [x] Ajustar comprimento do card `Últimas transações relacionadas`.
- [ ] Validar desktop e mobile em browser real.

### [x] P7.5 - Cartões de crédito: loading, botões, BRL e layout de detalhe

Feito:

- `Ver cartão` mantém loading e layout em uma linha.
- Campo de limite usa máscara BRL na criação e edição.
- Detalhe do cartão coloca `Últimas transações` ao lado de `Histórico de faturas` em desktop e empilha no mobile.
- Payload continua enviado como decimal aceito pela API.

Checklist:

- [x] Adicionar loading ao clicar em `Ver cartão`.
- [x] Ajustar texto e seta do botão `Ver cartão` para ocupar uma linha.
- [x] Adicionar máscara BRL no limite na criação de cartão.
- [x] Adicionar máscara BRL no limite na edição de cartão.
- [x] No detalhe do cartão, colocar `Últimas transações` ao lado direito de `Histórico de faturas` em desktop.
- [x] Manter layout empilhado no mobile.
- [x] Validar payload decimal aceito pela API via typecheck/build e fluxo de payload.

### [x] P7.6 - Importação: feedback, consistência da análise e UX do preview

Feito:

- Removido aviso inline de upload concluído; feedback fica em toast.
- Corrigida consistência da análise quando a diferença calculada é R$ 0,00.
- Card de upload fica oculto quando há preview aberto.
- Adicionado botão `Nova importação`.
- Tabela de preview foi simplificada removendo `País`, `Confiança` e `Status`.

Checklist:

- [x] Retirar aviso inline de upload concluído.
- [x] Usar toast para upload concluído.
- [x] Corrigir inconsistência onde diferença de R$ 0,00 informa que o valor não confere.
- [x] Ao mostrar preview, remover/ocultar card de enviar arquivo.
- [x] Adicionar botão `Nova importação` no canto superior da tela quando houver preview aberto.
- [x] Refazer lista de transações importadas para melhorar UX/UI em MVP.
- [x] Remover colunas `País`, `Confiança` e `Status`.
- [ ] Manter informações importantes acessíveis em detalhe, tooltip ou área secundária.
- [x] Garantir que confirmação de importação continua funcionando via testes backend e build frontend.

## P8 - Configurações: perfil, preferências, aparência e layout

### [x] P8.1 - Finalizar edição de perfil e preferências do usuário

Objetivo:

- Completar a área de perfil e preferências em Configurações, deixando a experiência editável, clara e persistente quando houver suporte atual no app.

Feito:

- Criado componente editável para Perfil e Preferências.
- Nome do usuário é salvo nos metadados do Supabase quando auth está configurado.
- Em modo local/sem Supabase, nome e preferências usam `localStorage`.
- E-mail, idioma e moeda ficam visíveis como campos somente leitura.
- Feedback usa toast de sucesso/erro.

Checklist:

- [x] Revisar estado atual da tela de Configurações.
- [x] Mapear quais dados de perfil já existem no frontend/backend.
- [x] Permitir editar campos de perfil já suportados.
- [x] Permitir editar preferências já suportadas.
- [x] Salvar alterações usando handlers/APIs existentes ou fallback local quando não houver suporte.
- [x] Exibir toast de sucesso/erro.
- [x] Garantir loading e estado vazio.
- [x] Validar responsividade via typecheck/lint/build.

Não feito:

- Persistência backend dedicada para preferências ainda não existe; preferências visuais ficam salvas no navegador.

### [x] P8.2 - Finalizar parte de aparência

Objetivo:

- Completar a seção de Aparência em Configurações, deixando controles visuais coerentes com o design atual.

Feito:

- Seção de Aparência deixou de ser placeholder/desabilitada.
- Adicionados controles de tema, densidade e redução de movimento.
- Preferências são persistidas em `localStorage` e refletidas como `data-*` no documento.
- Feedback usa toast.

Checklist:

- [x] Revisar se já existe suporte a tema, densidade, modo escuro/claro ou preferências visuais.
- [x] Implementar apenas opções suportadas sem criar comportamento falso.
- [x] Persistir preferências no storage existente do frontend.
- [x] Aplicar feedback visual imediato quando seguro.
- [x] Exibir toast de sucesso/erro.
- [x] Garantir que a UI fica consistente com o restante do app.
- [x] Validar responsividade via typecheck/lint/build.

Não feito:

- Tema escuro completo ainda não foi implementado globalmente.

### [x] P8.3 - Compactar categorias e regras em layout lado a lado

Objetivo:

- Reorganizar Configurações para colocar o card de Regras ao lado direito do card de Categorias em desktop, compactando ambos sem perder funcionalidades.

Feito:

- Categorias e Regras agora ficam lado a lado em desktop.
- Layout permanece empilhado no mobile.
- Componentes receberam modo `compact`.
- Formulários e linhas internas foram ajustados para evitar estouro horizontal.

Checklist:

- [x] Revisar componentes atuais de Categorias e Regras.
- [x] Criar layout em grid responsivo com Categorias à esquerda e Regras à direita no desktop.
- [x] Manter layout empilhado no mobile.
- [x] Compactar cabeçalhos, espaçamentos e cards internos.
- [x] Garantir que criação, edição e exclusão continuam funcionando.
- [x] Manter confirmação de exclusão e toasts.
- [x] Validar que listas longas não quebram o layout via ajustes responsivos.

Não feito:

- Validação visual com screenshots em browser real não foi executada nesta entrega.

### [x] P9.1 - Fundacao 2 de Ressarcimentos owner-only

Objetivo:

- Criar interface owner-only de ressarcimentos e fechar concorrencia/snapshots da Fundacao 1.

Feito:

- Navegacao `Ressarcimentos` adicionada.
- Rota `/reimbursements` criada com Visao geral, Cobrancas e Pessoas.
- Contatos podem ser criados, editados e inativados.
- Cobrancas draft podem ser criadas, editadas, receber itens, atualizar snapshots, finalizar e cancelar.
- Acao `Solicitar ressarcimento` adicionada em Transacoes para item individual e selecao em lote.
- Backend usa lock transacional no PostgreSQL para impedir alocacao concorrente acima do valor da despesa.
- Cancelamento libera saldo ressarcivel e preserva historico.
- Snapshots sao preliminares em draft e finalizados no envio.

Nao feito:

- Portal guest, convites, memberships, comentarios, pagamentos, Telegram, OCR, audio, inbox e filas.
- Migrations nao foram executadas.

### [x] P9.2 - Ambiente dev PostgreSQL para Fundacao 2.5

Objetivo:

- Criar e validar ambiente PostgreSQL local reproduzivel para fechar as pendencias tecnicas da Fundacao 2.5.

Feito:

- Docker Compose ajustado para banco local `financy_dev` com credencial apenas de desenvolvimento.
- Criado `scripts/setup_dev_db.ps1` com validacao anti-remoto, healthcheck, migrations e inspecao de schema.
- Migrations `001` a `006` aplicadas com sucesso no PostgreSQL local descartavel.
- Idempotencia validada via `schema_migrations`.
- Criados testes PostgreSQL reais separados por marker `postgres`.
- Repository PostgreSQL validado com fluxo owner-only de ressarcimentos.
- Concorrencia real validada com conexoes independentes e `SELECT ... FOR UPDATE`.
- Criado smoke test seguro para Supabase Storage dev, pendente de credenciais/projeto development.
- Documentacao atualizada em `README.md`, `scripts/README.md`, `docs/postgres-migration-checklist.md` e `output.md`.

Nao feito:

- Smoke real Supabase Storage nao foi executado porque nao ha `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` e bucket dev configurados.
- RLS final ainda nao foi implementada.
- Fundacao 3 nao foi iniciada.

### [x] P9.3 - Fundacao 3 de Ressarcimentos guest limitado

Objetivo:

- Implementar e fechar convites, memberships, portal guest limitado e comprovantes explicitamente compartilhados.

Feito:

- Migrations `007_reimbursement_guest_access.sql` e `008_reimbursement_claim_attachments.sql` criadas e validadas no PostgreSQL local.
- Convites usam token bruto apenas na criacao e persistem somente `token_hash`.
- Aceite exige usuario autenticado com e-mail convidado.
- Membership ativo autoriza portal guest; revogacao bloqueia lista, detalhe, acoes e novas signed URLs.
- Payload guest foi sanitizado para nao expor owner, transacao, contas, cartoes, storage path ou snapshot tecnico.
- Owner compartilha comprovantes explicitamente por cobranca; anexos de transacao nao sao compartilhados por padrao.
- Guest pode reconhecer e contestar com motivo; status livre nao e aceito.
- Testes locais, PostgreSQL reais, frontend e E2E foram atualizados.

Nao feito:

- Comentarios ficaram decididos para Fundacao 3.5.
- Pagamentos, Telegram, OCR, audio, inbox, filas, gateway e Pix nao foram iniciados.
- RLS final ainda nao foi implementada.

## Validações obrigatórias por entrega

Frontend:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

Backend, quando houver alteração de API, serviços, parser ou persistência:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

### [x] P9.4 - Fundacao 3.5 de Ressarcimentos

Objetivo:

- Implementar comunicacao segura owner/guest em claims e reforcar protecao de convites antes de pagamentos e automacoes.

Feito na Etapa A:

- Plano registrado em `docs/foundation-3.5-plan.md`.

Feito na Etapa B:

- Criadas migrations `009_reimbursement_comments.sql` e `010_invitation_accept_rate_limits.sql`.
- Backend de comentarios implementado com autorizacao owner/guest, texto puro, paginacao e soft delete.
- Rate limiting persistente do aceite de convites implementado com token hash e origem derivada.
- Testes unitarios e PostgreSQL reais adicionados.

Feito na Etapa C:

- UI owner de comentarios adicionada ao detalhe de cobranca.
- UI guest de comentarios adicionada ao portal compartilhado.
- Componente reutilizavel de comentarios criado com listagem, envio, exclusao, estados de loading/erro/vazio e dialogo de confirmacao.
- Client API tipado integrado aos endpoints de comentarios.
- E2E owner/guest adicionados para envio, ordem cronologica, exclusao, ausencia de HTML renderizado e feedback de rate limit.

Feito na Etapa D:

- Migration `011_reimbursements_security_hardening.sql` criada para habilitar RLS e revogar acesso direto a tabelas financeiras por roles publicas.
- Data API mantida fechada para `PUBLIC`, `anon` e `authenticated`; acesso funcional segue pelo FastAPI.
- Signed URLs e claim attachments revisados sem compartilhamento automatico de anexos de transacao.
- Protecao contra fallback remoto de `NEXT_PUBLIC_API_URL` implementada e testada.
- Logs seguros adicionados para comentarios, rate limit, acesso negado a attachment e falha de signed URL.
- Testes PostgreSQL reais, backend, frontend e E2E executados localmente.

Pendente operacional:

- Aplicar migrations `009`, `010` e `011` em Production somente com autorizacao explicita.
- Validar smoke manual autenticado em Dev/Preview antes de preparar merge para `main`.
- Nao iniciar pagamentos, Telegram, OCR, audio, inbox, filas ou Fundacao 4 antes da validacao remota autorizada.

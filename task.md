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

- [ ] Mapear transações categorizadas do usuário como contexto de aprendizado.
- [ ] Criar schema de sugestão de categoria com categoria existente, confiança e justificativa.
- [ ] Aplicar sugestão apenas em transações sem categoria ou marcadas para revisão.
- [ ] Preservar regras determinísticas existentes como prioridade.
- [ ] Exibir sugestão ao usuário antes de alterar a transação.
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

- [ ] Identificar grupos de transações similares com mesma categoria.
- [ ] Detectar se já existe regra equivalente ou sobreposta.
- [ ] Gerar sugestão com keyword, categoria, tipo, escopo e justificativa.
- [ ] Exibir sugestões em tela dedicada ou painel de revisão.
- [ ] Permitir criar regra individualmente.
- [ ] Permitir descartar sugestão.
- [ ] Evitar regras duplicadas.
- [ ] Criar testes para sugestão, duplicidade e descarte.

### [/] P6.3 - Resumo financeiro mensal

Objetivo:

- Gerar resumo mensal em linguagem natural com entradas, saídas, resultado, categorias em alta, maiores gastos e pontos de atenção.

Feito:

- Criado resumo financeiro em `/ai-finance/overview`.
- Dashboard exibe resumo, insights, loading e erro.

Checklist:

- [ ] Definir agregados enviados para IA sem mandar transações completas quando não necessário.
- [ ] Criar endpoint para resumo mensal por período.
- [ ] Incluir comparação com período anterior quando houver dados.
- [ ] Destacar categorias que mais cresceram.
- [ ] Destacar maiores transações ou despesas fora do padrão.
- [ ] Mostrar resumo no dashboard.
- [ ] Criar estado de loading e erro.
- [ ] Criar testes com resposta mockada da IA.

### [/] P6.4 - Busca em linguagem natural

Objetivo:

- Permitir buscas como `quanto gastei com mercado em junho?` ou `mostre gastos do cartão Inter acima de R$ 100`.

Feito:

- Criado endpoint `/ai-finance/ask`.
- Dashboard permite perguntas simples por tipo, categoria e mês.
- Backend calcula filtros em código e não executa SQL livre.

Checklist:

- [ ] Definir intents suportadas: listar transações, somar gastos, comparar período, filtrar por categoria/origem.
- [ ] Criar schema estruturado para a IA retornar filtros, nunca SQL livre.
- [ ] Validar filtros no backend antes de executar.
- [ ] Reutilizar endpoints/repository existentes.
- [ ] Exibir resultado como lista, total ou resumo conforme intent.
- [ ] Tratar perguntas fora do escopo com mensagem clara.
- [ ] Criar testes contra prompt injection e filtros inválidos.

### [/] P6.5 - Perguntas sobre finanças

Objetivo:

- Criar um assistente de perguntas financeiras baseado em dados agregados e transações do usuário.

Feito:

- Criada UI de pergunta/resposta no dashboard.
- Respostas usam dados do usuário autenticado e mostram total/quantidade analisada.

Checklist:

- [ ] Definir escopo permitido de perguntas.
- [ ] Criar camada de contexto com dados agregados, categorias, contas, cartões e transações relevantes.
- [ ] Evitar envio de dados excessivos ao provider.
- [ ] Responder com base nos dados disponíveis e indicar quando não houver dados suficientes.
- [ ] Adicionar aviso de resposta informativa, sem aconselhamento financeiro profissional.
- [ ] Criar UI de chat ou painel de pergunta/resposta.
- [ ] Criar testes com mock de IA e controle de escopo.

### [/] P6.6 - Detecção de recorrências

Objetivo:

- Detectar transações recorrentes e sugerir agrupamentos como assinatura, renda fixa, conta mensal ou compra parcelada recorrente.

Feito:

- Detecta recorrências prováveis por descrição normalizada, valor e ocorrência em meses diferentes.
- Exibe recorrências prováveis no dashboard.

Checklist:

- [ ] Criar heurística inicial por descrição normalizada, valor aproximado e intervalo mensal.
- [ ] Usar IA para nomear/explicar recorrências ambíguas.
- [ ] Mostrar recorrências com frequência, valor médio, próxima previsão e categoria.
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

- [ ] Criar schema de normalização com descrição sugerida, confiança e justificativa.
- [ ] Aplicar sugestão automaticamente apenas quando confiança for alta e regra do produto permitir.
- [ ] Para baixa confiança, mostrar sugestão para aceite manual.
- [ ] Manter `original_description` inalterado.
- [ ] Permitir aplicar sugestões em lote.
- [ ] Evitar alterar descrições editadas manualmente pelo usuário sem confirmação.
- [ ] Criar testes para descrições com adquirente, Pix, marketplace e assinatura.

## P7 - Polish Visual e UX Operacional

### [x] P7.1 - Sidebar: corrigir acentuação dos labels

Feito:

- Sidebar revisada com labels acentuados para Transações, Contas Bancárias, Cartões de Crédito, Importação e Configurações.

Checklist:

- [ ] Revisar todos os itens da sidebar.
- [ ] Corrigir `Transacoes` para `Transações`.
- [ ] Corrigir `Contas Bancarias` para `Contas Bancárias`.
- [ ] Corrigir outros textos sem acento.
- [ ] Garantir que labels cabem no layout desktop/mobile.

### [x] P7.2 - Dashboard: cards, gráficos, insights e filtros

Feito:

- Removido card de transações pendentes de revisão.
- Adicionados filtros rápidos, período personalizado, cards recalculados, gráfico de gastos por categoria, barras diárias e insights.
- Dashboard recebeu painel inicial de inteligência financeira.

Checklist:

- [ ] Remover card `Transações pendentes de revisão`.
- [ ] Adicionar gráficos de gastos por categoria, período ou origem.
- [ ] Adicionar área de insights financeiros.
- [ ] Adicionar filtros rápidos: esse mês, mês passado, essa semana, semana passada.
- [ ] Adicionar período personalizado.
- [ ] Garantir que filtros alteram cards, gráficos e insights de forma consistente.
- [ ] Validar responsividade dos gráficos.

### [x] P7.3 - Transações: polish do drawer, status e fluxo de salvar

Feito:

- Removido texto `confirmed` abaixo da data.
- Rodapé do drawer ajustado para evitar linha visual quebrada.
- Campo Origem ganhou truncamento para caber melhor.
- Criação e salvamento fecham o drawer automaticamente.

Checklist:

- [ ] Retirar texto `confirmed` abaixo da data da transação.
- [ ] Corrigir linha branca bugada no layout do drawer.
- [ ] Ajustar tamanho de `Origem` para caber em uma linha quando possível.
- [ ] Fechar drawer automaticamente ao criar transação com sucesso.
- [ ] Fechar drawer automaticamente ao salvar alterações com sucesso.
- [ ] Garantir toasts de sucesso/erro.
- [ ] Validar comportamento mobile.

### [x] P7.4 - Conta bancária: loading, filtros e layout dos detalhes

Feito:

- Botão `Detalhes` usa loading de navegação.
- Adicionado filtro local por nome, instituição e tipo.
- Cards de cartões vinculados e faturas abertas foram compactados.
- Tabela de últimas transações relacionadas recebeu largura consistente.

Checklist:

- [ ] Adicionar loading ao clicar em detalhes.
- [ ] Investigar filtro que não funciona ou está lento.
- [ ] Corrigir performance/estado do filtro.
- [ ] Ajustar altura dos cards em `Cartões vinculados`.
- [ ] Compactar cards de `Faturas abertas`.
- [ ] Ajustar comprimento do card `Últimas transações relacionadas`.
- [ ] Validar desktop e mobile.

### [x] P7.5 - Cartões de crédito: loading, botões, BRL e layout de detalhe

Feito:

- `Ver cartão` mantém loading e layout em uma linha.
- Campo de limite usa máscara BRL na criação e edição.
- Detalhe do cartão coloca `Últimas transações` ao lado de `Histórico de faturas` em desktop e empilha no mobile.
- Payload continua enviado como decimal aceito pela API.

Checklist:

- [ ] Adicionar loading ao clicar em `Ver cartão`.
- [ ] Ajustar texto e seta do botão `Ver cartão` para ocupar uma linha.
- [ ] Adicionar máscara BRL no limite na criação de cartão.
- [ ] Adicionar máscara BRL no limite na edição de cartão.
- [ ] No detalhe do cartão, colocar `Últimas transações` ao lado direito de `Histórico de faturas` em desktop.
- [ ] Manter layout empilhado no mobile.
- [ ] Validar payload decimal aceito pela API.

### [x] P7.6 - Importação: feedback, consistência da análise e UX do preview

Feito:

- Removido aviso inline de upload concluído; feedback fica em toast.
- Corrigida consistência da análise quando a diferença calculada é R$ 0,00.
- Card de upload fica oculto quando há preview aberto.
- Adicionado botão `Nova importação`.
- Tabela de preview foi simplificada removendo `País`, `Confiança` e `Status`.

Checklist:

- [ ] Retirar aviso inline de upload concluído.
- [ ] Usar toast para upload concluído.
- [ ] Corrigir inconsistência onde diferença de R$ 0,00 informa que o valor não confere.
- [ ] Ao mostrar preview, remover/ocultar card de enviar arquivo.
- [ ] Adicionar botão `Nova importação` no canto superior da tela quando houver preview aberto.
- [ ] Refazer lista de transações importadas para melhorar UX/UI.
- [ ] Remover colunas `País`, `Confiança` e `Status`.
- [ ] Manter informações importantes acessíveis em detalhe, tooltip ou área secundária.
- [ ] Garantir que confirmação de importação continua funcionando.

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

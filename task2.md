# Financy - Tasks de Produto e Estabilizacao Pos-Fase 3

## Legenda

- `[x]` Concluida
- `[ ]` Nao iniciada
- `[/]` Em andamento
- `[-]` Pausada/cancelada

## Objetivo da fase

Corrigir bugs e melhorar a experiencia principal do app apos a fase de autenticacao, com foco em confiabilidade das acoes, criacao/edicao de transacoes, feedback visual para o usuario e revisao do fluxo de cartoes/faturas.

## P0 - Confiabilidade de acoes e erros intermitentes

### [x] P0.1 - Investigar `Failed to fetch` em acoes de escrita

Contexto:

- O erro `Failed to fetch` foi mitigado na transicao entre abas com retry para carregamentos.
- Agora o erro ainda aparece de vez em quando em acoes como criar e excluir transacoes.
- Exemplo observado: `Falha de conexao com a API em /transactions. Tente novamente em alguns segundos. Detalhe: Failed to fetch`.
- Tambem pode ocorrer em outras funcoes de escrita.

Objetivo:

- Identificar e corrigir a causa das falhas intermitentes em `POST`, `PUT`, `PATCH` e `DELETE`, sem criar duplicidade de dados.

Checklist:

- [x] Mapear quais acoes falham: criar transacao, excluir transacao, editar transacao, criar categoria, editar categoria, criar regra, editar regra, upload/importacao.
- [-] Coletar Network no navegador para uma falha real.
- [-] Comparar horario da falha com logs do Render.
- [-] Verificar se a API recebe a requisicao quando o frontend mostra `Failed to fetch`.
- [-] Verificar se o erro ocorre antes da resposta HTTP, por timeout/cold start/conexao.
- [x] Avaliar retry seguro para acoes idempotentes.
- [x] Para acoes nao idempotentes, avaliar chave/idempotency key no frontend/backend antes de retry automatico.
- [x] Melhorar mensagens de erro para indicar se a acao pode ter sido aplicada mesmo com falha de conexao.
- [x] Validar que nenhuma acao duplica transacoes, categorias ou regras.

Feito:

- Mapeadas as principais acoes de escrita afetadas: transacoes, categorias, regras, contas, cartoes, importacao e faturas.
- Criado feedback global de erro/sucesso para deixar falhas intermitentes mais visiveis e acionaveis.
- Nao foi adicionado retry automatico em `POST`/criacao para evitar duplicidade de dados sem idempotency key.
- Decisao final: manter retry automatico apenas em leituras; para escritas nao idempotentes, usar bloqueio de clique concorrente, feedback claro e evitar repeticao silenciosa.
- Nao houve reproducao local de `Failed to fetch` durante validacoes; itens dependentes de falha real em Network ficam cancelados como etapa de investigacao ativa.

Observacao:

- Se o erro voltar em producao, a proxima task deve ser idempotency key para escritas antes de qualquer retry automatico.

Resultado esperado:

- Criar, editar e excluir dados deixa de falhar de forma intermitente.
- Quando ocorrer erro real, a mensagem e clara e acionavel.
- Nenhuma operacao de escrita e duplicada por retry.

## P1 - Criacao de transacoes

### [x] P1.1 - Adicionar `Salvar e criar nova`

Contexto:

- A criacao manual de transacoes deve ser mais rapida para lancamentos em sequencia.

Objetivo:

- Adicionar uma acao secundaria `Salvar e criar nova` no formulario de criacao de transacao.

Checklist:

- [x] Manter botao principal `Salvar`.
- [x] Adicionar botao `Salvar e criar nova`.
- [x] Ao salvar e criar nova, persistir a transacao e limpar campos de descricao/valor/data conforme melhor UX.
- [x] Manter origem/categoria/tipo se isso acelerar lancamentos repetidos, se fizer sentido no fluxo atual.
- [x] Mostrar feedback de sucesso.
- [x] Validar que nao cria duplicidades por clique duplo.

Feito:

- Adicionada acao `Salvar e criar nova` no drawer de criacao.
- Ao usar a acao, descricao e valor sao limpos, mantendo data, tipo, categoria, origem e pendencia para lancamentos repetidos.
- O estado `isBusy` continua bloqueando cliques concorrentes.

Resultado esperado:

- Usuario consegue cadastrar varias transacoes em sequencia sem reabrir formulario.

### [x] P1.2 - Trocar status por checkbox `Pendente`

Contexto:

- O campo de status em lista e pesado para a criacao manual.

Objetivo:

- Remover seletor de status e usar um checkbox simples para indicar se a transacao esta pendente.

Checklist:

- [x] Remover dropdown/lista de status da criacao/edicao.
- [x] Adicionar checkbox `Pendente`.
- [x] Checkbox marcado deve salvar status pendente.
- [x] Checkbox desmarcado deve salvar status confirmado.
- [x] Manter compatibilidade com status existentes internamente.

Feito:

- Criacao e edicao agora usam checkbox `Pendente`.
- Internamente o frontend continua salvando `pending` quando marcado e `confirmed` quando desmarcado.

Resultado esperado:

- Usuario entende e altera pendencia da transacao com um controle simples.

### [x] P1.3 - Formatar valor automaticamente em BRL

Contexto:

- Campo de valor manual deve aceitar digitacao natural e exibir formato monetario brasileiro.

Objetivo:

- Formatacao automatica do valor durante a digitacao no formato BRL.

Checklist:

- [x] Aplicar mascara visual `R$ 0,00`.
- [x] Aceitar digitacao com virgula, ponto e numeros.
- [x] Converter corretamente para o formato esperado pela API.
- [x] Validar valores negativos/positivos conforme tipo de transacao.
- [x] Reutilizar comportamento na criacao e edicao.

Feito:

- Criados helpers para mascara BRL, leitura do valor mascarado e preenchimento do drawer a partir do valor da transacao.
- Criacao e edicao compartilham o mesmo comportamento.

Resultado esperado:

- Valor digitado fica claro para o usuario e consistente com BRL.

### [x] P1.4 - Unificar origem da transacao

Contexto:

- Hoje existem opcoes separadas de conta e cartao, o que confunde o usuario.

Objetivo:

- Trocar campos separados por um unico campo `Origem`.

Checklist:

- [x] Remover selecao separada de conta/cartao na criacao de transacao.
- [x] Criar campo `Origem`.
- [x] Dentro da lista de origem, separar em sublistas `Contas` e `Cartoes`.
- [x] Ao selecionar uma conta, preencher `account_id` e limpar `card_id`.
- [x] Ao selecionar um cartao, preencher `card_id` e limpar `account_id`.
- [x] Manter compatibilidade com filtros e exibicao da tabela.
- [x] Reutilizar o mesmo componente na edicao.

Feito:

- Criacao e edicao agora exibem apenas o campo `Origem`, com grupos `Contas` e `Cartoes`.
- O payload enviado para a API continua usando `account_id` ou `card_id`, preservando contrato existente.

Resultado esperado:

- Usuario escolhe uma origem unica e entende claramente se ela e conta bancaria ou cartao de credito.

## P2 - Edicao completa de transacoes

### [x] P2.1 - Permitir editar todos os campos suportados

Contexto:

- A edicao atual ficou restrita e precisa permitir ajustes completos de uma transacao manual/importada.

Objetivo:

- Permitir editar: Data, Descricao, Tipo, Categoria, Origem, Valor e Pendente.

Checklist:

- [x] Adicionar campo Data na edicao.
- [x] Manter Descricao editavel.
- [x] Adicionar Tipo editavel.
- [x] Manter Categoria editavel.
- [x] Adicionar Origem unificada editavel.
- [x] Adicionar Valor editavel com mascara BRL.
- [x] Adicionar checkbox `Pendente`.
- [x] Validar referencias de conta/cartao/categoria.
- [x] Preservar comportamento de criar regra, excluir e fechar drawer.
- [x] Atualizar visual da drawer se necessario.

Feito:

- Drawer de detalhes passou a editar Data, Descricao, Tipo, Categoria, Origem, Valor e Pendente.
- Acoes de criar regra, excluir, salvar e fechar foram preservadas.
- Validacoes de referencia continuam no backend.

Resultado esperado:

- Usuario consegue corrigir qualquer informacao principal de uma transacao sem editar inline na tabela.

## P3 - Feedback global de acoes

### [x] P3.1 - Criar sistema global de notificacoes no canto superior direito

Contexto:

- Hoje mensagens de sucesso/erro aparecem de formas diferentes ou em areas locais.
- O usuario quer um popup no canto superior direito para toda acao concluida ou erro.

Objetivo:

- Criar um padrao global de notificacoes tipo toast.

Checklist:

- [x] Criar provider/componente global de notificacoes.
- [x] Posicionar notificacoes no canto superior direito.
- [x] Suportar sucesso, erro e informacao.
- [x] Permitir fechar manualmente.
- [x] Auto-fechar apos alguns segundos.
- [x] Evitar sobrepor conteudo importante em mobile.

Feito:

- Criado `ToastProvider` global com tipos sucesso, erro e informacao.
- Toasts aparecem no canto superior direito, podem ser fechados manualmente e somem automaticamente.

Resultado esperado:

- Toda acao relevante mostra feedback consistente e visivel.

### [x] P3.2 - Aplicar notificacoes em todas as partes do app

Checklist:

- [x] Transacoes: criar, editar, excluir, criar regra.
- [x] Categorias: criar, editar, inativar.
- [x] Regras: criar, editar, inativar.
- [x] Contas: criar, editar, excluir/inativar.
- [x] Cartoes: criar, editar, excluir/inativar.
- [x] Importacao: upload, erro de parse, confirmacao.
- [x] Faturas: atualizar status, excluir.
- [x] Erros de carregamento quando fizer sentido.

Feito:

- Aplicado toast nas principais acoes de escrita e confirmacao.
- Mensagens locais foram preservadas onde ja existiam, para nao reduzir contexto inline.
- Loaders de pagina agora tambem disparam toast em falhas de carregamento.

Resultado esperado:

- Sucesso e erro de acoes aparecem como popup no canto superior direito em todo o app.

## P4 - Filtros e avisos de transacoes

### [x] P4.1 - Mostrar aviso de transacoes sem categoria apenas quando existir pendencia

Contexto:

- O aviso/filtro de transacoes sem categoria esta bom, mas nao deve aparecer quando nao existem transacoes sem categoria.

Objetivo:

- Esconder o aviso quando todas as transacoes filtradas/visiveis ja possuem categoria.

Checklist:

- [x] Calcular se existem transacoes sem categoria.
- [x] Exibir aviso somente quando houver ao menos uma transacao sem categoria.
- [x] Confirmar comportamento com filtros ativos.
- [x] Confirmar comportamento em estado vazio.

Feito:

- O atalho de transacoes sem categoria so aparece quando `uncategorizedCount > 0`.

Resultado esperado:

- Interface fica mais limpa quando nao ha pendencias de categoria.

## P5 - Cartoes, faturas e dashboard

### [x] P5.1 - Revisar transacoes de cartao sem fatura vinculada

Contexto:

- Transacoes vinculadas a um cartao, mas nao importadas por uma fatura, nao afetam corretamente o dashboard do cartao.
- Elas nao aparecem como valor utilizado e nao alteram outros dados porque nao ficam vinculadas a uma fatura.

Objetivo:

- Revisar e repensar o funcionamento entre transacoes de cartao, faturas e indicadores do dashboard.

Checklist de investigacao:

- [x] Mapear como o dashboard de cartao calcula `utilizado`, totais e faturas.
- [x] Mapear diferenca entre transacao manual de cartao e transacao importada por fatura.
- [x] Identificar onde `card_statement_id` e exigido para impactar dashboard.
- [x] Definir regra de negocio para transacao manual de cartao sem fatura.
- [x] Avaliar se deve criar/encontrar fatura automaticamente ao criar transacao manual de cartao.
- [x] Avaliar se dashboard deve somar transacoes de cartao sem fatura em um bucket separado.
- [x] Avaliar impacto em pagamento de fatura, fechamento e importacao.
- [x] Documentar decisao antes de implementar mudanca estrutural.

Decisao:

- Transacao vinculada a cartao sem `card_statement_id` deve encontrar/criar automaticamente uma fatura aberta do mes da data da transacao.
- A data de vencimento/fechamento usa `due_day` e `closing_day` do cartao quando disponiveis.
- Nao foi criado bucket separado no dashboard para evitar duas fontes de verdade.

Resultado esperado:

- Transacoes de cartao criadas manualmente impactam indicadores de forma previsivel.
- Dashboard de cartao nao ignora gastos validos.
- Fluxo de faturas continua consistente.

### [x] P5.2 - Implementar correcao do fluxo de faturas apos decisao

Dependencia:

- Depende da conclusao da P5.1.

Checklist:

- [x] Implementar regra definida para vinculo de transacao manual de cartao.
- [x] Atualizar services/repository conforme necessario.
- [x] Atualizar frontend se houver novo estado/indicador.
- [x] Criar testes backend para transacao manual de cartao.
- [x] Criar teste para dashboard/summary de cartao.
- [x] Validar importacao de fatura continua funcionando.

Feito:

- `TransactionService` agora associa automaticamente uma fatura ao criar/editar transacao vinculada a cartao sem fatura.
- Importacao de fatura segue usando o fluxo existente de `card_statement_id` quando a previa ja informa fatura.
- Adicionado teste cobrindo criacao manual de transacao em cartao, associacao automatica com fatura e impacto em `limit_used`/`limit_available` no resumo do cartao.

Resultado esperado:

- Cartoes, faturas e dashboards ficam consistentes para transacoes importadas e manuais.

## Validacoes obrigatorias

### [x] VF1 - Backend

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

### [x] VF2 - Frontend

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

### [-] VF3 - Smoke de producao

- [-] Login.
- [-] Criar transacao manual.
- [-] Salvar e criar nova transacao.
- [-] Editar transacao completa.
- [-] Criar categoria.
- [-] Criar regra.
- [-] Excluir/inativar transacao/categoria/regra com feedback visual.
- [-] Navegar entre abas sem `Failed to fetch` persistente.
- [-] Validar dashboard de cartao com transacao manual.

Status:

- Pausado por depender de deploy das alteracoes e sessao autenticada em producao.
- Substituido nesta etapa por validacoes locais automatizadas: backend, typecheck, lint e build.
- Deve ser executado manualmente apos deploy para confirmar o ambiente real.

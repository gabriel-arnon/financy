# Financy - Tasks de Produto e Estabilizacao Pos-Fase 3

## Legenda

- `[x]` Concluida
- `[ ]` Nao iniciada
- `[/]` Em andamento
- `[-]` Pausada/cancelada

## Objetivo da fase

Corrigir bugs e melhorar a experiencia principal do app apos a fase de autenticacao, com foco em confiabilidade das acoes, criacao/edicao de transacoes, feedback visual para o usuario e revisao do fluxo de cartoes/faturas.

## P0 - Confiabilidade de acoes e erros intermitentes

### [ ] P0.1 - Investigar `Failed to fetch` em acoes de escrita

Contexto:

- O erro `Failed to fetch` foi mitigado na transicao entre abas com retry para carregamentos.
- Agora o erro ainda aparece de vez em quando em acoes como criar e excluir transacoes.
- Exemplo observado: `Falha de conexao com a API em /transactions. Tente novamente em alguns segundos. Detalhe: Failed to fetch`.
- Tambem pode ocorrer em outras funcoes de escrita.

Objetivo:

- Identificar e corrigir a causa das falhas intermitentes em `POST`, `PUT`, `PATCH` e `DELETE`, sem criar duplicidade de dados.

Checklist:

- [ ] Mapear quais acoes falham: criar transacao, excluir transacao, editar transacao, criar categoria, editar categoria, criar regra, editar regra, upload/importacao.
- [ ] Coletar Network no navegador para uma falha real.
- [ ] Comparar horario da falha com logs do Render.
- [ ] Verificar se a API recebe a requisicao quando o frontend mostra `Failed to fetch`.
- [ ] Verificar se o erro ocorre antes da resposta HTTP, por timeout/cold start/conexao.
- [ ] Avaliar retry seguro para acoes idempotentes.
- [ ] Para acoes nao idempotentes, avaliar chave/idempotency key no frontend/backend antes de retry automatico.
- [ ] Melhorar mensagens de erro para indicar se a acao pode ter sido aplicada mesmo com falha de conexao.
- [ ] Validar que nenhuma acao duplica transacoes, categorias ou regras.

Resultado esperado:

- Criar, editar e excluir dados deixa de falhar de forma intermitente.
- Quando ocorrer erro real, a mensagem e clara e acionavel.
- Nenhuma operacao de escrita e duplicada por retry.

## P1 - Criacao de transacoes

### [ ] P1.1 - Adicionar `Salvar e criar nova`

Contexto:

- A criacao manual de transacoes deve ser mais rapida para lancamentos em sequencia.

Objetivo:

- Adicionar uma acao secundaria `Salvar e criar nova` no formulario de criacao de transacao.

Checklist:

- [ ] Manter botao principal `Salvar`.
- [ ] Adicionar botao `Salvar e criar nova`.
- [ ] Ao salvar e criar nova, persistir a transacao e limpar campos de descricao/valor/data conforme melhor UX.
- [ ] Manter origem/categoria/tipo se isso acelerar lancamentos repetidos, se fizer sentido no fluxo atual.
- [ ] Mostrar feedback de sucesso.
- [ ] Validar que nao cria duplicidades por clique duplo.

Resultado esperado:

- Usuario consegue cadastrar varias transacoes em sequencia sem reabrir formulario.

### [ ] P1.2 - Trocar status por checkbox `Pendente`

Contexto:

- O campo de status em lista e pesado para a criacao manual.

Objetivo:

- Remover seletor de status e usar um checkbox simples para indicar se a transacao esta pendente.

Checklist:

- [ ] Remover dropdown/lista de status da criacao/edicao.
- [ ] Adicionar checkbox `Pendente`.
- [ ] Checkbox marcado deve salvar status pendente.
- [ ] Checkbox desmarcado deve salvar status confirmado.
- [ ] Manter compatibilidade com status existentes internamente.

Resultado esperado:

- Usuario entende e altera pendencia da transacao com um controle simples.

### [ ] P1.3 - Formatar valor automaticamente em BRL

Contexto:

- Campo de valor manual deve aceitar digitacao natural e exibir formato monetario brasileiro.

Objetivo:

- Formatacao automatica do valor durante a digitacao no formato BRL.

Checklist:

- [ ] Aplicar mascara visual `R$ 0,00`.
- [ ] Aceitar digitacao com virgula, ponto e numeros.
- [ ] Converter corretamente para o formato esperado pela API.
- [ ] Validar valores negativos/positivos conforme tipo de transacao.
- [ ] Reutilizar comportamento na criacao e edicao.

Resultado esperado:

- Valor digitado fica claro para o usuario e consistente com BRL.

### [ ] P1.4 - Unificar origem da transacao

Contexto:

- Hoje existem opcoes separadas de conta e cartao, o que confunde o usuario.

Objetivo:

- Trocar campos separados por um unico campo `Origem`.

Checklist:

- [ ] Remover selecao separada de conta/cartao na criacao de transacao.
- [ ] Criar campo `Origem`.
- [ ] Dentro da lista de origem, separar em sublistas `Contas` e `Cartoes`.
- [ ] Ao selecionar uma conta, preencher `account_id` e limpar `card_id`.
- [ ] Ao selecionar um cartao, preencher `card_id` e limpar `account_id`.
- [ ] Manter compatibilidade com filtros e exibicao da tabela.
- [ ] Reutilizar o mesmo componente na edicao.

Resultado esperado:

- Usuario escolhe uma origem unica e entende claramente se ela e conta bancaria ou cartao de credito.

## P2 - Edicao completa de transacoes

### [ ] P2.1 - Permitir editar todos os campos suportados

Contexto:

- A edicao atual ficou restrita e precisa permitir ajustes completos de uma transacao manual/importada.

Objetivo:

- Permitir editar: Data, Descricao, Tipo, Categoria, Origem, Valor e Pendente.

Checklist:

- [ ] Adicionar campo Data na edicao.
- [ ] Manter Descricao editavel.
- [ ] Adicionar Tipo editavel.
- [ ] Manter Categoria editavel.
- [ ] Adicionar Origem unificada editavel.
- [ ] Adicionar Valor editavel com mascara BRL.
- [ ] Adicionar checkbox `Pendente`.
- [ ] Validar referencias de conta/cartao/categoria.
- [ ] Preservar comportamento de criar regra, excluir e fechar drawer.
- [ ] Atualizar visual da drawer se necessario.

Resultado esperado:

- Usuario consegue corrigir qualquer informacao principal de uma transacao sem editar inline na tabela.

## P3 - Feedback global de acoes

### [ ] P3.1 - Criar sistema global de notificacoes no canto superior direito

Contexto:

- Hoje mensagens de sucesso/erro aparecem de formas diferentes ou em areas locais.
- O usuario quer um popup no canto superior direito para toda acao concluida ou erro.

Objetivo:

- Criar um padrao global de notificacoes tipo toast.

Checklist:

- [ ] Criar provider/componente global de notificacoes.
- [ ] Posicionar notificacoes no canto superior direito.
- [ ] Suportar sucesso, erro e informacao.
- [ ] Permitir fechar manualmente.
- [ ] Auto-fechar apos alguns segundos.
- [ ] Evitar sobrepor conteudo importante em mobile.

Resultado esperado:

- Toda acao relevante mostra feedback consistente e visivel.

### [ ] P3.2 - Aplicar notificacoes em todas as partes do app

Checklist:

- [ ] Transacoes: criar, editar, excluir, criar regra.
- [ ] Categorias: criar, editar, inativar.
- [ ] Regras: criar, editar, inativar.
- [ ] Contas: criar, editar, excluir/inativar.
- [ ] Cartoes: criar, editar, excluir/inativar.
- [ ] Importacao: upload, erro de parse, confirmacao.
- [ ] Faturas: atualizar status, excluir.
- [ ] Erros de carregamento quando fizer sentido.

Resultado esperado:

- Sucesso e erro de acoes aparecem como popup no canto superior direito em todo o app.

## P4 - Filtros e avisos de transacoes

### [ ] P4.1 - Mostrar aviso de transacoes sem categoria apenas quando existir pendencia

Contexto:

- O aviso/filtro de transacoes sem categoria esta bom, mas nao deve aparecer quando nao existem transacoes sem categoria.

Objetivo:

- Esconder o aviso quando todas as transacoes filtradas/visiveis ja possuem categoria.

Checklist:

- [ ] Calcular se existem transacoes sem categoria.
- [ ] Exibir aviso somente quando houver ao menos uma transacao sem categoria.
- [ ] Confirmar comportamento com filtros ativos.
- [ ] Confirmar comportamento em estado vazio.

Resultado esperado:

- Interface fica mais limpa quando nao ha pendencias de categoria.

## P5 - Cartoes, faturas e dashboard

### [ ] P5.1 - Revisar transacoes de cartao sem fatura vinculada

Contexto:

- Transacoes vinculadas a um cartao, mas nao importadas por uma fatura, nao afetam corretamente o dashboard do cartao.
- Elas nao aparecem como valor utilizado e nao alteram outros dados porque nao ficam vinculadas a uma fatura.

Objetivo:

- Revisar e repensar o funcionamento entre transacoes de cartao, faturas e indicadores do dashboard.

Checklist de investigacao:

- [ ] Mapear como o dashboard de cartao calcula `utilizado`, totais e faturas.
- [ ] Mapear diferenca entre transacao manual de cartao e transacao importada por fatura.
- [ ] Identificar onde `card_statement_id` e exigido para impactar dashboard.
- [ ] Definir regra de negocio para transacao manual de cartao sem fatura.
- [ ] Avaliar se deve criar/encontrar fatura automaticamente ao criar transacao manual de cartao.
- [ ] Avaliar se dashboard deve somar transacoes de cartao sem fatura em um bucket separado.
- [ ] Avaliar impacto em pagamento de fatura, fechamento e importacao.
- [ ] Documentar decisao antes de implementar mudanca estrutural.

Resultado esperado:

- Transacoes de cartao criadas manualmente impactam indicadores de forma previsivel.
- Dashboard de cartao nao ignora gastos validos.
- Fluxo de faturas continua consistente.

### [ ] P5.2 - Implementar correcao do fluxo de faturas apos decisao

Dependencia:

- Depende da conclusao da P5.1.

Checklist:

- [ ] Implementar regra definida para vinculo de transacao manual de cartao.
- [ ] Atualizar services/repository conforme necessario.
- [ ] Atualizar frontend se houver novo estado/indicador.
- [ ] Criar testes backend para transacao manual de cartao.
- [ ] Criar teste para dashboard/summary de cartao.
- [ ] Validar importacao de fatura continua funcionando.

Resultado esperado:

- Cartoes, faturas e dashboards ficam consistentes para transacoes importadas e manuais.

## Validacoes obrigatorias

### [ ] VF1 - Backend

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

### [ ] VF2 - Frontend

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

### [ ] VF3 - Smoke de producao

- [ ] Login.
- [ ] Criar transacao manual.
- [ ] Salvar e criar nova transacao.
- [ ] Editar transacao completa.
- [ ] Criar categoria.
- [ ] Criar regra.
- [ ] Excluir/inativar transacao/categoria/regra com feedback visual.
- [ ] Navegar entre abas sem `Failed to fetch` persistente.
- [ ] Validar dashboard de cartao com transacao manual.

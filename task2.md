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

### [x] P5.3 - Adicionar suporte ao padrao de fatura Cartoes CAIXA

Contexto:

- Foi analisada uma fatura PDF da CAIXA com vencimento em 17/06/2026.
- A fatura possui valor total, limite, melhor data de compra, dados de boleto e demonstrativo por cartao.
- O demonstrativo separa compras por final de cartao, por exemplo cartao 6823 e cartao 7164.
- As transacoes aparecem com Data, Descricao, Cidade/Pais e Credito/Debito em formato brasileiro, como `12,67D` e `542,37C`.
- Hoje esse padrao deve ser reconhecido corretamente na importacao para gerar preview/transacoes confiaveis.

Objetivo:

- Adicionar suporte explicito ao layout de faturas Cartoes CAIXA no parser/importador, preservando o fluxo atual de upload, preview, confirmacao e vinculo com fatura/cartao.

Checklist:

- [x] Criar ou ajustar detector de layout para identificar faturas CAIXA por textos como `Central de Atendimento Cartoes Caixa`, `CARTOES CAIXA`, `Valor total desta fatura` e blocos `Cartao`.
- [x] Extrair metadados da fatura: vencimento, valor total, limite total, limite utilizado, limite disponivel e melhor data para compra quando disponiveis.
- [x] Separar blocos por final de cartao, mantendo o final do cartao como referencia de origem.
- [x] Extrair compras por linha com data, descricao, cidade/pais quando houver, valor e tipo debito/credito.
- [x] Ignorar linhas de resumo, pagamento anterior, totais, encargos, boleto e opcoes de parcelamento que nao devem virar transacao de compra.
- [x] Tratar valores com sufixo `D` como despesa e valores com sufixo `C` como credito/estorno nao selecionado por padrao.
- [x] Criar preview de importacao com categoria pendente/classificacao automatica existente.
- [x] Vincular transacoes importadas ao cartao e a fatura correta quando o cartao existir no cadastro.
- [x] Se houver mais de um cartao na mesma fatura, preservar separacao por final de cartao.
- [x] Adicionar testes com fixture anonima baseada no padrao da fatura CAIXA.
- [x] Validar que faturas PDF ja suportadas continuam funcionando.

Feito:

- Criado detector dedicado para faturas Cartoes CAIXA no parser de PDF.
- Parser CAIXA extrai vencimento, valor total da fatura, referencia, instituicao, limite total e final do cartao principal.
- Compras sao extraidas por bloco `COMPRAS (Cartao XXXX)`, preservando o final do cartao em cada item.
- Linhas de pagamento anterior, totais, informativos, encargos, boleto e parcelamento ficam fora da selecao de transacoes.
- Linhas misturadas por extracao do PDF, como `MULTA ... 26/05 ... 15,00D`, tambem sao reconhecidas quando estao dentro do bloco de compras.
- Valores `D` entram como despesas selecionadas por padrao; valores `C` entram como estorno/credito nao selecionado por padrao.
- Importacao agora tenta preencher `card_id` automaticamente quando `card_last_digits` bate com um cartao cadastrado do usuario.
- Validado com a fatura real `fatura-0.pdf`: 20 compras extraidas, finais 6823 e 7164 preservados, total selecionado R$ 492,59.
- Adicionados testes de parser CAIXA e auto-vinculo por final de cartao no import service.

Resultado esperado:

- Upload de fatura CAIXA gera preview com as compras corretas por cartao.
- Confirmacao da importacao cria transacoes vinculadas a fatura/cartao, afetando dashboard e utilizado do cartao.
- O app nao transforma boleto, parcelamento, encargos ou totais duplicados em transacoes indevidas.

### [x] P5.4 - Adicionar suporte aos padroes de fatura Inter e Mercado Pago

Contexto:

- Foram analisadas faturas PDF do Banco Inter e do Mercado Pago.
- A fatura Inter possui resumo, vencimento, valor total, limite, pagamento minimo, detalhes por cartao e boleto.
- No Inter, uma mesma fatura pode trazer mais de um cartao, por exemplo `2306****8928` e `2306****1140`, com totais separados por cartao.
- A fatura Mercado Pago possui resumo, vencimento, total a pagar, limite, pagamento minimo, pagamentos/creditos e detalhes por cartao Visa.
- No Mercado Pago, uma mesma fatura pode trazer mais de um cartao, por exemplo `************2812` e `************2008`, com compras parceladas e totais separados.
- Hoje esses padroes devem ser reconhecidos na importacao para gerar preview/transacoes confiaveis.

Objetivo:

- Adicionar suporte explicito aos layouts de fatura Inter e Mercado Pago no parser/importador, preservando upload, preview, confirmacao, classificacao automatica e vinculo com cartao/fatura.

Checklist:

- [x] Criar ou ajustar detector de layout para identificar faturas Inter por textos como `inter`, `Resumo da fatura`, `Despesas da fatura`, `CARTAO` e `Valor total`.
- [x] Criar ou ajustar detector de layout para identificar faturas Mercado Pago por textos como `mercado pago`, `Essa e sua fatura`, `Detalhes de consumo`, `Cartao Visa` e `Total a pagar`.
- [x] Extrair metadados da fatura Inter: vencimento, valor total, limite total, pagamento minimo, data de corte/proxima fatura e valores de limite utilizado/disponivel quando disponiveis.
- [x] Extrair metadados da fatura Mercado Pago: emissao, vencimento, total a pagar, limite total, pagamento minimo, fechamento, proximo fechamento, limite utilizado/disponivel e lancamentos futuros quando disponiveis.
- [x] Separar blocos por final de cartao em ambos os layouts.
- [x] Extrair transacoes Inter por linha com data, descricao, parcela quando houver, valor e tipo despesa/credito.
- [x] Extrair transacoes Mercado Pago por linha com data, descricao, parcela quando houver, valor e tipo despesa/credito.
- [x] Ignorar pagamentos de fatura, boleto, resumos, totais, encargos, opcoes de parcelamento e textos informativos que nao devem virar compra.
- [x] Tratar pagamentos/creditos como credito/estorno e nao selecionar por padrao quando fizer sentido.
- [x] Vincular automaticamente ao cartao cadastrado quando `card_last_digits` bater com o final do cartao.
- [x] Se houver mais de um cartao na mesma fatura, preservar separacao por final de cartao no preview.
- [x] Criar fixtures anonimas baseadas nos padroes Inter e Mercado Pago.
- [x] Adicionar testes de parser para Inter e Mercado Pago.
- [x] Adicionar testes de import service garantindo auto-vinculo por final de cartao.
- [x] Validar que CAIXA e demais PDFs ja suportados continuam funcionando.

Feito:

- Criados detectores dedicados para faturas Inter e Mercado Pago no parser de PDF.
- Parser Inter extrai vencimento, valor total, limite total, referencia, instituicao e blocos por final de cartao.
- Parser Mercado Pago extrai vencimento, valor total, limite total, referencia, instituicao, bandeira Visa e blocos por final de cartao.
- Compras parceladas em formato `Parcela X de Y` sao normalizadas com `installment_current` e `installment_total`.
- Pagamentos de fatura, linhas de total, resumos, boletos, encargos, parcelamento e textos informativos sao ignorados para nao gerar compras duplicadas.
- Confirmado com PDFs reais analisados:
  - Inter: 7 compras extraidas, finais 8928 e 1140 preservados, total R$ 637,14.
  - Mercado Pago: 4 compras extraidas, finais 2812 e 2008 preservados, total R$ 351,96.
- Adicionados testes de parser para os dois padroes e teste de auto-vinculo no import service.

Resultado esperado:

- Upload de faturas Inter e Mercado Pago gera preview correto por cartao.
- Confirmacao da importacao cria transacoes vinculadas a fatura/cartao quando o cartao existir.
- Pagamentos, boleto, parcelamento, encargos e totais duplicados nao viram transacoes indevidas.

### [x] P5.5 - Importacao assistida por IA para PDFs desconhecidos ou baixa confianca

Contexto:

- O app ja possui parsers deterministas para layouts conhecidos, como CAIXA, Inter, Mercado Pago e outros padroes de PDF.
- Parsers deterministas sao rapidos, baratos e previsiveis, mas exigem manutencao para cada novo layout de banco/cartao.
- Faturas desconhecidas, PDFs escaneados, tabelas quebradas ou layouts alterados podem falhar ou gerar preview incompleto.
- Uma IA pode ajudar a interpretar PDFs desconhecidos e devolver uma estrutura normalizada, mas nao deve confirmar transacoes automaticamente sem revisao do usuario.

Objetivo:

- Adicionar um fluxo hibrido de importacao: tentar parser conhecido primeiro e usar IA apenas como fallback ou assistente quando a confianca for baixa.

Recomendacao de arquitetura:

- Parser deterministico continua como caminho principal.
- IA entra quando:
  - nenhum parser dedicado reconhece o layout;
  - o parser retorna zero transacoes;
  - a soma das transacoes diverge muito do total da fatura;
  - muitas linhas ficam como baixa confianca;
  - o usuario aciona manualmente `Analisar com IA`.
- A IA deve retornar JSON estruturado e o backend deve validar/normalizar antes de criar preview.
- A confirmacao da importacao continua dependendo da revisao do usuario no preview.

Checklist:

- [x] Definir provider de IA e variaveis de ambiente necessarias.
- [x] Definir schema JSON estrito para resposta da IA:
  - banco/instituicao;
  - tipo de documento;
  - vencimento;
  - referencia;
  - total da fatura;
  - limite quando disponivel;
  - cartoes detectados;
  - transacoes;
  - pagamentos/creditos;
  - linhas ignoradas;
  - nivel de confianca.
- [x] Criar prompt de extracao com instrucoes para nao inventar dados.
- [x] Criar validador backend para aceitar apenas JSON dentro do schema.
- [x] Normalizar datas, valores BRL, parcelas e finais de cartao retornados pela IA.
- [x] Bloquear confirmacao automatica de itens gerados por IA sem preview/revisao.
- [x] Marcar itens de IA com `needs_review=true` quando houver baixa confianca.
- [x] Registrar no `raw_row` que o item veio de IA e qual modelo/provider foi usado, sem salvar conteudo sensivel desnecessario.
- [x] Criar fallback seguro caso a IA falhe, exceda timeout ou retorne JSON invalido.
- [x] Adicionar botao opcional `Analisar com IA` na tela de preview ou importacao quando o parser falhar.
- [x] Garantir que dados financeiros sensiveis nao sejam enviados para IA sem decisao explicita de produto/privacidade.
- [x] Documentar custo, latencia, riscos e politica de privacidade do uso de IA.
- [x] Criar testes com resposta mockada da IA.
- [x] Validar que parsers deterministas existentes continuam sendo usados quando reconhecem o layout.

Feito:

- Adicionado servico `AiImportAnalyzer` opcional e desligado por padrao.
- Criadas variaveis `AI_IMPORT_ENABLED`, `AI_IMPORT_PROVIDER`, `AI_IMPORT_BASE_URL`, `AI_IMPORT_API_KEY`, `AI_IMPORT_MODEL` e `AI_IMPORT_TIMEOUT_SECONDS`.
- Criado schema Pydantic para validar a resposta JSON da IA antes de criar preview.
- Upload continua usando parser deterministico primeiro; IA so entra automaticamente se parser retornar zero itens e estiver configurada.
- Criado endpoint manual `POST /imports/{import_id}/analyze-ai` para imports sem itens de preview.
- Itens gerados por IA entram no preview com `needs_review=true` e metadados tecnicos no `raw_row`.
- Frontend mostra botao `Analisar com IA` quando a previa vem vazia.
- Criada documentacao operacional em `docs/ai-import.md`.
- Adicionados testes mockados para garantir criacao de preview por IA e evitar duplicidade quando ja existem itens.

Pendente externo para ativar em producao:

- Escolher provider/modelo final.
- Configurar chave da IA no Render.
- Revisar politica de privacidade antes de enviar dados financeiros para provider externo.

Resultado esperado:

- PDFs desconhecidos podem gerar preview utilizavel sem criar parser dedicado imediatamente.
- Layouts conhecidos continuam rapidos e previsiveis.
- A IA melhora cobertura de importacao, mas o usuario continua revisando antes de confirmar.
- O app reduz risco de erro silencioso em dados financeiros.

### [x] P5.6 - IA como assistente avancado de revisao de importacao

Contexto:

- A importacao assistida por IA ja pode gerar preview automaticamente quando parsers deterministas nao encontram transacoes.
- Ainda existem oportunidades de usar IA para melhorar a qualidade da revisao, sem confirmar nada automaticamente.
- O objetivo e usar IA para reduzir trabalho manual do usuario no preview, mantendo controle, auditoria e seguranca.

Objetivo:

- Adicionar recursos de IA no preview de importacao para classificar, normalizar, explicar, detectar inconsistencias e sugerir regras, sempre com revisao do usuario antes da confirmacao.

Checklist:

- [x] Classificacao inteligente de categorias:
  - sugerir categoria quando nao houver regra existente;
  - respeitar categorias existentes do usuario;
  - indicar confianca da sugestao;
  - nao substituir regra deterministica de maior prioridade.
- [x] Normalizacao de descricao:
  - sugerir descricao limpa/amigavel para exibicao;
  - preservar `original_description` internamente;
  - permitir ao usuario aceitar/editar a sugestao.
- [x] Deteccao avancada de duplicidades:
  - comparar descricao normalizada, data aproximada e valor;
  - marcar possiveis duplicatas no preview;
  - explicar por que um item foi marcado como duplicado.
- [x] Resumo inteligente da fatura importada:
  - total encontrado;
  - soma das transacoes selecionadas;
  - quantidade de compras;
  - cartoes detectados;
  - pagamentos/estornos ignorados;
  - divergencias entre soma e total da fatura.
- [x] Explicacao de baixa confianca:
  - exibir motivo para `needs_review`;
  - exemplos: cartao nao identificado, valor ambivalente, linha parece pagamento, parcela incerta.
- [-] Sugestao de criacao de regras:
  - apos confirmacao ou no preview, sugerir regras para comerciantes recorrentes;
  - permitir criar regras em lote;
  - evitar sugestoes duplicadas de regras ja existentes.
- [x] Deteccao rica de parcelamentos:
  - reconhecer `2/10`, `Parc 02`, `Parcela 2 de 10`, formatos quebrados e equivalentes;
  - preencher `installment_current` e `installment_total`;
  - sinalizar quando a parcela estiver incerta.
- [x] Analise de inconsistencias:
  - avisar quando soma selecionada bate com o total da fatura;
  - avisar quando ha diferenca relevante;
  - apontar possiveis causas: credito, pagamento, encargos, item ignorado ou linha nao reconhecida.
- [x] Criar schema backend para resposta de enriquecimento IA separado do schema de extracao.
- [x] Garantir que enriquecimento de IA seja opcional e nunca bloqueie confirmacao manual.
- [x] Criar testes com respostas mockadas para categorias, descricao, duplicidade e resumo.
- [x] Documentar custo, privacidade e limites do enriquecimento.

Feito:

- Criado schema separado `AiPreviewEnrichment`/`AiItemEnrichment` para enriquecimento, independente do schema de extracao de PDF.
- Importacao continua usando parser deterministico; com IA habilitada, a previa pode receber sugestoes de categoria, descricao normalizada, parcelas, duplicidade e explicacao.
- Sugestoes de categoria respeitam apenas categorias ativas existentes do usuario e nao sobrescrevem regras deterministicas ja aplicadas.
- Descricao normalizada fica como sugestao no preview, preservando `original_description` e exigindo acao do usuario para aplicar.
- Possiveis duplicatas sao marcadas no preview, desmarcadas por padrao e acompanhadas de motivo.
- Adicionado resumo de analise da previa com total selecionado, total da fatura, diferenca, itens para revisao, duplicatas, cartoes detectados e quantidade enriquecida por IA.
- Frontend mostra o resumo, confianca, explicacoes e botao para usar a descricao sugerida.
- A criacao de regras em lote foi pausada para evitar criar automacoes financeiras automaticamente sem uma UX de confirmacao dedicada.
- Documentacao de IA atualizada com privacidade, limites e comportamento assistivo.

Resultado esperado:

- Preview de importacao fica mais rapido de revisar.
- Usuario entende melhor por que itens foram selecionados, ignorados ou marcados para revisao.
- IA ajuda com categorias, descricoes e analise, mas nao salva transacoes sem confirmacao humana.

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

# Regras estruturadas

## Objetivo

Evoluir `classification_rules` de keyword simples para condicoes e acoes estruturadas, mantendo compatibilidade com regras atuais.

## Schema inicial

A migration proposta `docs/supabase/migrations/017_structured_classification_rules.sql` adiciona:

- `conditions jsonb`: lista de condicoes.
- `condition_logic text`: `all` por padrao; `any` quando uma regra explicitamente aceitar qualquer condicao.
- `actions jsonb`: lista de acoes.
- `rule_version integer`: versao do contrato.

Formato de condicao:

```json
{ "field": "description", "operator": "contains", "value": "openai" }
```

Campos permitidos:

- `description`
- `original_description`
- `combined_description`
- `normalized_description`
- `type`
- `amount`
- `category_id`
- `payee`
- `external_source`

Operadores permitidos:

- `contains`
- `starts_with`
- `equals`
- `regex`
- `gt`
- `lt`

Acoes permitidas:

- `set_category`
- `set_payee`
- `ignore_from_reports`

## Avaliador

`backend/app/services/structured_rules.py` contem um avaliador puro, sem acesso ao banco e sem efeitos colaterais.

Regras de seguranca:

- Regex invalida ou longa demais nao executa.
- Campo, operador ou acao desconhecida invalida a regra.
- O avaliador retorna acoes propostas; ele nao altera transacoes.
- Regras legacy de keyword podem ser convertidas para representacao estruturada por `legacy_keyword_rule_to_structured`.
- `match_scope=both` e representado por `combined_description`, preservando a semantica antiga de buscar em descricao ou descricao original sem tornar as demais condicoes opcionais.

## Preview de impacto

`POST /classification-rules/preview` recebe o mesmo contrato de criacao de regra, valida categorias e retorna:

- total de transacoes encontradas;
- quantas teriam categoria alterada;
- quantas ja estao na categoria final;
- amostras com categoria atual e categoria proposta.

O endpoint nao persiste a regra e nao altera transacoes. A tela de regras usa essa resposta para mostrar a previa antes de criar ou editar uma regra.

## Sugestoes de IA

As sugestoes de regra vindas de `AiFinanceService.overview` incluem `conditions`, `condition_logic`, `actions` e `rule_version`, mas continuam sendo apenas sugestoes. A aplicacao abre um dialog de revisao e so cria a regra quando o usuario confirma.

## Proximos passos

- Criar UI avancada para editar condicoes estruturadas manualmente, se necessario.

# Arquitetura

## Fluxo de importacao

1. `POST /imports/upload` recebe o arquivo e salva metadados em `import_files`.
2. Um `import_batch` representa a tentativa de importacao.
3. `ParserFactory` detecta extensao/MIME e chama o parser especifico.
4. Parsers retornam `NormalizedTransactionPreview`.
5. Os itens sao persistidos em `import_preview_items` com metadados brutos, confianca e status.
6. `GET /imports/{import_id}/preview` entrega itens editaveis ao frontend.
7. `POST /imports/{import_id}/confirm` grava apenas itens selecionados em `transactions`.

## Fronteiras

- Parsers extraem e normalizam dados, mas nao gravam transacoes finais.
- Preview guarda rastreabilidade: `raw_text`, `raw_row`, `parser_confidence`, `needs_review` e `duplicate_candidate`.
- Confirmacao aplica regras de duplicidade e status.
- Transacoes confirmadas sao a fonte principal para telas financeiras.

## Autenticacao

O backend usa `DEV_USER_ID` em ambiente local. A funcao de contexto de usuario esta isolada em `app/api/deps.py` para futura substituicao por Supabase Auth, validando JWT e usando `auth.uid()`.

## IA futura

A classificacao inteligente deve entrar como uma camada propria depois do parsing e antes da confirmacao. Ela podera sugerir categoria, tipo e merchant normalizado, mas a decisao final no MVP continua sendo do usuario.

## Merchant aliases

O sistema deve evoluir para uma tabela de aliases de estabelecimentos, vinculando descricoes originais como `MERCADO EXEMPLO 001` a um merchant canonico como `Mercado Exemplo`. Esses aliases poderao alimentar regras deterministicas e classificacao inteligente futura. Nesta base inicial, a intencao fica documentada e a normalizacao de descricao ja existe para deduplicacao.

# Open Finance providers

## Objetivo

Permitir que o Financy suporte novos providers Open Finance sem duplicar regra financeira, persistencia ou normalizacao de transacoes.

O provider deve cuidar apenas da conversa com a API externa. `OpenFinanceService` continua sendo o orquestrador de dominio: valida owner-only, cria sync runs, normaliza contas/cartoes/investimentos/transacoes, aplica dedupe, persiste links externos e registra motivos de ignorados.

## Contrato interno

Um provider deve expor:

- `provider_name`: identificador estavel salvo em items, links e sync runs.
- `create_connect_token(client_user_id)`: cria token de conexao para o usuario owner.
- `get_item(item_id)`: retorna metadados da conexao externa.
- `list_items()`: lista conexoes remotas quando ainda nao ha item local.
- `list_accounts(item_id)`: lista contas e cartoes do item.
- `list_transactions(account_id, from_date=None, to_date=None)`: lista transacoes da conta/cartao.
- `list_investments(item_id)`: lista investimentos quando o provider suportar.

O modulo atual `app.services.open_finance_provider` implementa esse contrato para Pluggy por meio de `PluggyOpenFinanceProvider`, que delega chamadas HTTP para `PluggyClient`.

## Fronteiras

- Segredos do provider ficam somente no backend.
- O frontend nunca recebe `client_id`, `client_secret`, API key ou paths internos.
- External IDs sao sempre tratados como strings antes de persistir.
- Metadata salva deve apoiar auditoria/debug, mas nao deve virar fonte de verdade para regras financeiras sensiveis.
- Erros externos devem ser convertidos para mensagens seguras antes de sair em sync runs ou respostas HTTP.

## Como adicionar um provider

1. Criar uma classe que implemente `OpenFinanceProvider`.
2. Definir `provider_name` curto, imutavel e unico.
3. Adaptar payloads externos para o formato bruto esperado por `OpenFinanceService`.
4. Injetar o provider em `get_open_finance_service`.
5. Adicionar testes de sync com fake provider cobrindo contas, cartoes, transacoes, investments quando houver, dedupe e erro externo.

Novos providers nao devem criar contas, cartoes ou transacoes diretamente. Toda criacao/atualizacao deve passar pelo `OpenFinanceService`.

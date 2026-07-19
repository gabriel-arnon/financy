# Payees e merchant aliases

## Objetivo

Criar uma camada canonica para reconhecer estabelecimentos por tras de descricoes bancarias ruidosas, sem alterar `original_description` e sem mesclar comerciantes automaticamente.

## Modelo

A migration `docs/supabase/migrations/016_payees_and_merchant_aliases.sql` define:

- `payees`: nome canonico por usuario.
- `merchant_aliases`: aliases normalizados vinculados a um payee.

Aliases sao user-owned e sempre ficam isolados por `user_id`. O cliente nao envia `user_id`.

## Uso atual

- `AiFinanceService.overview` sugere aliases candidatos em `suggested_payee_aliases`.
- As sugestoes aparecem no dashboard apenas como revisao; nenhuma regra, payee, alias ou transacao e criada automaticamente.
- Aliases confirmados no repository sao usados como contexto em classificacao deterministica, recorrencias e busca em linguagem natural.
- `original_description` permanece intacto. A camada canonica funciona como leitura/contexto.

## Regras de seguranca

- Nao mesclar comerciantes diferentes sem confirmacao humana.
- Nao substituir descricoes originais.
- Nao enviar segredos ou payload bruto desnecessario para provider externo.
- Manter aliases por usuario ate o modelo de workspace estar implementado.

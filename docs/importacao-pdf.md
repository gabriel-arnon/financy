# Importacao PDF

Este documento descreve o parser de faturas PDF. Ele nao usa IA: todas as decisoes sao heuristicas rastreaveis por linha, secao e metadados.

## Identificacao de transacoes

O parser extrai texto e tabelas com `pdfplumber`, percorre as linhas normalizadas e mantem a secao atual quando encontra cabecalhos como:

- `Lancamentos nesta fatura`
- `Restaurantes`
- `Servicos`
- `Supermercados`
- `Vestuario`
- `Outros lancamentos`
- `Compras parceladas`

Uma linha e considerada transacao quando possui data no inicio, descricao e valor no fim. Quando o pais aparece antes do valor, como `BRA`, `BRASIL`, `USA` ou `EUA`, ele e salvo em `merchant_country`.

## Linhas ignoradas

Totais e informativos nao viram transacoes confirmaveis. Eles sao registrados em `ignored_lines` com `excluded_reason`:

- `saldo_anterior`: saldo ou fatura anterior.
- `subtotal`: subtotais de secao.
- `total`: total da fatura.
- `informativo`: IOF, juros, limite, mensagens, atendimento e textos sem lancamento.
- `low_confidence`: linha parece ter data e valor, mas nao foi possivel separar campos com seguranca.

Duplicidades, pagamentos e refunds sao itens de preview quando representam movimentos financeiros, mas com `default_selected=false` e motivo proprio.

## Pagamentos e refunds

- `PGTO` e `PAGAMENTO` sao classificados como `type=payment`.
- `CREDITO`, `ESTORNO` e `DEVOLUCAO` sao classificados como `type=refund`.
- Ambos ficam desmarcados por padrao, mas podem ser marcados manualmente no frontend.

## Confianca

`parser_confidence` e calculado por sinais objetivos:

- data, descricao e valor reconhecidos;
- secao conhecida;
- pais reconhecido;
- parcela reconhecida;
- tipo especial reconhecido com seguranca.

Itens abaixo do limite de confianca sao marcados com `needs_review=true`, `default_selected=false` e `excluded_reason=low_confidence`.

## Compras parceladas

O parser reconhece parcelas em descricoes com:

- `PARC 01/03`
- `PARC 09/12`
- `01/03`
- `09/12`

Os valores sao salvos em `installment_current` e `installment_total`.

## Metadados da fatura

Quando detectaveis, o parser adiciona aos itens e ao resultado comum:

- `statement_total_amount`
- `statement_due_date`
- `statement_reference_month`
- `card_last_digits`

Esses metadados ajudam a auditar a importacao e preparar o vinculo futuro com `card_statements`.

## Debug com PDF real

Use o script local para testar um PDF privado sem salvar nada:

```powershell
cd C:\Users\Gabriel\Documents\Financy
python backend/scripts/debug_pdf_parser.py "C:\Users\Gabriel\Downloads\Comprovante_07-06-2026_185907.pdf"
```

O script mostra metadados, transacoes extraidas, linhas ignoradas e a soma dos itens com `default_selected=true`.

Nao copie PDFs reais para o repositorio e nao versione dados sensiveis.

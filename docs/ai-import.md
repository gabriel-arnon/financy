# Importacao assistida por IA

## Objetivo

Usar IA como fallback para PDFs desconhecidos ou de baixa confianca e como assistente opcional de revisao do preview, mantendo parsers deterministas como caminho principal.

## Fluxo recomendado

1. O upload tenta o parser conhecido.
2. Se o parser gerar preview confiavel, a IA nao e chamada.
3. Se o preview vier vazio ou insuficiente, o usuario pode acionar `Analisar com IA`.
4. A IA retorna JSON estruturado.
5. O backend valida e normaliza o JSON.
6. Os itens entram no preview com revisao obrigatoria.
7. Quando configurada, a IA pode enriquecer a previa com categoria sugerida, descricao normalizada, parcela, duplicidade e resumo de consistencia.
8. O usuario confirma manualmente os itens antes de criar transacoes.

## Variaveis de ambiente

```env
AI_ENABLED=false
AI_PROVIDER=openai-compatible
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=
AI_MODEL=gpt-4o-mini
AI_TIMEOUT_SECONDS=45
```

Aliases legados `AI_IMPORT_*` continuam aceitos quando os nomes `AI_*` nao estiverem configurados.

Esta camada e compartilhada pela importacao assistida e pelas sugestoes de planejamento/recorrentes.

## Privacidade

- O recurso deve permanecer desativado ate haver decisao explicita de produto/privacidade.
- Quando ativado, o texto extraido do PDF pode conter dados financeiros e identificadores pessoais.
- O app nao confirma transacoes automaticamente a partir da IA.
- O enriquecimento e assistivo: sugestoes de categoria, descricao e duplicidade ficam visiveis no preview e podem ser revisadas.
- O backend salva apenas o preview normalizado e metadados tecnicos no `raw_row`, sem salvar o prompt completo.

## Custo e latencia

- A IA pode aumentar custo por importacao e adicionar latencia ao preview.
- O uso deve ficar restrito a PDFs sem parser dedicado, falhas de extracao ou acionamento manual do usuario.
- Timeouts devem retornar erro claro sem bloquear o fluxo de importacao manual.

## Riscos

- A IA pode omitir, duplicar ou interpretar valores incorretamente.
- A IA pode classificar pagamento/credito como despesa se o PDF estiver ambivalente.
- Por isso, itens gerados por IA entram com `needs_review=true` e exigem revisao no preview.
- Sugestoes de categoria respeitam apenas categorias existentes do usuario; novas categorias/regras nao sao criadas automaticamente.

## Producao

Antes de ativar:

- Revisar politica de privacidade.
- Provider definido: OpenAI.
- Modelo inicial recomendado: `gpt-4o-mini`.
- Configurar segredo no Render.
- Executar smoke test com PDF desconhecido.
- Confirmar que parsers conhecidos continuam sem chamada de IA.

## Decisao de ativacao

- Em 2026-07-08, o owner autorizou o envio do texto extraido dos PDFs para a OpenAI para fins de analise/importacao assistida.
- A API key deve ser configurada apenas no ambiente do Render, nunca em arquivos versionados.
- Se a chave tiver sido compartilhada em chat, recomenda-se rotacionar a chave antes de ativar em producao.

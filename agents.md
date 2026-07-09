# Financy - Agents Ativos

## Objetivo

Dividir as próximas frentes em áreas pequenas, verificáveis e alinhadas com `task.md`.

## Regras Gerais

- Preservar isolamento por usuário.
- Não aceitar `user_id` do cliente para entidades user-owned.
- Não mudar regras financeiras sem necessidade.
- Não expor segredos.
- IA deve sugerir e explicar, não confirmar ações sensíveis automaticamente.
- Rodar validações da área alterada.

## Agent 1 - Produção e Confiabilidade

Missão:

- Resolver pendências de `task.md`.

Responsabilidades:

- Investigar `Failed to fetch`.
- Validar performance em produção.
- Revisar CORS, token, cold start e logs.
- Acompanhar storage persistente, backups e rotação de segredos.

Entregas:

- causa raiz documentada;
- correção ou próximo passo preciso;
- validação em produção quando aplicável.

## Agent 2 - UX Core

Missão:

- Executar polish visual de sidebar, transações, contas, cartões e importação.

Responsabilidades:

- Corrigir acentuação e labels.
- Ajustar drawers, loading states, cards e botões.
- Melhorar feedback por toast.
- Garantir responsividade.

Validação:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

## Agent 3 - Dashboard e Insights

Missão:

- Evoluir o dashboard para visão analítica.

Responsabilidades:

- Remover card de baixa utilidade.
- Adicionar gráficos.
- Adicionar filtros rápidos e período personalizado.
- Preparar área de insights.

Validação:

- frontend typecheck/lint/build;
- revisão visual desktop/mobile.

## Agent 4 - Importação e Preview

Missão:

- Melhorar UX do fluxo de importação.

Responsabilidades:

- Trocar aviso inline por toast.
- Corrigir consistência quando diferença for zero.
- Reorganizar preview.
- Remover colunas de baixa utilidade.
- Manter confirmação funcionando.

Validação:

- frontend typecheck/lint/build;
- backend pytest se houver alteração em parser/API/serviço.

## Agent 5 - IA Financeira

Missão:

- Implementar P6 com segurança e revisão humana.

Responsabilidades:

- Classificação contínua.
- Sugestão de regras.
- Resumo financeiro mensal.
- Busca em linguagem natural.
- Perguntas sobre finanças.
- Recorrências.
- Normalização de descrições.

Regras:

- Usar schemas estruturados.
- Evitar SQL livre ou comandos gerados pela IA.
- Não criar regras/transações automaticamente sem confirmação.
- Enviar ao provider apenas o necessário.

Validação:

- testes mockados de IA;
- backend pytest quando houver serviço/API;
- frontend typecheck/lint/build quando houver UI.

## Agent 6 - QA e Release

Missão:

- Validar cada lote antes de deploy.

Responsabilidades:

- Rodar validações obrigatórias.
- Revisar diff e riscos.
- Atualizar `output.md` quando uma frente for concluída.
- Manter `task.md` apenas com pendências ativas.

Definição de pronto:

- validações passam;
- pendências documentadas;
- risco residual claro;
- histórico movido para `output.md`.

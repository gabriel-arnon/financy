# Financy - Especificação Ativa

## Contexto

O Financy já possui autenticação, isolamento por usuário, importação de faturas, edição de transações, toasts globais, parsers dedicados e IA assistiva para importação. A próxima etapa concentra melhorias de UX, estabilidade de produção e inteligência financeira.

## Requisitos de Produto

### RP01 - UX consistente

- Corrigir labels e acentuação.
- Padronizar loading states.
- Remover ruídos visuais como status técnico exposto ao usuário.
- Fechar drawers automaticamente após ações bem-sucedidas quando fizer sentido.
- Usar toast para feedback global.

### RP02 - Dashboard analítico

- Remover cards pouco úteis.
- Adicionar gráficos de gastos.
- Adicionar insights.
- Melhorar filtros rápidos e período personalizado.
- Garantir que cards, gráficos e insights respondem ao mesmo filtro.

### RP03 - Transações

- Manter tabela e drawer limpos.
- Preservar edição completa de data, descrição, tipo, categoria, origem, valor e pendência.
- Evitar exposição de status técnico como `confirmed`.
- Manter criação/edição com feedback claro.

### RP04 - Contas e Cartões

- Melhorar navegação para detalhes com loading.
- Ajustar layout de cards relacionados.
- Padronizar BRL em criação/edição de cartão.
- Melhorar disposição de faturas e últimas transações.

### RP05 - Importação

- Substituir avisos inline redundantes por toast.
- Corrigir análise de consistência quando diferença for zero.
- Melhorar UX do preview.
- Remover colunas de baixa utilidade da lista principal.
- Manter detalhes importantes acessíveis de forma secundária.

### RP06 - IA Financeira Assistiva

- IA pode sugerir, explicar e resumir.
- IA não deve confirmar transações, criar regras ou alterar dados sensíveis sem revisão/ação do usuário.
- Sugestões devem usar categorias e entidades existentes quando aplicável.
- Respostas devem ser baseadas em dados do usuário autenticado.
- Deve haver proteção contra prompt injection em busca/perguntas.

## Requisitos Não Funcionais

- Preservar isolamento por usuário.
- Não aceitar `user_id` do cliente para entidades user-owned.
- Manter `/health` público.
- Evitar retry automático em escritas não idempotentes.
- Usar schemas estruturados para respostas de IA.
- Não enviar dados excessivos ao provider de IA.
- Manter segredos fora do repositório.

## Validação

Frontend:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

Backend, quando aplicável:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Smoke pós-deploy:

- login;
- navegação entre abas;
- criar/editar/excluir transação;
- criar/editar/inativar categoria/regra;
- importar fatura;
- confirmar preview;
- validar dashboard de cartão;
- validar isolamento entre dois usuários reais.

## Fora de Escopo Imediato

- Painel admin completo.
- Ativação de RLS sem staging.
- Aconselhamento financeiro profissional.
- Automação financeira irreversível por IA sem confirmação humana.

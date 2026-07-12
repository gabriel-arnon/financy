# Financy - Plano Ativo

## Objetivo

Evoluir o Financy após a fase de autenticação e estabilização inicial, priorizando:

- confiabilidade operacional em produção;
- UX mais polida nas áreas principais;
- inteligência financeira assistida por IA;
- preparação para uso privado estável e futuro uso público.

## Frentes Ativas

### 1. Produção e Operação

Arquivo principal: `task.md`

Foco:

- investigar `Failed to fetch` residual;
- validar performance real no Render/Vercel;
- definir storage persistente de uploads;
- confirmar backups e restore;
- rotacionar segredos;
- validar smoke multiusuário em produção;
- decidir ativação futura de RLS.

### 2. Produto e UX

Arquivo principal: `task.md`

Foco:

- polish visual e bugs de UX em sidebar, dashboard, transações, contas, cartões e importação;
- evolução do dashboard com gráficos, insights e filtros;
- melhoria do preview de importação;
- padronização de loading states e formatação BRL.

### 3. IA Financeira

Arquivo principal: `task.md`

Foco:

- classificação automática contínua;
- criação inteligente de regras;
- resumo financeiro mensal;
- busca em linguagem natural;
- perguntas sobre finanças;
- detecção de recorrências;
- renomeação de descrições importadas.

### 4. Ressarcimentos

Arquivo principal: `docs/reimbursements-plan.md`

Foco:

- manter Fundacoes 0, 1 e 2 estabilizadas;
- manter migrations validadas em PostgreSQL local e aplicar em Supabase remoto apenas com autorizacao explicita;
- preparar Fundacao 3 somente depois de validar RLS, convites e escopo de portal guest;
- nao iniciar Telegram, OCR, audio, pagamentos ou inbox antes das fundacoes owner/guest estarem seguras.

## Sequência Recomendada

1. Resolver P7.1, P7.3, P7.6 por serem ajustes diretos e visíveis.
2. Executar P7.2 para melhorar o dashboard com gráficos/filtros/insights.
3. Executar P7.4 e P7.5 para melhorar detalhes de conta/cartão.
4. Atacar PD0/PD1 em paralelo quando houver evidência de produção.
5. Iniciar P6.1 e P6.2 antes das demais features de IA, pois aproveitam dados e regras já existentes.
6. Implementar P6.3 depois que agregações e filtros do dashboard estiverem sólidos.
7. Implementar P6.4/P6.5 quando houver escopo claro de intents e limites de segurança.
8. Implementar P6.6/P6.7 como refinamentos contínuos.
9. Para Ressarcimentos, proxima fase recomendada: RLS final, convites/memberships e portal guest limitado, sem pagamentos integrados.

## Critérios de Pronto

Cada entrega deve:

- manter backend/API compatível, salvo quando a task exigir ajuste;
- preservar isolamento por usuário;
- manter labels em Português brasileiro;
- evitar automações financeiras sem confirmação humana;
- incluir testes proporcionais ao risco;
- passar nas validações obrigatórias da área alterada.

## Relatório Histórico

O histórico do que já foi implementado foi movido para `output.md`.

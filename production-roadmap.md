# Financy — Roadmap de Produção e Direção de Produto

> Objetivo: transformar o Financy em um SaaS de finanças pessoais inspirado em produtos como Dinzo e Recta, mas com identidade própria, customizações pessoais e diferenciais focados em importação inteligente, organização financeira e automação.

## 1. Direção do produto

O Financy não deve ser tratado apenas como um importador de faturas ou extratos. A importação de PDFs, OFX, CSV e XLSX é uma funcionalidade importante, mas o produto deve evoluir como uma plataforma completa de controle financeiro pessoal.

### Referências de mercado

- Dinzo: dashboard financeiro, planejamento, categorias, limites, previsões e visão geral bem organizada.
- Recta: contas, cartões, transações, recorrentes, metas, orçamentos, relatórios e análise financeira.

### Posicionamento desejado

O Financy deve ser um SaaS financeiro pessoal com:

- Dashboard centralizado.
- Gestão de contas bancárias.
- Gestão de cartões de crédito.
- Faturas mensais por cartão.
- Transações manuais e importadas.
- Categorias personalizadas.
- Regras de classificação automática.
- Importação de arquivos financeiros.
- Relatórios e análises.
- Futuramente: recorrências, orçamentos, metas, Open Finance e IA financeira.

## 2. Princípios de evolução

1. Estabilidade antes de novas features.
2. UX clara antes de complexidade.
3. Testes antes de produção.
4. Dados seguros antes de multiusuário.
5. Banco real antes de SaaS público.
6. Importação como diferencial, não como núcleo único.
7. Cada entidade deve existir independentemente da origem do dado.

## 3. Arquitetura alvo

### MVP local atual

- Frontend: Next.js.
- Backend: FastAPI.
- Banco local/dev: JSON local e estrutura preparada para PostgreSQL.
- Importação: PDF, OFX, CSV, XLSX.
- Regras: classificação determinística por palavra-chave.

### Produção privada recomendada

- Frontend: Vercel.
- Backend: Railway ou Render.
- Banco: Supabase PostgreSQL ou Neon.
- Storage: Cloudflare R2 ou Supabase Storage.
- Auth: Supabase Auth ou autenticação própria com JWT.

### Produção SaaS futura

- Multiusuário real.
- Isolamento por `user_id`.
- PostgreSQL definitivo.
- Backups automáticos.
- Logs e monitoramento.
- LGPD.
- Termos de uso e política de privacidade.
- Pagamentos e planos.

## 4. Roadmap técnico para produção

## Fase 1 — Preparação para produção privada

Objetivo: colocar o Financy no ar para uso próprio diário.

- [ ] Revisar `.env.example` do frontend e backend.
- [ ] Definir variáveis obrigatórias: `DATABASE_URL`, `NEXT_PUBLIC_API_URL`, `JWT_SECRET`, `APP_ENV`, `UPLOAD_STORAGE_PATH`.
- [ ] Criar Docker Compose completo para desenvolvimento.
- [ ] Garantir que backend rode sem depender de caminhos locais fixos.
- [ ] Garantir que frontend consuma API via variável de ambiente.
- [ ] Criar script de seed oficial.
- [ ] Criar script de backup local.
- [ ] Criar checklist de deploy.

## Fase 2 — PostgreSQL definitivo

Objetivo: sair do uso operacional do JSON local e consolidar banco relacional.

- [ ] Revisar migrations existentes.
- [ ] Criar schema PostgreSQL definitivo.
- [ ] Migrar entidades principais: users, accounts, cards, card_statements, transactions, categories, classification_rules.
- [ ] Criar script de migração do JSON local para PostgreSQL.
- [ ] Garantir `user_id` obrigatório nas entidades.
- [ ] Criar índices para `user_id`, `transaction_date`, `account_id`, `card_id`, `card_statement_id`, `category_id`.
- [ ] Rodar testes backend usando banco de teste.
- [ ] Garantir rollback seguro.

## Fase 3 — Autenticação

Objetivo: transformar o Financy em app privado com login.

- [ ] Escolher estratégia: Supabase Auth ou JWT próprio.
- [ ] Criar tela de login.
- [ ] Criar tela de cadastro.
- [ ] Criar recuperação de senha.
- [ ] Criar logout.
- [ ] Proteger rotas frontend.
- [ ] Proteger rotas backend.
- [ ] Garantir que toda query use `user_id`.
- [ ] Criar testes de isolamento por usuário.

## Fase 4 — Multiusuário e segurança

Objetivo: preparar base para SaaS real.

- [ ] Revisar todas as APIs para isolamento de dados.
- [ ] Impedir acesso cruzado entre usuários.
- [ ] Implementar rate limiting.
- [ ] Validar CORS de produção.
- [ ] Adicionar logs de erro.
- [ ] Adicionar logs de autenticação.
- [ ] Adicionar backups automáticos.
- [ ] Criar política de privacidade.
- [ ] Criar termos de uso.
- [ ] Criar rotina de exclusão de conta/dados.
- [ ] Criar rotina de exportação de dados.

## Fase 5 — Deploy privado

Objetivo: subir o sistema para uso real controlado.

Stack sugerida:

- Frontend: Vercel.
- Backend: Railway.
- Banco: Supabase PostgreSQL.
- Storage: Supabase Storage ou Cloudflare R2.

Tasks:

- [ ] Criar projeto na Vercel.
- [ ] Criar projeto no Railway ou Render.
- [ ] Criar banco PostgreSQL no Supabase ou Neon.
- [ ] Configurar variáveis de ambiente.
- [ ] Configurar domínio.
- [ ] Configurar HTTPS.
- [ ] Testar fluxo completo: login, criação de conta, criação de cartão, transação manual, importação, regra, dashboard.
- [ ] Criar backup inicial pós-deploy.

## 5. Roadmap funcional pós-MVP

## Prioridade A — Funcionalidades essenciais de SaaS financeiro

### Transações

- [x] Listagem moderna.
- [x] Drawer de edição.
- [x] Criação manual.
- [x] Ações em lote.
- [ ] Transações recorrentes.
- [ ] Parcelamento manual.
- [ ] Duplicação de transação.
- [ ] Anexos em transações.
- [ ] Histórico de alterações.

### Contas

- [x] CRUD de contas bancárias.
- [x] Detalhe operacional.
- [ ] Transferência entre contas.
- [ ] Ajuste de saldo.
- [ ] Saldo inicial e saldo atual calculado.
- [ ] Conta arquivada.
- [ ] Conta de investimento.

### Cartões

- [x] CRUD de cartões.
- [x] Cartão vinculado a conta.
- [x] Detalhe operacional.
- [x] Faturas mensais por cartão.
- [ ] Fechamento automático de fatura.
- [ ] Melhor dia de compra.
- [ ] Limite usado por período.
- [ ] Compra parcelada manual.
- [ ] Pagamento de fatura vinculado à conta.

### Categorias

- [x] CRUD de categorias personalizadas.
- [x] Categorias do sistema protegidas.
- [x] Agrupamento por tipo.
- [ ] Cores por categoria.
- [ ] Ícones por categoria.
- [ ] Categorias essenciais e não essenciais.
- [ ] Subcategorias.

### Regras

- [x] Regras determinísticas por palavra-chave.
- [x] Regras em configurações.
- [ ] Prioridade visual mais clara.
- [ ] Simulador de regra.
- [ ] Sugestão automática de regra após várias transações parecidas.

## Prioridade B — Planejamento financeiro

### Orçamentos

- [ ] Criar orçamento mensal por categoria.
- [ ] Comparar gasto real vs orçamento.
- [ ] Alertar estouro de orçamento.
- [ ] Mostrar progresso por categoria.

### Metas

- [ ] Criar metas financeiras.
- [ ] Acompanhar progresso.
- [ ] Vincular meta a conta.
- [ ] Estimar prazo para atingir meta.

### Limites

- [ ] Limites de gasto por categoria.
- [ ] Limites por cartão.
- [ ] Alertas visuais.

### Recorrências

- [ ] Criar receitas recorrentes.
- [ ] Criar despesas recorrentes.
- [ ] Criar assinaturas.
- [ ] Previsão mensal baseada em recorrências.

## Prioridade C — Análise e relatórios

### Dashboard

- [x] Cards principais.
- [ ] Fluxo de caixa mensal.
- [ ] Evolução de saldo.
- [ ] Gastos por categoria.
- [ ] Gastos por cartão.
- [ ] Próximas faturas.
- [ ] Previsão do mês.
- [ ] Comparativo mês atual vs mês anterior.

### Relatórios

- [ ] Relatório mensal.
- [ ] Relatório por categoria.
- [ ] Relatório por conta.
- [ ] Relatório por cartão.
- [ ] Exportar CSV.
- [ ] Exportar PDF.

### Inteligência financeira

- [ ] Insights simples baseados em regras.
- [ ] Alertas de aumento de gastos.
- [ ] Maior categoria de gastos.
- [ ] Taxa de economia.
- [ ] Previsão do próximo mês.
- [ ] IA futura para análise financeira.

## Prioridade D — Importação e automação

### Importação

- [x] Importação PDF.
- [x] Importação OFX/CSV/XLSX.
- [x] Preview antes de confirmar.
- [x] Aplicar conta/cartão no preview.
- [ ] Melhor detecção de duplicidade.
- [ ] Importação com histórico.
- [ ] Tela de importações anteriores.
- [ ] Reprocessar arquivo.
- [ ] Desfazer importação.
- [ ] Anexar arquivo à fatura/transações.

### Open Finance

- [ ] Estudar provedores.
- [ ] Mapear custos.
- [ ] Definir arquitetura.
- [ ] Sincronização bancária.
- [ ] Atualização automática de saldo.
- [ ] Importação automática de transações.

## 6. Referências visuais e de produto

### Dinzo

Pontos interessantes para observar:

- Sidebar organizada por domínios.
- Dashboard de visão geral.
- Fluxo de caixa.
- Equilíbrio financeiro.
- Contas e cartões em blocos.
- Categorias.
- Limites de gastos.
- Planejamento.

### Recta

Pontos interessantes para observar:

- Dashboard escuro bem estruturado.
- Contas bancárias.
- Cartões de crédito.
- Recorrentes.
- Metas.
- Orçamentos.
- Relatórios.
- Inteligência financeira.
- Previsão de próximo mês.

### Como o Financy deve se diferenciar

- Melhor fluxo de importação de arquivos.
- Regras de classificação simples e editáveis.
- UX mais limpa e direta.
- Foco inicial em uso pessoal real.
- Possibilidade futura de IA.
- Customização maior por usuário.
- Controle manual + automação.

## 7. Checklist antes de produção pública

### Técnico

- [ ] PostgreSQL definitivo.
- [ ] Autenticação.
- [ ] Isolamento por usuário.
- [ ] Backups.
- [ ] Logs.
- [ ] Monitoramento.
- [ ] Error Boundary.
- [ ] Testes E2E principais.
- [ ] CI/CD.
- [ ] HTTPS.
- [ ] Variáveis de ambiente seguras.

### Produto

- [ ] Onboarding.
- [ ] Dados de exemplo.
- [ ] Empty states claros.
- [ ] Tutorial de importação.
- [ ] Página de plano/assinatura.
- [ ] Política de privacidade.
- [ ] Termos de uso.
- [ ] Suporte/feedback.

### Segurança e LGPD

- [ ] Consentimento de tratamento de dados.
- [ ] Exportação dos dados do usuário.
- [ ] Exclusão da conta.
- [ ] Criptografia de senhas.
- [ ] Proteção contra acesso cruzado.
- [ ] Rate limiting.
- [ ] Logs de acesso.
- [ ] Política de retenção de dados.

## 8. Fora do escopo imediato

- Aplicativo mobile nativo.
- Open Finance em produção.
- IA avançada.
- Compartilhamento familiar.
- Multiempresa.
- Emissão fiscal.
- Integração contábil.
- Investimentos avançados.
- Comunidade interna.

## 9. Ordem recomendada a partir de agora

1. Finalizar revisão visual da tela de transações.
2. Criar baseline limpo dos dados locais.
3. Criar roadmap de produção.
4. Migrar para PostgreSQL definitivo.
5. Implementar autenticação.
6. Subir produção privada.
7. Usar diariamente por 2 a 4 semanas.
8. Ajustar bugs reais.
9. Implementar recorrências/orçamentos/metas.
10. Planejar versão pública.

## 10. Critério de pronto para produção privada

O Financy estará pronto para produção privada quando:

- [ ] Rodar com PostgreSQL real.
- [ ] Não depender de JSON local.
- [ ] Tiver autenticação.
- [ ] Tiver backup.
- [ ] Tiver deploy separado de frontend e backend.
- [ ] Tiver variáveis de ambiente configuradas.
- [ ] Tiver dados isolados por usuário.
- [ ] Tiver dashboard, contas, cartões, transações, categorias, regras e importação funcionando.
- [ ] Tiver logs básicos.
- [ ] Tiver documentação de setup.

## 11. Critério de pronto para produção pública

O Financy estará pronto para produção pública quando:

- [ ] Produção privada estiver estável.
- [ ] Fluxo de onboarding estiver claro.
- [ ] Termos e política estiverem publicados.
- [ ] Multiusuário estiver testado.
- [ ] Backups estiverem automatizados.
- [ ] Segurança básica estiver revisada.
- [ ] Planos e limites estiverem definidos.
- [ ] Suporte/feedback estiver implementado.
- [ ] Bugs críticos estiverem zerados.
- [ ] O produto resolver um fluxo financeiro completo melhor do que uma planilha.

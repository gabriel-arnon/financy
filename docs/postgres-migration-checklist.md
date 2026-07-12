# Financy - Checklist de Migracao PostgreSQL

Use este checklist antes de migrar dados locais do JSON para PostgreSQL.

## Pre-migracao

- [ ] Confirmar que o Docker esta rodando.
- [ ] Subir PostgreSQL: `.\scripts\setup_dev_db.ps1 -ResetSchema`.
- [ ] Confirmar `DATABASE_URL` do destino.
- [ ] Confirmar se o destino e local/teste ou producao Supabase/Neon.
- [ ] Se for producao, confirmar backup automatico do provedor antes do apply.
- [ ] Rodar `docker-compose config`.
- [ ] Rodar testes JSON: `cd backend && .\.venv\Scripts\python.exe -m pytest`.
- [ ] Preparar banco de teste: `scripts\prepare_test_database.py`.
- [ ] Rodar testes PostgreSQL contra `financy_dev_test`.

## Dry-run

- [ ] Rodar `scripts\migrate_json_to_postgres.py --dry-run`.
- [ ] Conferir contagens do JSON.
- [ ] Conferir reparos de integridade relatados.
- [ ] Confirmar que nao ha erros de UUID, enum ou referencia.

## Apply

- [ ] Confirmar que o banco alvo pode receber a migracao.
- [ ] Rodar `scripts\migrate_json_to_postgres.py --apply`.
- [ ] Registrar caminho do backup criado.
- [ ] Conferir contagens PostgreSQL.
- [ ] Confirmar que as contagens batem com o relatorio efetivo da migracao.
- [ ] Se os dados migrados ainda usam `DEV_USER_ID`, executar `scripts\reassign_user_data.py` para mover ownership ao usuario Supabase real.

## Validacao

- [ ] Subir backend com `STORAGE_BACKEND=postgres`.
- [ ] Em producao/staging, subir backend com `AUTH_REQUIRED=true` e `AUTH_DEV_BYPASS=false`.
- [ ] Abrir `/health`.
- [ ] Listar categorias.
- [ ] Listar contas.
- [ ] Listar cartoes.
- [ ] Listar transacoes.
- [ ] Criar/editar/inativar uma conta de teste.
- [ ] Criar/editar/inativar um cartao de teste.
- [ ] Criar/editar/excluir uma transacao de teste.
- [ ] Criar regra de classificacao de teste.
- [ ] Testar preview de importacao basica.

## Rollback

- [ ] Parar backend em modo PostgreSQL.
- [ ] Voltar `STORAGE_BACKEND=json`.
- [ ] Restaurar `local_dev_db.json` do backup se necessario.
- [ ] Recolocar uploads do backup se necessario.
- [ ] Reiniciar backend.
- [ ] Validar `/health` e listagens principais.

## Limpeza de banco de teste

Para resetar o banco de teste:

```powershell
cd backend
$env:TEST_DATABASE_URL='postgresql://financy_dev:financy_dev_local@localhost:5432/financy_dev_test'
.\.venv\Scripts\python.exe scripts\prepare_test_database.py
.\.venv\Scripts\python.exe -m pytest tests_postgres -m postgres
```

## Riscos remanescentes

- Autenticacao Supabase existe, mas depende de `JWT_SECRET`/issuer/audience corretos no ambiente.
- RLS ainda nao foi ativado automaticamente; existe draft em `docs/supabase/rls_phase3_draft.sql`.
- Dados legados podem continuar no `DEV_USER_ID` ate executar reassociacao para o usuario real.
- Deploy real ainda precisa de configuracao propria.
- JSON permanece como fallback/dev ate a proxima fase.

# Checklist de Deploy Financy

Use este checklist antes e depois de deploys em Dev ou Production. Nao registre
secrets nos logs, documentos ou screenshots.

## Antes do Deploy

- Branch correta para o ambiente.
- `git status` sem alteracoes inesperadas.
- Backend tests executados.
- Frontend build executado quando houver alteracao de frontend.
- Migrations presentes e revisadas.
- Migrations pendentes identificadas, incluindo `009_reimbursement_comments.sql` e `010_invitation_accept_rate_limits.sql` quando a Fundacao 3.5 for liberada.
- `DATABASE_URL` aponta para o banco correto e nao usa `localhost` em ambiente remoto.
- `NEXT_PUBLIC_API_URL` aponta para o backend correto e nao usa `localhost` em ambiente remoto.
- JWT issuer/JWKS correspondem ao projeto Supabase correto.
- CORS inclui somente origens esperadas do ambiente.
- Bucket privado `private-files` existe quando storage Supabase estiver ativo.
- `SUPABASE_SERVICE_ROLE_KEY` existe somente no backend.
- Nenhuma credencial esta versionada.
- Variaveis de rate limit de convites configuradas:
  - `INVITATION_ACCEPT_RATE_LIMIT_ENABLED`
  - `INVITATION_ACCEPT_RATE_LIMIT_MAX_ATTEMPTS`
  - `INVITATION_ACCEPT_RATE_LIMIT_WINDOW_SECONDS`

## Depois do Deploy

- `/health` responde.
- Login/logout funcionam.
- Dashboard carrega.
- Transacoes carregam.
- Contas carregam.
- Cartoes carregam.
- Importacoes carregam.
- Ressarcimentos owner-only carregam.
- Invitations e memberships funcionam.
- Portal guest carrega apenas dados compartilhados.
- Claim attachments e signed URLs continuam protegidas.
- Comentarios de ressarcimento funcionam para owner e guest autorizado.
- Exclusao de comentarios usa dialogo, respeita permissoes e nao usa confirmacao nativa do navegador.
- Comentarios sao exibidos como texto puro e nao renderizam HTML arbitrario.
- Aceite de convite retorna `429` apos excesso de tentativas configurado.
- Logs revisados para `401`, `403`, `429` e `500`.
- DevTools nao mostra chamadas para ambiente incorreto.
- TTFB medido e registrado quando relevante.

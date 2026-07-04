# Financy - Phase 3 Auth and User Isolation Plan

## Goal

Implement authentication and strict user isolation without changing the financial behavior already validated in Phases 1 and 2.

This document is planning only. It does not implement auth and does not change API behavior yet.

## Recommendation

Use Supabase Auth as the primary authentication provider, with the frontend sending the Supabase access token to the FastAPI backend as a Bearer token.

Recommended shape:

- Frontend: Supabase Auth via `@supabase/supabase-js`.
- Backend: validate Supabase JWTs and derive `user_id` from the token subject (`sub`).
- Database: keep `profiles` as the app user table, with `profiles.id` matching Supabase Auth user IDs.
- Local development: keep `DEV_USER_ID` only behind an explicit local/dev bypass, not as production fallback.
- Future hardening: add Supabase RLS policies after backend auth is stable.

Why this is the best fit:

- The database already uses `profiles`, which matches the common Supabase Auth pattern.
- Existing roadmap/docs already mention replacing `DEV_USER_ID` with Supabase Auth.
- It avoids building password storage, password reset, email verification, refresh-token handling and account recovery.
- It keeps the FastAPI backend as the owner of business rules while delegating identity to a managed provider.
- It allows private production quickly, then RLS can be added as an additional database safety layer.

## Auth Approach Comparison

### JWT own auth

Pros:

- Full control over token claims, user lifecycle and password policy.
- No dependency on Supabase Auth.

Cons:

- Requires implementing password hashing, refresh tokens, reset flows, email verification, lockout/rate limits and account recovery.
- Higher security burden.
- Duplicates what Supabase already provides.
- More implementation time before private production.

Verdict:

- Not recommended for this project now.

### Supabase Auth

Pros:

- Aligns with existing `profiles` schema.
- Provides hosted auth flows, JWTs, refresh sessions and user management.
- Pairs naturally with future RLS.
- Reduces custom security code.

Cons:

- Adds external service dependency.
- Backend must validate JWT correctly and handle key rotation.
- Local/test mode needs a clear bypass or test token strategy.

Verdict:

- Recommended.

### Session cookies

Pros:

- Can be very secure with httpOnly, Secure and SameSite cookies.
- Good for server-rendered apps and browser-first flows.

Cons:

- Requires session middleware or a backend-for-frontend pattern.
- Current frontend API client is a direct `fetch` wrapper using `NEXT_PUBLIC_API_URL`.
- Cross-origin local dev and CORS become more sensitive.
- Still needs an identity provider or custom login underneath.

Verdict:

- Not recommended as the first Phase 3 implementation. Consider later if the app moves to a server-side Next auth boundary.

## Current State

### User Context

Current user handling is centralized in `backend/app/api/deps.py`:

```python
def get_user_id() -> str:
    # Future swap point: validate Supabase Auth JWT and return auth.uid().
    return settings.dev_user_id
```

Current implications:

- Every protected API call behaves as the same local user.
- `DEV_USER_ID` is configured in `backend/app/core/config.py`.
- Repositories already receive `user_id` as an argument in most operations.
- Phase 2 PostgreSQL creates a placeholder `profiles` row for the dev user.

### Frontend API Client

Current frontend client is `frontend/src/lib/api.ts`.

Current behavior:

- Sends JSON requests to `NEXT_PUBLIC_API_URL`.
- Does not attach `Authorization`.
- Does not handle `401` or session expiration.
- Does not have login/logout/session state.

### Public Endpoint

Only this endpoint should remain public:

- `GET /health`

## Entities Requiring User Isolation

### User-owned entities

These entities must always be scoped by authenticated `user_id`:

- `accounts`
- `cards`
- `card_statements`
- `transactions`
- `classification_rules`
- `import_files`
- `import_batches`
- `import_preview_items`

### Shared/system entities

These entities can be shared globally:

- `categories` where `user_id is null` and `is_system = true`

### User-customizable shared model

`categories` needs mixed behavior:

- System categories are visible to all users.
- User categories belong to exactly one user.
- Create/update/delete of user categories must not mutate another user's category.
- Editing/deleting system categories should be restricted or treated carefully. Current code allows updates to categories where `user_id is null or user_id = current_user`; Phase 3 should tighten this so normal users cannot modify system categories.

### Identity entity

`profiles` should represent app users:

- `profiles.id` should equal Supabase Auth `auth.users.id`.
- `profiles.email` and `profiles.full_name` can be mirrored from auth metadata.
- Profile creation should happen on first authenticated request or via a Supabase trigger/migration.

### Storage/upload isolation

File uploads are represented by `import_files.user_id`, but the physical storage path is not yet user-partitioned.

Target:

- Store uploaded files under a user-scoped path, for example `uploads/{user_id}/{file_id}.ext`.
- Ensure file reads never use only arbitrary paths from request input.
- Existing migrated files can remain in place while DB access is user-scoped.

## Endpoints That Must Be Protected

All financial endpoints below must require authentication and derive `user_id` from the token.

### Transactions

- `GET /transactions`
- `POST /transactions`
- `PUT /transactions/{transaction_id}`
- `DELETE /transactions/{transaction_id}`

Isolation rule:

- Users can only list, create, edit and delete their own transactions.
- Linked `account_id`, `card_id`, `card_statement_id`, `category_id` and `source_file_id` must either belong to the same user or be a valid system/shared entity.

### Imports

- `POST /imports/upload`
- `GET /imports/{import_id}/preview`
- `POST /imports/{import_id}/confirm`

Isolation rule:

- Users can only access their own import batches and preview items.
- Confirmed transactions must inherit the authenticated user ID.
- File metadata must be written with authenticated user ID.

### Statements

- `GET /statements`
- `GET /statements/{statement_id}`
- `DELETE /statements/{statement_id}`
- `PATCH /statements/{statement_id}/status`

Isolation rule:

- Users can only access statements owned by them.
- Statement cards and transactions must also belong to the same user.

### Categories

- `GET /categories`
- `POST /categories`
- `PUT /categories/{category_id}`
- `DELETE /categories/{category_id}`

Isolation rule:

- Users can list system categories plus their own categories.
- Users can create only user-owned categories.
- Users should not update/delete system categories in normal app flows.
- Users cannot update/delete another user's category.

### Accounts

- `GET /accounts`
- `GET /accounts/{account_id}/summary`
- `POST /accounts`
- `PUT /accounts/{account_id}`
- `DELETE /accounts/{account_id}`

Isolation rule:

- Users can only access their own accounts.
- Summary calculations must include only the authenticated user's cards, statements and transactions.

### Cards

- `GET /cards`
- `GET /cards/{card_id}/summary`
- `POST /cards`
- `PUT /cards/{card_id}`
- `DELETE /cards/{card_id}`

Isolation rule:

- Users can only access their own cards.
- Card `account_id` must belong to the same user.
- Summary calculations must include only authenticated user's statements and transactions.

### Classification Rules

- `GET /classification-rules`
- `POST /classification-rules`
- `PUT /classification-rules/{rule_id}`
- `DELETE /classification-rules/{rule_id}`

Isolation rule:

- Users can only manage their own rules.
- Rule `category_id` must reference a system category or one of the user's categories.

## Target State

### Backend

- `get_user_id()` is replaced by an authenticated dependency, for example `get_current_user()` or `get_current_user_id()`.
- The dependency validates Supabase JWT access tokens.
- `user_id` is never accepted from request body for user-owned records.
- Repository methods continue receiving `user_id` from backend context.
- All entity lookups remain scoped by `user_id`.
- Unauthorized requests return `401`.
- Authenticated users trying to access another user's resource receive `404` or `403`.

Recommendation:

- Prefer `404` for cross-user resource access to avoid leaking resource existence.
- Use `403` only for authenticated users performing known disallowed actions, such as editing a system category if the resource is intentionally visible.

### Frontend

- Add login/logout/session screens.
- Store Supabase session through the Supabase client.
- Attach `Authorization: Bearer <access_token>` to every protected API request.
- Redirect unauthenticated users away from app routes.
- Handle `401` by clearing session and sending the user to login.

### Database

- `profiles.id` continues to be the canonical app user ID.
- All user-owned tables keep `user_id`.
- Add constraints/indexes where needed for user-scoped uniqueness.
- Add RLS policies after backend token auth is verified.

## Database Changes Needed

### Required before auth goes live

- Ensure every real user has a `profiles` row.
- Decide profile creation strategy:
  - Backend upsert on first valid request, or
  - Supabase trigger on `auth.users` insert.
- Tighten category policy:
  - System categories: `user_id is null`.
  - User categories: `user_id = auth user`.
  - Normal app users cannot mutate system categories.

### Recommended constraints/indexes

- Keep indexes from Phase 2 on all `user_id` fields.
- Consider composite indexes for frequent scoped lookups:
  - `transactions(user_id, transaction_date)`
  - `cards(user_id, account_id)`
  - `card_statements(user_id, card_id, reference_month)`
  - `import_preview_items(user_id, import_batch_id)`
- Consider user-scoped uniqueness:
  - `accounts(user_id, name)` where status is active, if duplicate account names should be prevented.
  - `cards(user_id, account_id, last_digits)` where status is active, if duplicate cards should be prevented.
  - `classification_rules(user_id, keyword, category_id, transaction_type, match_scope)` if duplicate rules become a problem.

### RLS later in the phase

RLS should not be the first implementation step unless the backend is ready to pass verified user context to database calls.

Recommended RLS direction:

- `profiles`: user can select/update own profile.
- `accounts`: user can CRUD rows where `user_id = auth.uid()`.
- `cards`: user can CRUD rows where `user_id = auth.uid()`.
- `card_statements`: user can CRUD rows where `user_id = auth.uid()`.
- `transactions`: user can CRUD rows where `user_id = auth.uid()`.
- `classification_rules`: user can CRUD rows where `user_id = auth.uid()`.
- `import_files`: user can CRUD rows where `user_id = auth.uid()`.
- `import_batches`: user can CRUD rows where `user_id = auth.uid()`.
- `import_preview_items`: user can CRUD rows where `user_id = auth.uid()`.
- `categories`: everyone can select system categories; users can CRUD own non-system categories.

## Backend Changes Needed

### Settings

Add explicit auth config:

- `AUTH_PROVIDER=supabase`
- `AUTH_REQUIRED=true`
- `AUTH_DEV_BYPASS=false`
- `SUPABASE_URL`
- `SUPABASE_JWT_ISSUER`
- `SUPABASE_JWKS_URL` or equivalent derived URL
- `SUPABASE_AUDIENCE`, if audience validation is needed

Keep local compatibility:

- `DEV_USER_ID` only works when `AUTH_DEV_BYPASS=true` and environment is local/test.

### Auth dependency

Replace current `get_user_id()` behavior with:

- Parse `Authorization: Bearer <token>`.
- Validate JWT signature.
- Validate issuer/audience/expiration.
- Extract `sub`.
- Upsert or fetch `profiles` row.
- Return current user context.

Possible shape:

```python
class CurrentUser(BaseModel):
    id: str
    email: str | None = None
```

Then:

```python
def get_current_user_id(user: CurrentUser = Depends(get_current_user)) -> str:
    return user.id
```

This allows existing endpoints to keep receiving `user_id` with minimal churn.

### Repository hardening

Review all repository methods for cross-user references:

- Creating/updating card must validate account belongs to current user.
- Creating/updating transaction must validate account/card/statement/import file/category references.
- Creating/updating classification rule must validate category is system or user-owned.
- Confirm import must ensure preview item, import batch and resulting transaction are for same user.
- Statement detail/summary must never aggregate another user's transactions.

### Error handling

Add standard responses:

- `401 unauthenticated`: missing, expired or invalid token.
- `403 forbidden`: authenticated but action not allowed.
- `404 not found`: cross-user resource access where existence should not be leaked.

### OpenAPI

Add HTTP Bearer security scheme after implementation.

## Frontend Changes Needed

### Dependencies

Add Supabase client dependency when implementation starts:

- `@supabase/supabase-js`

### Environment

Use existing prepared envs:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### App structure

Add:

- Login page.
- Signup or invite-only accept page, depending on private release needs.
- Logout action.
- Auth/session provider.
- Protected route wrapper for app pages.
- Loading state while restoring session.

### API client

Update `frontend/src/lib/api.ts`:

- Get current Supabase access token before each request.
- Add `Authorization: Bearer <token>`.
- On `401`, redirect to login or signal session expiration.
- Preserve existing API function names and payloads.

### UX decisions

Recommended for private production:

- Start with email/password login or magic link.
- If access should be limited, use invite-only account creation.
- Do not expose multi-tenant/admin UI in Phase 3 unless required.

## Test Plan

### Backend unit/integration tests

Add tests for auth dependency:

- Missing token returns `401`.
- Invalid token returns `401`.
- Expired token returns `401`.
- Valid token returns user ID from `sub`.
- Dev bypass only works in local/test and when explicitly enabled.

Add user isolation tests:

- User A cannot list User B accounts.
- User A cannot fetch/update/delete User B account by ID.
- User A cannot create card using User B account.
- User A cannot create transaction using User B account/card/statement.
- User A cannot read User B import preview.
- User A cannot confirm User B import.
- User A cannot edit User B classification rule.
- User A can read system categories.
- User A cannot mutate system categories unless an admin path is explicitly implemented.

Add repository tests:

- Same test suite should run in PostgreSQL mode.
- Cross-user reference validation should fail before insert/update.
- RLS tests should be added after RLS is enabled.

### Frontend tests

Add tests for:

- Unauthenticated user is redirected to login.
- Authenticated user can access dashboard pages.
- API requests include `Authorization`.
- `401` clears session or redirects.
- Login form validation.
- Logout removes access to protected pages.

### Manual smoke test

For two test users:

1. User A creates account, card, transaction, category and rule.
2. User B logs in and sees none of User A's private data.
3. User B can still see system categories.
4. User B cannot access User A resource IDs by direct URL/API call.
5. User A still sees own data after reload.
6. Import flow works for User A and remains invisible to User B.

## Migration Risks

- Existing JSON/PostgreSQL data is currently owned by `DEV_USER_ID`.
- When real auth starts, old data must either remain attached to the original dev profile or be reassigned to a real Supabase user.
- If RLS is enabled too early, backend jobs/scripts may lose access until service-role behavior is designed.
- Upload files are not physically partitioned by user yet.
- Frontend currently assumes API calls work without token.
- Tests currently rely on `settings.dev_user_id`.
- System categories currently can be updated through the category repository if `user_id is null`; this needs tightening.
- Cross-user reference validation must cover nested flows like import confirmation and statement summaries.
- Supabase JWT validation must handle key rotation and clock skew.

## Data Migration Strategy

Before enabling auth in a real environment:

1. Create the real Supabase user.
2. Decide whether current `DEV_USER_ID` data should be reassigned.
3. If yes, run a controlled SQL migration updating all user-owned tables from `DEV_USER_ID` to the real `auth.users.id`.
4. Also update `profiles.id` carefully, or create the real profile and update foreign keys in dependent tables.
5. Validate counts before and after.
6. Backup before any reassignment.

Tables to reassign together:

- `accounts`
- `cards`
- `card_statements`
- `transactions`
- `classification_rules`
- `import_files`
- `import_batches`
- `import_preview_items`
- User-owned `categories`

Do not reassign system categories where `user_id is null`.

## Implementation Phases

### Phase 3.1 - Auth foundation

- Add auth settings.
- Add Supabase JWT validation dependency.
- Add `CurrentUser` model/context.
- Keep a guarded local/test dev bypass.
- Protect all routes except `/health`.
- Add backend auth tests.

### Phase 3.2 - Frontend auth shell

- Add Supabase client.
- Add login/logout/session provider.
- Protect frontend app routes.
- Attach Bearer token in API client.
- Handle `401`.

### Phase 3.3 - User isolation hardening

- Add cross-user reference validation in backend services/routes.
- Tighten system category mutation behavior.
- Add two-user API tests for all resources.
- Add upload path partitioning for new uploads.

### Phase 3.4 - Data ownership migration

- Create script/checklist to reassign `DEV_USER_ID` data to a real user.
- Validate counts and ownership.
- Keep rollback path.

### Phase 3.5 - RLS preparation

- Draft policies in a migration file.
- Test policies in a disposable database.
- Decide service role behavior for scripts/imports.

### Phase 3.6 - RLS activation

- Enable RLS table by table.
- Run full backend PostgreSQL suite.
- Run two-user smoke test.
- Document production auth checklist.

## Next Implementation Task

Start with Phase 3.1:

- Create backend auth settings and `get_current_user` dependency.
- Add tests for missing/invalid/dev-bypass auth.
- Wire existing endpoints to require authenticated user while preserving their current request/response payloads.

Do not start with frontend login or RLS. The backend user boundary should be reliable first.

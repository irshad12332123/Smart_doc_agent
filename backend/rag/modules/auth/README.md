# Auth module

Routes are mounted at `/auth`:

- `POST /check` with `{ "email": "...", "role": "student" | "faculty", "action": "login" | "register" }`
  Unified eligibility check.
  - For `register`: checks email exists in DB and is not already registered.
  - For `login`: checks email exists in DB and is already registered.
- `POST /register` with `{ "registration_token": "...", "password": "...", "confirm_password": "..." }` or `{ "email": "...", "password": "..." }`
  Registers user via Supabase, sending a confirmation email. Accounts require email confirmation before sign-in.
- `POST /login` with `{ "email": "...", "password": "..." }`
  Authenticates registered and email-confirmed users.
- `POST /resend-confirmation` with `{ "email": "..." }`
  Resends Supabase confirmation email if needed.
- `GET /me` with `Authorization: Bearer <access_token>`
  Returns profile and current authenticated user.

Compatibility endpoints:
- `POST /check-student` with `{ "email": "..." }`
- `POST /check-faculty` with `{ "email": "..." }`

Set `SUPABASE_SERVICE_ROLE_KEY` and a random `AUTH_REGISTRATION_TOKEN_SECRET` on the API server. Never add either to frontend environment variables. Apply `supabase/migrations/20260820000000_auth_registry.sql` before using registration.

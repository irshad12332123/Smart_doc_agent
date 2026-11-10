# Auth module

Routes are mounted at `/auth`:

- `POST /check` with `{ "email": "...", "role": "student" | "faculty", "action": "register" }`
  Checks that an official email exists in the registry and is not already registered,
  then returns a registration token. Login no longer calls this endpoint; `/login`
  performs its own registry check before authenticating.
- `POST /register` with `{ "registration_token": "...", "password": "...", "confirm_password": "..." }` or `{ "email": "...", "password": "..." }`
  Registers user via Supabase, sending a confirmation email. Accounts require email confirmation before sign-in.
- `POST /login` with `{ "email": "...", "password": "..." }`
  Authenticates registered and email-confirmed users. Returns the token session and a
  lightweight `profile_summary` containing only `id`, `full_name`, and `role`.
- `POST /resend-confirmation` with `{ "email": "..." }`
  Resends Supabase confirmation email if needed.
- `GET /me` with `Authorization: Bearer <access_token>`
  Validates the token and returns the current user plus the lightweight profile
  summary used to restore the application shell. Full student/faculty details remain
  behind `GET /u/profile` and are loaded on demand.

Compatibility endpoints:
- `POST /check-student` with `{ "email": "..." }`
- `POST /check-faculty` with `{ "email": "..." }`

Set `SUPABASE_SERVICE_ROLE_KEY` and a random `AUTH_REGISTRATION_TOKEN_SECRET` on the API server. Never add either to frontend environment variables. Apply `supabase/migrations/20260820000000_auth_registry.sql` before using registration.

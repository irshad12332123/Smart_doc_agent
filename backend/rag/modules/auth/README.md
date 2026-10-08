# Auth module

Routes are mounted at `/auth`:

- `POST /check-student` with `{ "student_id": "24031009031" }`
- `POST /check-faculty` with `{ "faculty_id": "..." }`
- `POST /register` with `{ "registration_token": "...", "password": "...", "confirm_password": "..." }`
- `POST /login` with `{ "email": "...", "password": "..." }`
- `GET /me` with `Authorization: Bearer <access_token>`

Set `SUPABASE_SERVICE_ROLE_KEY` and a random `AUTH_REGISTRATION_TOKEN_SECRET` on the API server. Never add either to frontend environment variables. Apply `supabase/migrations/20260820000000_auth_registry.sql` before using registration.

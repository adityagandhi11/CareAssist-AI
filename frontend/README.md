# CareAssist AI frontend

A standalone Angular 19 patient portal and clinic workspace. Includes responsive patient/admin dashboards, appointment requests, patient enquiries, an administrator-managed clinic knowledge base, and an AI care chat with conversation history and source citations.

## Run locally

```bash
npm install
npm start
```

Open `http://localhost:4200`. The Angular dev server proxies `/api` requests to `http://localhost:8000` through `proxy.conf.json`, avoiding local CORS configuration. Set `src/environments/environment.ts` `apiUrl` to another API base (including `/api`) when deploying behind a different host.

## Backend integration

All requests use the `/api` prefix and bearer JWT authentication. Registration sends `{ full_name, email, password }` and returns a user; login sends `{ email, password }` and returns `access_token` plus a user with `id`, `full_name`, `email`, and `role`.

- Appointments: `GET /appointments`, `GET /appointments/available-slots?slot_date=YYYY-MM-DD`, `POST /appointments` with `{ starts_at, ends_at, reason }`. Slot and appointment timestamps are UTC; naive backend timestamps are treated as UTC by the client.
- Enquiries: `GET /enquiries`, `POST /enquiries` with `{ subject, message }`.
- Documents (admin): `GET /documents`, `POST /documents/upload` with the `file` multipart field only (PDF/TXT, max 10 MB), `POST /documents/{id}/process`, and `DELETE /documents/{id}`.
- Chat: `GET|POST /chat/conversations` (create with `{ title }`), `GET|POST /chat/conversations/{id}/messages` (ask with `{ question }`), and `DELETE /chat/conversations/{id}`. Message responses include `content`, `sources` (citation strings), and timestamps.

Collections are returned as arrays. The API limits conversation questions to 4,000 characters and appointment reasons to 500 characters.

## Validate

```bash
npm run build
npm test -- --watch=false
```

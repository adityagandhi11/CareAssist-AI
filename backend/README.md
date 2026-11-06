# CareAssist AI backend

FastAPI REST API with SQLite persistence, patient/admin roles, appointment and enquiry management, and optional document-grounded AI chat.

## Setup

Requires Python 3.10 or newer. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set a long, unique `SECRET_KEY` and `GROQ_API_KEY` in `.env`. The configured chat model is `openai/gpt-oss-120b` on Groq; the default OpenAI-compatible endpoint is `https://api.groq.com/openai/v1`. Override these with `GROQ_MODEL` or `GROQ_BASE_URL` if needed. Install the optional AI packages with `python -m pip install -r requirements-ai.txt` to enable document indexing and document-grounded chat. Chroma uses its built-in local embedding model, so indexing does not require a separate embeddings API key. AI features return an explicit HTTP 503 error when required configuration or optional packages are unavailable instead of preventing the core API from starting.

```powershell
python seed.py
uvicorn app.main:app --reload
```

The local seeded administrator credentials are:

- Email: `admin@careassist.local`
- Password: `CareAssistAdmin123!`

Synthetic patient accounts all use `PatientDemo123!`:

- `demo.avery@careassist.local`
- `demo.jordan@careassist.local`
- `demo.sam@careassist.local`

`python seed.py` creates the administrator and synthetic patients, appointments, enquiries, and pending clinic documents. It is safe to rerun: seeded items are not duplicated. It resets the local demo credentials to the values above. Change demo credentials and the signing key before any non-local deployment.

Interactive API documentation is available at `http://127.0.0.1:8000/docs`; health check: `/health`.

## Main API

All routes except `/health` use the `/api` prefix. Register patients with `POST /api/auth/register`, authenticate using `POST /api/auth/login` (JSON `{ "email": "...", "password": "..." }`), then send the returned bearer token as `Authorization: Bearer <token>`.

- `/api/patients`: administrator patient listing and deactivation
- `/api/appointments`: patient-owned CRUD/cancellation; administrators can manage all records and statuses. Overlapping pending/approved slots are rejected with 409.
- `/api/enquiries`: patient-owned submissions and reads; admin update/list; deterministic local category classification requires no AI key.
- `/api/documents`: admin-only PDF/TXT upload and indexing. Indexing uses Chroma's local embedding model and persistent ChromaDB; reprocess documents previously indexed with another embedding model to make them available in the local-embedding collection.
- `/api/chat`: patient-owned conversation history; grounded answers cite document filenames. The assistant does not provide medical advice or emergency triage.
- `/api/dashboard`: role-specific counts calculated from current database records

Uploaded file payloads are size-limited by `MAX_UPLOAD_SIZE_MB`. Configure CORS with comma-separated origins in `CORS_ORIGINS`. Clinic availability uses `CLINIC_TIMEZONE` (IANA zone), `CLINIC_OPEN_TIME`, `CLINIC_CLOSE_TIME`, `CLINIC_WORKING_DAYS` (weekday numbers, Monday=0), and `APPOINTMENT_DURATION_MINUTES`. `GET /api/appointments/available-slots?slot_date=YYYY-MM-DD` lists unbooked future slots in UTC. Enquiry AI analysis uses validated structured output when configured and falls back to local classification, summary, and a staff-reviewable suggested response; new enquiries remain pending staff review. Admins can approve/reject with `PATCH /api/enquiries/{id}`. `GET /api/documents/{id}/summary` returns an AI summary when configured or a local extractive summary, with source pages. Identical uploaded files are rejected; reprocessing replaces that document's indexed chunks. PDF chunks and RAG citations retain page numbers. The default SQLite database and document/vector storage are under `backend/`.

## Development and tests

```powershell
python -m pytest
```

Tests use an isolated in-memory SQLite database. Never put real patient records or sensitive health information in this demonstration system.

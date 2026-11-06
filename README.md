# CareAssist AI

CareAssist AI is a local clinic-management demonstration with separate Angular and FastAPI applications. It uses synthetic sample data only and is not a medical service. Do not enter real patient information.

## Requirements

- Python 3.11 or later
- Node.js and npm
- A Groq API key for live LLM-backed chat, classification, and summarization

## Backend

From the project root in PowerShell:

```powershell
Set-Location backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend\.env` for local settings. Never commit secrets or real patient information. Initialize the local database and synthetic demonstration accounts, then start the API:

```powershell
python seed.py
python -m uvicorn app.main:app --reload
```

The API is available at [http://localhost:8000](http://localhost:8000), and the Swagger UI is at [http://localhost:8000/docs](http://localhost:8000/docs).

Local demonstration administrator:

- Email: `admin@careassist.local`
- Password: `CareAssistAdmin123!`

Synthetic patient accounts (all use the same local demo password):

- `demo.avery@careassist.local`
- `demo.jordan@careassist.local`
- `demo.sam@careassist.local`
- Password: `PatientDemo123!`

Running `python seed.py` again safely adds any missing demo records without duplicating seeded patients, appointments, enquiries, or clinic documents. Change demo passwords before using the application beyond a local demonstration.

## Frontend

In a second PowerShell terminal, from the project root:

```powershell
Set-Location frontend
npm install
npm start
```

The Angular application is available at [http://localhost:4200](http://localhost:4200). The API URL and any frontend-specific environment configuration are documented in [frontend/README.md](./frontend/README.md).

## Sample clinic documents

The fictional, synthetic clinic materials in [sample_data/](./sample_data/) are added to the administrator's document list as pending when you run the seed script. Configure `GROQ_API_KEY` in `backend\.env` and install the optional AI dependencies, then process these documents from the document-management page to index them for RAG. The application uses Groq's `openai/gpt-oss-120b` model for LLM-backed features and Chroma's built-in local embedding model for document indexing. The assistant answers only from processed clinic documents and does not provide medical advice.

## Tests

Run backend tests from the project root after installing backend dependencies:

```powershell
python -m pytest backend\tests
```

Run frontend checks from `frontend\` using the scripts declared in `package.json`.

## Privacy and safety

This project is a software demonstration, not a HIPAA-compliant or clinical system. Use synthetic data only. The AI assistant is limited to administrative clinic information, does not diagnose or recommend treatment, and directs medical concerns to qualified professionals.
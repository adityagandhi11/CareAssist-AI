from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import initialize_database
from app.routers import appointments, auth, chat, dashboard, documents, enquiries, patients


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title=settings.app_name,
    description="CareAssist AI clinic administration and document-grounded patient assistant API.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for api_router in (auth.router, patients.router, appointments.router, enquiries.router, documents.router, chat.router, dashboard.router):
    app.include_router(api_router, prefix="/api")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": settings.app_name}

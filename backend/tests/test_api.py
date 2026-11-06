from datetime import datetime, timedelta, timezone
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.config import settings
from app.main import app
from app.models import Appointment, Enquiry, KnowledgeDocument, User
from app.security import hash_password


@pytest.fixture()
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.state.test_session_factory = TestSession
    with TestSession() as db:
        db.add(
            User(
                email="admin@careassist.local",
                full_name="Test Admin",
                password_hash=hash_password("CareAssistAdmin123!"),
                role="admin",
            )
        )
        db.commit()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    del app.state.test_session_factory
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def register(client: TestClient, email: str = "patient@example.com") -> dict:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "full_name": "Test Patient", "password": "patient-password-1"},
    )
    assert response.status_code == 201
    token = client.post(
        "/api/auth/login",
        json={"email": email, "password": "patient-password-1"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_registration_login_and_role_protection(client: TestClient):
    headers = register(client)
    assert client.get("/api/auth/me", headers=headers).json()["role"] == "patient"
    assert client.get("/api/patients", headers=headers).status_code == 403
    assert client.post(
        "/api/auth/register",
        json={"email": "patient@example.com", "full_name": "Duplicate", "password": "patient-password-1"},
    ).status_code == 409


def test_appointment_conflict_and_patient_ownership(client: TestClient):
    patient_headers = register(client)
    other_headers = register(client, "other@example.com")
    appointment_date = datetime.now(timezone.utc).date() + timedelta(days=2)
    while appointment_date.weekday() > 4:
        appointment_date += timedelta(days=1)
    start = datetime.combine(appointment_date, datetime.min.time()).replace(hour=10)
    payload = {
        "starts_at": start.isoformat(),
        "ends_at": (start + timedelta(minutes=30)).isoformat(),
        "reason": "Checkup",
    }
    created = client.post("/api/appointments", json=payload, headers=patient_headers)
    assert created.status_code == 201
    assert client.post("/api/appointments", json=payload, headers=other_headers).status_code == 409
    assert client.get(f"/api/appointments/{created.json()['id']}", headers=other_headers).status_code == 404
    assert client.delete(f"/api/appointments/{created.json()['id']}", headers=patient_headers).status_code == 204
    assert client.post("/api/appointments", json=payload, headers=other_headers).status_code == 201


def test_enquiry_fallback_patient_scope_and_dashboard(client: TestClient):
    patient_headers = register(client)
    enquiry = client.post(
        "/api/enquiries",
        json={"subject": "Reschedule appointment", "message": "I need to change my appointment."},
        headers=patient_headers,
    )
    assert enquiry.status_code == 201
    assert enquiry.json()["category"] == "appointment"
    assert enquiry.json()["summary"].startswith("Reschedule appointment.")
    assert enquiry.json()["intent"] == "appointment"
    assert enquiry.json()["suggested_response"]
    assert enquiry.json()["review_status"] == "pending"
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@careassist.local", "password": "CareAssistAdmin123!"},
    )
    assert admin_login.status_code == 200, admin_login.text
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    stats = client.get("/api/dashboard", headers=admin_headers).json()
    assert stats["patients_total"] == 1
    assert stats["enquiries_open"] == 1
    approved = client.patch(
        f"/api/enquiries/{enquiry.json()['id']}",
        headers=admin_headers,
        json={"review_status": "approved"},
    )
    assert approved.status_code == 200
    assert approved.json()["review_status"] == "approved"


def test_enquiry_structured_ai_fields_are_validated_with_local_fallback(monkeypatch: pytest.MonkeyPatch):
    from app.services.classification import analyze_enquiry

    responses = [
        {
            "category": "services",
            "intent": "service inquiry",
            "summary": "Asks about wellness visits.",
            "suggested_response": "Staff can confirm service availability.",
        },
        {
            "category": "unsafe-unrecognized-category",
            "intent": "x",
            "summary": "",
            "suggested_response": "",
        },
    ]

    class FakeModel:
        def with_structured_output(self, schema):
            return self

        def invoke(self, prompt):
            return responses.pop(0)

    options = []
    fake_openai = types.ModuleType("langchain_openai")

    def fake_chat_openai(**kwargs):
        options.append(kwargs)
        return FakeModel()

    fake_openai.ChatOpenAI = fake_chat_openai
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_openai)
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    assert analyze_enquiry("Service question", "Are wellness visits offered?").category == "services"
    assert options[0]["model"] == "openai/gpt-oss-120b"
    assert options[0]["base_url"] == "https://api.groq.com/openai/v1"
    fallback = analyze_enquiry("Reschedule appointment", "Please change my booking.")
    assert fallback.category == "appointment"
    assert fallback.suggested_response


def test_ai_unavailable_is_explicit_and_conversation_remains_owned(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "groq_api_key", None)
    headers = register(client)
    conversation = client.post("/api/chat/conversations", json={}, headers=headers)
    assert conversation.status_code == 201
    response = client.post(
        f"/api/chat/conversations/{conversation.json()['id']}/messages",
        json={"question": "What services are available?"},
        headers=headers,
    )
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()
    other_headers = register(client, "other@example.com")
    assert client.get(
        f"/api/chat/conversations/{conversation.json()['id']}/messages",
        headers=other_headers,
    ).status_code == 404


def test_admin_document_upload_and_local_indexing_without_groq_key(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    from app.services import documents as document_service

    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(document_service, "_local_embeddings", lambda: object())
    test_upload_dir = Path(__file__).parent / "upload_test_data"
    monkeypatch.setattr(settings, "upload_directory", str(test_upload_dir))
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@careassist.local", "password": "CareAssistAdmin123!"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    patient_headers = register(client)
    try:
        rejected = client.post(
            "/api/documents/upload",
            headers=patient_headers,
            files={"file": ("notes.txt", b"Clinic sample", "text/plain")},
        )
        assert rejected.status_code == 403
        uploaded = client.post(
            "/api/documents/upload",
            headers=admin_headers,
            files={"file": ("clinic.txt", b"Clinic hours are Monday to Friday.", "text/plain")},
        )
        assert uploaded.status_code == 201
        document_id = uploaded.json()["id"]
        fake_chroma = types.ModuleType("langchain_chroma")
        fake_core = types.ModuleType("langchain_core.documents")

        class FakeChroma:
            def __init__(self, **kwargs):
                pass

            def delete(self, where):
                pass

            def add_documents(self, docs, ids):
                pass

        fake_chroma.Chroma = FakeChroma
        fake_core.Document = lambda **kwargs: SimpleNamespace(**kwargs)
        monkeypatch.setitem(sys.modules, "langchain_chroma", fake_chroma)
        monkeypatch.setitem(sys.modules, "langchain_core.documents", fake_core)
        processed = client.post(f"/api/documents/{document_id}/process", headers=admin_headers)
        assert processed.status_code == 200
        assert client.get("/api/documents", headers=admin_headers).json()[0]["status"] == "processed"
        summary = client.get(f"/api/documents/{document_id}/summary", headers=admin_headers)
        assert summary.status_code == 200
        assert "Clinic hours" in summary.json()["summary"]
        assert summary.json()["source_pages"] == [1]
        duplicate = client.post(
            "/api/documents/upload",
            headers=admin_headers,
            files={"file": ("duplicate.txt", b"Clinic hours are Monday to Friday.", "text/plain")},
        )
        assert duplicate.status_code == 409
    finally:
        for path in test_upload_dir.glob("*"):
            path.unlink()
        test_upload_dir.rmdir()


def test_available_slots_use_configured_hours_and_busy_appointments(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    from app.config import settings

    headers = register(client)
    target_date = datetime.now(timezone.utc).date() + timedelta(days=2)
    while target_date.weekday() > 4:
        target_date += timedelta(days=1)
    monkeypatch.setattr(settings, "clinic_timezone", "UTC")
    monkeypatch.setattr(settings, "clinic_open_time", "09:00")
    monkeypatch.setattr(settings, "clinic_close_time", "10:30")
    monkeypatch.setattr(settings, "clinic_working_days", "0,1,2,3,4")
    monkeypatch.setattr(settings, "appointment_duration_minutes", 30)

    start = datetime.combine(target_date, datetime.min.time()).replace(hour=9, minute=30)
    booked = client.post(
        "/api/appointments",
        headers=headers,
        json={
            "starts_at": start.isoformat(),
            "ends_at": (start + timedelta(minutes=30)).isoformat(),
            "reason": "Clinic visit",
        },
    )
    assert booked.status_code == 201
    slots = client.get(f"/api/appointments/available-slots?slot_date={target_date.isoformat()}", headers=headers)
    assert slots.status_code == 200
    assert [slot["starts_at"][11:16] for slot in slots.json()] == ["09:00", "10:00"]
    outside_hours = client.post(
        "/api/appointments",
        headers=headers,
        json={
            "starts_at": datetime.combine(target_date, datetime.min.time()).replace(hour=8).isoformat(),
            "ends_at": datetime.combine(target_date, datetime.min.time()).replace(hour=8, minute=30).isoformat(),
            "reason": "Outside clinic hours",
        },
    )
    assert outside_hours.status_code == 422
    assert client.get(
        f"/api/appointments/available-slots?slot_date={(target_date + timedelta(days=5)).isoformat()}",
        headers=headers,
    ).json() == []


def test_chat_passes_previous_turns_to_answerer(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    from app.routers import chat

    headers = register(client)
    conversation = client.post("/api/chat/conversations", json={}, headers=headers).json()
    received_history = []

    def fake_answer(question, history=None):
        received_history.append((question, history))
        return f"Answer to {question}", []

    monkeypatch.setattr(chat, "answer_question", fake_answer)
    for question in ("First question?", "Follow-up question?"):
        result = client.post(
            f"/api/chat/conversations/{conversation['id']}/messages",
            headers=headers,
            json={"question": question},
        )
        assert result.status_code == 201
    assert received_history[1] == (
        "Follow-up question?",
        [("user", "First question?"), ("assistant", "Answer to First question?")],
    )


def test_document_pdf_pages_and_reprocess_replace_chunks(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    import pypdf
    from app.services import documents as document_service
    from app.services.documents import process_document

    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@careassist.local", "password": "CareAssistAdmin123!"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    test_upload_dir = Path(__file__).parent / "pdf_test_data"
    monkeypatch.setattr(settings, "upload_directory", str(test_upload_dir))
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(document_service, "_local_embeddings", lambda: object())
    monkeypatch.setattr(
        pypdf,
        "PdfReader",
        lambda _: SimpleNamespace(
            pages=[
                SimpleNamespace(extract_text=lambda: "First page has clinic details."),
                SimpleNamespace(extract_text=lambda: ""),
                SimpleNamespace(extract_text=lambda: "Third page has hours."),
            ]
        ),
    )
    uploaded = client.post(
        "/api/documents/upload",
        headers=admin_headers,
        files={"file": ("pages.pdf", b"fake pdf bytes", "application/pdf")},
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["page_count"] == 3

    with app.state.test_session_factory() as db:
        from app.models import KnowledgeDocument

        document = db.get(KnowledgeDocument, uploaded.json()["id"])
        assert json.loads(document.page_contents) == [
            "First page has clinic details.",
            "",
            "Third page has hours.",
        ]
        summary = client.get(f"/api/documents/{document.id}/summary", headers=admin_headers).json()
        assert summary["source_pages"] == [1, 3]

        deleted, added = [], []

        class FakeChroma:
            def __init__(self, **kwargs):
                pass

            def delete(self, where):
                deleted.append(where)

            def add_documents(self, docs, ids):
                added.append(ids)

        fake_chroma = types.ModuleType("langchain_chroma")
        fake_chroma.Chroma = FakeChroma
        fake_core = types.ModuleType("langchain_core.documents")
        fake_core.Document = lambda **kwargs: SimpleNamespace(**kwargs)
        monkeypatch.setitem(sys.modules, "langchain_chroma", fake_chroma)
        monkeypatch.setitem(sys.modules, "langchain_core.documents", fake_core)
        assert process_document(document) == 2
        assert process_document(document) == 2
        assert deleted == [{"document_id": document.id}, {"document_id": document.id}]
        assert added[0] == added[1] == [f"{document.id}-p1-c0", f"{document.id}-p3-c0"]

    try:
        for path in test_upload_dir.glob("*"):
            path.unlink()
        test_upload_dir.rmdir()
    except FileNotFoundError:
        pass


def test_demo_seed_populates_synthetic_data_once(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    from seed import DEMO_PATIENT_PASSWORD, seed_demo_data

    monkeypatch.setattr(settings, "upload_directory", str(tmp_path))
    with app.state.test_session_factory() as db:
        admin = db.scalar(select(User).where(User.email == "admin@careassist.local"))
        assert admin is not None
        seed_demo_data(db, admin)
        db.commit()
        initial_counts = (
            db.scalar(select(func.count(User.id)).where(User.role == "patient")),
            db.scalar(select(func.count(Appointment.id))),
            db.scalar(select(func.count(Enquiry.id))),
            db.scalar(select(func.count(KnowledgeDocument.id))),
        )

        seed_demo_data(db, admin)
        db.commit()
        repeated_counts = (
            db.scalar(select(func.count(User.id)).where(User.role == "patient")),
            db.scalar(select(func.count(Appointment.id))),
            db.scalar(select(func.count(Enquiry.id))),
            db.scalar(select(func.count(KnowledgeDocument.id))),
        )

    assert initial_counts == repeated_counts == (3, 4, 4, 3)
    assert DEMO_PATIENT_PASSWORD == "PatientDemo123!"

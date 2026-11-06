import hashlib
import json
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KnowledgeDocument, User


_DOCUMENT_COLLECTION = "careassist_docs_local"


def _local_embeddings():
    try:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        from langchain_core.embeddings import Embeddings
    except ImportError as exc:
        raise RuntimeError(
            "AI processing is unavailable: install the optional LangChain/Chroma dependencies"
        ) from exc

    class LocalChromaEmbeddings(Embeddings):
        def __init__(self):
            self.embedding_function = DefaultEmbeddingFunction()

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return self.embedding_function(texts)

        def embed_query(self, text: str) -> list[float]:
            return self.embedding_function([text])[0]

    return LocalChromaEmbeddings()


async def upload_document(file: UploadFile, admin: User, db: Session) -> KnowledgeDocument:
    suffix = Path(file.filename or "").suffix.casefold()
    if suffix not in {".txt", ".pdf"}:
        raise HTTPException(status_code=415, detail="Only PDF and TXT documents are supported")
    data = await file.read(settings.max_upload_size_mb * 1024 * 1024 + 1)
    if not data:
        raise HTTPException(status_code=422, detail="Uploaded document is empty")
    if len(data) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_size_mb} MB limit")

    original_name = Path(file.filename or "document").name
    content_hash = hashlib.sha256(data).hexdigest()
    if db.scalar(select(KnowledgeDocument.id).where(KnowledgeDocument.content_hash == content_hash)):
        raise HTTPException(status_code=409, detail="This document has already been uploaded")
    try:
        if suffix == ".txt":
            page_contents = [data.decode("utf-8-sig").strip()]
        else:
            from pypdf import PdfReader

            import io

            reader = PdfReader(io.BytesIO(data))
            page_contents = [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not read uploaded document: {exc}") from exc
    page_contents = [text for text in page_contents if text] if suffix == ".txt" else page_contents
    content = "\n\n".join(text for text in page_contents if text)
    if not content:
        raise HTTPException(status_code=422, detail="No readable text found in the document")

    upload_dir = Path(settings.upload_directory)
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / f"{uuid.uuid4().hex}{suffix}"
    target.write_bytes(data)
    document = KnowledgeDocument(
        filename=original_name,
        storage_path=str(target),
        content=content,
        content_hash=content_hash,
        page_contents=json.dumps(page_contents),
        page_count=len(page_contents),
        status="pending",
        uploaded_by=admin.id,
    )
    db.add(document)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        target.unlink(missing_ok=True)
        if db.scalar(select(KnowledgeDocument.id).where(KnowledgeDocument.content_hash == content_hash)):
            raise HTTPException(status_code=409, detail="This document has already been uploaded") from exc
        raise
    db.refresh(document)
    return document


def _chunks(text: str, size: int = 1200, overlap: int = 200) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        chunk = " ".join(words[start : start + size])
        if chunk:
            chunks.append(chunk)
        start += max(1, size - overlap)
    return chunks


def process_document(document: KnowledgeDocument) -> int:
    try:
        from langchain_chroma import Chroma
        from langchain_core.documents import Document
    except ImportError as exc:
        raise RuntimeError("AI processing is unavailable: install the optional LangChain/Chroma dependencies") from exc

    pages = json.loads(document.page_contents or "[]") or [document.content]
    chunks = [
        (page_number, chunk_number, piece)
        for page_number, text in enumerate(pages, start=1)
        for chunk_number, piece in enumerate(_chunks(text))
    ]
    if not chunks:
        raise RuntimeError("Document contains no indexable text")
    vectorstore = Chroma(
        collection_name=_DOCUMENT_COLLECTION,
        persist_directory=settings.chroma_persist_directory,
        embedding_function=_local_embeddings(),
    )
    vectorstore.delete(where={"document_id": document.id})
    vectorstore.add_documents(
        [
            Document(
                page_content=piece,
                metadata={
                    "source": document.filename,
                    "document_id": document.id,
                    "page": page_number,
                    "chunk": chunk_number,
                },
            )
            for page_number, chunk_number, piece in chunks
        ],
        ids=[f"{document.id}-p{page_number}-c{chunk_number}" for page_number, chunk_number, _ in chunks],
    )
    return len(chunks)


def delete_document_vectors(document_id: int) -> None:
    try:
        from langchain_chroma import Chroma
    except ImportError as exc:
        raise RuntimeError("Cannot remove indexed document: install the optional LangChain/Chroma dependencies") from exc
    vectorstore = Chroma(
        collection_name=_DOCUMENT_COLLECTION,
        persist_directory=settings.chroma_persist_directory,
        embedding_function=_local_embeddings(),
    )
    vectorstore.delete(where={"document_id": document_id})


def answer_question(
    question: str,
    history: list[tuple[str, str]] | None = None,
) -> tuple[str, list[str]]:
    if not settings.groq_api_key:
        raise RuntimeError("AI assistant is unavailable: GROQ_API_KEY is not configured")
    try:
        from langchain_chroma import Chroma
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError("AI assistant is unavailable: install the optional LangChain/Chroma dependencies") from exc

    vectorstore = Chroma(
        collection_name=_DOCUMENT_COLLECTION,
        persist_directory=settings.chroma_persist_directory,
    )
    matches = vectorstore.similarity_search_with_relevance_scores(question, k=4)
    relevant = [(doc, score) for doc, score in matches if score >= 0.15]
    if not relevant:
        return (
            "I couldn't find this information in the clinic documents. Please contact clinic staff. "
            "I can't provide medical advice or emergency triage.",
            [],
        )
    sources = list(
        dict.fromkeys(
            f"{doc.metadata.get('source', 'Clinic document')} (page {doc.metadata['page']})"
            if doc.metadata.get("page")
            else str(doc.metadata.get("source", "Clinic document"))
            for doc, _ in relevant
        )
    )
    excerpts = "\n\n".join(
        "[{}{}]\n{}".format(
            doc.metadata.get("source", "Clinic document"),
            f", page {doc.metadata['page']}" if doc.metadata.get("page") else "",
            doc.page_content,
        )
        for doc, _ in relevant
    )
    system_prompt = (
        "You are a clinic's administrative information assistant, not a medical professional. "
        "Answer only from the provided clinic document excerpts. Do not diagnose, recommend treatment, "
        "or perform emergency triage. If the excerpts do not answer the question, say so and direct the "
        "patient to clinic staff. Cite each factual claim using the exact bracketed document filename and "
        "page when supplied, for example [clinic_information.txt, page 1]. Do not invent citations.\n\n"
        f"Clinic document excerpts:\n{excerpts}"
    )
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    messages = [SystemMessage(content=system_prompt)]
    for role, content in (history or [])[-12:]:
        if role == "user":
            messages.append(HumanMessage(content=content[:4000]))
        elif role == "assistant":
            messages.append(AIMessage(content=content[:6000]))
    messages.append(HumanMessage(content=question))
    response = ChatOpenAI(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
        temperature=0,
    ).invoke(messages)
    answer = str(response.content).strip()
    if not answer:
        raise RuntimeError("AI assistant returned an empty response")
    return answer, sources


def summarize_document(document: KnowledgeDocument) -> tuple[str, list[int]]:
    pages = json.loads(document.page_contents or "[]") or [document.content]
    selected = []
    for page_number, page in enumerate(pages, start=1):
        sentences = [sentence.strip() for sentence in page.replace("\n", " ").split(".") if sentence.strip()]
        if sentences:
            selected.append((page_number, ". ".join(sentences[:2])[:500]))
    if not selected:
        return "No readable text is available to summarize.", []
    fallback = " ".join(text.rstrip(".") + "." for _, text in selected[:8])[:1600]
    if not settings.groq_api_key:
        return fallback, [page for page, _ in selected]
    try:
        from langchain_openai import ChatOpenAI

        pages_text = "\n\n".join(f"[Page {page}]\n{text}" for page, text in selected[:20])
        response = ChatOpenAI(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            temperature=0,
        ).invoke(
            "Summarize this clinic document faithfully and concisely. Use only its content, include no "
            "medical advice, and do not invent facts. Cite page numbers as [Page N].\n\n"
            f"Document: {document.filename}\n{pages_text}"
        )
        summary = str(response.content).strip()
        if summary:
            return summary[:4000], [page for page, _ in selected]
    except Exception:
        pass
    return fallback, [page for page, _ in selected]

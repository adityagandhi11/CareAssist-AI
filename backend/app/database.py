from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database() -> None:
    """Create tables and add fields introduced after the initial SQLite MVP."""
    additions = {
        "enquiries": {
            "summary": "TEXT NOT NULL DEFAULT ''",
            "intent": "VARCHAR(60) NOT NULL DEFAULT 'general'",
            "suggested_response": "TEXT NOT NULL DEFAULT ''",
            "review_status": "VARCHAR(20) NOT NULL DEFAULT 'pending'",
        },
        "knowledge_documents": {
            "content_hash": "VARCHAR(64)",
            "page_contents": "TEXT NOT NULL DEFAULT '[]'",
            "page_count": "INTEGER NOT NULL DEFAULT 1",
        },
    }
    existing_tables = set(inspect(engine).get_table_names())
    with engine.begin() as connection:
        for table_name, columns in additions.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspect(engine).get_columns(table_name)}
            for name, declaration in columns.items():
                if name not in existing_columns:
                    connection.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{name}" {declaration}'))
    Base.metadata.create_all(bind=engine)

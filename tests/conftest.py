import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture(autouse=True)
def isolated_chroma(tmp_path, monkeypatch):
    """Every test gets its own on-disk Chroma store so learned-pattern
    state never leaks between tests (or across previous local runs)."""
    from app.tier2 import embeddings

    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma_data"))
    embeddings._client.cache_clear()
    yield
    embeddings._client.cache_clear()


@pytest.fixture()
def db_session(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    session = testing_session_local()
    yield session
    session.close()
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture()
def client(db_session):
    return TestClient(app)

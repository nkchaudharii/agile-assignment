import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import create_app
from app.services.document_service import (
    ChromaVectorStore,
    build_chunks,
    embed_text,
    embed_texts,
    initialize_document_index,
    reset_index,
    search_documents,
)


def _admin_headers() -> dict[str, str]:
    token = create_access_token({"sub": "test-user", "role": "Admin"})
    return {"Authorization": f"Bearer {token}"}


def _settings(tmp_path: Path):
    from app.core.config import Settings

    return Settings(
        document_storage_path=str(tmp_path / "documents"),
        chroma_db_path=str(tmp_path / "chroma"),
        chroma_collection_name="company-documents-test",
    )


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr("app.services.document_service.get_settings", lambda: settings)
    reset_index(settings)
    yield settings
    reset_index(settings)


def test_initial_document_is_indexed_from_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr("app.services.document_service.get_settings", lambda: settings)
    storage = Path(settings.document_storage_path)
    storage.mkdir(parents=True)
    (storage / "company.txt").write_text("Acme builds clinical AI tools for hospitals.", encoding="utf-8")

    indexed = initialize_document_index()

    assert indexed == "company.txt"
    results = search_documents("clinical hospitals", top_k=1)
    assert len(results) == 1
    assert "clinical AI tools" in results[0].text


def test_replacement_refreshes_future_query_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr("app.services.document_service.get_settings", lambda: settings)
    client = TestClient(create_app(settings))

    first_response = client.put(
        "/documents",
        files={"file": ("company.txt", io.BytesIO(b"Acme builds clinical AI tools for hospitals."), "text/plain")},
        headers=_admin_headers(),
    )
    assert first_response.status_code == 200
    first_query = client.post("/query", json={"query": "clinical hospitals"})
    assert first_query.status_code == 200
    assert "clinical AI tools" in first_query.json()["answer"]

    second_response = client.put(
        "/documents",
        files={
            "file": (
                "company.txt",
                io.BytesIO(b"Acme now provides logistics optimization for delivery fleets."),
                "text/plain",
            )
        },
        headers=_admin_headers(),
    )
    assert second_response.status_code == 200

    second_query = client.post("/query", json={"query": "delivery logistics"})
    assert second_query.status_code == 200
    assert "logistics optimization" in second_query.json()["answer"]
    assert "clinical AI tools" not in second_query.json()["answer"]


def test_invalid_replacement_preserves_current_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr("app.services.document_service.get_settings", lambda: settings)
    client = TestClient(create_app(settings))
    headers = _admin_headers()

    response = client.put(
        "/documents",
        files={"file": ("company.txt", io.BytesIO(b"Acme builds healthcare software."), "text/plain")},
        headers=headers,
    )
    assert response.status_code == 200

    invalid_response = client.put(
        "/documents",
        files={"file": ("company.txt", io.BytesIO(b"   "), "text/plain")},
        headers=headers,
    )
    assert invalid_response.status_code == 422
    assert invalid_response.json()["detail"] == "Uploaded file is empty"

    query_response = client.post("/query", json={"query": "healthcare software"})
    assert query_response.status_code == 200
    assert "healthcare software" in query_response.json()["answer"]


def test_chroma_vector_store_persists_embeddings(tmp_path: Path) -> None:
    store_path = tmp_path / "persistent-chroma"
    chunks = build_chunks("company.txt", "Acme builds durable analytics software.")
    vectors = embed_texts([chunk.text for chunk in chunks])

    ChromaVectorStore(str(store_path), "company-documents-test").replace(chunks, vectors)
    restored_store = ChromaVectorStore(str(store_path), "company-documents-test")

    results = restored_store.search(embed_text("analytics software"), top_k=1)
    assert len(results) == 1
    assert "durable analytics software" in results[0].text


def test_query_without_loaded_document_returns_400() -> None:
    from app.core.config import get_settings

    client = TestClient(create_app(get_settings()))

    response = client.post("/query", json={"query": "What does the company do?"})

    assert response.status_code == 400
    assert response.json()["detail"] == "No company document loaded"

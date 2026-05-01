# API Foundation

This FastAPI app is a foundation only. It defines the project shape and placeholder contracts for a future backend similar in spirit to `agile-rag`, without implementing any feature pipeline.

## Included

- application entrypoint
- settings
- health route
- placeholder voice endpoint
- document replacement, indexing, and retrieval-backed query endpoints
- typed schemas
- provider interface stubs
- tests for startup, health, auth, document replacement, and retrieval

## Not Included

- LLM providers
- speech pipelines
- background jobs

## API Endpoints

### `PUT /documents` - Replace company document

Replaces the document used by the API with a newly uploaded file. The new document is parsed, chunked, embedded, stored in Chroma, and then stored as the single active company document. Invalid replacements do not overwrite the existing document or active index.

**Authentication:** Bearer token with `Admin` role required.
- No token → `401 Unauthorized`
- Valid token but non-admin role → `403 Forbidden`

**Accepted formats:** `.pdf`, `.docx`, `.txt`

**Constraints:** Maximum file size 10 MB; file must not be empty.

**Success response `200`:**
```json
{ "accepted": true, "filename": "handbook.pdf", "message": "Document 'handbook.pdf' replaced successfully" }
```

**Error responses:** `401`, `403`, `422` (unsupported format / empty file / oversized file)

### `POST /query` - Query indexed company document

Returns the highest-ranked chunks from the active company document.

**Request:**
```json
{ "query": "What does the company do?", "top_k": 5 }
```

**Success response `200`:**
```json
{ "answer": "...", "sources": ["company.txt#0"] }
```

**Error responses:** `400` (no loaded document / empty query)

## Vector Store

The API uses Chroma through a local `PersistentClient`. Configure the database path and collection name with:

```bash
CHROMA_DB_PATH=data/chroma
CHROMA_COLLECTION_NAME=company-documents
```

## Commands

```bash
python -m uv sync
python -m uv run uvicorn app.main:app --reload
python -m uv run pytest
```

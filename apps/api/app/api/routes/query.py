from fastapi import APIRouter, HTTPException, status

from app.schemas.query import QueryRequest, QueryResponse
from app.services.document_service import search_documents

router = APIRouter(tags=["query"])


@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
)
def run_query(request: QueryRequest) -> QueryResponse:
    try:
        results = search_documents(request.query, top_k=request.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return QueryResponse(
        answer="\n\n".join(result.text for result in results),
        sources=[
            f"{result.metadata.get('source_name', 'document')}#{result.metadata.get('chunk_index', 0)}"
            for result in results
        ],
    )

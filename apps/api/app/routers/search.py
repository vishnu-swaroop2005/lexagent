from fastapi import APIRouter, Depends

from app.deps import get_current_user, CurrentUser
from app.models.schemas import SemanticSearchRequest, SemanticSearchResult
from app.services.embeddings import EmbeddingService

router = APIRouter()


@router.post("/clauses")
async def search_clauses(
    request: SemanticSearchRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Semantic search across all clauses in the organization's contracts."""
    service = EmbeddingService()
    results = await service.semantic_search(
        query=request.query,
        org_id=user.org_id,
        threshold=request.threshold,
        limit=request.limit,
    )
    return {"results": results}


@router.post("/similar")
async def find_similar(
    clause_id: str,
    limit: int = 10,
    user: CurrentUser = Depends(get_current_user),
):
    """Find clauses similar to a given clause."""
    service = EmbeddingService()
    results = await service.find_similar(
        clause_id=clause_id,
        org_id=user.org_id,
        limit=limit,
    )
    return {"results": results}
